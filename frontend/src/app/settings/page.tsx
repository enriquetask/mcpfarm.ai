"use client";

import { useState } from "react";
import { useAPIKeys } from "@/stores/farm-store";
import { createAPIKey, revokeAPIKey } from "@/lib/api";

export default function SettingsPage() {
  const { keys, loading, refresh } = useAPIKeys();
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState("");
  const [creating, setCreating] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;

    setCreating(true);
    setError(null);
    try {
      const scopeList = scopes
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const result = await createAPIKey(name.trim(), scopeList);
      setNewKey(result.key);
      setName("");
      setScopes("");
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create key");
    } finally {
      setCreating(false);
    }
  }

  async function handleRevoke(id: string) {
    try {
      await revokeAPIKey(id);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to revoke key");
    }
  }

  function handleCopy() {
    if (newKey) {
      navigator.clipboard.writeText(newKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <div className="animate-fade-in">
      <h2
        className="mb-6 text-2xl font-semibold"
        style={{ color: "var(--text-primary)" }}
      >
        Settings
      </h2>

      {/* Create API Key */}
      <div className="glass-card p-6 mb-6">
        <h3
          className="text-lg font-medium mb-4"
          style={{ color: "var(--text-primary)" }}
        >
          Create API Key
        </h3>
        <form onSubmit={handleCreate} className="flex gap-3 items-end flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <label
              className="block text-sm mb-1"
              style={{ color: "var(--text-secondary)" }}
            >
              Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. my-agent"
              className="w-full px-3 py-2 rounded-lg border text-sm"
              style={{
                backgroundColor: "var(--bg-secondary)",
                borderColor: "var(--border-primary)",
                color: "var(--text-primary)",
              }}
            />
          </div>
          <div className="flex-1 min-w-[200px]">
            <label
              className="block text-sm mb-1"
              style={{ color: "var(--text-secondary)" }}
            >
              Scopes (comma-separated, optional)
            </label>
            <input
              type="text"
              value={scopes}
              onChange={(e) => setScopes(e.target.value)}
              placeholder="e.g. echo,calc (empty = all)"
              className="w-full px-3 py-2 rounded-lg border text-sm"
              style={{
                backgroundColor: "var(--bg-secondary)",
                borderColor: "var(--border-primary)",
                color: "var(--text-primary)",
              }}
            />
          </div>
          <button
            type="submit"
            disabled={creating || !name.trim()}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            style={{
              backgroundColor: "var(--accent-primary)",
              color: "white",
              opacity: creating || !name.trim() ? 0.5 : 1,
            }}
          >
            {creating ? "Creating..." : "Create Key"}
          </button>
        </form>

        {error && (
          <div
            className="mt-3 p-3 rounded-lg text-sm"
            style={{
              backgroundColor: "rgba(239, 68, 68, 0.1)",
              color: "var(--status-error)",
            }}
          >
            {error}
          </div>
        )}
      </div>

      {/* Newly Created Key Banner */}
      {newKey && (
        <div
          className="glass-card p-4 mb-6 border-2"
          style={{ borderColor: "var(--status-warning)" }}
        >
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <p
                className="text-sm font-medium mb-1"
                style={{ color: "var(--status-warning)" }}
              >
                Save this key now - it will not be shown again!
              </p>
              <code
                className="block text-sm break-all p-2 rounded"
                style={{
                  backgroundColor: "var(--bg-secondary)",
                  color: "var(--text-primary)",
                }}
              >
                {newKey}
              </code>
            </div>
            <div className="flex gap-2 shrink-0">
              <button
                onClick={handleCopy}
                className="px-3 py-1.5 rounded text-sm font-medium transition-colors"
                style={{
                  backgroundColor: "var(--accent-primary)",
                  color: "white",
                }}
              >
                {copied ? "Copied!" : "Copy"}
              </button>
              <button
                onClick={() => setNewKey(null)}
                className="px-3 py-1.5 rounded text-sm transition-colors"
                style={{
                  backgroundColor: "var(--bg-tertiary)",
                  color: "var(--text-secondary)",
                }}
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {/* API Keys List */}
      <div className="glass-card p-6">
        <h3
          className="text-lg font-medium mb-4"
          style={{ color: "var(--text-primary)" }}
        >
          API Keys
        </h3>

        {loading ? (
          <p style={{ color: "var(--text-tertiary)" }}>Loading...</p>
        ) : keys.length === 0 ? (
          <p style={{ color: "var(--text-tertiary)" }}>
            No API keys yet. Create one above.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr
                  style={{
                    color: "var(--text-secondary)",
                    borderBottom: "1px solid var(--border-primary)",
                  }}
                >
                  <th className="text-left py-2 pr-4">Name</th>
                  <th className="text-left py-2 pr-4">Scopes</th>
                  <th className="text-left py-2 pr-4">Status</th>
                  <th className="text-left py-2 pr-4">Created</th>
                  <th className="text-right py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {keys.map((k) => (
                  <tr
                    key={k.id}
                    style={{
                      borderBottom: "1px solid var(--border-primary)",
                    }}
                  >
                    <td
                      className="py-3 pr-4 font-medium"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {k.name}
                    </td>
                    <td
                      className="py-3 pr-4"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {k.scopes.length > 0 ? k.scopes.join(", ") : "all"}
                    </td>
                    <td className="py-3 pr-4">
                      <span
                        className="px-2 py-0.5 rounded-full text-xs font-medium"
                        style={{
                          backgroundColor: k.is_active
                            ? "rgba(16, 185, 129, 0.1)"
                            : "rgba(239, 68, 68, 0.1)",
                          color: k.is_active
                            ? "var(--status-healthy)"
                            : "var(--status-error)",
                        }}
                      >
                        {k.is_active ? "Active" : "Revoked"}
                      </span>
                    </td>
                    <td
                      className="py-3 pr-4"
                      style={{ color: "var(--text-tertiary)" }}
                    >
                      {new Date(k.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 text-right">
                      {k.is_active && (
                        <button
                          onClick={() => handleRevoke(k.id)}
                          className="px-3 py-1 rounded text-xs font-medium transition-colors"
                          style={{
                            backgroundColor: "rgba(239, 68, 68, 0.1)",
                            color: "var(--status-error)",
                          }}
                        >
                          Revoke
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
