"use client";

import { useState } from "react";

/* ── Types ──────────────────────────────────────────────── */

interface Param {
  name: string;
  type: string;
  required?: boolean;
  description: string;
  default?: string;
}

interface Endpoint {
  method: "GET" | "POST" | "PATCH" | "DELETE";
  path: string;
  summary: string;
  description?: string;
  auth: boolean;
  params?: Param[];
  body?: Param[];
  response?: string;
  responseExample?: string;
  statusCodes?: { code: number; description: string }[];
}

interface Section {
  id: string;
  title: string;
  description: string;
  endpoints: Endpoint[];
}

/* ── API Data ───────────────────────────────────────────── */

const API_SECTIONS: Section[] = [
  {
    id: "auth",
    title: "Authentication",
    description:
      "All API endpoints (except health checks and metrics) require a Bearer token. Pass your API key in the Authorization header.",
    endpoints: [
      {
        method: "POST",
        path: "/api/keys/",
        summary: "Create API Key",
        description:
          "Generate a new API key. The plaintext key is returned only once in the response - store it securely.",
        auth: true,
        body: [
          { name: "name", type: "string", required: true, description: "Descriptive name for the key" },
          { name: "scopes", type: "string[]", description: "Namespace scopes (empty = full access)", default: "[]" },
        ],
        responseExample: `{
  "id": "a1b2c3d4-...",
  "name": "my-agent",
  "key": "mf_a1b2c3d4e5f6...",
  "scopes": [],
  "is_active": true,
  "expires_at": null,
  "created_at": "2026-02-20T..."
}`,
        statusCodes: [
          { code: 201, description: "Key created successfully" },
          { code: 401, description: "Missing or invalid auth" },
        ],
      },
      {
        method: "GET",
        path: "/api/keys/",
        summary: "List API Keys",
        description: "List all API keys (plaintext keys are never returned after creation).",
        auth: true,
        responseExample: `{
  "keys": [
    {
      "id": "a1b2c3d4-...",
      "name": "my-agent",
      "scopes": [],
      "is_active": true,
      "expires_at": null,
      "created_at": "2026-02-20T..."
    }
  ],
  "total": 1
}`,
      },
      {
        method: "DELETE",
        path: "/api/keys/{key_id}",
        summary: "Revoke API Key",
        description: "Permanently revoke an API key. This cannot be undone.",
        auth: true,
        params: [{ name: "key_id", type: "uuid", required: true, description: "The API key ID" }],
        statusCodes: [
          { code: 204, description: "Key revoked" },
          { code: 404, description: "Key not found" },
        ],
      },
    ],
  },
  {
    id: "health",
    title: "Health & Observability",
    description: "Health probes and metrics endpoints. These do not require authentication.",
    endpoints: [
      {
        method: "GET",
        path: "/health",
        summary: "Shallow Health Check",
        auth: false,
        responseExample: `{ "status": "ok", "service": "mcpfarm-gateway", "version": "0.1.0" }`,
      },
      {
        method: "GET",
        path: "/health/live",
        summary: "Liveness Probe",
        description: "Returns 200 if the process is running. Use for Kubernetes liveness probes.",
        auth: false,
        responseExample: `{ "status": "ok" }`,
      },
      {
        method: "GET",
        path: "/health/ready",
        summary: "Deep Readiness Probe",
        description: "Checks database, Redis, and tool availability. Returns 503 if any dependency is down.",
        auth: false,
        responseExample: `{
  "status": "ok",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "tools_available": 17
  }
}`,
        statusCodes: [
          { code: 200, description: "All dependencies healthy" },
          { code: 503, description: "One or more dependencies down" },
        ],
      },
      {
        method: "GET",
        path: "/api/stats",
        summary: "Farm Statistics",
        auth: false,
        responseExample: `{
  "total_servers": 3,
  "healthy_servers": 3,
  "total_tools": 17,
  "total_invocations": 142
}`,
      },
      {
        method: "GET",
        path: "/metrics",
        summary: "Prometheus Metrics",
        description:
          "Prometheus text format metrics. Includes HTTP request rates, tool invocation counters, auth failures, server health gauges, and WebSocket connection counts.",
        auth: false,
        response: "text/plain (Prometheus exposition format)",
      },
    ],
  },
  {
    id: "servers",
    title: "Servers",
    description:
      "Manage MCP server containers. Servers are Docker containers running FastMCP services, identified by a unique namespace.",
    endpoints: [
      {
        method: "GET",
        path: "/api/servers/",
        summary: "List Servers",
        auth: true,
        responseExample: `{
  "servers": [
    {
      "id": "91114c4d-...",
      "name": "Echo Server",
      "namespace": "echo",
      "image": "mcpfarmai-echo-server:latest",
      "port": 9001,
      "env_vars": {},
      "status": "HEALTHY",
      "container_id": "3aa262d1842f...",
      "auto_restart": false,
      "tool_count": 3,
      "created_at": "2026-02-20T...",
      "updated_at": "2026-02-20T..."
    }
  ],
  "total": 3
}`,
      },
      {
        method: "POST",
        path: "/api/servers/",
        summary: "Register Server",
        description: "Register a new MCP server. This creates a database record but does not start the container. Call /start to launch it.",
        auth: true,
        body: [
          { name: "name", type: "string", required: true, description: "Display name (unique)" },
          { name: "namespace", type: "string", required: true, description: "Unique identifier, lowercase alphanumeric + underscore. Pattern: ^[a-z][a-z0-9_]*$" },
          { name: "image", type: "string", required: true, description: "Docker image reference" },
          { name: "port", type: "integer", description: "MCP server port inside container", default: "9001" },
          { name: "env_vars", type: "object", description: "Environment variables as key-value pairs", default: "{}" },
          { name: "auto_restart", type: "boolean", description: "Auto-restart on failure", default: "true" },
        ],
        statusCodes: [
          { code: 201, description: "Server registered" },
          { code: 409, description: "Namespace already exists" },
        ],
      },
      {
        method: "GET",
        path: "/api/servers/{server_id}",
        summary: "Get Server",
        auth: true,
        params: [{ name: "server_id", type: "uuid", required: true, description: "Server UUID" }],
      },
      {
        method: "PATCH",
        path: "/api/servers/{server_id}",
        summary: "Update Server",
        auth: true,
        params: [{ name: "server_id", type: "uuid", required: true, description: "Server UUID" }],
        body: [
          { name: "name", type: "string", description: "New display name" },
          { name: "image", type: "string", description: "New Docker image" },
          { name: "port", type: "integer", description: "New port" },
          { name: "env_vars", type: "object", description: "New environment variables" },
          { name: "auto_restart", type: "boolean", description: "Toggle auto-restart" },
        ],
      },
      {
        method: "DELETE",
        path: "/api/servers/{server_id}",
        summary: "Delete Server",
        description: "Stop and remove the container, unmount proxy, unregister tools, delete database record.",
        auth: true,
        params: [{ name: "server_id", type: "uuid", required: true, description: "Server UUID" }],
        statusCodes: [
          { code: 204, description: "Server deleted" },
          { code: 404, description: "Server not found" },
        ],
      },
      {
        method: "POST",
        path: "/api/servers/{server_id}/start",
        summary: "Start Server",
        description:
          "Create a Docker container, wait for MCP readiness, mount the proxy, and discover tools.",
        auth: true,
        params: [{ name: "server_id", type: "uuid", required: true, description: "Server UUID" }],
        statusCodes: [
          { code: 200, description: "Server started (status: HEALTHY or DEGRADED)" },
          { code: 409, description: "Server is already running" },
        ],
      },
      {
        method: "POST",
        path: "/api/servers/{server_id}/stop",
        summary: "Stop Server",
        description: "Stop and remove the container, unmount proxy, mark tools unavailable.",
        auth: true,
        params: [{ name: "server_id", type: "uuid", required: true, description: "Server UUID" }],
      },
      {
        method: "POST",
        path: "/api/servers/{server_id}/restart",
        summary: "Restart Server",
        description: "Stop, remove, recreate container, and re-mount proxy. Equivalent to stop + start.",
        auth: true,
        params: [{ name: "server_id", type: "uuid", required: true, description: "Server UUID" }],
      },
    ],
  },
  {
    id: "tools",
    title: "Tools",
    description:
      "Discover and invoke MCP tools across all servers. Tools are namespaced: {namespace}_{tool_name} (e.g. calc_add, web_search).",
    endpoints: [
      {
        method: "GET",
        path: "/api/tools/",
        summary: "List Tools",
        description: "Returns all available tools across all healthy servers.",
        auth: true,
        responseExample: `{
  "tools": [
    {
      "name": "add",
      "namespaced_name": "calc_add",
      "description": "Add two numbers.",
      "input_schema": {
        "properties": {
          "a": { "type": "number" },
          "b": { "type": "number" }
        },
        "required": ["a", "b"]
      },
      "server_namespace": "calc",
      "is_available": true
    }
  ],
  "total": 17
}`,
      },
      {
        method: "GET",
        path: "/api/tools/{namespaced_name}",
        summary: "Get Tool",
        auth: true,
        params: [
          {
            name: "namespaced_name",
            type: "string",
            required: true,
            description: "Namespaced tool name (e.g. calc_add, web_search)",
          },
        ],
      },
      {
        method: "POST",
        path: "/api/tools/call",
        summary: "Call Tool",
        description:
          "Invoke any tool by namespaced name. The call is proxied to the underlying MCP server, logged as an invocation, and tracked in metrics.",
        auth: true,
        body: [
          { name: "tool_name", type: "string", required: true, description: "Namespaced tool name (e.g. calc_add)" },
          { name: "arguments", type: "object", description: "Tool arguments matching the input schema", default: "{}" },
        ],
        responseExample: `{
  "result": "8.0",
  "duration_ms": 23,
  "invocation_id": "e5f6a7b8-..."
}`,
        statusCodes: [
          { code: 200, description: "Tool executed successfully" },
          { code: 404, description: "Tool not found" },
          { code: 500, description: "Tool execution failed" },
        ],
      },
    ],
  },
  {
    id: "invocations",
    title: "Invocations",
    description: "Query the audit log of all tool invocations with input/output data and timing.",
    endpoints: [
      {
        method: "GET",
        path: "/api/invocations",
        summary: "List Invocations",
        auth: true,
        params: [
          { name: "limit", type: "integer", description: "Max results", default: "50" },
          { name: "offset", type: "integer", description: "Pagination offset", default: "0" },
        ],
        responseExample: `{
  "invocations": [
    {
      "id": "e5f6a7b8-...",
      "tool_id": "d4c3b2a1-...",
      "server_id": "91114c4d-...",
      "caller_id": "my-agent",
      "input_data": { "a": 5, "b": 3 },
      "output_data": { "result": "8.0" },
      "duration_ms": 23,
      "status": "success",
      "created_at": "2026-02-20T..."
    }
  ],
  "total": 142
}`,
      },
    ],
  },
  {
    id: "mcp",
    title: "MCP Protocol",
    description:
      "The gateway exposes a standard MCP Streamable HTTP endpoint. Connect any MCP-compatible client (Claude Desktop, LangChain MCP adapters, etc.) to access all farm tools via the MCP protocol.",
    endpoints: [
      {
        method: "POST",
        path: "/mcp",
        summary: "MCP Streamable HTTP",
        description:
          "Standard MCP protocol endpoint. Supports tool listing and tool calling via the MCP specification. Use Bearer auth in the Authorization header. Compatible with langchain-mcp-adapters MultiServerMCPClient.",
        auth: true,
        response: "MCP protocol responses (JSON-RPC over HTTP)",
      },
    ],
  },
  {
    id: "websocket",
    title: "WebSocket Events",
    description: "Real-time event stream for live UI updates. Broadcasts server health changes, tool invocations, and other farm events.",
    endpoints: [
      {
        method: "GET",
        path: "/ws",
        summary: "WebSocket Connection",
        description:
          "Connect to receive real-time events. Events are JSON objects with { type, data } structure.",
        auth: false,
        responseExample: `// Event types:
{ "type": "server.health_changed", "data": { "server_id": "...", "name": "Echo Server", "old_status": "DEGRADED", "new_status": "HEALTHY", "reason": "Recovered" } }
{ "type": "server.started",        "data": { "server_id": "...", "name": "Echo Server", "status": "HEALTHY" } }
{ "type": "server.stopped",        "data": { "server_id": "...", "name": "Echo Server" } }
{ "type": "tool.invoked",          "data": { "tool_name": "calc_add", "server_id": "...", "duration_ms": 23, "status": "success" } }
{ "type": "tool.error",            "data": { "tool_name": "calc_add", "server_id": "...", "error": "..." } }
{ "type": "server.deleted",        "data": { "server_id": "...", "name": "Echo Server" } }`,
      },
    ],
  },
  {
    id: "sdk",
    title: "Python SDK",
    description:
      "The mcpfarm-sdk package provides a high-level async client for connecting agents to the farm.",
    endpoints: [
      {
        method: "GET",
        path: "pip install mcpfarm-sdk[langchain]",
        summary: "Installation",
        description: "Install the SDK with LangChain integration support.",
        auth: false,
        responseExample: `from mcpfarm_sdk import MCPFarmClient

client = MCPFarmClient(
    url="http://localhost:8000/mcp",
    api_key="your-api-key",
)

# Health check
await client.is_healthy()

# List tools (raw dicts)
tools = await client.list_tools()

# Call a tool directly
result = await client.call_tool("calc_add", {"a": 5, "b": 3})

# Get LangChain StructuredTool wrappers (REST-based)
lc_tools = await client.create_tools()

# Get LangChain tools via MCP protocol (requires langchain-mcp-adapters)
lc_tools = await client.get_langchain_tools()

# Use with LangGraph
from langgraph.prebuilt import ToolNode
tool_node = ToolNode(lc_tools)`,
      },
    ],
  },
];

