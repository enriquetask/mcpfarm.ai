"use client";

import { useState, useCallback } from "react";
import { useServers, useWebSocket } from "@/stores/farm-store";
import { ServerCard } from "@/components/server-card";
import {
  createServer,
  startServer,
  stopServer,
  deleteServer,
} from "@/lib/api";

export default function ServersPage() {
  const { servers, refresh } = useServers();
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    namespace: "",
    image: "",
    port: 9001,
    auto_restart: true,
  });

  const handleEvent = useCallback(() => {
    refresh();
  }, [refresh]);

  useWebSocket(handleEvent);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    await createServer({ ...formData, env_vars: {} });
    setShowForm(false);
    setFormData({ name: "", namespace: "", image: "", port: 9001, auto_restart: true });
    refresh();
  }

  async function handleStart(id: string) {
    await startServer(id);
    refresh();
  }

  async function handleStop(id: string) {
    await stopServer(id);
    refresh();
  }

  async function handleDelete(id: string) {
    await deleteServer(id);
    refresh();
  }

  return (
    <div className="mx-auto max-w-7xl animate-fade-in">
      <div className="mb-6 flex items-center justify-between">
        <h2
          className="text-2xl font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Servers
        </h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-lg bg-neural-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neural-500"
        >
          {showForm ? "Cancel" : "Add Server"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="glass-card mb-6 p-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label
                className="mb-1 block text-sm"
                style={{ color: "var(--text-secondary)" }}
              >
                Name
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                className="w-full rounded-lg border px-3 py-2 text-sm focus:border-neural-500 focus:outline-none transition-colors"
                style={{
                  background: "var(--bg-tertiary)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                }}
                placeholder="Echo Server"
              />
            </div>
            <div>
              <label
                className="mb-1 block text-sm"
                style={{ color: "var(--text-secondary)" }}
              >
                Namespace
              </label>
              <input
                type="text"
                required
                pattern="^[a-z][a-z0-9_]*$"
                value={formData.namespace}
                onChange={(e) =>
                  setFormData({ ...formData, namespace: e.target.value })
                }
                className="w-full rounded-lg border px-3 py-2 text-sm focus:border-neural-500 focus:outline-none transition-colors"
                style={{
                  background: "var(--bg-tertiary)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                }}
                placeholder="echo"
              />
            </div>
            <div>
              <label
                className="mb-1 block text-sm"
                style={{ color: "var(--text-secondary)" }}
              >
                Docker Image
              </label>
              <input
                type="text"
                required
                value={formData.image}
                onChange={(e) =>
                  setFormData({ ...formData, image: e.target.value })
                }
                className="w-full rounded-lg border px-3 py-2 text-sm focus:border-neural-500 focus:outline-none transition-colors"
                style={{
                  background: "var(--bg-tertiary)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                }}
                placeholder="mcpfarmai-echo-server"
              />
            </div>
            <div>
              <label
                className="mb-1 block text-sm"
                style={{ color: "var(--text-secondary)" }}
              >
                Port
              </label>
              <input
                type="number"
                value={formData.port}
                onChange={(e) =>
                  setFormData({ ...formData, port: parseInt(e.target.value) })
                }
                className="w-full rounded-lg border px-3 py-2 text-sm focus:border-neural-500 focus:outline-none transition-colors"
                style={{
                  background: "var(--bg-tertiary)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                }}
              />
            </div>
          </div>
          <button
            type="submit"
            className="mt-4 rounded-lg bg-neural-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neural-500"
          >
            Create Server
          </button>
        </form>
      )}

      {servers.length === 0 ? (
        <div className="glass-card p-8 text-center">
          <p style={{ color: "var(--text-tertiary)" }}>
            No servers yet. Click Add Server above.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {servers.map((s) => (
            <div key={s.id} className="relative">
              <ServerCard
                server={s}
                onStart={() => handleStart(s.id)}
                onStop={() => handleStop(s.id)}
              />
              <button
                onClick={() => handleDelete(s.id)}
                className="absolute right-2 top-2 rounded-lg p-1 transition-colors hover:text-red-400"
                style={{ color: "var(--text-tertiary)" }}
                title="Delete server"
              >
                <svg
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
