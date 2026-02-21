"use client";

import { useEffect, useState, useCallback } from "react";
import type { ServerData, Stats, ToolData, InvocationData, APIKeyData } from "@/lib/api";
import { fetchServers, fetchStats, fetchTools, fetchServer, fetchInvocations, fetchAPIKeys } from "@/lib/api";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

export function useStats() {
  const [stats, setStats] = useState<Stats>({
    total_servers: 0,
    healthy_servers: 0,
    total_tools: 0,
    total_invocations: 0,
  });
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchStats();
      setStats(data);
    } catch {
      // gateway not reachable
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { stats, loading, refresh };
}

export function useServers() {
  const [servers, setServers] = useState<ServerData[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchServers();
      setServers(data);
    } catch {
      // gateway not reachable
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { servers, loading, refresh };
}

export function useTools() {
  const [tools, setTools] = useState<ToolData[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchTools();
      setTools(data);
    } catch {
      // gateway not reachable
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { tools, loading, refresh };
}

export function useServer(id: string) {
  const [server, setServer] = useState<ServerData | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchServer(id);
      setServer(data);
    } catch {
      // gateway not reachable
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { server, loading, refresh };
}

export function useInvocations(limit = 50) {
  const [invocations, setInvocations] = useState<InvocationData[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchInvocations(limit);
      setInvocations(data.invocations);
      setTotal(data.total);
    } catch {
      // gateway not reachable
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { invocations, total, loading, refresh };
}

export function useAPIKeys() {
  const [keys, setKeys] = useState<APIKeyData[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchAPIKeys();
      setKeys(data);
    } catch {
      // gateway not reachable
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { keys, loading, refresh };
}

export interface WSEvent {
  type: string;
  data: Record<string, unknown>;
}

export function useWebSocket(onEvent?: (event: WSEvent) => void) {
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: NodeJS.Timeout;

    function connect() {
      ws = new WebSocket(WS_URL);
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        reconnectTimer = setTimeout(connect, 3000);
      };
      ws.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data) as WSEvent;
          onEvent?.(event);
        } catch {
          // ignore malformed messages
        }
      };
    }

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [onEvent]);

  return { connected };
}
