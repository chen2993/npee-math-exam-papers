/**
 * Static presets: accent palettes and the merge/normalise helpers.
 *
 * The accent palettes are plain data (name → hex), exactly like vben's
 * `BUILT_IN_THEME_PRESETS`. Keeping them as data means adding a palette is a
 * one-line change and needs no component edit.
 */

import { DEFAULT_PREFERENCES, type Preferences } from "./types";

interface AccentPreset {
  name: Preferences["accent"];
  label: string;
  /** Base accent; hover and soft variants are derived in CSS. */
  color: string;
  hover: string;
}

export const ACCENT_PRESETS: readonly AccentPreset[] = [
  { name: "teal", label: "青绿", color: "#13776f", hover: "#0f625c" },
  { name: "indigo", label: "靛蓝", color: "#3f4cc4", hover: "#333ea3" },
  { name: "amber", label: "琥珀", color: "#a2660f", hover: "#85540c" },
  { name: "rose", label: "绯红", color: "#a83b52", hover: "#8c3044" },
  { name: "slate", label: "石板", color: "#3f4a56", hover: "#333d47" },
];

export function accentPreset(name: Preferences["accent"]): AccentPreset {
  return ACCENT_PRESETS.find((preset) => preset.name === name) ?? ACCENT_PRESETS[0];
}

/**
 * Merge a stored/partial preference object onto the defaults.
 *
 * Every field is validated against its allowed set, so a value written by an
 * older build, a hand-edited localStorage entry or a future field can never
 * produce an invalid preference (e.g. a density the CSS does not know).
 */
export function mergePreferences(base: Preferences, patch: Partial<Preferences> | null | undefined): Preferences {
  const source = patch ?? {};
  const pick = <T extends string>(value: unknown, allowed: readonly T[], fallback: T): T =>
    allowed.includes(value as T) ? (value as T) : fallback;
  const clampNumber = (value: unknown, min: number, max: number, fallback: number): number => {
    const parsed = typeof value === "number" ? value : Number(value);
    if (!Number.isFinite(parsed)) return fallback;
    return Math.min(max, Math.max(min, parsed));
  };
  return {
    themeMode: pick(source.themeMode, ["light", "dark", "system"] as const, base.themeMode),
    density: pick(source.density, ["compact", "comfortable", "spacious"] as const, base.density),
    fontScale: pick(source.fontScale, ["small", "base", "large"] as const, base.fontScale),
    accent: pick(source.accent, ["teal", "indigo", "amber", "rose", "slate"] as const, base.accent),
    radius: clampNumber(source.radius, 0, 18, base.radius),
    reduceMotion: typeof source.reduceMotion === "boolean" ? source.reduceMotion : base.reduceMotion,
    contentWidth: pick(source.contentWidth, ["fixed", "fluid"] as const, base.contentWidth),
    sidebarCollapsed:
      typeof source.sidebarCollapsed === "boolean" ? source.sidebarCollapsed : base.sidebarCollapsed,
    showBreadcrumb: typeof source.showBreadcrumb === "boolean" ? source.showBreadcrumb : base.showBreadcrumb,
    logRefreshSeconds: clampNumber(source.logRefreshSeconds, 0, 60, base.logRefreshSeconds),
    pageSize: clampNumber(source.pageSize, 10, 200, base.pageSize),
  };
}

export function defaultPreferences(): Preferences {
  return { ...DEFAULT_PREFERENCES };
}
