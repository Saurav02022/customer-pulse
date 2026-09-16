"use client";

import {
  createContext,
  use,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  fetchAssessment,
  type AssessmentFailure,
  type AssessmentFetchResult,
} from "./api";
import type {
  AssessmentResult,
  AssessmentState,
  ListAssessed,
  RelationshipSummary,
  UnavailableCause,
} from "./types";

/**
 * At most this many assessment requests run at once, for the list and the detail
 * together. Work scheduling, not business logic (technical design, section 11.2).
 */
export const MAX_ACTIVE_ASSESSMENTS = 2;

export type AssessmentWork =
  | { status: "idle" }
  | { status: "queued" }
  | { status: "assessing" }
  | { status: "failed"; failure: AssessmentFailure };

export type AssessmentEntry = {
  /** State and reason from the list, when storage already had them. */
  summary: ListAssessed | null;
  /** The full result from the assessment route, or an unavailable cause. */
  full: AssessmentResult | null;
  /** Request work for the full result. "assessing" only while a request is in flight. */
  work: AssessmentWork;
  /** True once a request has started for it in this page load. */
  requested: boolean;
};

type Entries = ReadonlyMap<string, AssessmentEntry>;

function entryAfter(
  entry: AssessmentEntry,
  result: AssessmentFetchResult,
): AssessmentEntry {
  switch (result.status) {
    case "ok":
      return { ...entry, full: result.data, work: { status: "idle" } };
    case "not_found":
      // The facts say it exists, so the assessment route disagreeing is not explained.
      return { ...entry, work: { status: "failed", failure: "unknown" } };
    case "failed":
      return { ...entry, work: { status: "failed", failure: result.failure } };
  }
}

const NEW_ENTRY: AssessmentEntry = {
  summary: null,
  full: null,
  work: { status: "idle" },
  requested: false,
};

/**
 * A small promise pool. Ids wait in `queue` in the order they were asked for; a detail
 * request or a retry goes to the front. Each id is requested only when nothing is known,
 * queued or running for it, so nothing is assessed twice in one page load.
 */
function createScheduler(publish: (entries: Entries) => void) {
  const entries = new Map<string, AssessmentEntry>();
  let queue: string[] = [];
  const running = new Set<string>();
  // Null while unmounted. Results from an older controller are ignored.
  let controller: AbortController | null = null;

  const set = (id: string, change: Partial<AssessmentEntry>) =>
    entries.set(id, { ...(entries.get(id) ?? NEW_ENTRY), ...change });

  function pump() {
    const current = controller;
    if (current === null) return;
    while (running.size < MAX_ACTIVE_ASSESSMENTS && queue.length > 0) {
      const id = queue.shift()!;
      running.add(id);
      set(id, { work: { status: "assessing" }, requested: true });
      void fetchAssessment(id, current.signal).then((result) => {
        if (current !== controller) return;
        running.delete(id);
        entries.set(id, entryAfter(entries.get(id) ?? NEW_ENTRY, result));
        pump();
      });
    }
    publish(new Map(entries));
  }

  function enqueueFirst(id: string) {
    queue = [id, ...queue.filter((queued) => queued !== id)];
    set(id, { work: { status: "queued" } });
  }

  return {
    start() {
      controller = new AbortController();
      pump();
    },

    stop() {
      controller?.abort();
      controller = null;
      // Interrupted work goes back to the front, in case the provider mounts again.
      for (const id of running) set(id, { work: { status: "queued" } });
      queue = [...running, ...queue];
      running.clear();
    },

    /** Records what the list knows, and queues every relationship it has no result for. */
    addListed(rows: RelationshipSummary[]) {
      for (const row of rows) {
        const entry = entries.get(row.id);
        if (row.assessment === null) {
          if (entry === undefined) {
            queue.push(row.id);
            set(row.id, { work: { status: "queued" } });
          }
        } else if (row.assessment.status === "unavailable") {
          // The same answer the assessment route would give.
          if (!entry?.full) set(row.id, { full: row.assessment });
        } else {
          set(row.id, { summary: row.assessment });
        }
      }
      pump();
    },

    /** The detail needs the full result. Moves queued work to the front. */
    requestFull(id: string) {
      const entry = entries.get(id) ?? NEW_ENTRY;
      const waiting = entry.work.status === "queued";
      if (entry.full || !(waiting || entry.work.status === "idle")) return;
      enqueueFirst(id);
      pump();
    },

    /** "Try again" after a temporary failure: this relationship only. */
    retry(id: string) {
      if (entries.get(id)?.work.status !== "failed") return;
      enqueueFirst(id);
      pump();
    },
  };
}

type Scheduler = ReturnType<typeof createScheduler>;

type AssessmentsValue = Pick<
  Scheduler,
  "addListed" | "requestFull" | "retry"
> & {
  entries: Entries;
};

const AssessmentsContext = createContext<AssessmentsValue | null>(null);

/** Owns assessment work for the list and the detail, so both share one pool. */
export function AssessmentsProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<Entries>(() => new Map());
  const [scheduler] = useState(() => createScheduler(setEntries));

  useEffect(() => {
    scheduler.start();
    return () => scheduler.stop();
  }, [scheduler]);

  const value = useMemo(
    () => ({
      entries,
      addListed: scheduler.addListed,
      requestFull: scheduler.requestFull,
      retry: scheduler.retry,
    }),
    [entries, scheduler],
  );
  return <AssessmentsContext value={value}>{children}</AssessmentsContext>;
}

export function useAssessments(): AssessmentsValue {
  const value = use(AssessmentsContext);
  if (value === null) {
    throw new Error("useAssessments needs an AssessmentsProvider above it.");
  }
  return value;
}

// --- what each view shows ---

export type RowAssessment =
  | { kind: "assessed"; state: AssessmentState; reason: string }
  | { kind: "unavailable"; cause: UnavailableCause | AssessmentFailure }
  /** No result yet. `active` is true only while its request is in flight. */
  | { kind: "pending"; active: boolean };

export function rowAssessment(
  listed: RelationshipSummary["assessment"],
  entry: AssessmentEntry | undefined,
): RowAssessment {
  const result = entry?.full ?? entry?.summary ?? listed;
  if (result?.status === "assessed") {
    const reason =
      typeof result.reason === "string" ? result.reason : result.reason.text;
    return { kind: "assessed", state: result.state, reason };
  }
  if (result?.status === "unavailable") {
    return { kind: "unavailable", cause: result.cause };
  }
  if (entry?.work.status === "failed") {
    return { kind: "unavailable", cause: entry.work.failure };
  }
  return { kind: "pending", active: entry?.work.status === "assessing" };
}

export type DetailAssessment =
  | { kind: "ready"; assessment: AssessmentResult }
  | { kind: "failed"; failure: AssessmentFailure }
  | { kind: "pending"; active: boolean };

export function detailAssessment(
  entry: AssessmentEntry | undefined,
): DetailAssessment {
  if (entry?.full) return { kind: "ready", assessment: entry.full };
  if (entry?.work.status === "failed") {
    return { kind: "failed", failure: entry.work.failure };
  }
  return { kind: "pending", active: entry?.work.status === "assessing" };
}
