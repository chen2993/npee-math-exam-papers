/**
 * Preferences → CSS variables (the single mutation point).
 *
 * This is the module that makes the whole theme system cheap: instead of every
 * component subscribing to preferences, we write the handful of user-facing
 * variables onto :root and let CSS derive the rest. A change is one style write.
 *
 * Resolution of `themeMode: "system"` happens here too, so the rest of the app
 * only ever sees `light` or `dark`.
 */

import { accentPreset } from "./presets";
import type { Preferences } from "./types";

export type ResolvedTheme = "light" | "dark";

/** Query the OS colour-scheme preference. */
export function systemTheme(): ResolvedTheme {
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function resolveTheme(mode: Preferences["themeMode"]): ResolvedTheme {
  return mode === "system" ? systemTheme() : mode;
}

/**
 * Apply preferences to the document root.
 *
 * Only `preferences` is read; the returned resolved theme is provided so callers
 * (e.g. a `<meta name="color-scheme">` sync) do not have to recompute it.
 */
export function applyPreferences(preferences: Preferences): ResolvedTheme {
  const root = document.documentElement;
  const resolved = resolveTheme(preferences.themeMode);
  const accent = accentPreset(preferences.accent);

  root.dataset.theme = resolved;
  root.dataset.density = preferences.density;
  root.dataset.fontScale = preferences.fontScale;
  root.dataset.motion = preferences.reduceMotion ? "reduced" : "full";
  root.dataset.contentWidth = preferences.contentWidth;

  root.style.setProperty("--accent", accent.color);
  root.style.setProperty("--accent-hover", accent.hover);
  root.style.setProperty("--radius", `${preferences.radius}px`);

  return resolved;
}

/** Subscribe to OS theme changes; returns an unsubscribe function. */
export function watchSystemTheme(listener: (theme: ResolvedTheme) => void): () => void {
  if (typeof window === "undefined" || !window.matchMedia) return () => {};
  const query = window.matchMedia("(prefers-color-scheme: dark)");
  const handler = () => listener(query.matches ? "dark" : "light");
  query.addEventListener("change", handler);
  return () => query.removeEventListener("change", handler);
}
