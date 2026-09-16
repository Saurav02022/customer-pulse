import { useEffect, useState } from "react";

import type { ApiResult } from "./api";

export type RequestState<T> = { status: "loading" } | ApiResult<T>;

type Settled<K, T> = { key: K; attempt: number; result: ApiResult<T> };

/**
 * Runs one read-only request for `key` and exposes its state. A result that arrives after
 * the key changed, or after the component unmounted, is ignored, so a slow response for
 * one relationship never overwrites another. `retry` asks for the same data again.
 */
export function useApiRequest<K, T>(
  request: (key: K) => Promise<ApiResult<T>>,
  key: K,
) {
  const [attempt, setAttempt] = useState(0);
  const [settled, setSettled] = useState<Settled<K, T> | null>(null);

  useEffect(() => {
    let cancelled = false;
    request(key).then((result) => {
      if (!cancelled) setSettled({ key, attempt, result });
    });
    return () => {
      cancelled = true;
    };
  }, [request, key, attempt]);

  const state: RequestState<T> =
    settled !== null && settled.key === key && settled.attempt === attempt
      ? settled.result
      : { status: "loading" };

  const retry = () => setAttempt((current) => current + 1);

  return { state, retry };
}
