"use client";

import { useEffect, useState } from "react";
import { resolveApiBaseUrl } from "@/api/apiClient";

export type HealthState = "checking" | "online" | "offline";

export function useBackendHealth(intervalMs = 60000) {
  const [health, setHealth] = useState<HealthState>("checking");

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      try {
        const response = await fetch(`${resolveApiBaseUrl()}/health/live`, {
          signal: AbortSignal.timeout(5000),
        });
        if (!cancelled) {
          setHealth(response.ok ? "online" : "offline");
        }
      } catch {
        if (!cancelled) {
          setHealth("offline");
        }
      }
    };

    void check();
    const timer = window.setInterval(() => void check(), intervalMs);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [intervalMs]);

  return health;
}
