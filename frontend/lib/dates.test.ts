import { describe, expect, it } from "vitest";

import { formatDate, isDateOnly } from "./dates";

describe("formatDate", () => {
  it("formats a date-only value with the month as a word", () => {
    expect(formatDate("2026-08-20")).toBe("20 Aug 2026");
    expect(formatDate("2026-05-12")).toBe("12 May 2026");
  });

  it("never shifts the day, whatever the browser time zone", () => {
    // `new Date("2026-01-01")` is midnight UTC, which is still 31 Dec 2025 in any
    // time zone west of Greenwich. The helper reads the string, so the day holds.
    expect(formatDate("2026-01-01")).toBe("1 Jan 2026");
    expect(formatDate("2025-12-31")).toBe("31 Dec 2025");
  });

  it("returns anything that is not a date-only value unchanged", () => {
    expect(formatDate("2026-08-20T00:00:00Z")).toBe("2026-08-20T00:00:00Z");
    expect(formatDate("2026-13-01")).toBe("2026-13-01");
    expect(formatDate("")).toBe("");
  });
});

describe("isDateOnly", () => {
  it("accepts only YYYY-MM-DD strings", () => {
    expect(isDateOnly("2026-08-20")).toBe(true);
    expect(isDateOnly("2026-08-20T00:00:00Z")).toBe(false);
    expect(isDateOnly("20 Aug 2026")).toBe(false);
    expect(isDateOnly(20260820)).toBe(false);
    expect(isDateOnly(null)).toBe(false);
  });
});
