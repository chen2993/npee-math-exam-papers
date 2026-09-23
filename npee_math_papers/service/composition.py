"""Composition use cases: 组卷构建、校验与编译。

本模块负责：

- 由套卷选择生成组卷文档，并封印每套的 ``content_hash``；
- 校验组卷结构与版本绑定；
- 调用 :mod:`npee_math_papers.service.tex_builder` 生成并编译 PDF。
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from npee_math_papers.core.composition import (
    CompositionSpec,
    Group,
    PaperRef,
    composition_document,
    load_composition,
    parse_composition,
    verify_bindings,
)
from npee_math_papers.core.domain import DEFAULT_PRINT, DEFAULT_SPACING, SUBJECTS, SUBJECT_TEMPLATE
from npee_math_papers.core.errors import NotFoundError, ValidationError
from npee_math_papers.core.store import atomic_write_json
from npee_math_papers.service.context import ServiceContext
from npee_math_papers.service.jobs import CompileJob, CompileJobStore
from npee_math_papers.service.tex_builder import BuildOptions, build as build_tex

#: The stocks the print deliverable is produced on.
PRINT_LAYOUTS: tuple[str, ...] = ("a3", "a4")

DEFAULT_DOCUMENT = {
    "toc": {"enabled": True, "title": "目录", "include_groups": True, "include_papers": True},
    "layout": "a4",
    "theme": "print",
    "spacing": DEFAULT_SPACING,
    "opening": {"show": True, "candidate_info": True, "notices": True},
}

#: 默认编译矩阵：两种纸张各一份，默认留白（打印交付物）。
#:
#: ``spacing`` 只决定解答题怎么排，``print`` 只决定留白，两者互相独立。
DEFAULT_COMPILE = {
    "engine": "xelatex",
    "passes": 3,
    "targets": [
        {
            "layout": layout,
            "theme": "print",
            "spacing": DEFAULT_SPACING,
            "print": DEFAULT_PRINT,
            "enabled": True,
            "answers": False,
            "output_suffix": None,
        }
        for layout in PRINT_LAYOUTS
    ],
    "output": {
        "directory": "build/output",
        "filename_template": "[{layout}][{subject_label}][{spacing_label}] {title}.pdf",
        "overwrite": True,
    },
}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass
class CompileResult:
    """一次编译的结果。"""

    ok: bool
    composition_id: str
    report: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "composition_id": self.composition_id,
            "artifacts": list(self.artifacts),
            "error": self.error,
            "report": self.report,
        }


class CompositionService:
    """由套卷选择构建并编译组卷。"""

    def __init__(self, context: ServiceContext, *, repository_root: Path) -> None:
        self.ctx = context
        self.repository_root = Path(repository_root).resolve()
        self.jobs = CompileJobStore()

    # --- 选择 -> 组卷文档 --------------------------------------------------

    def build(
        self,
        composition_id: str,
        title: str,
        selections: Sequence[Mapping[str, Any]],
        *,
        document: Mapping[str, Any] | None = None,
        compile_config: Mapping[str, Any] | None = None,
        pin_hashes: bool = True,
        release_id: str | None = None,
    ) -> dict[str, Any]:
        """由平铺的套卷选择生成组卷文档。

        每项选择为 ``{series_key, year, subject, paper_no}``。``pin_hashes`` 为真时
        每个引用都会记录当前 ``content_hash``，从而在之后编译时能检测题库漂移。
        """

        if not ID_RE.fullmatch(composition_id or ""):
            raise ValidationError("composition_id 必须是小写 ASCII ID")
        if not title.strip():
            raise ValidationError("title 不能为空")
        if not selections:
            raise ValidationError("至少选择一套试卷")

        refs: list[PaperRef] = []
        source_ids: list[str] = []
        for index, selection in enumerate(selections):
            if not isinstance(selection, Mapping):
                raise ValidationError(f"selections[{index}] 必须是对象")
            series_key = str(selection.get("series_key") or "")
            subject = str(selection.get("subject") or "")
            try:
                year = int(selection.get("year"))
                paper_no = int(selection.get("paper_no"))
            except (TypeError, ValueError) as error:
                raise ValidationError(f"selections[{index}] 需要整数 year 与 paper_no") from error
            if subject not in SUBJECTS:
                raise ValidationError(f"selections[{index}].subject 必须是 math1/math2/math3")
            if not self.ctx.store.has_paper(series_key, year, subject, paper_no):
                raise ValidationError(f"selections[{index}] 指向不存在的套卷：{series_key}/{year}/{subject}/{paper_no}")
            content_hash = None
            if pin_hashes:
                content_hash = self.ctx.store.read_paper_summary(series_key, year, subject, paper_no)["content_hash"] or None
            refs.append(PaperRef(year=year, subject=subject, series_key=series_key, paper_no=paper_no, content_hash=content_hash))
            if series_key not in source_ids:
                source_ids.append(series_key)

        group = Group(id="selected", title="试卷", order_index=1, papers=refs)
        return composition_document(
            composition_id=composition_id,
            title=title,
            groups=[group],
            source_ids=source_ids,
            document=dict(document or DEFAULT_DOCUMENT),
            compile_config=dict(compile_config or DEFAULT_COMPILE),
            release_id=release_id,
        )

    def build_by_group(
        self,
        composition_id: str,
        groups: Sequence[Mapping[str, Any]],
        *,
        document: Mapping[str, Any] | None = None,
        compile_config: Mapping[str, Any] | None = None,
        pin_hashes: bool = True,
        release_id: str | None = None,
    ) -> dict[str, Any]:
        """由显式分组生成组卷文档。"""

        if not ID_RE.fullmatch(composition_id or ""):
            raise ValidationError("composition_id 必须是小写 ASCII ID")
        if not groups:
            raise ValidationError("至少需要一个分组")
        parsed_groups: list[Group] = []
        source_ids: list[str] = []
        for group_index, group in enumerate(groups):
            if not isinstance(group, Mapping):
                raise ValidationError(f"groups[{group_index}] 必须是对象")
            group_id = str(group.get("id") or f"group-{group_index + 1}")
            group_title = str(group.get("title") or f"第 {group_index + 1} 组")
            order_index = int(group.get("order_index", group_index + 1))
            papers_raw = group.get("papers")
            if not isinstance(papers_raw, list) or not papers_raw:
                raise ValidationError(f"groups[{group_index}].papers 不能为空")
            refs: list[PaperRef] = []
            for paper_index, paper in enumerate(papers_raw):
                if not isinstance(paper, Mapping):
                    raise ValidationError(f"groups[{group_index}].papers[{paper_index}] 必须是对象")
                series_key = str(paper.get("series_key") or "")
                subject = str(paper.get("subject") or "")
                try:
                    year = int(paper.get("year"))
                    paper_no = int(paper.get("paper_no"))
                except (TypeError, ValueError) as error:
                    raise ValidationError(f"groups[{group_index}].papers[{paper_index}] 需要整数 year 与 paper_no") from error
                if subject not in SUBJECTS:
                    raise ValidationError(f"groups[{group_index}].papers[{paper_index}].subject 无效")
                if not self.ctx.store.has_paper(series_key, year, subject, paper_no):
                    raise ValidationError(f"套卷不存在：{series_key}/{year}/{subject}/{paper_no}")
                content_hash = None
                if pin_hashes:
                    content_hash = self.ctx.store.read_paper_summary(series_key, year, subject, paper_no)["content_hash"] or None
                refs.append(PaperRef(year=year, subject=subject, series_key=series_key, paper_no=paper_no, content_hash=content_hash))
                if series_key not in source_ids:
                    source_ids.append(series_key)
            parsed_groups.append(Group(id=group_id, title=group_title, order_index=order_index, papers=refs))
        return composition_document(
            composition_id=composition_id,
            title="组卷",
            groups=parsed_groups,
            source_ids=source_ids,
            document=dict(document or DEFAULT_DOCUMENT),
            compile_config=dict(compile_config or DEFAULT_COMPILE),
            release_id=release_id,
        )

    # --- 校验 --------------------------------------------------------------

    def validate(self, composition: Mapping[str, Any]) -> dict[str, Any]:
        """校验组卷结构及其与当前题库的内容绑定。"""

        spec = parse_composition(composition)
        lookup = self.ctx.store.content_hash_lookup()
        binding = verify_bindings(spec, lookup)
        return {"ok": binding["ok"], "composition_id": spec.composition_id, "bindings": binding}

    def load(self, path: str | Path) -> dict[str, Any]:
        """读取组卷文件并校验。"""

        return self.validate(load_composition(Path(path)).to_dict())

    # --- 组卷包仓库 --------------------------------------------------------
    #
    # ``composition/<id>/composition.json`` 是人工维护的组卷包（封面、Hook 与资源
    # 都在同目录）。此前只有维护脚本会去读写它们，前端只能另存一份 localStorage
    # 草稿，两边因此长期不同步；这里把它当作服务端仓库暴露出来，浏览器与 Agent
    # 看到的是同一批文件。

    @property
    def packages_root(self) -> Path:
        return self.repository_root / "composition"

    def _package_path(self, composition_id: str) -> Path:
        if not ID_RE.fullmatch(composition_id or ""):
            raise ValidationError("composition_id 必须是小写 ASCII ID")
        root = self.packages_root.resolve()
        candidate = (root / composition_id / "composition.json").resolve()
        # 目录穿越守卫：解析后的路径必须仍在 composition/ 之内。
        if root not in candidate.parents:
            raise ValidationError("composition_id 越出了 composition/ 目录")
        return candidate

    def list_packages(self) -> list[dict[str, Any]]:
        """列出仓库里的组卷包，附带一份轻量摘要（不解析整份引用）。"""

        if not self.packages_root.is_dir():
            return []
        entries: list[dict[str, Any]] = []
        for path in sorted(self.packages_root.glob("*/composition.json")):
            try:
                spec = load_composition(path)
            except Exception:  # 坏包不该让整个列表打不开
                continue
            document = spec.raw.get("document") or {}
            compile_config = spec.raw.get("compile") or {}
            targets = [
                target for target in compile_config.get("targets") or []
                if isinstance(target, dict) and target.get("enabled", True)
            ]
            subjects = compile_config.get("subjects") or ["math1"]
            # ``$subject`` 引用会在每个科目下各展开一次，所以按科目数折算实际套数；
            # 只写死科目的引用算一套。这样列表里的数字与真正会排版出来的卷数一致。
            paper_count = sum(
                len(subjects) if paper.subject == SUBJECT_TEMPLATE else 1
                for paper in spec.papers
            )
            entries.append({
                "composition_id": spec.composition_id,
                "title": spec.title,
                "group_count": len(spec.groups),
                "reference_count": len(spec.papers),
                "paper_count": paper_count,
                "subjects": list(subjects),
                "target_count": len(targets),
                "layout": document.get("layout"),
                "theme": document.get("theme"),
                "spacing": document.get("spacing"),
                "has_cover": bool((document.get("cover") or {}).get("path")),
            })
        return entries

    def load_package(self, composition_id: str) -> dict[str, Any]:
        """读取一个组卷包的完整文档（含封面与 Hook 声明）。"""

        path = self._package_path(composition_id)
        if not path.is_file():
            raise NotFoundError(f"组卷包不存在：{composition_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "composition_id": composition_id,
            "path": path.relative_to(self.repository_root).as_posix(),
            "composition": data,
            "validation": self.validate(data),
        }

    def save_package(self, composition_id: str, composition: Mapping[str, Any]) -> dict[str, Any]:
        """把一份组卷文档写回 ``composition/<id>/composition.json``。

        先校验再落盘，因此写坏一个包不会被静默保存。封面、Hook 等资源不在这里
        管理——它们本来就是包内的普通文件，缺哪个由编译时的相对路径检查报出来。
        """

        path = self._package_path(composition_id)
        self.validate(composition)
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, dict(composition))
        return {
            "composition_id": composition_id,
            "path": path.relative_to(self.repository_root).as_posix(),
            "validation": self.validate(composition),
        }

    def compile_collection(
        self,
        path: str | Path,
        *,
        dry_run: bool = False,
        layouts: str | None = None,
        spacing: str | None = None,
        check_bindings: bool = True,
        verbose: bool = False,
        work_dir: str | Path | None = None,
        output_dir: str | Path | None = None,
    ) -> CompileResult:
        """编译一个组卷包目录下的 ``composition.json``。

        组卷包（``composition/<id>/``）可以在 ``composition.json`` 旁放置封面、前言与
        Hook 等 ``.tex`` 资源。本方法读取该文件并把这些包内资源一并交给构建器，因此
        走用例层（HTTP/MCP/启动器）时也能解析包内相对路径。
        """

        composition_path = Path(path)
        if composition_path.is_dir():
            composition_path = composition_path / "composition.json"
        spec = load_composition(composition_path)
        return self.compile(
            spec.to_dict(),
            dry_run=dry_run,
            layouts=layouts,
            spacing=spacing,
            check_bindings=check_bindings,
            verbose=verbose,
            work_dir=work_dir,
            output_dir=output_dir,
            package_dir=composition_path.parent,
        )

    # --- 编译 --------------------------------------------------------------

    def compile(
        self,
        composition: Mapping[str, Any],
        *,
        dry_run: bool = False,
        layouts: str | None = None,
        spacing: str | None = None,
        work_dir: str | Path | None = None,
        output_dir: str | Path | None = None,
        check_bindings: bool = True,
        verbose: bool = False,
        package_dir: str | Path | None = None,
    ) -> CompileResult:
        """校验绑定后调用 TeX 构建器。

        先校验绑定，可在题库变更时快速失败，而不是渲染出与预期不同的内容。

        ``package_dir`` 指向组卷包目录（与 ``composition.json`` 同级的封面、前言与
        Hook 所在处）。构建器会把 ``composition.json`` 复制到构建目录，因此这里需要
        知道原始组卷包，才能解析其中的相对 ``.tex`` 资源；不传时不启用包资源。
        """

        spec = parse_composition(composition)
        composition_id = spec.composition_id
        if check_bindings:
            lookup = self.ctx.store.content_hash_lookup()
            result = verify_bindings(spec, lookup)
            if not result["ok"]:
                return CompileResult(
                    ok=False,
                    composition_id=composition_id,
                    error=f"组卷绑定已过期：changed={result['changed']} missing={result['missing']}",
                    report=result,
                )
        work = Path(work_dir) if work_dir else self.repository_root / "build" / "compositions" / composition_id / "generated"
        out = Path(output_dir) if output_dir else self.repository_root / "dist" / composition_id
        work.mkdir(parents=True, exist_ok=True)
        composition_path = work.parent / "composition.json"
        composition_path.write_text(json.dumps(composition, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        # 组卷包资源（封面/前言/Hook）按相对路径解析。构建器以 composition.json 所在
        # 目录为包根，因此把组卷包里的 .tex 资源复制到生成的 composition.json 旁边，
        # 使 `document.cover.path` 之类的相对引用在服务端路径下同样可解析。
        resolved_package: Path | None = None
        if package_dir is not None:
            resolved_package = Path(package_dir)
            if not resolved_package.is_dir():
                return CompileResult(
                    ok=False,
                    composition_id=composition_id,
                    error=f"组卷包目录不存在：{resolved_package.as_posix()}",
                )
            for asset in resolved_package.glob("*.tex"):
                shutil.copy2(asset, composition_path.parent / asset.name)
            assets_dir = resolved_package / "assets"
            if assets_dir.is_dir():
                shutil.copytree(assets_dir, composition_path.parent / "assets", dirs_exist_ok=True)

        options = BuildOptions(
            composition=composition_path,
            work_dir=work,
            output_dir=out,
            dry_run=dry_run,
            clean=True,
            layouts=layouts,
            spacing=spacing,
            verbose=verbose,
            package_dir=composition_path.parent if resolved_package is not None else None,
            store=self.ctx.store,
        )
        try:
            report = build_tex(options)
        except Exception as error:  # tex_builder raises its own error type
            return CompileResult(ok=False, composition_id=composition_id, error=str(error))
        artifacts = [str(target.get("pdf")) for target in report.get("targets", []) if isinstance(target, dict) and target.get("pdf")]
        return CompileResult(ok=True, composition_id=composition_id, report=report, artifacts=artifacts)

    def submit_compile(
        self,
        composition: Mapping[str, Any],
        *,
        dry_run: bool = False,
        layouts: str | None = None,
        spacing: str | None = None,
        check_bindings: bool = True,
        package_dir: str | Path | None = None,
    ) -> CompileJob:
        """把编译放到后台线程，立即返回可轮询的任务。

        绑定校验在提交前同步完成：过期组卷会立刻失败，而不是占用一个后台任务。
        """

        spec = parse_composition(composition)
        if check_bindings:
            lookup = self.ctx.store.content_hash_lookup()
            verdict = verify_bindings(spec, lookup)
            if not verdict["ok"]:
                job = CompileJob(job_id="rejected", composition_id=spec.composition_id, status="failed")
                job.error = f"组卷绑定已过期：changed={verdict['changed']} missing={verdict['missing']}"
                job.report = verdict
                job.finished_at = job.created_at
                return job

        def runner() -> tuple[bool, list[str], dict[str, Any], str | None]:
            result = self.compile(
                composition,
                dry_run=dry_run,
                layouts=layouts,
                spacing=spacing,
                check_bindings=False,
                package_dir=package_dir,
            )
            return result.ok, result.artifacts, result.report, result.error

        return self.jobs.submit(spec.composition_id, runner)

    def get_job(self, job_id: str) -> CompileJob | None:
        """按 ID 读取编译任务。"""

        return self.jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        """返回最近的编译任务。"""

        return self.jobs.list(limit)
