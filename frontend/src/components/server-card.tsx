"use client";

import Link from "next/link";
import type { ServerData } from "@/lib/api";

const STATUS_STYLES: Record<
  string,
  { dot: string; border: string; label: string }
> = {
  HEALTHY: {
    dot: "bg-emerald-400 animate-pulse",
    border: "border-emerald-500/30",
    label: "text-emerald-500",
  },
  STARTING: {
    dot: "bg-amber-400 animate-pulse",
    border: "border-amber-500/30",
    label: "text-amber-500",
  },
  DEGRADED: {
    dot: "bg-amber-500",
    border: "border-amber-500/30",
    label: "text-amber-500",
  },
  UNHEALTHY: {
    dot: "bg-red-500",
    border: "border-red-500/30",
    label: "text-red-500",
  },
  STOPPED: {
    dot: "bg-gray-400 dark:bg-gray-600",
    border: "",
    label: "",
  },
};

export function ServerCard({
  server,
  onStart,
  onStop,
}: {
  server: ServerData;
  onStart: () => void;
  onStop: () => void;
}) {
  const style = STATUS_STYLES[server.status] || STATUS_STYLES.STOPPED;

  return (
    <div className={`glass-card p-4 ${style.border}`}>
      <div className="mb-3 flex items-center justify-between">
        <Link href={`/servers/${server.id}`} className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <span className={`h-2.5 w-2.5 rounded-full ${style.dot}`} />
          <h3 className="font-semibold" style={{ color: "var(--text-primary)" }}>
            {server.name}
          </h3>
        </Link>
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-medium"
          style={{
            background: "var(--bg-tertiary)",
            color: "var(--text-secondary)",
          }}
        >
          {server.namespace}
        </span>
      </div>

      <div className="mb-3 space-y-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
        <p>
          Image:{" "}
          <span style={{ color: "var(--text-secondary)" }}>{server.image}</span>
        </p>
        <p>
          Tools:{" "}
          <span style={{ color: "var(--text-secondary)" }}>
            {server.tool_count}
          </span>
        </p>
        <p>
          Status:{" "}
          <span className={`font-medium ${style.label}`}>
            {server.status}
          </span>
        </p>
      </div>

      <div className="flex gap-2">
        {server.status === "STOPPED" || server.status === "UNHEALTHY" ? (
          <button
            onClick={onStart}
            className="rounded-lg bg-neural-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-neural-500"
          >
            Start
          </button>
        ) : (
          <button
            onClick={onStop}
            className="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
            style={{
              background: "var(--bg-tertiary)",
              color: "var(--text-secondary)",
            }}
          >
            Stop
          </button>
        )}
      </div>
    </div>
  );
}
