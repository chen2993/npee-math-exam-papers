/**
 * Keyboard-shortcut cheat sheet.
 *
 * Shortcuts are only useful if they are discoverable, so they are listed in a
 * popover under a `?` button (and shown with the correct modifier for the
 * platform). Pressing `?` anywhere outside a text field opens the same panel.
 */

import { Keyboard } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useHotkeys, type Hotkey } from "../../shared/hooks/useHotkeys";
import { IconButton } from "../../shared/ui";

interface ShortcutRow {
  keys: string[];
  label: string;
}

export function ShortcutHelp() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const rootRef = useRef<HTMLDivElement>(null);

  const isMac = typeof navigator !== "undefined" && /mac/i.test(navigator.platform || navigator.userAgent);
  const mod = isMac ? "⌘" : "Ctrl";

  const rows = useMemo<ShortcutRow[]>(
    () => [
      { keys: [mod, "G"], label: "跳到仪表盘" },
      { keys: [mod, "⇧", "P"], label: "跳到套卷列表" },
      { keys: [mod, "⇧", "E"], label: "跳到组卷" },
      { keys: ["/"], label: "打开题目检索" },
      { keys: ["["], label: "收起 / 展开侧栏" },
      { keys: ["?"], label: "显示 / 隐藏本表" },
      { keys: ["Esc"], label: "关闭弹层" },
    ],
    [mod],
  );

  const hotkeys = useMemo<Hotkey[]>(() => [{ key: "?", shift: true, handler: () => setOpen((value) => !value) }], [setOpen]);
  useHotkeys(hotkeys);

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
    <div className="shortcut-root" ref={rootRef}>
      <IconButton label="键盘快捷键" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <Keyboard size={17} />
      </IconButton>
      {open ? (
        <div className="shortcut-panel surface" role="dialog" aria-label="键盘快捷键">
          <strong className="shortcut-title">键盘快捷键</strong>
          <ul className="shortcut-list">
            {rows.map((row) => (
              <li key={row.label}>
                <span className="shortcut-keys">
                  {row.keys.map((key) => (
                    <kbd key={key}>{key}</kbd>
                  ))}
                </span>
                <span className="shortcut-label">{row.label}</span>
              </li>
            ))}
          </ul>
          <button type="button" className="plain-button" onClick={() => { setOpen(false); navigate("/papers"); }}>
            打开套卷列表
          </button>
        </div>
      ) : null}
    </div>
  );
}
