/**
 * Preferences store: context + versioned persistence.
 *
 * The store owns the preference object, applies it to the document on every
 * change, and persists it. Persistence is versioned (like the composition
 * drafts) so a future shape change is detectable rather than silently misread.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { applyPreferences, watchSystemTheme } from "./apply";
import { defaultPreferences, mergePreferences } from "./presets";
import type { Preferences } from "./types";

export const PREFERENCES_STORAGE_KEY = "npee-preferences-v1";
const SCHEMA_VERSION = 1;

interface StoredPreferences {
  schema_version: number;
  preferences: Partial<Preferences>;
}

/** Read persisted preferences, tolerating any corruption. */
export function loadStoredPreferences(key = PREFERENCES_STORAGE_KEY): Partial<Preferences> {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as StoredPreferences | Partial<Preferences>;
    if (parsed && typeof parsed === "object" && "preferences" in parsed) {
      return ((parsed as StoredPreferences).preferences ?? {}) as Partial<Preferences>;
    }
    return parsed as Partial<Preferences>;
  } catch {
    try {
      localStorage.removeItem(key);
    } catch {
      /* storage disabled */
    }
    return {};
  }
}

export function savePreferences(preferences: Preferences, key = PREFERENCES_STORAGE_KEY): void {
  try {
    const payload: StoredPreferences = { schema_version: SCHEMA_VERSION, preferences };
    localStorage.setItem(key, JSON.stringify(payload));
  } catch {
    /* quota or disabled storage: preferences stay in memory for this session */
  }
}

interface PreferencesContextValue {
  preferences: Preferences;
  /** Merge a partial patch; unknown fields are ignored. */
  update: (patch: Partial<Preferences>) => void;
  /** Return every field to its default. */
  reset: () => void;
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

export function PreferencesProvider({
  children,
  initial,
  persist = true,
}: {
  children: ReactNode;
  initial?: Partial<Preferences>;
  persist?: boolean;
}) {
  const [preferences, setPreferences] = useState<Preferences>(() =>
    mergePreferences(defaultPreferences(), { ...loadStoredPreferences(), ...initial }),
  );
  const persistRef = useRef(persist);
  const preferencesRef = useRef(preferences);
  preferencesRef.current = preferences;

  // Apply on mount and on every change: the DOM is the only consumer.
  useEffect(() => {
    applyPreferences(preferences);
    if (persistRef.current) savePreferences(preferences);
  }, [preferences]);

  // Follow the OS only while the mode is "system".
  useEffect(() => {
    if (preferences.themeMode !== "system") return undefined;
    return watchSystemTheme(() => applyPreferences(preferencesRef.current));
  }, [preferences.themeMode]);

  const update = useCallback((patch: Partial<Preferences>) => {
    setPreferences((current) => mergePreferences(current, { ...current, ...patch }));
  }, []);

  const reset = useCallback(() => setPreferences(defaultPreferences()), []);

  const value = useMemo<PreferencesContextValue>(
    () => ({ preferences, update, reset }),
    [preferences, update, reset],
  );

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences(): PreferencesContextValue {
  const context = useContext(PreferencesContext);
  if (!context) throw new Error("usePreferences 必须在 PreferencesProvider 内使用");
  return context;
}
