"""Composition document: cover / back matter, hooks, watermarks and file naming.

A composition document is the human-authored half of the build: which pages are
compiled, what furniture they carry and how the output is named. Everything here
validates that half and turns it into arguments for the class, so the orchestration
module only has to wire the pieces together.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from npee_math_papers.core.domain import (
    HOOK_PHASES,
    ID_RE,
    LAYOUTS,
    SUBJECT_CODES,
    SUBJECT_LABELS,
    SUBJECTS,
)

#: Output subject label lookup (alias of the shared domain label table).
SUBJECT_NAMES = SUBJECT_LABELS

from npee_math_papers.service.rendering.errors import fail
from npee_math_papers.service.rendering.paths import (
    package_path,
    package_tex_path,
    relative_tex_path,
)
from npee_math_papers.service.rendering.text import nonempty_string, tex_literal

#: ``#rrggbbaa`` colours accepted in watermark settings.
HEX_RGBA_RE = re.compile(r"^#([0-9a-f]{8})$", re.I)
#: ``rgba(r, g, b, a)`` colours accepted in watermark settings.
RGBA_RE = re.compile(r"^rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(0|1|0?\.\d+)\s*\)$", re.I)

def matter_block(
    matter: dict[str, Any] | None,
    phase: str,
    package_root: Path,
) -> tuple[list[str], list[str], bool]:
    if not matter or not matter.get("enabled", False):
        return [], [], False
    required = {"enabled", "kind", "path", "bookmark_title"}
    if set(matter) - (required | {"number_pages", "preamble"}):
        fail(f"document.{phase} has unsupported fields")
    if matter["kind"] not in {"tex", "pdf"}:
        fail(f"document.{phase}.kind must be tex or pdf")
    path = matter.get("path")
    if not isinstance(path, str):
        fail(f"document.{phase}.path is required when enabled")
    path_resolver = package_tex_path if matter["kind"] == "tex" else package_path
    full = path_resolver(path, package_root, f"document.{phase}.path")
    if not full.is_file():
        fail(f"document.{phase}.path does not exist: {path}")
    title = tex_literal(matter["bookmark_title"], f"document.{phase}.bookmark_title")
    key = f"composition-{phase.replace('_', '-')}"
    preamble_lines: list[str] = []
    preamble_path = matter.get("preamble")
    if preamble_path is not None:
        if matter["kind"] != "tex":
            fail(f"document.{phase}.preamble is only valid for tex matter")
        if not isinstance(preamble_path, str):
            fail(f"document.{phase}.preamble must be a package-relative path or null")
        preamble = package_tex_path(preamble_path, package_root, f"document.{phase}.preamble")
        if not preamble.is_file():
            fail(f"document.{phase}.preamble does not exist: {preamble_path}")
        preamble_lines.append(f"\\input{{{relative_tex_path(preamble)}}}")
    if matter["kind"] == "tex":
        return preamble_lines, [f"\\pdfbookmark[0]{{{title}}}{{{key}}}", f"\\input{{{relative_tex_path(full)}}}", "\\clearpage"], False
    return preamble_lines, [f"\\pdfbookmark[0]{{{title}}}{{{key}}}", f"\\includepdf[pages=-,pagecommand={{}}]{{{relative_tex_path(full)}}}", "\\clearpage"], True


def appendix_blocks(document: dict[str, Any], package_root: Path) -> tuple[list[str], bool]:
    appendices = document.get("appendices", [])
    if appendices is None:
        return [], False
    if not isinstance(appendices, list):
        fail("document.appendices must be an array")
    lines: list[str] = []
    needs_pdfpages = False
    for index, appendix in enumerate(appendices):
        if not isinstance(appendix, dict):
            fail(f"document.appendices[{index}] must be an object")
        required = {"id", "title", "kind", "path", "bookmark_title", "enabled"}
        if set(appendix) - (required | {"watermark", "number_pages"}):
            fail(f"document.appendices[{index}] has unsupported fields")
        if not appendix.get("enabled", False):
            continue
        if not isinstance(appendix.get("id"), str) or not ID_RE.fullmatch(appendix["id"]):
            fail(f"document.appendices[{index}].id is invalid")
        if appendix.get("kind") not in {"tex", "pdf"}:
            fail(f"document.appendices[{index}].kind must be tex or pdf")
        path = appendix.get("path")
        if not isinstance(path, str):
            fail(f"document.appendices[{index}].path is required")
        full = package_path(path, package_root, f"document.appendices[{index}].path")
        if not full.is_file():
            fail(f"document.appendices[{index}].path does not exist: {path}")
        title = tex_literal(appendix["bookmark_title"], f"document.appendices[{index}].bookmark_title")
        lines.append(f"\\ExamBeginAppendix{{{title}}}{{{appendix['id']}}}")
        if appendix["kind"] == "tex":
            lines.append(f"\\input{{{relative_tex_path(full)}}}")
        else:
            needs_pdfpages = True
            lines.append(f"\\includepdf[pages=-,pagecommand={{}}]{{{relative_tex_path(full)}}}")
        lines.append("\\clearpage")
    return lines, needs_pdfpages


def hook_lines(document: dict[str, Any], package_root: Path) -> dict[str, list[str]]:
    """Load package-local TeX fragments at explicit document lifecycle hooks."""

    hooks = {phase: [] for phase in HOOK_PHASES}
    raw = document.get("hooks")
    if raw is None:
        return hooks
    if not isinstance(raw, dict):
        fail("document.hooks must be an object")
    unknown = sorted(set(raw) - set(HOOK_PHASES))
    if unknown:
        fail(f"document.hooks has unsupported phases: {', '.join(unknown)}")
    for phase, paths in raw.items():
        if not isinstance(paths, list) or not paths:
            fail(f"document.hooks.{phase} must be a non-empty array")
        for index, path in enumerate(paths):
            if not isinstance(path, str):
                fail(f"document.hooks.{phase}[{index}] must be a package-local .tex path")
            source = package_tex_path(path, package_root, f"document.hooks.{phase}[{index}]")
            if not source.is_file():
                fail(f"document.hooks.{phase}[{index}] does not exist: {path}")
            hooks[phase].append(f"\\input{{{relative_tex_path(source)}}}")
    return hooks


def target_matrix(document: dict[str, Any], compile_config: dict[str, Any]) -> list[dict[str, Any]]:
    targets = compile_config.get("targets")
    if not isinstance(targets, list) or not targets:
        fail("compile.targets must be a non-empty array")
    clean: list[dict[str, Any]] = []
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            fail(f"compile.targets[{index}] must be an object")
        required = {"layout", "theme", "spacing", "enabled"}
        if set(target) - (required | {"answers", "output_suffix"}):
            fail(f"compile.targets[{index}] has unsupported fields")
        if not target.get("enabled", False):
            continue
        if target.get("layout") not in LAYOUTS:
            fail(f"compile.targets[{index}].layout must be a3 or a4")
        if target.get("theme") not in {"print", "cream"}:
            fail(f"compile.targets[{index}].theme must be print or cream")
        if target.get("spacing") not in {"compact", "spaced", "a4-blank"}:
            fail(f"compile.targets[{index}].spacing is invalid")
        if target.get("spacing") == "a4-blank" and target.get("layout") != "a4":
            fail(f"compile.targets[{index}].a4-blank requires layout a4")
        clean.append(dict(target))
    if not clean:
        fail("compile.targets contains no enabled target")
    return clean


def solution_structure(document: dict[str, Any]) -> dict[str, Any]:
    """Return the structural response policy for generated papers.

    Response-cell dimensions are deliberately absent from composition data.  A
    composition selects a semantic grouping policy and the class derives the
    physical slots from the active paper stock and spacing mode.
    """
    raw = document.get("solution")
    if raw is None:
        return {"structure": "pair-first", "pair_count": 2}
    if not isinstance(raw, dict):
        fail("document.solution must be an object")
    required = {"structure", "pair_count"}
    if set(raw) != required:
        missing = sorted(required - set(raw))
        extra = sorted(set(raw) - required)
        if missing:
            fail(f"document.solution is missing fields: {', '.join(missing)}")
        if extra:
            fail(f"document.solution has unsupported fields: {', '.join(extra)}")
    if raw["structure"] not in {"pair-first", "natural", "full-page"}:
        fail("document.solution.structure is invalid")
    pair_count = raw["pair_count"]
    if isinstance(pair_count, bool) or not isinstance(pair_count, int) or not 1 <= pair_count <= 8:
        fail("document.solution.pair_count must be an integer from 1 to 8")
    return {"structure": raw["structure"], "pair_count": pair_count}


def opening_settings(document: dict[str, Any]) -> dict[str, bool]:
    """Return the optional paper-opening visibility settings."""

    raw = document.get("opening")
    if raw is None:
        return {"show": True, "candidate_info": True, "notices": True}
    if not isinstance(raw, dict):
        fail("document.opening must be an object")
    required = {"show", "candidate_info", "notices"}
    if set(raw) != required:
        missing = sorted(required - set(raw))
        extra = sorted(set(raw) - required)
        if missing:
            fail(f"document.opening is missing fields: {', '.join(missing)}")
        if extra:
            fail(f"document.opening has unsupported fields: {', '.join(extra)}")
    if any(not isinstance(raw[key], bool) for key in required):
        fail("document.opening.show, candidate_info, and notices must be booleans")
    return {key: raw[key] for key in required}


RGBA_RE = re.compile(r"^rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(0|1|0?\.\d+)\s*\)$", re.I)
HEX_RGBA_RE = re.compile(r"^#([0-9a-f]{8})$", re.I)


def rgba_color(value: Any, field: str) -> tuple[str, str]:
    if not isinstance(value, str):
        fail(f"{field} must be rgba(r,g,b,a) or #RRGGBBAA")
    match = RGBA_RE.fullmatch(value.strip())
    if match:
        red, green, blue, alpha = match.groups()
        if any(int(channel) > 255 for channel in (red, green, blue)):
            fail(f"{field} RGB channels must be between 0 and 255")
        return f"{red},{green},{blue}", alpha
    match = HEX_RGBA_RE.fullmatch(value.strip())
    if match:
        raw = match.group(1)
        return f"{int(raw[0:2], 16)},{int(raw[2:4], 16)},{int(raw[4:6], 16)}", str(round(int(raw[6:8], 16) / 255, 4))
    fail(f"{field} must be rgba(r,g,b,a) or #RRGGBBAA")


def multiply_opacity(first: str, second: str) -> str:
    return f"{float(first) * float(second):.4f}".rstrip("0").rstrip(".") or "0"


def watermark_lines(document: dict[str, Any]) -> list[str]:
    raw = document.get("watermark")
    if raw is None:
        return []
    required = {"enabled", "text", "color", "opacity", "text_color", "background_color"}
    if not isinstance(raw, dict) or set(raw) != required:
        fail("document.watermark must contain enabled, text, color, opacity, text_color, background_color")
    if not isinstance(raw["enabled"], bool) or not isinstance(raw["text"], str):
        fail("document.watermark.enabled and text have invalid types")
    opacity = raw["opacity"]
    if not isinstance(opacity, (int, float)) or isinstance(opacity, bool) or not 0 <= opacity <= 1:
        fail("document.watermark.opacity must be between 0 and 1")
    colors = [rgba_color(raw[key], f"document.watermark.{key}") for key in ("color", "text_color", "background_color")]
    effective = [multiply_opacity(alpha, str(opacity)) for _, alpha in colors]
    text = tex_literal(raw["text"], "document.watermark.text")
    return [
        f"\\definecolor{{NPEEWatermarkInk}}{{RGB}}{{{colors[0][0]}}}",
        f"\\definecolor{{NPEEWatermarkText}}{{RGB}}{{{colors[1][0]}}}",
        f"\\definecolor{{NPEEWatermarkBackground}}{{RGB}}{{{colors[2][0]}}}",
        f"\\NPEESetWatermarkText{{{text}}}",
        f"\\NPEESetWatermarkOpacity{{{opacity}}}",
        "\\NPEESetWatermarkColor{NPEEWatermarkInk}",
        "\\NPEESetWatermarkTextColor{NPEEWatermarkText}",
        "\\NPEESetWatermarkBackgroundColor{NPEEWatermarkBackground}",
        f"\\NPEESetWatermarkColorOpacity{{{effective[0]}}}",
        f"\\NPEESetWatermarkTextColorOpacity{{{effective[1]}}}",
        f"\\NPEESetWatermarkBackgroundColorOpacity{{{effective[2]}}}",
        "\\NPEEEnableWatermark" if raw["enabled"] else "\\NPEEDisableWatermark",
    ]


def make_main(
    composition: dict[str, Any],
    groups: list[tuple[dict[str, Any], list[tuple[dict[str, Any], Path]]]],
    target: dict[str, Any],
    subject: str | None,
    package_root: Path,
    preamble_lines: list[str],
    hooks: dict[str, list[str]],
    cover_lines: list[str],
    back_lines: list[str],
    appendix_lines: list[str],
    needs_pdfpages: bool,
    watermark_document: dict[str, Any],
) -> str:
    # ``answers`` 是类选项（``\DeclareOption{answers}``），控制解答/答案槽是否内联显示。
    # 目标矩阵里它可能缺省；只在显式为真时追加，保持历史产物不变。
    option_parts = [target["layout"], target["theme"], target["spacing"]]
    if target.get("answers"):
        option_parts.append("answers")
    options = ",".join(option_parts)
    metadata = composition["metadata"]
    lines = ["% Generated composition entry point; do not edit by hand.", f"\\documentclass[{options}]{{npee-math-exam}}"]
    if needs_pdfpages:
        lines.append("\\usepackage{pdfpages}")
    input_paths = [f"{relative_tex_path(package_root)}/"]
    asset_root = package_root / "assets"
    if asset_root.is_dir():
        input_paths.append(f"{relative_tex_path(asset_root)}/")
    lines.extend(["\\makeatletter", f"\\def\\input@path{{{''.join(f'{{{path}}}' for path in input_paths)}}}", "\\makeatother"])
    if asset_root.is_dir():
        lines.append(f"\\graphicspath{{{{{relative_tex_path(asset_root)}/}}}}")
    active_subject = subject or (
        metadata.get("subject_scope", [None])[0]
        if len(metadata.get("subject_scope", [])) == 1
        else None
    )
    lines.extend([
        f"\\def\\NPEECompositionId{{{composition['composition_id']}}}",
        f"\\def\\NPEECompositionTitle{{{tex_literal(metadata['title'], 'metadata.title')}}}",
        f"\\def\\NPEECompositionYear{{{metadata['year']}}}",
        f"\\def\\NPEEActiveSubject{{{active_subject or ''}}}",
        f"\\def\\NPEEActiveSubjectName{{{SUBJECT_NAMES.get(active_subject, '')}}}",
        f"\\def\\NPEEActiveLayout{{{target['layout']}}}",
        f"\\def\\NPEEActiveTheme{{{target['theme']}}}",
        f"\\def\\NPEEActiveSpacing{{{target['spacing']}}}",
    ])
    lines.extend(preamble_lines)
    lines.extend(hooks["preamble"])
    if active_subject is not None:
        lines.extend([
            f"\\renewcommand{{\\NPEESubjectName}}{{{SUBJECT_NAMES[active_subject]}}}",
            f"\\renewcommand{{\\NPEESubjectCode}}{{{SUBJECT_CODES[active_subject]}}}",
        ])
    # Cover material must be in the document body; the class resets page state
    # when the collection starts.
    lines += ["\\begin{document}"]
    solution = solution_structure(composition["document"])
    lines.append(
        "\\ExamSetup{solution/structure="
        f"{solution['structure']},solution/pair-count={solution['pair_count']}}}"
    )
    lines.append(f"\\NPEEApplyTargetSpacingPolicy{{{target['spacing']}}}")
    opening = opening_settings(composition["document"])
    lines.append(
        "\\ExamSetup{"
        f"opening/show={'true' if opening['show'] else 'false'},"
        f"candidate-info/show={'true' if opening['candidate_info'] else 'false'},"
        f"candidate-notices/show={'true' if opening['notices'] else 'false'}}}"
    )
    lines += cover_lines
    lines += hooks["before_collection"]
    # Composition settings are applied after package hooks so a CLI override
    # such as --no-watermark cannot be undone by a package-local hook.
    lines += watermark_lines(watermark_document)
    lines.append("")
    lines.append("\\begin{ExamCollection}")
    document = composition["document"]
    toc = document.get("toc", {})
    if toc.get("enabled", False):
        title = tex_literal(toc.get("title", "目录"), "document.toc.title")
        include_groups = 1 if toc.get("include_groups", True) else 0
        include_papers = 1 if toc.get("include_papers", True) else 0
        lines.append(f"  \\NPEESetContentsTitle{{{title}}}")
        lines.append(f"  \\NPEESetCollectionContentsEntries{{{include_groups}}}{{{include_papers}}}")
        lines.append("  \\ExamCollectionContents")
    for group, papers in groups:
        lines.extend([
            f"\\def\\NPEEHookGroupId{{{group['id']}}}",
            f"\\def\\NPEEHookGroupTitle{{{tex_literal(group['title'], 'group.title')}}}",
        ])
        lines += hooks["before_group"]
        title = tex_literal(group["title"], "group.title")
        redundant_single_group = len(papers) == 1 and group["title"] == (
            papers[0][0].get("bookmark_title") or f"第{papers[0][0]['paper_no']}套"
        )
        if not redundant_single_group:
            lines.append(f"  \\ExamCollectionSectionMarker[{group['id']}]{{{title}}}")
        for ref, body in papers:
            title_value = ref.get("bookmark_title") or f"第{ref['paper_no']}套"
            title = tex_literal(title_value, "paper.bookmark_title")
            key = f"{ref['year']}-{ref['subject']}-{ref['series_key']}-{ref['paper_no']}"
            heading = tex_literal(
                ref.get("display_title")
                or f"{ref['year']} {ref.get('_series_name', ref['series_key'])} {title_value}",
                "paper.heading_title",
            )
            lines.append(
                f"  \\ExamInputPaper[bookmark-title={{{title}}},bookmark-key={{{key}}},heading-title={{{heading}}}]{{{relative_tex_path(body)}}}"
            )
        lines += hooks["after_group"]
    lines += ["\\end{ExamCollection}", ""]
    lines += hooks["after_collection"]
    lines += appendix_lines
    lines += back_lines
    lines += hooks["before_end_document"]
    lines += ["", "\\end{document}", ""]
    return "\n".join(lines)


def safe_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    return value.strip(" .") or "composition"


def output_name(template: str, values: dict[str, Any], suffix: str | None) -> str:
    try:
        name = template.format_map({key: str(value) for key, value in values.items()})
    except KeyError as exc:
        fail(f"Unknown output filename placeholder: {exc.args[0]}")
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    if suffix:
        stem = Path(name).stem
        name = f"{stem}{suffix}.pdf"
    return safe_filename(name)


def subject_output_name(
    template: str,
    values: dict[str, Any],
    suffix: str | None,
    subject: str | None,
) -> str:
    name = output_name(template, values, suffix)
    if subject is None or "{subject" in template:
        return name
    return safe_filename(f"{Path(name).stem} [{subject}].pdf")


def paper_reference(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{field} must be an object")
    allowed = {"year", "subject", "series_key", "paper_no", "content_hash", "catalog_id", "bookmark_title", "display_title"}
    required = {"year", "subject", "series_key", "paper_no"}
    missing = required - set(value)
    if missing:
        fail(f"{field} is missing fields: {', '.join(sorted(missing))}")
    extra = set(value) - allowed
    if extra:
        fail(f"{field} has unsupported fields: {', '.join(sorted(extra))}")
    year, subject, series_key, paper_no = value["year"], value["subject"], value["series_key"], value["paper_no"]
    if isinstance(year, bool) or not isinstance(year, int) or not 1900 <= year <= 2200:
        fail(f"{field}.year is invalid")
    if subject not in SUBJECTS and subject != "$subject":
        fail(f"{field}.subject is invalid")
    if not isinstance(series_key, str) or not ID_RE.fullmatch(series_key):
        fail(f"{field}.series_key is invalid")
    if "catalog_id" in value and (not isinstance(value["catalog_id"], str) or not ID_RE.fullmatch(value["catalog_id"])):
        fail(f"{field}.catalog_id is invalid")
    if isinstance(paper_no, bool) or not isinstance(paper_no, int) or paper_no < 1:
        fail(f"{field}.paper_no is invalid")
    for optional in ("bookmark_title", "display_title"):
        if optional in value and value[optional] is not None:
            nonempty_string(value[optional], f"{field}.{optional}")
    return dict(value)


def composition_subjects(
    composition: dict[str, Any],
    compile_config: dict[str, Any],
    groups: list[dict[str, Any]],
) -> list[str | None]:
    """Return subject variants, using ``$subject`` refs as a template switch."""

    has_template = any(
        isinstance(group, dict)
        and any(isinstance(ref, dict) and ref.get("subject") == "$subject" for ref in group.get("papers", []))
        for group in groups
    )
    raw_subjects = compile_config.get("subjects")
    if raw_subjects is None and has_template:
        metadata = composition.get("metadata")
        raw_subjects = metadata.get("subject_scope") if isinstance(metadata, dict) else None
    if raw_subjects is None:
        if has_template:
            fail("compile.subjects or metadata.subject_scope is required when paper subject is $subject")
        return [None]
    if not has_template:
        fail("compile.subjects is only valid when paper subject is $subject")
    if not isinstance(raw_subjects, list) or not raw_subjects:
        fail("compile.subjects must be a non-empty array")
    subjects: list[str] = []
    for index, subject in enumerate(raw_subjects):
        if subject not in SUBJECTS:
            fail(f"compile.subjects[{index}] must be math1, math2, or math3")
        if subject not in subjects:
            subjects.append(subject)
    return subjects


def materialize_groups(
    groups: list[dict[str, Any]],
    subject: str | None,
) -> list[tuple[dict[str, Any], list[tuple[dict[str, Any], Path]]]]:
    materialized: list[tuple[dict[str, Any], list[tuple[dict[str, Any], Path]]]] = []
    for group in groups:
        refs: list[tuple[dict[str, Any], Path]] = []
        for ref, _ in group["_refs"]:
            if ref["subject"] == "$subject":
                if subject is None:
                    fail("paper subject template could not be resolved")
                refs.append(({**ref, "subject": subject}, Path()))
            else:
                refs.append((ref, Path()))
        materialized.append((group, refs))
    return materialized
