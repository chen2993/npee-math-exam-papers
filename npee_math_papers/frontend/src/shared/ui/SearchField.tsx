/**
 * Labelled search input with a debounced commit.
 *
 * The catalogue's search runs on the *server* (it scans the whole library, not
 * just the loaded page), so committing on every keystroke would fire one request
 * per character and make the row list flicker. This control keeps the typed text
 * in local state for instant feedback and only reports it upward once the user
 * pauses — or immediately on Enter, for people who type and hit return.
 *
 * The committed value is tracked separately from the prop so an external reset
 * (the "clear filters" button) still updates the box, while typing does not fight
 * a parent that echoes the last commit back down.
 */

import { Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { IconButton } from "./Button";

export function SearchField({
  value,
  onChange,
  label = "搜索",
  placeholder = "搜索",
  delayMs = 280,
  wrapperClassName,
}: {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  placeholder?: string;
  delayMs?: number;
  wrapperClassName?: string;
}) {
  const [text, setText] = useState(value);
  /** The last value this control sent (or received) — the debounce baseline. */
  const committed = useRef(value);
  /** Kept in a ref so a re-render never restarts a pending commit. */
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  // Adopt an external change (e.g. "clear filters") without clobbering typing.
  useEffect(() => {
    if (value === committed.current) return;
    committed.current = value;
    setText(value);
  }, [value]);

  useEffect(() => {
    if (text === committed.current) return undefined;
    const timer = window.setTimeout(() => {
      committed.current = text;
      onChangeRef.current(text);
    }, delayMs);
    return () => window.clearTimeout(timer);
  }, [text, delayMs]);

  function commitNow() {
    if (text === committed.current) return;
    committed.current = text;
    onChangeRef.current(text);
  }

  return (
    <label className={`field tool-field tool-field-grow ${wrapperClassName ?? ""}`.trim()}>
      <span className="field-label">{label}</span>
      <span className="search-input">
        <Search size={14} />
        <input
          className="field-control"
          type="search"
          value={text}
          placeholder={placeholder}
          aria-label={label}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              commitNow();
            }
            if (event.key === "Escape") {
              setText("");
              committed.current = "";
              onChangeRef.current("");
            }
          }}
        />
        {text ? (
          <IconButton
            label="清空搜索"
            size="sm"
            className="search-input-clear"
            onClick={() => {
              setText("");
              committed.current = "";
              onChangeRef.current("");
            }}
          >
            <X size={12} />
          </IconButton>
        ) : null}
      </span>
    </label>
  );
}
