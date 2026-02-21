"use client";

import { useState, useMemo, useEffect } from "react";
import { useTools } from "@/stores/farm-store";
import { callTool } from "@/lib/api";
import type { ToolData } from "@/lib/api";

function formatNamespace(ns: string): string {
  return ns
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ToolsPage() {
  const { tools, loading } = useTools();
  const [selectedTool, setSelectedTool] = useState<ToolData | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(),
  );

  const grouped = useMemo(() => {
    const map = new Map<string, ToolData[]>();
    for (const tool of tools) {
      const ns = tool.server_namespace || "other";
      if (!map.has(ns)) map.set(ns, []);
      map.get(ns)!.push(tool);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [tools]);

  function toggleGroup(ns: string) {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(ns)) {
        next.delete(ns);
      } else {
        next.add(ns);
      }
      return next;
    });
  }

  return (
    <div className="mx-auto max-w-7xl animate-fade-in">
      <div className="mb-6 flex items-center justify-between">
        <h2
          className="text-2xl font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Tools
          {tools.length > 0 && (
            <span
              className="ml-3 text-base font-normal"
              style={{ color: "var(--text-tertiary)" }}
            >
              {tools.length} total
            </span>
          )}
        </h2>
        {grouped.length > 0 && (
          <div className="flex gap-3 text-xs">
            <button
              onClick={() =>
                setExpandedGroups(new Set(grouped.map(([ns]) => ns)))
              }
              className="transition-colors hover:underline"
              style={{ color: "var(--text-tertiary)" }}
            >
              Expand All
            </button>
            <button
              onClick={() => setExpandedGroups(new Set())}
              className="transition-colors hover:underline"
              style={{ color: "var(--text-tertiary)" }}
            >
              Collapse All
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <div className="glass-card p-8 text-center">
          <div className="progress-shimmer mx-auto h-1 w-48 rounded-full" />
          <p className="mt-4" style={{ color: "var(--text-tertiary)" }}>
            Loading...
          </p>
        </div>
      ) : tools.length === 0 ? (
        <div className="glass-card p-8 text-center">
          <p style={{ color: "var(--text-tertiary)" }}>
            No tools available. Start an MCP server to see its tools here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Tool list — grouped by server namespace */}
          <div className="space-y-4">
            {grouped.map(([ns, groupTools]) => {
              const isExpanded = expandedGroups.has(ns);
              return (
                <div key={ns}>
                  {/* Accordion header */}
                  <button
                    onClick={() => toggleGroup(ns)}
                    className="glass-card flex w-full items-center gap-3 px-4 py-3 text-left transition-all hover:brightness-110"
                  >
                    <svg
                      className={`h-4 w-4 shrink-0 transition-transform duration-200 ${
                        isExpanded ? "rotate-90" : ""
                      }`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      style={{ color: "var(--text-tertiary)" }}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                    <span
                      className="text-sm font-semibold"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {formatNamespace(ns)}
                    </span>
                    <span className="ml-auto rounded-full bg-neural-500/10 px-2.5 py-0.5 text-xs font-medium text-neural-400">
                      {groupTools.length}{" "}
                      {groupTools.length === 1 ? "tool" : "tools"}
                    </span>
                  </button>

                  {/* Accordion body */}
                  {isExpanded && (
                    <div className="mt-2 space-y-2 pl-4">
                      {groupTools.map((tool) => (
                        <button
                          key={tool.namespaced_name}
                          onClick={() => setSelectedTool(tool)}
                          className={`glass-card w-full p-4 text-left transition-all ${
                            selectedTool?.namespaced_name ===
                            tool.namespaced_name
                              ? "border-neural-500/50 ring-1 ring-neural-500/30"
                              : ""
                          }`}
                        >
                          <h3
                            className="font-mono text-sm font-semibold"
                            style={{ color: "var(--text-primary)" }}
                          >
                            {tool.namespaced_name}
                          </h3>
                          {tool.description && (
                            <p
                              className="mt-1 text-sm"
                              style={{ color: "var(--text-secondary)" }}
                            >
                              {tool.description}
                            </p>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Playground panel */}
          <div className="lg:sticky lg:top-6 lg:self-start">
            {selectedTool ? (
              <ToolPlayground tool={selectedTool} />
            ) : (
              <div className="glass-card p-8 text-center">
                <svg
                  className="mx-auto h-12 w-12 opacity-30"
                  fill="none"
                  viewBox="0 0 24 24"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  <path
                    d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <p
                  className="mt-4"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  Select a tool to test it in the playground.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function ToolPlayground({ tool }: { tool: ToolData }) {
  const [args, setArgs] = useState<Record<string, string>>({});
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [durationMs, setDurationMs] = useState<number | null>(null);

  useEffect(() => {
    setArgs({});
    setResult(null);
    setError(null);
    setDurationMs(null);
  }, [tool.namespaced_name]);

  const schema = tool.input_schema as {
    properties?: Record<string, { type?: string; description?: string }>;
    required?: string[];
  };

  const params = schema.properties
    ? Object.entries(schema.properties)
    : [];
  const required = new Set(schema.required || []);

  async function handleRun() {
    setRunning(true);
    setError(null);
    setResult(null);
    setDurationMs(null);

    // Parse argument values based on type
    const parsedArgs: Record<string, unknown> = {};
    for (const [name, def] of params) {
      const val = args[name];
      if (!val && required.has(name)) {
        setError(`Missing required parameter: ${name}`);
        setRunning(false);
        return;
      }
      if (!val) continue;

      if (def.type === "number" || def.type === "integer") {
        parsedArgs[name] = Number(val);
      } else if (def.type === "boolean") {
        parsedArgs[name] = val === "true";
      } else {
        parsedArgs[name] = val;
      }
    }

    try {
      const res = await callTool(tool.namespaced_name, parsedArgs);
      setResult(res.result);
      setDurationMs(res.duration_ms);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Tool call failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="glass-card p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3
          className="font-mono text-sm font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          {tool.namespaced_name}
        </h3>
        <span className="rounded-full bg-neural-500/10 px-2.5 py-0.5 text-xs font-medium text-neural-400">
          Playground
        </span>
      </div>

      {tool.description && (
        <p
          className="mb-4 text-sm"
          style={{ color: "var(--text-secondary)" }}
        >
          {tool.description}
        </p>
      )}

      {/* Parameter inputs */}
      {params.length > 0 ? (
        <div className="mb-4 space-y-3">
          {params.map(([name, def]) => (
            <div key={name}>
              <label
                className="mb-1 block text-xs font-medium"
                style={{ color: "var(--text-tertiary)" }}
              >
                {name}
                {required.has(name) && (
                  <span className="ml-1 text-red-400">*</span>
                )}
                <span className="ml-2 font-normal opacity-60">
                  {def.type || "string"}
                </span>
              </label>
              <input
                type={
                  def.type === "number" || def.type === "integer"
                    ? "number"
                    : "text"
                }
                value={args[name] || ""}
                onChange={(e) =>
                  setArgs((prev) => ({ ...prev, [name]: e.target.value }))
                }
                placeholder={def.description || name}
                className="w-full rounded-lg border px-3 py-2 font-mono text-sm outline-none transition-colors focus:border-neural-500"
                style={{
                  background: "var(--bg-tertiary)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                }}
              />
            </div>
          ))}
        </div>
      ) : (
        <p
          className="mb-4 text-sm italic"
          style={{ color: "var(--text-tertiary)" }}
        >
          This tool takes no parameters.
        </p>
      )}

      {/* Run button */}
      <button
        onClick={handleRun}
        disabled={running}
        className="w-full rounded-lg bg-neural-600 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neural-500 disabled:opacity-50"
      >
        {running ? "Running..." : "Run Tool"}
      </button>

      {/* Result */}
      {(result !== null || error) && (
        <ResultBlock
          text={error || JSON.stringify(result, null, 2)}
          isError={!!error}
          durationMs={durationMs}
        />
      )}
    </div>
  );
}

function ResultBlock({
  text,
  isError,
  durationMs,
}: {
  text: string;
  isError: boolean;
  durationMs: number | null;
}) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <div className="mt-4">
      <div className="mb-2 flex items-center justify-between">
        <span
          className="text-xs font-medium"
          style={{ color: "var(--text-tertiary)" }}
        >
          Result
        </span>
        <div className="flex items-center gap-3">
          {durationMs !== null && (
            <span className="text-xs text-neural-400">{durationMs}ms</span>
          )}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs transition-colors hover:bg-neural-500/10"
            style={{ color: "var(--text-tertiary)" }}
          >
            {copied ? (
              <>
                <svg className="h-3.5 w-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-emerald-500">Copied</span>
              </>
            ) : (
              <>
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <rect x="9" y="9" width="13" height="13" rx="2" strokeWidth={2} />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                </svg>
                Copy
              </>
            )}
          </button>
        </div>
      </div>
      <pre
        className="overflow-auto rounded-lg p-3 font-mono text-xs"
        style={{
          background: "var(--bg-tertiary)",
          color: isError ? "#ef4444" : "var(--text-primary)",
          maxHeight: "200px",
        }}
      >
        {text}
      </pre>
    </div>
  );
}
