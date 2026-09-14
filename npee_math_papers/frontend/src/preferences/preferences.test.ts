import { describe, expect, it } from "vitest";

import { applyPreferences, accentPreset, defaultPreferences, mergePreferences } from "./index";
import { ACCENT_PRESETS } from "./presets";

describe("mergePreferences", () => {
  it("returns the defaults for an empty patch", () => {
    expect(mergePreferences(defaultPreferences(), {})).toEqual(defaultPreferences());
    expect(mergePreferences(defaultPreferences(), null)).toEqual(defaultPreferences());
  });

  it("applies valid fields and ignores unknown ones", () => {
    const merged = mergePreferences(defaultPreferences(), { themeMode: "dark", density: "compact" });
    expect(merged.themeMode).toBe("dark");
    expect(merged.density).toBe("compact");
  });

  it("rejects values outside the allowed set", () => {
    const merged = mergePreferences(defaultPreferences(), {
      // @ts-expect-error - deliberately invalid, as a stale/corrupt store would be
      themeMode: "neon",
      // @ts-expect-error - deliberately invalid
      density: "tiny",
    });
    expect(merged.themeMode).toBe(defaultPreferences().themeMode);
    expect(merged.density).toBe(defaultPreferences().density);
  });

  it("clamps numeric fields into range", () => {
    const merged = mergePreferences(defaultPreferences(), { radius: 999, pageSize: -5, logRefreshSeconds: 1000 });
    expect(merged.radius).toBe(18);
    expect(merged.pageSize).toBe(10);
    expect(merged.logRefreshSeconds).toBe(60);
  });

  it("ignores non-numeric junk in numeric fields", () => {
    const merged = mergePreferences(defaultPreferences(), {
      // @ts-expect-error - deliberately invalid
      radius: "wide",
    });
    expect(merged.radius).toBe(defaultPreferences().radius);
  });
});

describe("accentPreset", () => {
  it("returns the requested preset", () => {
    expect(accentPreset("indigo").name).toBe("indigo");
  });

  it("falls back to the first preset for an unknown name", () => {
    // @ts-expect-error - deliberately invalid
    expect(accentPreset("neon").name).toBe(ACCENT_PRESETS[0].name);
  });
});

describe("applyPreferences", () => {
  it("writes data attributes and accent variables onto the document root", () => {
    const resolved = applyPreferences({
      ...defaultPreferences(),
      themeMode: "dark",
      density: "compact",
      fontScale: "large",
      accent: "rose",
      radius: 12,
      contentWidth: "fixed",
    });
    const root = document.documentElement;
    expect(resolved).toBe("dark");
    expect(root.dataset.theme).toBe("dark");
    expect(root.dataset.density).toBe("compact");
    expect(root.dataset.fontScale).toBe("large");
    expect(root.dataset.contentWidth).toBe("fixed");
    expect(root.style.getPropertyValue("--radius")).toBe("12px");
    expect(root.style.getPropertyValue("--accent")).toBe(accentPreset("rose").color);
  });
});
