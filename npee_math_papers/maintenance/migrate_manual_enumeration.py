r"""Normalise hand-typed ``（1）（2）（3）`` enumerations.

Why this is a separate pass
---------------------------
``migrate_circled_sequence`` is a *rename*: it only inserts line breaks around
circled digits that are already there.  This pass changes what a field **is**,
so it is kept apart and reviewed on its own:

* In a **choice** question, ``（1）…（2）…（3）…`` lists alternative statements.
  The house template prints those as ``\n①\n②\n③`` (a circled hanging list), so
  the markers are rewritten to that shape.  A choice text that *references* the
  list (``（1）（2）（3）``) is rewritten to the same circled digits, otherwise the
  answer key would point at labels the stem no longer prints.
* In a **solution** question, ``（1）…（2）…`` are sub-questions.  The document
  contract puts those in ``subparts`` and the class numbers them itself, so they
  are moved there and the ordinal prefixes are dropped.
* A **choice** question whose propositions are already stored in ``subparts``
  is the mirror image: the class renders subparts as ``(1) (2) …``, but a
  choice stem prints its statements with the circled template.  They are
  merged back into the stem as ``\\n①\\n②…``.  Any answer key that is a
  *reference* to those statements (``①②``, ``（1）（3）``) is rewritten to the
  same circled digits; a key that is a *count* (``$1$``…``$4$``) is left alone,
  because it answers "how many" rather than "which".

Only a **consecutive run starting at 1** with at least two members qualifies, and
markers inside math mode or an alignment body are ignored -- so ``t(2)`` in a
formula, ``(x-1)``, and a matrix entry are never mistaken for an enumeration.

Usage::

   python -m npee_math_papers.maintenance.migrate_manual_enumeration            # dry run
   python -m npee_math_papers.maintenance.migrate_manual_enumeration --apply
   python -m npee_math_papers.maintenance.migrate_manual_enumeration --json out.json
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

#: The stored spelling of one line break.
BREAK = "\\" + "n"

#: Circled digits in order; index 0 is ``①``.
CIRCLED = "\u2460\u2461\u2462\u2463\u2464\u2465\u2466\u2467\u2468\u2469"

#: Environments whose body is a grid.
ALIGNMENT_ENVIRONMENTS = (
    "cases", "matrix", "pmatrix", "bmatrix", "Bmatrix", "vmatrix",
    "Vmatrix", "smallmatrix", "array", "aligned", "gathered", "split",
)
_ALIGNMENT_RE = re.compile(
    r"\\begin\{(?P<environment>" + "|".join(ALIGNMENT_ENVIRONMENTS) + r")\}(?P<body>.*?)\\end\{(?P=environment)\}",
    re.DOTALL,
)
_ESCAPED_DOLLAR = chr(92) + "$"

#: ``（1）`` or ``(1)``, with optional spaces inside the brackets.
_ORDINAL_RE = re.compile(r"(?:\uff08\s*([1-9])\s*\uff09|\(\s*([1-9])\s*\))")

#: Punctuation that ends a statement.
_SENTENCE_END = "\u3002\uff1b;"

def _protected(text: str) -> list[bool]:
    """Flag indices that must not be read as enumeration prose."""

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

def _run(text: str) -> tuple[list[re.Match[str]], str, list[str]] | None:
    """Return ``(markers, lead, bodies)`` for a qualifying enumeration.

    ``markers`` are the ``（N）`` matches, ``lead`` is the text before the first
    marker, and ``bodies`` are the statement texts with the markers removed.
    """

    protected = _protected(text)
    markers: list[re.Match[str]] = []
    expected = 1
    for match in _ORDINAL_RE.finditer(text):
        if protected[match.start()]:
            continue
        order = int(match.group(1) or match.group(2))
        if order == expected:
            markers.append(match)
            expected += 1
        elif markers:
            break
    if len(markers) < 2:
        return None
    lead = text[: markers[0].start()]
    bodies: list[str] = []
    for offset, marker in enumerate(markers):
        end = markers[offset + 1].start() if offset + 1 < len(markers) else len(text)
        bodies.append(text[marker.end():end].strip())
    return markers, lead, bodies

def _strip_breaks(text: str) -> str:
    """Remove every line break from ``text`` and trim it.

    A body sits between two enumeration markers, so a break inside it is always
    left over from a previous pass.  Dropping all of them is what makes this pass
    idempotent: the caller re-inserts exactly one break at each marker.
    """

    pattern = re.compile(r"(?:" + re.escape(BREAK) + r")+")
    return pattern.sub("", text).strip()

def _break_before_closing(text: str) -> str:
    """Insert one break before the closing prose of a choice stem.

    The closing sentence is the run that ends at the answer macro, so the break
    goes after the last sentence-ending punctuation *before* that macro.  Keying
    on the macro is what makes this unambiguous: the last statement may itself
    contain ``；``.
    """

    anchor = len(text)
    for token in ("\\ExamSelection", "\\ExamBlank"):
        at = text.find(token)
        if at >= 0:
            anchor = min(anchor, at)
    cut = -1
    for index in range(anchor):
        if text[index] in _SENTENCE_END:
            cut = index
    if cut < 0:
        return text
    rest = text[cut + 1:]
    stripped = rest.lstrip()
    if not stripped or stripped.startswith(BREAK):
        return text
    lead = len(rest) - len(stripped)
    return text[: cut + 1] + rest[:lead] + BREAK + stripped

def choice_statements(text: str) -> str | None:
    """Rewrite a choice stem's ``（1）（2）…`` list as ``\\n①\\n②…``."""

    found = _run(text)
    if found is None:
        return None
    _markers, lead, bodies = found
    pieces: list[str] = []
    if lead.strip():
        pieces.append(_strip_breaks(lead))
    for offset, body in enumerate(bodies):
        body = _strip_breaks(body)
        if not body:
            continue
        # One space after the marker, matching the house template the circled
        # digits already use (``\n① 设正项级数``).  LaTeX swallows it when the
        # body opens with math, so prose and formulas stay consistent.
        pieces.append(BREAK + CIRCLED[offset] + " " + body)
    return _break_before_closing("".join(pieces))

