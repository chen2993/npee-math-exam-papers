r"""Rewrite inline circled-proposition sequences into the line-break template.

The store records a proposition sequence inline::

    设 $k$ 为实数，则下列说法正确的是\ExamSelection。① 甲；② 乙；③ 丙；④ 丁。则正确的个数为\ExamSelection。

The house template puts each proposition on its own line and separates the
surrounding prose from the list::

    设 $k$ 为实数，则下列说法正确的是\ExamSelection。\n① 甲；\n② 乙；\n③ 丙；\n④ 丁。\n则正确的个数为\ExamSelection。

``\n`` is the stored spelling of one line break.  ``service/rendering/inline_tex``
rewrites it to ``\NPEEQuestionContinuation`` (a plain ``\par``) on read, and the
layout class turns the run of circled digits into a hanging list.

The same pass also normalises two earlier spellings of that break, which leaked
the *rendering* macro and raw ``\par`` into stored text and so violated the rule
that only ``\ExamSelection`` and ``\ExamBlank`` may appear in the store:

* ``\NPEEQuestionContinuation`` -> ``\n``
* a bare ``\par`` acting as a break -> ``\n``


Scope and safety
----------------
* Only ``stem`` and ``subparts`` are rewritten.  A choice text is an *answer
  key* (``①③``), not a proposition list, and must stay inline.
* A field is rewritten only when it holds a **consecutive run starting at ①**
  with at least two members.  A lone marker, or a marker buried inside a formula
  or a ``cases``/``matrix`` body, is left untouched.
* One earlier spelling puts the marker at the *head* of a math run
  (``$①f(1)>f(0)$``).  The renderer already lifts such a marker out of math, so
  the output is identical either way; this pass also rewrites the stored text to
  the template spelling so the whole library reads the same.
* A break already present before a marker is not doubled.
* Idempotent: a second run makes no change.

Usage::

   python -m npee_math_papers.maintenance.migrate_circled_sequence           # dry run
   python -m npee_math_papers.maintenance.migrate_circled_sequence --apply    # write
   python -m npee_math_papers.maintenance.migrate_circled_sequence --json out.json
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from npee_math_papers.service import NpeeService  # noqa: E402

#: The stored spelling of one line break (backslash + ``n``).
BREAK = "\\" + "n"

#: Circled digits in order; index 0 is ``①``.
CIRCLED = "\u2460\u2461\u2462\u2463\u2464\u2465\u2466\u2467\u2468\u2469"

#: Environments whose body is a grid: a marker there belongs to a cell.
ALIGNMENT_ENVIRONMENTS = (
    "cases", "matrix", "pmatrix", "bmatrix", "Bmatrix", "vmatrix",
    "Vmatrix", "smallmatrix", "array", "aligned", "gathered", "split",
)
_ALIGNMENT_RE = re.compile(
    r"\\begin\{(?P<environment>" + "|".join(ALIGNMENT_ENVIRONMENTS) + r")\}(?P<body>.*?)\\end\{(?P=environment)\}",
    re.DOTALL,
)
_ESCAPED_DOLLAR = chr(92) + "$"

#: Punctuation that closes a proposition body.
_SENTENCE_END = "\u3002\uff1b;"

def _protected(text: str) -> list[bool]:
    """Flag every index that must not be read as proposition prose.

    Two regions are protected: math mode (``$...$``) and the body of an
    alignment environment (where a circled digit is a table cell).
    """

    protected = [False] * len(text)
    cursor = 0
    while cursor < len(text):
        opening = text.find("$", cursor)
        if opening < 0:
            break
        if text.startswith(_ESCAPED_DOLLAR, opening):
            cursor = opening + 2
            continue
        closing = opening + 1
        while closing < len(text):
            closing = text.find("$", closing)
            if closing < 0:
                closing = len(text)
                break
            if not text.startswith(_ESCAPED_DOLLAR, closing):
                break
            closing += 2
        for index in range(opening, min(closing + 1, len(text))):
            protected[index] = True
        cursor = closing + 1
    for match in _ALIGNMENT_RE.finditer(text):
        for index in range(match.start(), match.end()):
            protected[index] = True
    return protected

#: ``$①$`` -- a math run holding nothing but the marker.
_MATH_ONLY_MARKER = re.compile(r"\$\s*([" + CIRCLED + r"])\s*\$")
#: ``$①若…`` -- the marker heads a math run that also carries content.
_MATH_LED_MARKER = re.compile(r"\$\s*([" + CIRCLED + r"])")

def normalize_math_led_markers(text: str) -> str:
    """Lift a proposition marker written at the head of a math run out of math.

    ``$①f(1)>f(0)$`` becomes ``①$f(1)>f(0)$``, matching the template.  The empty
    run case is applied first, so the content-bearing rule cannot re-wrap a marker
    the first rule already freed.  This mirrors ``rendering.content``.
    """

    if not any(marker in text for marker in CIRCLED):
        return text
    text = _MATH_ONLY_MARKER.sub(lambda m: m.group(1), text)
    return _MATH_LED_MARKER.sub(lambda m: m.group(1) + "$", text)

def _leading_run(text: str) -> list[int] | None:
    """Indices of a leading consecutive circled run (``①②③``...), or ``None``."""

    protected = _protected(text)
    seen: list[tuple[int, int]] = []
    for index, char in enumerate(text):
        if char in CIRCLED and not protected[index]:
            seen.append((index, CIRCLED.index(char)))
    if len(seen) < 2:
        return None
    run: list[int] = []
    expected = 0
    for index, order in seen:
        if order == expected:
            run.append(index)
            expected += 1
        elif run:
            break
    return run if len(run) >= 2 else None

def _strip_trailing_break(text: str) -> str:
    """Remove breaks already ending ``text``, so none is doubled."""

    pattern = re.compile(re.escape(BREAK) + r"[ \t]*$")
    while True:
        trimmed = pattern.sub("", text)
        if trimmed == text:
            return text
        text = trimmed

#: The rendering macro that ``\n`` expands to; it must not appear in the store.
RENDER_MACRO = "\\NPEEQuestionContinuation"

#: A bare ``\par`` used as a line break.
_BARE_PAR = re.compile(r"(?<!\\)\\par\b[ \t]*")

#: The stored break marker, with the same guards the renderer applies: a literal
#: backslash-``n`` that is neither escaped nor the start of a command name.
_BREAK_MARKER = re.compile(r"(?<!\\)" + re.escape(BREAK) + r"(?![A-Za-z])")

def _as_break(_match: re.Match[str]) -> str:
    """Replacement callback that inserts the literal two-character break.

    A plain replacement string cannot be used: ``re.sub`` interprets backslash
    escapes in it, so ``"\n"`` would insert a real newline instead of the
    backslash-and-``n`` marker the store expects.
    """

    return BREAK

def normalize_legacy(text: str) -> str:
    """Fold earlier spellings of a line break into the stored ``\n`` form."""

    if RENDER_MACRO not in text and "\\par" not in text:
        return text
    # Drop a stray space the old emitter left after the macro, so the result is
    # exactly one break marker followed by the content.
    text = re.sub(re.escape(RENDER_MACRO) + r"[ \t]*", _as_break, text)
    text = _BARE_PAR.sub(_as_break, text)
    # Collapse any run of breaks into one and trim breaks at either end: the
    # renderer treats a break in vertical mode as a no-op, so duplicates are
    # inert but noise in the data.
    #
    # Every pattern for the marker carries the same two guards the renderer uses
    # (``inline_tex``): not preceded by a backslash and not followed by a letter.
    # Without them ``\ne``, ``\nabla`` and friends would be read as a break
    # followed by prose, and the collapse would corrupt the math.
    marker = _BREAK_MARKER.pattern
    text = re.sub(r"(?:" + marker + r")+", _as_break, text)
    text = re.sub(r"^(?:" + marker + r")+", "", text)
    return re.sub(r"(?:" + marker + r")+$", "", text)

def rewrite(text: str) -> str:
    """Return ``text`` in the line-break template, or unchanged if inapplicable."""

    text = normalize_legacy(text)
    text = normalize_math_led_markers(text)
    run = _leading_run(text)
    if run is None:
        return text

    # Insert a break before each proposition marker, never doubling one, and
    # remember where each marker lands: the rebuilt string has different
    # offsets from the original, so the closing-prose scan below must use these.
    pieces: list[str] = []
    cursor = 0
    length = 0
    marker_positions: list[int] = []
    for start in run:
        head = _strip_trailing_break(text[cursor:start])
        if head:
            pieces.append(head)
            length += len(head)
        pieces.append(BREAK)
        length += len(BREAK)
        marker_positions.append(length)     # the digit begins here
        cursor = start
    pieces.append(text[cursor:])
    body = "".join(pieces)

    # Break before the closing prose that follows the last proposition.
    for index in range(marker_positions[-1], len(body)):
        if body[index] in _SENTENCE_END:
            tail = body[index + 1:]
            stripped = tail.lstrip()
            if stripped and not stripped.startswith(BREAK):
                lead = len(tail) - len(stripped)
                body = body[: index + 1] + tail[:lead] + BREAK + stripped
            break
    return body

def _fields(question: dict) -> list[tuple[str, str]]:
    """Yield ``(field_name, text)`` for the rewritable fields of one question."""

    found = [("stem", (question.get("stem") or {}).get("text") or "")]
    for order, part in enumerate(question.get("subparts") or [], 1):
        found.append((f"subparts[{order}]", (part or {}).get("text") or ""))
    return found

def _set_field(question: dict, field: str, value: str) -> None:
    if field == "stem":
        question["stem"]["text"] = value
        return
    order = int(field[len("subparts["):-1])
    question["subparts"][order - 1]["text"] = value

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--json", type=Path, default=Path("build/circled-sequence-repairs.json"),
                        help="where to record the per-field before/after list")
    args = parser.parse_args()

    service = NpeeService.create()
    store = service.context.store

    repairs: list[dict[str, str]] = []
    touched: dict[str, dict] = {}

    for record in store.iter_records():
        modified: dict | None = None
        for question in record.questions:
            for field, text in _fields(question):
                if not text:
                    continue
                fixed = rewrite(text)
                if fixed == text:
                    continue
                if modified is None:
                    modified = {
                        "series_key": record.series_key,
                        "year": record.year,
                        "subject": record.subject,
                        "paper_no": record.paper_no,
                        "questions": copy.deepcopy(record.questions),
                    }
                target = next(
                    item for item in modified["questions"]
                    if int(item["number"]) == int(question["number"])
                )
                _set_field(target, field, fixed)
                repairs.append({
                    "natural_key": record.natural_key,
                    "question": int(question["number"]),
                    "field": field,
                    "before": text,
                    "after": fixed,
                })
        if modified is not None:
            touched[record.natural_key] = modified

    print(f"需要重排的字段：{len(repairs)} 处，涉及 {len(touched)} 套")
    print()
    for repair in repairs[:3]:
        print(f"  {repair['natural_key']} q{repair['question']} {repair['field']}")
        print(f"    BEFORE: {repair['before'][:120]!r}")
        print(f"    AFTER : {repair['after'][:120]!r}")
    if len(repairs) > 3:
        print(f"  ... 另有 {len(repairs) - 3} 处")

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(repairs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if not args.apply:
        print()
        print(f"预览模式；加 --apply 写回。清单：{args.json.as_posix()}")
        return 0

    from npee_math_papers.core.store import PaperRecord

    applied = 0
    for key, payload in touched.items():
        store.write_paper(
            PaperRecord(
                series_key=payload["series_key"],
                year=payload["year"],
                subject=payload["subject"],
                paper_no=payload["paper_no"],
                questions=payload["questions"],
            ),
            replace=True,
        )
        applied += 1
    store.rebuild_index()
    store.write_release()
    print()
    print(f"已写回 {applied} 套，并重建索引与发布清单。")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
