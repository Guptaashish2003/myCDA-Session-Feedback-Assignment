"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * Loads a GET endpoint and tracks loading / error state.
 * Every card that reads data uses this, so loading and error handling
 * live in one place.
 */
export function useApiResource<T>(path: string | null, errorMessage = "Could not load data.") {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(path !== null);
  const [error, setError] = useState("");

  const reload = useCallback(
    async (silent = false) => {
      if (path === null) return;
      if (!silent) setLoading(true);
      try {
        setData(await api.get<T>(path));
        setError("");
      } catch {
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    },
    [path, errorMessage]
  );

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, setData, loading, error, reload };
}