/* ── Subcomponents ──────────────────────────────────────── */

const METHOD_STYLES: Record<string, string> = {
  GET: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  POST: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  PATCH: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  DELETE: "bg-red-500/15 text-red-400 border-red-500/30",
};

function MethodBadge({ method }: { method: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-mono font-bold ${METHOD_STYLES[method] || ""}`}
    >
      {method}
    </span>
  );
}

function ParamTable({ title, params }: { title: string; params: Param[] }) {
  return (
    <div className="mt-3">
      <h5 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-tertiary)" }}>
        {title}
      </h5>
      <div
        className="rounded-lg border overflow-hidden"
        style={{ borderColor: "var(--border)", background: "var(--bg-tertiary)" }}
      >
        <table className="w-full text-sm">
          <thead>
            <tr style={{ borderColor: "var(--border)" }} className="border-b">
              <th className="text-left px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>Name</th>
              <th className="text-left px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>Type</th>
              <th className="text-left px-3 py-2 font-medium hidden sm:table-cell" style={{ color: "var(--text-secondary)" }}>Default</th>
              <th className="text-left px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>Description</th>
            </tr>
          </thead>
          <tbody>
            {params.map((p) => (
              <tr key={p.name} className="border-t" style={{ borderColor: "var(--border)" }}>
                <td className="px-3 py-2 font-mono text-xs">
                  <span className="text-neural-400">{p.name}</span>
                  {p.required && <span className="text-red-400 ml-1">*</span>}
                </td>
                <td className="px-3 py-2 font-mono text-xs" style={{ color: "var(--text-tertiary)" }}>{p.type}</td>
                <td className="px-3 py-2 font-mono text-xs hidden sm:table-cell" style={{ color: "var(--text-tertiary)" }}>
                  {p.default || "—"}
                </td>
                <td className="px-3 py-2 text-xs" style={{ color: "var(--text-secondary)" }}>{p.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EndpointCard({ ep }: { ep: Endpoint }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = ep.description || ep.params || ep.body || ep.responseExample || ep.statusCodes;

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => hasDetails && setExpanded(!expanded)}
        className={`w-full flex items-center gap-3 px-4 py-3 text-left ${hasDetails ? "cursor-pointer" : "cursor-default"}`}
      >
        <MethodBadge method={ep.method} />
        <code className="text-sm font-mono flex-1" style={{ color: "var(--text-primary)" }}>
          {ep.path}
        </code>
        <span className="text-sm hidden md:inline" style={{ color: "var(--text-secondary)" }}>
          {ep.summary}
        </span>
        {ep.auth && (
          <span className="text-[10px] rounded-full px-2 py-0.5 border border-neural-500/30 text-neural-400 bg-neural-500/10">
            AUTH
          </span>
        )}
        {hasDetails && (
          <svg
            className={`h-4 w-4 transition-transform ${expanded ? "rotate-180" : ""}`}
            style={{ color: "var(--text-tertiary)" }}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t" style={{ borderColor: "var(--border)" }}>
          {ep.description && (
            <p className="mt-3 text-sm" style={{ color: "var(--text-secondary)" }}>
              {ep.description}
            </p>
          )}

          {ep.params && <ParamTable title="Path / Query Parameters" params={ep.params} />}
          {ep.body && <ParamTable title="Request Body (JSON)" params={ep.body} />}

          {ep.statusCodes && (
            <div className="mt-3">
              <h5 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-tertiary)" }}>
                Status Codes
              </h5>
              <div className="flex flex-wrap gap-2">
                {ep.statusCodes.map((sc) => (
                  <span
                    key={sc.code}
                    className={`text-xs rounded-md px-2 py-1 border font-mono ${
                      sc.code < 300
                        ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                        : sc.code < 500
                          ? "border-amber-500/30 text-amber-400 bg-amber-500/10"
                          : "border-red-500/30 text-red-400 bg-red-500/10"
                    }`}
                  >
                    {sc.code} {sc.description}
                  </span>
                ))}
              </div>
            </div>
          )}

          {ep.response && !ep.responseExample && (
            <div className="mt-3">
              <h5 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-tertiary)" }}>
                Response
              </h5>
              <p className="text-sm font-mono" style={{ color: "var(--text-secondary)" }}>{ep.response}</p>
            </div>
          )}

          {ep.responseExample && (
            <div className="mt-3">
              <h5 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-tertiary)" }}>
                Response Example
              </h5>
              <pre
                className="rounded-lg p-3 text-xs font-mono overflow-x-auto custom-scrollbar"
                style={{ background: "var(--bg-tertiary)", color: "var(--text-secondary)" }}
              >
                {ep.responseExample}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── TOC + Main Page ────────────────────────────────────── */

export default function APIReferencePage() {
  const [activeSection, setActiveSection] = useState<string | null>(null);

  const scrollTo = (id: string) => {
    setActiveSection(id);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="mx-auto max-w-6xl animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gradient">API Reference</h1>
        <p className="mt-2 text-sm" style={{ color: "var(--text-secondary)" }}>
          Complete reference for the MCPFarm.ai Gateway REST API, MCP protocol, WebSocket events, and Python SDK.
        </p>
        <div
          className="mt-4 flex items-center gap-3 rounded-lg border px-4 py-3"
          style={{ background: "var(--bg-tertiary)", borderColor: "var(--border)" }}
        >
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>
            Base URL
          </span>
          <code className="text-sm font-mono text-neural-400">http://localhost:8000</code>
          <span className="mx-2" style={{ color: "var(--border)" }}>|</span>
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>
            Auth
          </span>
          <code className="text-sm font-mono text-cyber-400">Authorization: Bearer &lt;api_key&gt;</code>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Sticky sidebar TOC */}
        <nav className="hidden lg:block w-48 shrink-0">
          <div className="sticky top-6">
            <h4 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--text-tertiary)" }}>
              Sections
            </h4>
            <div className="flex flex-col gap-1">
              {API_SECTIONS.map((s) => (
                <button
                  key={s.id}
                  onClick={() => scrollTo(s.id)}
                  className={`text-left text-sm px-2 py-1.5 rounded-md transition-colors ${
                    activeSection === s.id
                      ? "bg-neural-500/10 text-neural-400"
                      : "hover:bg-[var(--bg-tertiary)]"
                  }`}
                  style={activeSection === s.id ? {} : { color: "var(--text-secondary)" }}
                >
                  {s.title}
                </button>
              ))}
            </div>

            <div
              className="mt-6 rounded-lg border p-3"
              style={{ borderColor: "var(--border)", background: "var(--bg-tertiary)" }}
            >
              <h5 className="text-xs font-semibold mb-1" style={{ color: "var(--text-tertiary)" }}>Quick Start</h5>
              <pre className="text-[10px] font-mono leading-relaxed" style={{ color: "var(--text-secondary)" }}>
{`curl -H "Authorization: \\
  Bearer mcpfarm-dev-key" \\
  localhost:8000/api/tools/`}
              </pre>
            </div>
          </div>
        </nav>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {API_SECTIONS.map((section) => (
            <section key={section.id} id={section.id} className="mb-10 scroll-mt-6">
              <div className="mb-4">
                <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
                  {section.title}
                </h2>
                <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
                  {section.description}
                </p>
              </div>
              <div className="flex flex-col gap-2">
                {section.endpoints.map((ep, i) => (
                  <EndpointCard key={`${ep.method}-${ep.path}-${i}`} ep={ep} />
                ))}
              </div>
            </section>
          ))}

          {/* Server status legend */}
          <section className="mb-10 scroll-mt-6">
            <h2 className="text-xl font-bold mb-4" style={{ color: "var(--text-primary)" }}>
              Server Status Reference
            </h2>
            <div className="glass-card p-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  { status: "HEALTHY", color: "emerald", desc: "Container running, MCP endpoint responding, proxy mounted" },
                  { status: "STARTING", color: "blue", desc: "Container launched, waiting for MCP readiness" },
                  { status: "DEGRADED", color: "amber", desc: "Container running but MCP endpoint unresponsive" },
                  { status: "UNHEALTHY", color: "red", desc: "Container down, max restart attempts exceeded" },
                  { status: "STOPPED", color: "gray", desc: "Intentionally stopped via API or management" },
                ].map((s) => (
                  <div key={s.status} className="flex items-start gap-3">
                    <span className={`mt-1 h-2.5 w-2.5 rounded-full shrink-0 bg-${s.color}-500`} />
                    <div>
                      <span className="text-sm font-mono font-semibold" style={{ color: "var(--text-primary)" }}>
                        {s.status}
                      </span>
                      <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{s.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* Rate limiting */}
          <section className="mb-10 scroll-mt-6">
            <h2 className="text-xl font-bold mb-4" style={{ color: "var(--text-primary)" }}>
              Rate Limiting
            </h2>
            <div className="glass-card p-4">
              <p className="text-sm mb-3" style={{ color: "var(--text-secondary)" }}>
                All authenticated endpoints are rate-limited per API key using a sliding window counter in Redis.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="rounded-lg border p-3" style={{ borderColor: "var(--border)", background: "var(--bg-tertiary)" }}>
                  <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>Window</span>
                  <p className="text-lg font-mono font-bold text-neural-400">1 min</p>
                </div>
                <div className="rounded-lg border p-3" style={{ borderColor: "var(--border)", background: "var(--bg-tertiary)" }}>
                  <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>Default Limit</span>
                  <p className="text-lg font-mono font-bold text-cyber-400">60 req/min</p>
                </div>
                <div className="rounded-lg border p-3" style={{ borderColor: "var(--border)", background: "var(--bg-tertiary)" }}>
                  <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>Response</span>
                  <p className="text-lg font-mono font-bold text-amber-400">429</p>
                  <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>+ Retry-After header</p>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
