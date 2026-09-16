// Public configuration. NEXT_PUBLIC_* values are inlined into the browser bundle, so they
// are never secrets. The fallback matches the local FastAPI address.
const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export const apiBaseUrl = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL
).replace(/\/+$/, "");
