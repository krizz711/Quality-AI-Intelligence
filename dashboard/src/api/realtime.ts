"use client";

import { useEffect, useRef } from "react";
import { resolveApiBaseUrl, resolveApiKey } from "@/api/apiClient";

export interface RealtimeEvent {
  type: string;
  timestamp?: string;
  process_name?: string;
  part_number?: string;
  characteristic_name?: string;
  equipment_id?: string;
  source_event_id?: string;
  [key: string]: unknown;
}

export interface UseRealtimeStreamOptions {
  path?: string;
  enabled?: boolean;
  heartbeatMs?: number;
  maxBackoffMs?: number;
  /** Interval for the HTTP polling fallback when a WebSocket is unavailable. */
  pollMs?: number;
  onEvent: (event: RealtimeEvent) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
}

/** Emitted by the polling fallback so consumers can refetch on a steady cadence. */
export const POLL_EVENT_TYPE = "poll.tick";

const WS_FAILURES_BEFORE_FALLBACK = 3;

function resolveWsEnvUrl(): string | undefined {
  return typeof globalThis !== "undefined"
    ? (globalThis as typeof globalThis & {
        process?: { env?: { NEXT_PUBLIC_WS_URL?: string } };
      }).process?.env?.NEXT_PUBLIC_WS_URL
    : undefined;
}

/**
 * Build the authenticated WebSocket URL.
 * Returns null when no direct API origin is known (e.g. the REST layer is on
 * the same-origin /api/backend proxy, which cannot carry WebSocket upgrades).
 */
function buildWebSocketUrl(path: string): string | null {
  const wsEnv = resolveWsEnvUrl();
  const baseUrl = resolveApiBaseUrl();

  let url: URL | null = null;
  if (wsEnv) {
    url = new URL(wsEnv);
  } else if (/^https?:\/\//i.test(baseUrl)) {
    url = new URL(baseUrl);
  } else {
    return null;
  }

  url.protocol = url.protocol === "https:" || url.protocol === "wss:" ? "wss:" : "ws:";
  url.pathname = path;

  const token = resolveApiKey();
  if (token) {
    url.searchParams.set("token", token);
  }

  return url.toString();
}

export function useRealtimeStream(options: UseRealtimeStreamOptions) {
  const onEventRef = useRef(options.onEvent);
  const onOpenRef = useRef(options.onOpen);
  const onCloseRef = useRef(options.onClose);
  const onErrorRef = useRef(options.onError);

  useEffect(() => {
    onEventRef.current = options.onEvent;
    onOpenRef.current = options.onOpen;
    onCloseRef.current = options.onClose;
    onErrorRef.current = options.onError;
  }, [options.onEvent, options.onOpen, options.onClose, options.onError]);

  useEffect(() => {
    if (options.enabled === false || typeof window === "undefined") {
      return;
    }

    const path = options.path || "/api/v1/ws/measurements";
    const heartbeatMs = options.heartbeatMs ?? 25000;
    const maxBackoffMs = options.maxBackoffMs ?? 5000;
    const pollMs = options.pollMs ?? 15000;
    const backoffBaseMs = 500;

    let socket: WebSocket | null = null;
    let heartbeatTimer: number | null = null;
    let reconnectTimer: number | null = null;
    let pollTimer: number | null = null;
    let cancelled = false;
    let backoffMs = backoffBaseMs;
    let consecutiveFailures = 0;
    let everConnected = false;

    const clearTimers = () => {
      if (heartbeatTimer !== null) {
        window.clearInterval(heartbeatTimer);
        heartbeatTimer = null;
      }
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    };

    const startPolling = () => {
      if (cancelled || pollTimer !== null) {
        return;
      }
      pollTimer = window.setInterval(() => {
        onEventRef.current({ type: POLL_EVENT_TYPE, timestamp: new Date().toISOString() });
      }, pollMs);
    };

    const scheduleReconnect = () => {
      if (cancelled) {
        return;
      }
      if (!everConnected && consecutiveFailures >= WS_FAILURES_BEFORE_FALLBACK) {
        // The socket endpoint is unreachable from this network — degrade to polling.
        startPolling();
        return;
      }
      reconnectTimer = window.setTimeout(() => {
        connect();
      }, backoffMs);
      backoffMs = Math.min(backoffMs * 2, maxBackoffMs);
    };

    const connect = () => {
      if (cancelled) {
        return;
      }

      const wsUrl = buildWebSocketUrl(path);
      if (!wsUrl) {
        // REST runs through the same-origin proxy; no WS origin configured.
        startPolling();
        return;
      }

      try {
        socket = new WebSocket(wsUrl);
      } catch {
        consecutiveFailures += 1;
        scheduleReconnect();
        return;
      }
      socket.onopen = () => {
        everConnected = true;
        consecutiveFailures = 0;
        backoffMs = backoffBaseMs;
        onOpenRef.current?.();
        clearTimers();
        heartbeatTimer = window.setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "ping", timestamp: new Date().toISOString() }));
          }
        }, heartbeatMs);
      };
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(String(event.data)) as RealtimeEvent;
          onEventRef.current(payload);
        } catch {
          // Ignore malformed payloads.
        }
      };
      socket.onerror = (error) => {
        onErrorRef.current?.(error);
      };
      socket.onclose = () => {
        clearTimers();
        consecutiveFailures += 1;
        onCloseRef.current?.();
        scheduleReconnect();
      };
    };

    connect();

    return () => {
      cancelled = true;
      clearTimers();
      if (pollTimer !== null) {
        window.clearInterval(pollTimer);
        pollTimer = null;
      }
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
      socket = null;
    };
  }, [options.enabled, options.heartbeatMs, options.maxBackoffMs, options.path, options.pollMs]);
}
