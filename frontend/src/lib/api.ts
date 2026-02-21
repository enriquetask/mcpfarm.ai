const GATEWAY_URL =
  process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

export interface ServerData {
  id: string;
  name: string;
  namespace: string;
  image: string;
  port: number;
  env_vars: Record<string, string>;
  status: string;
  container_id: string | null;
  auto_restart: boolean;
  tool_count: number;
  created_at: string;
  updated_at: string;
}

export interface ToolData {
  name: string;
  namespaced_name: string;
  description: string | null;
  input_schema: Record<string, unknown>;
  server_namespace: string;
  is_available: boolean;
}

export interface Stats {
  total_servers: number;
  healthy_servers: number;
  total_tools: number;
  total_invocations: number;
}

export interface InvocationData {
  id: string;
  tool_id: string | null;
  server_id: string;
  caller_id: string | null;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown> | null;
  duration_ms: number | null;
  status: string;
  created_at: string;
}

export interface ToolCallResult {
  result: unknown;
  duration_ms: number;
  invocation_id: string;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...init?.headers as Record<string, string>,
  };
  if (API_KEY) {
    headers["Authorization"] = `Bearer ${API_KEY}`;
  }
  const res = await fetch(`${GATEWAY_URL}${path}`, {
    ...init,
    headers,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

export async function fetchStats(): Promise<Stats> {
  return apiFetch<Stats>("/api/stats");
}

export async function fetchServers(): Promise<ServerData[]> {
  const data = await apiFetch<{ servers: ServerData[]; total: number }>(
    "/api/servers/"
  );
  return data.servers;
}

export async function fetchTools(): Promise<ToolData[]> {
  const data = await apiFetch<{ tools: ToolData[]; total: number }>(
    "/api/tools/"
  );
  return data.tools;
}

export async function createServer(
  body: Omit<ServerData, "id" | "status" | "container_id" | "tool_count" | "created_at" | "updated_at">
): Promise<ServerData> {
  return apiFetch<ServerData>("/api/servers/", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function startServer(id: string): Promise<ServerData> {
  return apiFetch<ServerData>(`/api/servers/${id}/start`, { method: "POST" });
}

export async function stopServer(id: string): Promise<ServerData> {
  return apiFetch<ServerData>(`/api/servers/${id}/stop`, { method: "POST" });
}

export async function restartServer(id: string): Promise<ServerData> {
  return apiFetch<ServerData>(`/api/servers/${id}/restart`, { method: "POST" });
}

export async function deleteServer(id: string): Promise<void> {
  await fetch(`${GATEWAY_URL}/api/servers/${id}`, { method: "DELETE" });
}

export async function fetchServer(id: string): Promise<ServerData> {
  return apiFetch<ServerData>(`/api/servers/${id}`);
}

export async function fetchInvocations(
  limit = 50,
  offset = 0
): Promise<{ invocations: InvocationData[]; total: number }> {
  return apiFetch<{ invocations: InvocationData[]; total: number }>(
    `/api/invocations?limit=${limit}&offset=${offset}`
  );
}

export async function callTool(
  toolName: string,
  args: Record<string, unknown>
): Promise<ToolCallResult> {
  return apiFetch<ToolCallResult>("/api/tools/call", {
    method: "POST",
    body: JSON.stringify({ tool_name: toolName, arguments: args }),
  });
}

// ── API Key types and functions ──────────────────────────────

export interface APIKeyData {
  id: string;
  name: string;
  scopes: string[];
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
}

export interface APIKeyCreatedData extends APIKeyData {
  key: string;
}

export async function createAPIKey(
  name: string,
  scopes: string[] = []
): Promise<APIKeyCreatedData> {
  return apiFetch<APIKeyCreatedData>("/api/keys/", {
    method: "POST",
    body: JSON.stringify({ name, scopes }),
  });
}

export async function fetchAPIKeys(): Promise<APIKeyData[]> {
  const data = await apiFetch<{ keys: APIKeyData[]; total: number }>(
    "/api/keys/"
  );
  return data.keys;
}

export async function revokeAPIKey(id: string): Promise<void> {
  await apiFetch<void>(`/api/keys/${id}`, { method: "DELETE" });
}
