// API dates are plain YYYY-MM-DD strings with no time or time zone. They are formatted
// from the string itself, never through `new Date()`, which can shift the day.
const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;
const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

export function isDateOnly(value: unknown): value is string {
  return typeof value === "string" && DATE_ONLY.test(value);
}

/** "2026-08-20" becomes "20 Aug 2026". Anything else is returned unchanged. */
export function formatDate(value: string): string {
  const match = DATE_ONLY.exec(value);
  if (!match) return value;
  const [, year, month, day] = match;
  const monthName = MONTHS[Number(month) - 1];
  return monthName ? `${Number(day)} ${monthName} ${year}` : value;
}
