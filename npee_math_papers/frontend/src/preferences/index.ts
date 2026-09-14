export { PreferencesProvider, usePreferences, PREFERENCES_STORAGE_KEY, loadStoredPreferences, savePreferences } from "./store";
export { applyPreferences, resolveTheme, systemTheme, watchSystemTheme } from "./apply";
export { ACCENT_PRESETS, accentPreset, defaultPreferences, mergePreferences } from "./presets";
export { DEFAULT_PREFERENCES } from "./types";
export type { AccentName, Density, FontScale, Preferences, ThemeMode } from "./types";
