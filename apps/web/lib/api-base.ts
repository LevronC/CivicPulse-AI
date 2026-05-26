/**
 * Resolve the API base URL for browser and server contexts.
 *
 * Priority:
 * 1. NEXT_PUBLIC_API_URL — direct backend URL (requires CORS on API)
 * 2. Production without public URL — same-origin /api proxy (recommended on Vercel)
 * 3. Local dev — http://localhost:8000
 */
export function getApiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (configured) {
    return configured;
  }

  if (process.env.NODE_ENV === "production") {
    return "/api";
  }

  return "http://localhost:8000";
}
