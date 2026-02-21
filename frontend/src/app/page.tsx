"use client";

import { useCallback } from "react";
import { useStats, useServers, useWebSocket } from "@/stores/farm-store";
import { ServerCard } from "@/components/server-card";
import { startServer, stopServer } from "@/lib/api";

export default function DashboardPage() {
  const { stats, refresh: refreshStats } = useStats();
  const { servers, refresh: refreshServers } = useServers();

  const handleEvent = useCallback(() => {
    refreshStats();
    refreshServers();
  }, [refreshStats, refreshServers]);

  const { connected } = useWebSocket(handleEvent);

  async function handleStart(id: string) {
    await startServer(id);
    refreshStats();
    refreshServers();
  }

  async function handleStop(id: string) {
    await stopServer(id);
    refreshStats();
    refreshServers();
  }

  return (
    <div className="mx-auto max-w-7xl animate-fade-in">
      <div className="mb-6 flex items-center justify-between">
        <h2
          className="text-2xl font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Dashboard
        </h2>
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-400 animate-pulse" : "bg-gray-400 dark:bg-gray-600"}`}
          />
          <span className="text-xs" style={{ color: "var(--text-tertiary)" }}>
            {connected ? "Live" : "Disconnected"}
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Servers" value={stats.total_servers} />
        <MetricCard
          label="Healthy"
          value={stats.healthy_servers}
          accent="emerald"
        />
        <MetricCard label="Tools" value={stats.total_tools} accent="neural" />
        <MetricCard label="Invocations" value={stats.total_invocations} />
      </div>

      {/* Server grid */}
      {servers.length === 0 ? (
        <div className="glass-card p-8 text-center">
          <p style={{ color: "var(--text-tertiary)" }}>
            No MCP servers configured yet. Add your first server to get started.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {servers.map((s) => (
            <ServerCard
              key={s.id}
              server={s}
              onStart={() => handleStart(s.id)}
              onStop={() => handleStop(s.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: "emerald" | "neural" | "cyber" | "amber" | "red";
}) {
  const accentColors: Record<string, string> = {
    emerald: "text-emerald-500",
    neural: "text-neural-400",
    cyber: "text-cyber-400",
    amber: "text-amber-500",
    red: "text-red-500",
  };

  return (
    <div className="glass-card p-4">
      <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>
        {label}
      </p>
      <p
        className={`mt-1 text-2xl font-bold ${accent ? accentColors[accent] : ""}`}
        style={accent ? {} : { color: "var(--text-primary)" }}
      >
        {value}
      </p>
    </div>
  );
}
