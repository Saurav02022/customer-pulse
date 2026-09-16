"use client";

import { useParams } from "next/navigation";
import type { ReactNode } from "react";

import { AssessmentsProvider } from "../assessments";
import { RelationshipList } from "./relationship-list";

/**
 * Composes the relationship list and the detail slot for both routes. The selected
 * relationship comes only from the URL. Wide screens show both panes; on narrow screens
 * the route decides which one is the screen. The list lives here, above the pages, so
 * it keeps its data and scroll position while relationships open and close. Assessment
 * work lives here too, so the list and the detail share one request pool.
 */
export function RelationshipWorkspace({ children }: { children: ReactNode }) {
  const params = useParams<{ id?: string }>();
  const selectedId = typeof params.id === "string" ? params.id : null;
  const detailIsOpen = selectedId !== null;

  return (
    <AssessmentsProvider>
      <div className="mx-auto grid w-full max-w-6xl flex-1 md:grid-cols-[20rem_minmax(0,1fr)]">
        <div
          className={`${detailIsOpen ? "hidden md:block" : ""} md:sticky md:top-0 md:max-h-dvh md:self-start md:overflow-y-auto`}
        >
          <RelationshipList selectedId={selectedId} />
        </div>
        <div
          className={`${detailIsOpen ? "" : "hidden md:block"} px-4 py-6 md:border-l md:border-neutral-200 md:px-8`}
        >
          {children}
        </div>
      </div>
    </AssessmentsProvider>
  );
}
