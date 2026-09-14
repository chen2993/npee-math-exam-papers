/**
 * The typed preference object.
 *
 * Everything a user can change about appearance and reading comfort lives here,
 * in one flat, serialisable shape. Components never read these directly; the
 * store projects the few visual ones onto CSS variables (see `apply.ts`), so a
 * preference change is a single DOM write rather than a re-render cascade.
 *
 * This mirrors vue-vben-admin's `AppPreferences`: one source of truth, a
 * versioned persistence payload, and a strict "defaults + partial override"
 * merge so an unknown or stale key can never crash the app.
 */

export type ThemeMode = "light" | "dark" | "system";
export type Density = "compact" | "comfortable" | "spacious";
export type FontScale = "small" | "base" | "large";
export type AccentName = "teal" | "indigo" | "amber" | "rose" | "slate";

export interface Preferences {
  /** Light, dark or follow the operating system. */
  themeMode: ThemeMode;
  /** Vertical rhythm; independent of type size. */
  density: Density;
  /** Type size only. */
  fontScale: FontScale;
  /** Named accent palette; drives every derived accent colour. */
  accent: AccentName;
  /** Corner rounding in pixels. */
  radius: number;
  /** Motion for transitions; disabling respects reduced-motion users. */
  reduceMotion: boolean;
  /** Width of the reading area: fixed column or fluid. */
  contentWidth: "fixed" | "fluid";
  /** Keep the sidebar collapsed on load. */
  sidebarCollapsed: boolean;
  /** Show the breadcrumb trail in the header. */
  showBreadcrumb: boolean;
  /** Auto-refresh interval for the activity log, in seconds (0 disables). */
  logRefreshSeconds: number;
  /** Rows per page in the paper catalogue. */
  pageSize: number;
}

/** Non-visual defaults that the API or storage may override at runtime. */
export const DEFAULT_PREFERENCES: Preferences = {
  themeMode: "light",
  density: "comfortable",
  fontScale: "base",
  accent: "teal",
  radius: 7,
  reduceMotion: false,
  contentWidth: "fluid",
  sidebarCollapsed: false,
  showBreadcrumb: true,
  logRefreshSeconds: 3,
  pageSize: 60,
};
