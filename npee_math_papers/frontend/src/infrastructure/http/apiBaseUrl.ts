/**
 * Resolve the API origin at runtime.
 *
 * Why this exists: in development Vite proxies ``/api`` to the backend, so a
 * relative base works. In production the launcher serves ``dist/`` with
 * ``python -m http.server``, which has **no proxy and no SPA fallback** — a
 * relative ``/api`` would 404 on the static server itself.
 *
 * The launcher exports ``NPEE_API_URL`` (see ``launcher/main.py``); the build
 * step bakes it in as ``VITE_API_BASE_URL``. This module also reads the
 * launcher variable and the page's own ``?api=`` parameter so a pre-built
 * bundle can still be pointed at a non-default backend without a rebuild.
 */

declare global {
  interface Window {
    NPEE_API_URL?: string;
  }
}

const DEFAULT_BASE = "/api";

/** Normalise a base so it never ends with a slash. */
function normalize(value: string): string {
  return value.replace(/\/+$/, "");
}

/**
 * The base URL all gateways should use.
 *
 * Resolution order (first non-empty wins):
 * 1. ``VITE_API_BASE_URL`` — baked in at build time;
 * 2. ``window.NPEE_API_URL`` — injected by the serving page;
 * 3. ``?api=`` query parameter — for ad-hoc pointing without a rebuild;
 * 4. ``/api`` — the development proxy.
 */
export function resolveApiBaseUrl(): string {
  const baked = typeof import.meta.env !== "undefined" ? import.meta.env.VITE_API_BASE_URL : "";
  if (baked && baked.trim()) return normalize(baked.trim());

  if (typeof window !== "undefined") {
    const injected = window.NPEE_API_URL;
    if (injected && injected.trim()) return normalize(injected.trim());

    try {
      const param = new URLSearchParams(window.location.search).get("api");
      if (param && param.trim()) return normalize(param.trim());
    } catch {
      /* no window.location (SSR/tests) */
    }
  }

  return DEFAULT_BASE;
}
