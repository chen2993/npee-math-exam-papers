/**
 * The preferences popover.
 *
 * Exposes every user-facing knob from the preference object: theme, density,
 * font scale, accent palette and reading width. Because the store writes CSS
 * variables, every change here is applied live with no page re-render.
 */

import { Check, Monitor, Moon, Palette, RotateCcw, SlidersHorizontal, Sun } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ACCENT_PRESETS, usePreferences, type Density, type FontScale, type ThemeMode } from "../../preferences";
import { Button, CheckField, IconButton, Segmented, classNames } from "../../shared/ui";

const THEME_OPTIONS: { value: ThemeMode; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "浅色", icon: Sun },
  { value: "dark", label: "深色", icon: Moon },
  { value: "system", label: "跟随系统", icon: Monitor },
];

const DENSITY_OPTIONS: { value: Density; label: string }[] = [
  { value: "compact", label: "紧凑" },
  { value: "comfortable", label: "标准" },
  { value: "spacious", label: "宽松" },
];

const FONT_OPTIONS: { value: FontScale; label: string }[] = [
  { value: "small", label: "小" },
  { value: "base", label: "中" },
  { value: "large", label: "大" },
];

export function PreferencesMenu() {
  const { preferences, update, reset } = usePreferences();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Close on outside click and Escape, like any well-behaved popover.
  useEffect(() => {
    if (!open) return undefined;
    function onPointerDown(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div className="preferences-root" ref={rootRef}>
      <IconButton label="界面偏好" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <SlidersHorizontal size={17} />
      </IconButton>
      {open ? (
        <div className="preferences-panel surface" role="dialog" aria-label="界面偏好">
          <header className="preferences-head">
            <strong>界面偏好</strong>
            <Button size="sm" variant="quiet" icon={<RotateCcw size={13} />} onClick={reset}>
              重置
            </Button>
          </header>

          <div className="preferences-section">
            <span className="preferences-label">主题</span>
            <div className="theme-choices">
              {THEME_OPTIONS.map((option) => {
                const Icon = option.icon;
                return (
                  <button
                    key={option.value}
                    type="button"
                    className={classNames("theme-choice", preferences.themeMode === option.value && "is-active")}
                    onClick={() => update({ themeMode: option.value })}
                    aria-pressed={preferences.themeMode === option.value}
                  >
                    <Icon size={16} />
                    {option.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="preferences-section">
            <span className="preferences-label">信息密度</span>
            <Segmented label="信息密度" options={DENSITY_OPTIONS} value={preferences.density} onChange={(value) => update({ density: value })} />
          </div>

          <div className="preferences-section">
            <span className="preferences-label">字号</span>
            <Segmented label="字号" options={FONT_OPTIONS} value={preferences.fontScale} onChange={(value) => update({ fontScale: value })} />
          </div>

          <div className="preferences-section">
            <span className="preferences-label">
              <Palette size={13} /> 强调色
            </span>
            <div className="accent-choices">
              {ACCENT_PRESETS.map((preset) => (
                <button
                  key={preset.name}
                  type="button"
                  className={classNames("accent-swatch", preferences.accent === preset.name && "is-active")}
                  style={{ background: preset.color }}
                  onClick={() => update({ accent: preset.name })}
                  title={preset.label}
                  aria-label={preset.label}
                  aria-pressed={preferences.accent === preset.name}
                >
                  {preferences.accent === preset.name ? <Check size={13} /> : null}
                </button>
              ))}
            </div>
          </div>

          <div className="preferences-section">
            <span className="preferences-label">圆角</span>
            <input
              type="range"
              min={0}
              max={18}
              value={preferences.radius}
              onChange={(event) => update({ radius: Number(event.target.value) })}
              aria-label="圆角"
            />
          </div>

          <div className="preferences-toggles">
            <CheckField
              label="内容定宽"
              checked={preferences.contentWidth === "fixed"}
              onChange={(checked) => update({ contentWidth: checked ? "fixed" : "fluid" })}
            />
            <CheckField
              label="显示面包屑"
              checked={preferences.showBreadcrumb}
              onChange={(checked) => update({ showBreadcrumb: checked })}
            />
            <CheckField
              label="减少动效"
              checked={preferences.reduceMotion}
              onChange={(checked) => update({ reduceMotion: checked })}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
