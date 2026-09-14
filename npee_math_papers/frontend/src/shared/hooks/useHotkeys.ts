/**
 * Global keyboard shortcuts.
 *
 * A console someone uses all day benefits from speed keys. The handler is
 * deliberately conservative: it ignores keystrokes while the user is typing in a
 * field (so ``/`` can be typed), and skips modifier combinations the browser owns.
 */

import { useEffect } from "react";

export interface Hotkey {
  /** Lower-case key name, e.g. ``"k"``, ``"/"``, ``"escape"``. */
  key: string;
  /** Require Cmd (macOS) / Ctrl (elsewhere). */
  meta?: boolean;
  /** Require the Shift modifier. */
  shift?: boolean;
  handler: (event: KeyboardEvent) => void;
  /** Fire even while an input/textarea has focus (default false). */
  allowInInput?: boolean;
}

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

export function useHotkeys(hotkeys: Hotkey[]): void {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const key = event.key.toLowerCase();
      for (const hotkey of hotkeys) {
        if (hotkey.key !== key) continue;
        const wantsMeta = Boolean(hotkey.meta);
        const hasMeta = event.metaKey || event.ctrlKey;
        if (wantsMeta !== hasMeta) continue;
        if (Boolean(hotkey.shift) !== event.shiftKey) continue;
        if (!hotkey.allowInInput && isTypingTarget(event.target)) continue;
        event.preventDefault();
        hotkey.handler(event);
        return;
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [hotkeys]);
}
