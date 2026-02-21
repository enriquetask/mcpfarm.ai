"use client";

import { useState, useCallback, useMemo } from "react";
import { useInvocations, useWebSocket } from "@/stores/farm-store";
import type { InvocationData } from "@/lib/api";

function formatNamespace(ns: string): string {
  return ns
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ActivityPage() {
  const { invocations, total, loading, refresh } = useInvocations(50);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(),
  );

  const handleEvent = useCallback(() => {
    refresh();
  }, [refresh]);

  useWebSocket(handleEvent);

  const grouped = useMemo(() => {
    const map = new Map<string, InvocationData[]>();
    for (const inv of invocations) {
      const ns = inv.server_namespace || "other";
      if (!map.has(ns)) map.set(ns, []);
      map.get(ns)!.push(inv);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [invocations]);

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
    <div className="mx-auto max-w-5xl animate-fade-in">
      <div className="mb-6 flex items-center justify-between">
        <h2
          className="text-2xl font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Activity
          {total > 0 && (
            <span
              className="ml-3 text-base font-normal"
              style={{ color: "var(--text-tertiary)" }}
            >
              {total} total invocations
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
      ) : invocations.length === 0 ? (
        <div className="glass-card p-8 text-center">
          <p style={{ color: "var(--text-tertiary)" }}>
            No tool invocations yet. Use the tool playground to call a tool.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {grouped.map(([ns, groupInvocations]) => {
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
                    {groupInvocations.length}{" "}
                    {groupInvocations.length === 1
                      ? "invocation"
                      : "invocations"}
                  </span>
                </button>

                {/* Accordion body */}
                {isExpanded && (
                  <div className="mt-2 space-y-2 pl-4">
                    {groupInvocations.map((inv) => (
                      <InvocationRow
                        key={inv.id}
                        invocation={inv}
                        expanded={expanded === inv.id}
                        onToggle={() =>
                          setExpanded(expanded === inv.id ? null : inv.id)
                        }
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function InvocationRow({
  invocation,
  expanded,
  onToggle,
}: {
  invocation: InvocationData;
  expanded: boolean;
  onToggle: () => void;
}) {
  const statusColor =
    invocation.status === "success"
      ? "text-emerald-500"
      : invocation.status === "error"
        ? "text-red-500"
        : "text-amber-500";

  const statusDot =
    invocation.status === "success"
      ? "bg-emerald-400"
      : invocation.status === "error"
        ? "bg-red-400"
        : "bg-amber-400";

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-3 p-4 text-left transition-colors hover:bg-neural-500/5"
      >
        <span className={`h-2 w-2 flex-shrink-0 rounded-full ${statusDot}`} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span
              className="truncate font-mono text-sm font-medium"
              style={{ color: "var(--text-primary)" }}
            >
              {invocation.tool_name || formatArgs(invocation.input_data)}
            </span>
          </div>
          <div className="mt-0.5 flex items-center gap-3 text-xs" style={{ color: "var(--text-tertiary)" }}>
            <span>{formatTime(invocation.created_at)}</span>
            {invocation.duration_ms !== null && (
              <span className="text-neural-400">
                {invocation.duration_ms}ms
              </span>
            )}
            <span className={statusColor}>{invocation.status}</span>
          </div>
        </div>
        <svg
          className={`h-4 w-4 flex-shrink-0 transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          style={{ color: "var(--text-tertiary)" }}
        >
          <path
            d="M6 9l6 6 6-6"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {expanded && (
        <div
          className="border-t p-4"
          style={{ borderColor: "var(--border)" }}
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <p
                className="mb-2 text-xs font-semibold uppercase tracking-wider"
                style={{ color: "var(--text-tertiary)" }}
              >
                Input
              </p>
              <pre
                className="overflow-auto rounded-lg p-3 font-mono text-xs"
                style={{
                  background: "var(--bg-tertiary)",
                  color: "var(--text-primary)",
                  maxHeight: "200px",
                }}
              >
                {JSON.stringify(invocation.input_data, null, 2)}
              </pre>
            </div>
            <div>
              <p
                className="mb-2 text-xs font-semibold uppercase tracking-wider"
                style={{ color: "var(--text-tertiary)" }}
              >
                Output
              </p>
              <pre
                className="overflow-auto rounded-lg p-3 font-mono text-xs"
                style={{
                  background: "var(--bg-tertiary)",
                  color:
                    invocation.status === "error"
                      ? "#ef4444"
                      : "var(--text-primary)",
                  maxHeight: "200px",
                }}
              >
                {invocation.output_data
                  ? JSON.stringify(invocation.output_data, null, 2)
                  : "No output"}
              </pre>
            </div>
          </div>
          <div
            className="mt-3 flex gap-4 text-xs"
            style={{ color: "var(--text-tertiary)" }}
          >
            <span>ID: {invocation.id.substring(0, 8)}</span>
            <span>Server: {invocation.server_id.substring(0, 8)}</span>
            {invocation.tool_id && (
              <span>Tool: {invocation.tool_id.substring(0, 8)}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();

  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return d.toLocaleDateString();
}

function formatArgs(data: Record<string, unknown>): string {
  const entries = Object.entries(data);
  if (entries.length === 0) return "(no args)";
  return entries
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(", ");
}