def solution_subparts(text: str) -> tuple[str, list[str]] | None:
    """Split a solution stem into ``(stem, subparts)`` when it lists sub-questions."""

    found = _run(text)
    if found is None:
        return None
    _markers, lead, bodies = found
    cleaned = [_strip_breaks(b) for b in bodies if _strip_breaks(b)]
    if len(cleaned) < 2:
        return None
    if not lead.strip():
        # The stem is nothing but the sub-questions.  The render model needs a
        # non-empty body, so the documented ``{}`` placeholder is used; the class
        # label and the subparts still carry the question, and ``{}`` prints
        # nothing.  See ``strip_solution_score_label`` for the same convention.
        return "{}", cleaned
    return lead.strip(), cleaned

def reference_to_circled(text: str) -> str | None:
    """Rewrite a bare ``（1）（3）``-style answer key as ``①③``.

    The digits need not be consecutive -- ``（1）（3）`` answers "statements 1 and
    3" -- so this does not go through :func:`_run`, which requires a consecutive
    run.  The whole text must be nothing but the references, optionally followed
    by a full stop, so an ordinary sentence containing ``(2)`` is left alone.
    """

    text = text.strip()
    if not text:
        return None
    # ``$(1)(2)$`` is the same reference written in math mode.
    if len(text) > 1 and text.startswith("$") and text.endswith("$"):
        text = text[1:-1].strip()
    residue = _ORDINAL_RE.sub("", text).strip().rstrip("\u3002").strip()
    if residue:
        return None
    markers = list(_ORDINAL_RE.finditer(text))
    if not markers:
        return None
    return "".join(CIRCLED[int(m.group(1) or m.group(2)) - 1] for m in markers)

def merge_choice_subparts(stem: str, subparts: list[str]) -> str | None:
    """Move a choice question's propositions back into the stem.

    The class prints subparts as ``(1) (2) …``; a choice stem prints statements
    with the circled template, so the two must not be mixed.  Returns ``None``
    when a subpart carries a figure (which cannot be flattened into text) or the
    list is too short to be a statement sequence.
    """

    parts = [text.strip() for text in subparts]
    if len(parts) < 2 or any(not text for text in parts):
        return None
    pieces = [_strip_breaks(stem)]
    for offset, text in enumerate(parts):
        # The stored subpart may already carry the circled label the class
        # prints for a subpart (``① $|A|=0$；``); drop it so the template does
        # not emit the marker twice.
        body = text[1:].lstrip() if text[:1] in CIRCLED else text
        pieces.append(BREAK + CIRCLED[offset] + " " + _strip_breaks(body))
    return "".join(pieces)

