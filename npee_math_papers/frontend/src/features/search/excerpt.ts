/**
 * Make a raw-LaTeX excerpt safe to preview.
 *
 * Search results are substrings of question LaTeX, so an excerpt can end in the
 * middle of an inline math run (``…$\sum_{n=1}`` with no closing ``$``). Rendering
 * that as-is leaks the command source as literal text, which reads like a bug.
 *
 * Rather than guess, we trim the excerpt back to the last point where the math
 * state is balanced, and note that it was shortened.
 */

const MAX_LENGTH = 180;

/** Return ``excerpt`` trimmed to a balanced-math prefix, with an ellipsis. */
export function balancedExcerpt(raw: string, maxLength = MAX_LENGTH): string {
  const collapsed = String(raw ?? "").replace(/\s+/g, " ").trim();
  const truncated = collapsed.length > maxLength;
  const window = truncated ? collapsed.slice(0, maxLength) : collapsed;
  // Walk the window tracking inline-math state so we can cut at a safe boundary.
  let inMath = false;
  let lastBalanced = -1;
  let lastOpened = -1;
  for (let index = 0; index < window.length; index += 1) {
    const char = window[index];
    if (char === "\\") {
      index += 1; // skip the escaped character
      continue;
    }
    if (char === "$") {
      inMath = !inMath;
      if (inMath) lastOpened = index;
      else lastBalanced = index;
    }
  }

  // The API truncates excerpts too, so an excerpt that fits our length can still
  // end mid-math; rebalance whenever the scan leaves math open. Prefer the last
  // balanced run; if there is none, drop the unterminated math entirely.
  let cutAt = window.length;
  if (inMath) {
    cutAt = lastBalanced >= 0 ? lastBalanced + 1 : lastOpened >= 0 ? lastOpened : window.length;
  }
  const body = window.slice(0, cutAt).trimEnd();
  return cutAt < collapsed.length ? `${body}…` : body;
}
