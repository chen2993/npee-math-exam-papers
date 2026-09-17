#!/usr/bin/env python3
"""Composition builder: composition JSON -> generated TeX -> XeLaTeX -> PDF.

The data path is intentionally one-way, and the builder never edits the store:

    composition JSON -> paper store -> generated TeX -> XeLaTeX/LuaLaTeX -> PDF

This module is the orchestrator. The pieces live in
:mod:`npee_math_papers.service.rendering`:

* :mod:`~npee_math_papers.service.rendering.paths` — repository/package path safety
* :mod:`~npee_math_papers.service.rendering.text` — literal and key helpers
* :mod:`~npee_math_papers.service.rendering.inline_tex` — inline-TeX repair rules
* :mod:`~npee_math_papers.service.rendering.validation` — render-model validation
* :mod:`~npee_math_papers.service.rendering.catalogs` — store -> catalog resolution
* :mod:`~npee_math_papers.service.rendering.content` — question rendering
* :mod:`~npee_math_papers.service.rendering.document` — targets, hooks, watermark, naming

It stays importable as before: :class:`BuildOptions`, :func:`build` and every helper
it re-exports are the module's public surface for the CLI and the service layer.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

from npee_math_papers.core.domain import (  # noqa: E402
    HOOK_PHASES,
    ID_RE,
    LAYOUTS,
    SECTION_LABELS,
    SPACING_LABELS,
    SPACINGS,
    SUBJECT_CODES,
    SUBJECT_LABELS,
    SUBJECTS,
)
from npee_math_papers.service.rendering.errors import CompositionError, fail  # noqa: E402
from npee_math_papers.service.rendering.content import (  # noqa: E402,F401
    CIRCLED_DIGITS,
    format_circled_markers,
    render_body,
    render_question,
    score_option,
)
from npee_math_papers.service.rendering.document import (  # noqa: E402,F401
    appendix_blocks,
    composition_subjects,
    materialize_groups,
    paper_reference,
    hook_lines,
    make_main,
    matter_block,
    opening_settings,
    solution_structure,
    subject_output_name,
    target_matrix,
    watermark_lines,
)
from npee_math_papers.service.rendering.catalogs import (  # noqa: E402,F401
    derive_year,
    load_catalogs,
    resolve_catalog_paper,
)
from npee_math_papers.service.rendering.inline_tex import (  # noqa: E402,F401
    ALIGNMENT_ENVIRONMENTS,
    ALIGNMENT_ROW_COMMANDS,
    DOUBLE_SLASH_MATH_COMMANDS,
    INLINE_TEX_COMMANDS,
    OPERATOR_LIMIT_RE,
    cjk_math_characters,
    repair_alignment_rows,
    repair_cases_rows,
    repair_quoted_math_runs,
    repair_repeated_escaped_braces,
    repair_text_arrays,
    repair_text_mode_unit_exponents,
    validate_inline_tex,
)
from npee_math_papers.service.rendering.paths import (  # noqa: E402,F401
    package_path,
    package_tex_path,
    relative_tex_path,
    repository_path,
)
from npee_math_papers.service.rendering.text import (  # noqa: E402,F401
    nonempty_string,
    require_keys,
    tex_literal,
)
from npee_math_papers.service.rendering.validation import (  # noqa: E402,F401
    FIGURE_KEYS,
    QUESTION_KEYS,
    validate_figure,
    validate_questions,
)

# --- 兼容再导出 ---------------------------------------------------------
# 下面这些名字由 service.rendering 的实现模块提供，tex_builder 继续再导出，
# 以保证既有调用点（CLI、maintenance、测试）无需改动。它们不是本模块的实现。

# 术语常量只有一份定义（core.domain），这里仅做别名以保持既有调用点可读。
SUBJECT_NAMES = SUBJECT_LABELS
SPACING_NAMES = SPACING_LABELS
SECTIONS = SECTION_LABELS
LAYOUTS = set(LAYOUTS)

@dataclass

class BuildOptions:
    """组卷编译选项。

    由用例层或 CLI 构造，替代原先的 argparse 命名空间，使本模块可直接被导入调用。
    """

    composition: Path
    work_dir: Path | None = None
    output_dir: Path | None = None
    dry_run: bool = False
    clean: bool = False
    no_watermark: bool = False
    spacing: str | None = None
    layouts: str | None = None
    verbose: bool = True
    # 组卷包根目录：封面、前言、Hook 等与 composition.json 同级的 .tex 资源所在目录。
    # 用例层把 composition.json 复制到构建目录后，仍需要按"原始组卷包"解析这些相对
    # 路径；为空时退回到 composition.json 的所在目录（CLI 直接编译组卷包时的行为）。
    package_dir: Path | None = None
    # 用例层注入的题库存储。显式传入可保证构建器读取的题库与调用它的
    # ``NpeeService`` 是同一个数据根；CLI 不传时回退到默认数据根。
    store: "PaperStore | None" = None


def parse_args(argv: list[str] | None = None) -> BuildOptions:
    """解析命令行参数，主要供 ``python -m npee_math_papers.service.tex_builder`` 使用。"""

    parser = argparse.ArgumentParser(description="NPEE 组卷编译器")
    parser.add_argument("--composition", required=True, type=Path, help="组卷 JSON 路径")
    parser.add_argument("--work-dir", type=Path, help="生成的 TeX/日志目录")
    parser.add_argument("--output-dir", type=Path, help="覆盖 compile.output.directory")
    parser.add_argument("--dry-run", action="store_true", help="只生成 TeX，不调用 XeLaTeX")
    parser.add_argument("--clean", action="store_true", help="先清空本组卷的生成目录")
    parser.add_argument("--no-watermark", action="store_true", help="关闭本次编译水印")
    parser.add_argument("--spacing", choices=SPACINGS, help="只编译指定版式")
    parser.add_argument("--layouts", choices=("a3", "a4", "both"), help="只编译指定纸张")
    args = parser.parse_args(argv)
    return BuildOptions(
        composition=args.composition,
        work_dir=args.work_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        clean=args.clean,
        no_watermark=args.no_watermark,
        spacing=args.spacing,
        layouts=args.layouts,
    )


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        fail(f"Composition JSON does not exist: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid composition JSON: {exc}")
    if not isinstance(value, dict):
        fail("Composition root must be an object")
    return value


def build(options: BuildOptions) -> dict[str, Any]:
    """编译一份组卷，返回结果报告。

    由 :class:`npee_math_papers.service.composition.CompositionService` 调用。失败时抛出
    :class:`CompositionError`，成功时返回包含产物路径的报告字典。
    """

    composition_path = repository_path(options.composition, "--composition")
    return _build_impl(options, composition_path)


def main(argv: list[str] | None = None) -> int:
    """命令行入口。"""

    options = parse_args(argv)
    try:
        report = build(options)
    except CompositionError as exc:
        print(f"tex_builder: error: {exc}", file=sys.stderr)
        return 2
    if options.dry_run:
        for target in report.get("targets", []):
            label = target.get("subject") or "fixed"
            print(f"DRY-RUN {label} {target.get('layout')} {target.get('theme')} {target.get('spacing')} -> {target.get('pdf')}")
    return 0


def _build_impl(options: BuildOptions, composition_path: Path) -> dict[str, Any]:
    composition = load_json(composition_path)
    # 组卷包资源（封面/前言/Hook）与 composition.json 同级。用例层会把 composition.json
    # 复制进构建目录，因此这里允许显式给出原始组卷包目录，缺省才回退到文件所在目录。
    package_root = (options.package_dir or composition_path.parent).resolve()
    require_keys(composition, {"schema_version", "composition_id", "metadata", "catalog", "document", "groups", "compile"}, "composition")
    if composition["schema_version"] not in {"2.0", "3.0"}:
        fail("composition.schema_version must be '2.0' or '3.0'")
    composition_id = composition["composition_id"]
    if not isinstance(composition_id, str) or not ID_RE.fullmatch(composition_id):
        fail("composition_id must be a lowercase ASCII ID")
    metadata = composition["metadata"]
    if not isinstance(metadata, dict) or not isinstance(metadata.get("title"), str) or not metadata["title"].strip():
        fail("metadata.title must be non-empty")
    if not isinstance(metadata.get("year"), int) or not 1900 <= metadata["year"] <= 2200:
        # schema 3.0 compositions may omit the year; derive it from the papers so a
        # minimal selection still produces a correct cover page.
        derived_year = derive_year(composition)
        if derived_year is None:
            fail("metadata.year is invalid and could not be derived from the selected papers")
        metadata = {**metadata, "year": derived_year}
        composition = {**composition, "metadata": metadata}
    document = composition["document"]
    if not isinstance(document, dict):
        fail("document must be an object")
    compile_config = composition["compile"]
    if not isinstance(compile_config, dict):
        fail("compile must be an object")
    engine = compile_config.get("engine", "xelatex")
    if engine not in {"xelatex", "lualatex"}:
        fail("compile.engine must be xelatex or lualatex")
    passes = compile_config.get("passes", 3)
    if isinstance(passes, bool) or not isinstance(passes, int) or not 1 <= passes <= 5:
        fail("compile.passes must be an integer from 1 to 5")
    targets = target_matrix(document, compile_config)
    if options.spacing:
        targets = [target for target in targets if target["spacing"] == options.spacing]
    if options.layouts and options.layouts != "both":
        targets = [target for target in targets if target["layout"] == options.layouts]
    if not targets:
        fail("the requested target overrides selected no compile targets")
    watermark_document = document
    if options.no_watermark:
        watermark_document = {**document, "watermark": {
            "enabled": False,
            "text": "disabled",
            "color": "rgba(0, 0, 0, 0)",
            "opacity": 0,
            "text_color": "rgba(0, 0, 0, 0)",
            "background_color": "rgba(255, 255, 255, 0)",
        }}
    series, papers = load_catalogs(composition, store=options.store)

    groups_raw = composition["groups"]
    if not isinstance(groups_raw, list) or not groups_raw:
        fail("groups must be a non-empty array")
    groups: list[dict[str, Any]] = []
    ordered_groups = sorted(
        groups_raw,
        key=lambda item: item.get("order_index", 0) if isinstance(item, dict) else 0,
    )
    for group_index, group in enumerate(ordered_groups):
        if not isinstance(group, dict):
            fail(f"groups[{group_index}] must be an object")
        for key in ("id", "title", "order_index", "papers"):
            if key not in group:
                fail(f"groups[{group_index}] is missing {key}")
        if not isinstance(group["id"], str) or not ID_RE.fullmatch(group["id"]):
            fail(f"groups[{group_index}].id is invalid")
        if not isinstance(group["papers"], list) or not group["papers"]:
            fail(f"groups[{group_index}].papers must be non-empty")
        refs: list[tuple[dict[str, Any], Path]] = []
        for paper_index, raw_ref in enumerate(group["papers"]):
            ref = paper_reference(raw_ref, f"groups[{group_index}].papers[{paper_index}]")
            ref = {**ref, "_series_name": series.get(ref["series_key"], ref["series_key"])}
            refs.append((ref, Path()))
        groups.append({**group, "_refs": refs})
    subject_variants = composition_subjects(composition, compile_config, groups)

    work_dir = repository_path(options.work_dir, "--work-dir") if options.work_dir else ROOT / "build" / "generated" / composition_id
    if options.clean and work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    body_dir = work_dir / "papers"
    body_dir.mkdir(parents=True, exist_ok=True)

    rebuilt_variants: list[tuple[str | None, list[tuple[dict[str, Any], list[tuple[dict[str, Any], Path]]]]]] = []
    for subject in subject_variants:
        occurrence = 0
        rebuilt_groups: list[tuple[dict[str, Any], list[tuple[dict[str, Any], Path]]]] = []
        variant_body_dir = body_dir / (subject or "fixed")
        variant_body_dir.mkdir(parents=True, exist_ok=True)
        for group, refs in materialize_groups(groups, subject):
            rebuilt: list[tuple[dict[str, Any], Path]] = []
            for ref, _ in refs:
                occurrence += 1
                body = variant_body_dir / f"paper-{occurrence:03d}.tex"
                key = (ref["year"], ref["subject"], ref["series_key"], ref["paper_no"])
                questions = resolve_catalog_paper(papers, key, ref.get("catalog_id"), "paper reference")
                body.write_text(render_body(questions, occurrence), encoding="utf-8")
                rebuilt.append((ref, body))
            rebuilt_groups.append((group, rebuilt))
        rebuilt_variants.append((subject, rebuilt_groups))

    cover_preamble, cover_lines, cover_pdf = matter_block(document.get("cover"), "cover", package_root)
    back_preamble, back_lines, back_pdf = matter_block(document.get("back_matter"), "back_matter", package_root)
    appendix_lines, appendix_pdf = appendix_blocks(document, package_root)
    preamble_lines = [*cover_preamble, *back_preamble]
    hooks = hook_lines(document, package_root)
    needs_pdfpages = cover_pdf or back_pdf or appendix_pdf

    output_config = compile_config.get("output")
    if not isinstance(output_config, dict) or not isinstance(output_config.get("directory"), str) or not isinstance(output_config.get("filename_template"), str):
        fail("compile.output.directory and compile.output.filename_template are required")
    output_dir = repository_path(options.output_dir, "--output-dir") if options.output_dir else repository_path(output_config["directory"], "compile.output.directory")
    output_dir.mkdir(parents=True, exist_ok=True)

    generated: list[dict[str, Any]] = []
    for subject, rebuilt_groups in rebuilt_variants:
        for target in targets:
            label_parts = [part for part in (subject, target["layout"], target["theme"], target["spacing"]) if part]
            label = "-".join(label_parts)
            variant_dir = work_dir / label
            variant_dir.mkdir(parents=True, exist_ok=True)
            main_tex = variant_dir / "main.tex"
            main_tex.write_text(
                make_main(composition, rebuilt_groups, target, subject, package_root, preamble_lines, hooks, cover_lines, back_lines, appendix_lines, needs_pdfpages, watermark_document),
                encoding="utf-8",
            )
            values = {
                "layout": target["layout"].upper(),
                "theme": target["theme"],
                "spacing": target["spacing"],
                "spacing_label": SPACING_NAMES[target["spacing"]],
                "title": metadata["title"],
                "composition_id": composition_id,
                "year": metadata["year"],
                "subject": subject or "-".join(metadata.get("subject_scope", [])),
                "subject_label": SUBJECT_NAMES[subject] if subject else "-".join(
                    SUBJECT_NAMES.get(item, item) for item in metadata.get("subject_scope", [])
                ),
            }
            name = subject_output_name(output_config["filename_template"], values, target.get("output_suffix"), subject)
            target_pdf = output_dir / name
            generated.append({"subject": subject, "target": target, "main": main_tex, "pdf": target_pdf})

    report = {
        "composition_id": composition_id,
        "work_dir": relative_tex_path(work_dir),
        "targets": [{"subject": item["subject"], "layout": item["target"]["layout"], "theme": item["target"]["theme"], "spacing": item["target"]["spacing"], "pdf": str(item["pdf"].relative_to(ROOT)).replace("\\", "/")} for item in generated],
        "paper_count": sum(len(items) for _, groups_for_subject in rebuilt_variants for _, items in groups_for_subject),
    }
    (work_dir / "composition.report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if options.dry_run:
        if options.verbose:
            for item in generated:
                subject_label = item["subject"] or "fixed"
                print(f"DRY-RUN {subject_label} {item['target']['layout']} {item['target']['theme']} {item['target']['spacing']} -> {item['pdf']}")
        return report

    executable = shutil.which(engine)
    if not executable:
        fail(f"TeX engine not found on PATH: {engine}")
    old_texinputs = os.environ.get("TEXINPUTS")
    texinput_paths = [ROOT, work_dir, package_root, package_root / "assets", ROOT / "npee_math_papers" / "tex"]
    texinputs = os.pathsep.join(str(path) for path in texinput_paths if path.is_dir()) + os.pathsep
    os.environ["TEXINPUTS"] = texinputs + (old_texinputs or "")
    try:
        for item in generated:
            variant_dir = item["main"].parent
            log_path = variant_dir / "build.log"
            with log_path.open("w", encoding="utf-8") as log:
                for pass_index in range(1, passes + 1):
                    command = [
                        executable,
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        "-file-line-error",
                        f"-output-directory={variant_dir}",
                        "-jobname=main",
                        str(item["main"]),
                    ]
                    result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, text=True)
                    if result.returncode != 0:
                        fail(f"{engine} pass {pass_index} failed; see {log_path}")
            built_pdf = variant_dir / "main.pdf"
            if not built_pdf.is_file():
                fail(f"TeX completed without producing {built_pdf}")
            if item["pdf"].exists() and not output_config.get("overwrite", False):
                fail(f"Output already exists and overwrite=false: {item['pdf']}")
            shutil.copy2(built_pdf, item["pdf"])
            if options.verbose:
                print(f"Built {item['pdf']}")
    finally:
        if old_texinputs is None:
            os.environ.pop("TEXINPUTS", None)
        else:
            os.environ["TEXINPUTS"] = old_texinputs
    return report


if __name__ == "__main__":
    raise SystemExit(main())
