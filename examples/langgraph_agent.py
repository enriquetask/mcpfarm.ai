"""LangGraph ReAct agent that discovers and calls MCPFarm.ai tools.

Usage:
    uv run python langgraph_agent.py "Add 5 and 3, then echo the result"

Requires:
    - MCPFarm gateway running (docker compose up)
    - API key created via bootstrap or UI
    - .env file with MCPFARM_API_KEY and LLM API key
"""

from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

import os

from langchain_core.messages import HumanMessage
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from mcpfarm_sdk import MCPFarmClient


def build_llm():
    """Build LLM based on MODEL_PROVIDER env var."""
    provider = os.getenv("MODEL_PROVIDER", "openai").lower()
    model_name = os.getenv("MODEL_NAME")

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model_name or "claude-sonnet-4-20250514")
    else:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model_name or "gpt-4o")


async def main(query: str) -> None:
    # ── Connect to MCPFarm ────────────────────────────────────
    farm_url = os.getenv("MCPFARM_URL", "http://localhost:8000/mcp")
    api_key = os.getenv("MCPFARM_API_KEY", "")

    client = MCPFarmClient(url=farm_url, api_key=api_key)

    if not await client.is_healthy():
        print("ERROR: MCPFarm gateway is not healthy. Is it running?")
        sys.exit(1)

    print(f"Connected to MCPFarm at {farm_url}")

    # ── Discover tools ────────────────────────────────────────
    # Uses REST wrapper approach (stateless, works across multi-turn loops).
    # Alternative: tools = await client.get_langchain_tools()  # direct MCP
    tools = await client.create_tools()
    print(f"Discovered {len(tools)} tools: {[t.name for t in tools]}")

    if not tools:
        print("ERROR: No tools available. Check that MCP servers are healthy.")
        sys.exit(1)

    # ── Build LLM + bind tools ────────────────────────────────
    llm = build_llm()
    llm_with_tools = llm.bind_tools(tools)

    # ── Build LangGraph ReAct agent ───────────────────────────
    def agent_node(state: MessagesState):
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    def should_continue(state: MessagesState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    app = graph.compile()

    # ── Run the agent ─────────────────────────────────────────
    print(f"\nQuery: {query}\n{'─' * 60}")

    result = await app.ainvoke({"messages": [HumanMessage(content=query)]})

    # ── Print conversation trace ──────────────────────────────
    for msg in result["messages"]:
        role = msg.__class__.__name__.replace("Message", "")
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            print(f"\n[{role}] Tool calls:")
            for tc in msg.tool_calls:
                print(f"  -> {tc['name']}({tc['args']})")
        elif hasattr(msg, "name") and msg.name:
            # Tool response
            content = msg.content if len(msg.content) < 200 else msg.content[:200] + "..."
            print(f"\n[Tool: {msg.name}] {content}")
        else:
            print(f"\n[{role}] {msg.content}")

    print(f"\n{'─' * 60}")
    print("Done.")


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What tools do you have available?"
    asyncio.run(main(query))
