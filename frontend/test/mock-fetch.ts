import { vi } from "vitest";

type Reply = { status?: number; body?: unknown; text?: string } | Error;

/**
 * Replaces global fetch for one test. Each reply answers one call in order: a JSON
 * body with a status, raw text, or an Error to simulate a network failure.
 */
export function mockFetch(...replies: Reply[]) {
  const fetchMock = vi.fn();
  for (const reply of replies) {
    if (reply instanceof Error) {
      fetchMock.mockRejectedValueOnce(reply);
    } else {
      fetchMock.mockResolvedValueOnce(
        new Response(reply.text ?? JSON.stringify(reply.body ?? null), {
          status: reply.status ?? 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }
  }
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