def count_key(text: str) -> bool:
    """Whether an answer key is a plain count (``$1$``) rather than a reference."""

    plain = re.sub(r"[\s$。.．，,、]", "", text)
    return bool(re.fullmatch(r"[0-9]+", plain))

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--json", type=Path, default=Path("build/manual-enumeration-repairs.json"))
    args = parser.parse_args()

    service = NpeeService.create()
    store = service.context.store

    repairs: list[dict] = []
    touched: dict[str, dict] = {}
    skipped: list[str] = []

    for record in store.iter_records():
        modified: dict | None = None

        def ensure() -> dict:
            nonlocal modified
            if modified is None:
                modified = {
                    "series_key": record.series_key,
                    "year": record.year,
                    "subject": record.subject,
                    "paper_no": record.paper_no,
                    "questions": copy.deepcopy(record.questions),
                }
            return modified

        for question in record.questions:
            section = question.get("section")
            stem = (question.get("stem") or {}).get("text") or ""

            if section == "choice" and (question.get("subparts") or []):
                if any((part or {}).get("figures") for part in question["subparts"]):
                    skipped.append(f"{record.natural_key} q{question['number']} (subpart has a figure)")
                    continue
                merged = merge_choice_subparts(
                    stem, [(part or {}).get("text") or "" for part in question["subparts"]]
                )
                if merged is None:
                    skipped.append(f"{record.natural_key} q{question['number']} (subparts not mergeable)")
                    continue
                target = ensure()
                keys: dict[str, str] = {}
                for choice in question.get("choices") or []:
                    text = choice.get("text") or ""
                    label = choice.get("label")
                    if count_key(text):
                        continue                     # a count, not a reference
                    reference = reference_to_circled(text)
                    if reference:
                        keys[label] = reference
                repairs.append({
                    "natural_key": record.natural_key, "question": int(question["number"]),
                    "field": "subparts->stem", "before": stem + " :: " +
                    json.dumps([(p or {}).get("text") or "" for p in question["subparts"]], ensure_ascii=False),
                    "after": merged, "also": keys,
                })
                q = next(x for x in target["questions"] if int(x["number"]) == int(question["number"]))
                q["stem"]["text"] = merged
                q["subparts"] = []
                for choice in q.get("choices") or []:
                    if choice.get("label") in keys:
                        choice["text"] = keys[choice["label"]]
                continue

            if section == "choice":
                converted = choice_statements(stem)
                if converted is None:
                    continue
                target = ensure()
                changed = converted
                # Any choice that *references* the list must follow it.
                referenced: dict[str, str] = {}
                for choice in question.get("choices") or []:
                    label = choice.get("label")
                    got = reference_to_circled(choice.get("text") or "")
                    if got:
                        referenced[label] = got
                repairs.append({
                    "natural_key": record.natural_key, "question": int(question["number"]),
                    "field": "stem", "before": stem, "after": changed,
                    "also": referenced,
                })
                q = next(x for x in target["questions"] if int(x["number"]) == int(question["number"]))
                q["stem"]["text"] = changed
                for choice in q.get("choices") or []:
                    if choice.get("label") in referenced:
                        choice["text"] = referenced[choice["label"]]

            elif section == "solution":
                split = solution_subparts(stem)
                if split is None:
                    continue
                lead, parts = split
                target = ensure()
                repairs.append({
                    "natural_key": record.natural_key, "question": int(question["number"]),
                    "field": "stem+subparts", "before": stem,
                    "after": lead + "  -> subparts=" + json.dumps(parts, ensure_ascii=False),
                    "also": {},
                })
                q = next(x for x in target["questions"] if int(x["number"]) == int(question["number"]))
                q["stem"]["text"] = lead
                q["subparts"] = [{"text": part, "figures": []} for part in parts]

        if modified is not None:
            touched[record.natural_key] = modified

    print(f"拟改写字段：{len(repairs)} 处，涉及 {len(touched)} 套")
    for item in repairs:
        print()
        print("=" * 78)
        print(f"{item['natural_key']} q{item['question']}  [{item['field']}]")
        print(f"  BEFORE: {item['before'][:190]!r}")
        print(f"  AFTER : {item['after'][:190]!r}")
        if item["also"]:
            print(f"  choice refs -> {item['also']}")
    if skipped:
        print()
        print("跳过（无前导文字，无法拆分）：")
        for item in skipped:
            print("   ", item)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(repairs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.apply:
        print()
        print(f"预览模式；加 --apply 写回。清单：{args.json.as_posix()}")
        return 0

    from npee_math_papers.core.store import PaperRecord

    for payload in touched.values():
        store.write_paper(
            PaperRecord(
                series_key=payload["series_key"], year=payload["year"],
                subject=payload["subject"], paper_no=payload["paper_no"],
                questions=payload["questions"],
            ),
            replace=True,
        )
    store.rebuild_index()
    store.write_release()
    print()
    print(f"已写回 {len(touched)} 套，并重建索引与发布清单。")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
