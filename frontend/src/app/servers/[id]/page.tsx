"use client";

import { useParams, useRouter } from "next/navigation";
import { useState, useCallback } from "react";
import { useServer, useTools, useWebSocket } from "@/stores/farm-store";
import {
  startServer,
  stopServer,
  restartServer,
  deleteServer,
} from "@/lib/api";

const STATUS_STYLES: Record<string, { dot: string; label: string }> = {
  HEALTHY: { dot: "bg-emerald-400 animate-pulse", label: "text-emerald-500" },
  STARTING: { dot: "bg-amber-400 animate-pulse", label: "text-amber-500" },
  DEGRADED: { dot: "bg-amber-500", label: "text-amber-500" },
  UNHEALTHY: { dot: "bg-red-500", label: "text-red-500" },
  STOPPED: { dot: "bg-gray-400 dark:bg-gray-600", label: "" },
};

type Tab = "overview" | "tools" | "settings";

export default function ServerDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { server, loading, refresh } = useServer(id);
  const { tools } = useTools();
  const [tab, setTab] = useState<Tab>("overview");
  const [actionLoading, setActionLoading] = useState(false);

  const handleEvent = useCallback(() => {
    refresh();
  }, [refresh]);

  useWebSocket(handleEvent);

  async function handleAction(action: () => Promise<unknown>) {
    setActionLoading(true);
    try {
      await action();
      await refresh();
    } catch {
      // handle error silently for now
    } finally {
      setActionLoading(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Are you sure you want to delete this server?")) return;
    await deleteServer(id);
    router.push("/servers");
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl animate-fade-in">
        <div className="glass-card p-8 text-center">
          <div className="progress-shimmer mx-auto h-1 w-48 rounded-full" />
          <p className="mt-4" style={{ color: "var(--text-tertiary)" }}>
            Loading server...
          </p>
        </div>
      </div>
    );
  }

  if (!server) {
    return (
      <div className="mx-auto max-w-5xl animate-fade-in">
        <div className="glass-card p-8 text-center">
          <p style={{ color: "var(--text-tertiary)" }}>Server not found.</p>
          <button
            onClick={() => router.push("/servers")}
            className="mt-4 rounded-lg bg-neural-600 px-4 py-2 text-sm text-white hover:bg-neural-500"
          >
            Back to Servers
          </button>
        </div>
      </div>
    );
  }

  const style = STATUS_STYLES[server.status] || STATUS_STYLES.STOPPED;
  const serverTools = tools.filter(
    (t) => t.server_namespace === server.namespace
  );

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "tools", label: `Tools (${server.tool_count})` },
    { key: "settings", label: "Settings" },
  ];

  return (
    <div className="mx-auto max-w-5xl animate-fade-in">
      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <button
          onClick={() => router.push("/servers")}
          className="rounded-lg p-1.5 transition-colors hover:bg-neural-500/10"
          style={{ color: "var(--text-tertiary)" }}
        >
          <svg width="20" height="20" fill="none" viewBox="0 0 24 24">
            <path
              d="M15 18l-6-6 6-6"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <span className={`h-3 w-3 rounded-full ${style.dot}`} />
            <h2
              className="text-2xl font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              {server.name}
            </h2>
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
          <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
            {server.image} &middot; Port {server.port}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {server.status === "STOPPED" || server.status === "UNHEALTHY" ? (
            <button
              onClick={() => handleAction(() => startServer(id))}
              disabled={actionLoading}
              className="rounded-lg bg-neural-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neural-500 disabled:opacity-50"
            >
              {actionLoading ? "Starting..." : "Start"}
            </button>
          ) : (
            <>
              <button
                onClick={() => handleAction(() => restartServer(id))}
                disabled={actionLoading}
                className="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                style={{
                  background: "var(--bg-tertiary)",
                  color: "var(--text-secondary)",
                }}
              >
                Restart
              </button>
              <button
                onClick={() => handleAction(() => stopServer(id))}
                disabled={actionLoading}
                className="rounded-lg px-4 py-2 text-sm font-medium text-red-400 transition-colors hover:bg-red-500/10"
              >
                Stop
              </button>
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div
        className="mb-6 flex gap-1 rounded-lg p-1"
        style={{ background: "var(--bg-tertiary)" }}
      >
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-neural-600 text-white"
                : ""
            }`}
            style={
              tab === t.key
                ? {}
                : { color: "var(--text-tertiary)" }
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "overview" && (
        <OverviewTab server={server} style={style} />
      )}
      {tab === "tools" && <ToolsTab tools={serverTools} />}
      {tab === "settings" && (
        <SettingsTab server={server} onDelete={handleDelete} />
      )}
    </div>
  );
}

function OverviewTab({
  server,
  style,
}: {
  server: import("@/lib/api").ServerData;
  style: { dot: string; label: string };
}) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {/* Status card */}
      <div className="glass-card p-5">
        <h3
          className="mb-4 text-sm font-semibold uppercase tracking-wider"
          style={{ color: "var(--text-tertiary)" }}
        >
          Status
        </h3>
        <div className="space-y-3">
          <Row label="Status">
            <span className={`font-medium ${style.label}`}>
              {server.status}
            </span>
          </Row>
          <Row label="Container">
            <span className="font-mono text-xs">
              {server.container_id
                ? server.container_id.substring(0, 12)
                : "None"}
            </span>
          </Row>
          <Row label="Auto Restart">
            <span>{server.auto_restart ? "Enabled" : "Disabled"}</span>
          </Row>
          <Row label="Tools">
            <span className="text-neural-400">{server.tool_count}</span>
          </Row>
        </div>
      </div>

      {/* Config card */}
      <div className="glass-card p-5">
        <h3
          className="mb-4 text-sm font-semibold uppercase tracking-wider"
          style={{ color: "var(--text-tertiary)" }}
        >
          Configuration
        </h3>
        <div className="space-y-3">
          <Row label="Image">
            <span className="font-mono text-xs">{server.image}</span>
          </Row>
          <Row label="Namespace">
            <span className="font-mono text-xs">{server.namespace}</span>
          </Row>
          <Row label="Port">
            <span>{server.port}</span>
          </Row>
          <Row label="Created">
            <span>{new Date(server.created_at).toLocaleString()}</span>
          </Row>
          <Row label="Updated">
            <span>{new Date(server.updated_at).toLocaleString()}</span>
          </Row>
        </div>
      </div>

      {/* Env vars card */}
      {Object.keys(server.env_vars).length > 0 && (
        <div className="glass-card p-5 lg:col-span-2">
          <h3
            className="mb-4 text-sm font-semibold uppercase tracking-wider"
            style={{ color: "var(--text-tertiary)" }}
          >
            Environment Variables
          </h3>
          <div className="space-y-2">
            {Object.entries(server.env_vars).map(([key, value]) => (
              <div
                key={key}
                className="flex items-center gap-3 rounded-lg p-2"
                style={{ background: "var(--bg-tertiary)" }}
              >
                <span
                  className="font-mono text-xs font-semibold"
                  style={{ color: "var(--text-primary)" }}
                >
                  {key}
                </span>
                <span className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                  =
                </span>
                <span
                  className="font-mono text-xs"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {value}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ToolsTab({ tools }: { tools: import("@/lib/api").ToolData[] }) {
  if (tools.length === 0) {
    return (
      <div className="glass-card p-8 text-center">
        <p style={{ color: "var(--text-tertiary)" }}>
          No tools available. Start the server to discover its tools.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {tools.map((tool) => (
        <div key={tool.namespaced_name} className="glass-card p-4">
          <div className="flex items-start justify-between">
            <div>
              <h4
                className="font-mono text-sm font-semibold"
                style={{ color: "var(--text-primary)" }}
              >
                {tool.name}
              </h4>
              {tool.description && (
                <p
                  className="mt-1 text-sm"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {tool.description}
                </p>
              )}
            </div>
            <span
              className={`rounded-full px-2 py-0.5 text-xs ${tool.is_available ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"}`}
            >
              {tool.is_available ? "Available" : "Unavailable"}
            </span>
          </div>
          {tool.input_schema &&
            (tool.input_schema as { properties?: Record<string, unknown> })
              .properties && (
              <div className="mt-3">
                <p
                  className="mb-1.5 text-xs font-medium"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  Parameters
                </p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(
                    (tool.input_schema as { properties: Record<string, { type?: string }> })
                      .properties
                  ).map(([name, schema]) => (
                    <span
                      key={name}
                      className="rounded-md px-2 py-0.5 font-mono text-xs"
                      style={{
                        background: "var(--bg-tertiary)",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {name}: {schema.type || "any"}
                    </span>
                  ))}
                </div>
              </div>
            )}
        </div>
      ))}
    </div>
  );
}

function SettingsTab({
  server,
  onDelete,
}: {
  server: import("@/lib/api").ServerData;
  onDelete: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="glass-card p-5">
        <h3
          className="mb-4 text-sm font-semibold uppercase tracking-wider"
          style={{ color: "var(--text-tertiary)" }}
        >
          Server Information
        </h3>
        <div className="space-y-3">
          <Row label="ID">
            <span className="font-mono text-xs">{server.id}</span>
          </Row>
          <Row label="Name">{server.name}</Row>
          <Row label="Namespace">{server.namespace}</Row>
          <Row label="Image">{server.image}</Row>
        </div>
      </div>

      <div className="glass-card border-red-500/20 p-5">
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-red-400">
          Danger Zone
        </h3>
        <p className="mb-4 text-sm" style={{ color: "var(--text-tertiary)" }}>
          Deleting this server will stop its container and remove all
          configuration.
        </p>
        <button
          onClick={onDelete}
          className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-500"
        >
          Delete Server
        </button>
      </div>
    </div>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm" style={{ color: "var(--text-tertiary)" }}>
        {label}
      </span>
      <span className="text-sm" style={{ color: "var(--text-primary)" }}>
        {children}
      </span>
    </div>
  );
}
