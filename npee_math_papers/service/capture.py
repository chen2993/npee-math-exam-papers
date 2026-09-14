"""PDF 页面捕获：把来源 PDF 渲染为可提取的页面 PNG。

流程：

1. 用 ``pdfinfo`` 读取页数；
2. 按给定范围与排除页计算题面页集合；
3. 用 ``pdftoppm`` 按 DPI 渲染；
4. 只保留题面页，重命名为 ``p####.png`` 写入 capture；
5. 登记来源 PDF 与 capture 元数据（页码边界、哈希）。

页面证据进入 ``.npee-math-papers/captures/``，是可复现的中间产物。
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from npee_math_papers.core.errors import ValidationError
from npee_math_papers.service.context import ServiceContext

DEFAULT_DPI = 220
MIN_DPI = 150
MAX_DPI = 600
PAGE_RENDER_RE = re.compile(r"^p(\d{4})\.png$")


@dataclass(frozen=True)
class PdfInfo:
    """来源 PDF 的基础信息。"""

    page_count: int
    path: Path


@dataclass(frozen=True)
class CaptureResult:
    """一次页面捕获的结果。"""

    source: dict
    capture: dict
    rendered_pages: list[int]

    def to_dict(self) -> dict:
        return {"source": self.source, "capture": self.capture, "rendered_pages": list(self.rendered_pages)}


def _require_tool(name: str) -> str:
    """返回可执行文件路径，缺失时给出可操作的错误。"""

    found = shutil.which(name)
    if not found:
        raise ValidationError(
            f"缺少 PDF 工具 {name!r}；请安装 Poppler 并把它的 bin 目录加入 PATH，"
            f"或改用 --copy/--no-render 跳过渲染。"
        )
    return found


def read_pdf_info(pdf_path: Path) -> PdfInfo:
    """读取 PDF 页数。"""

    if not pdf_path.is_file():
        raise ValidationError(f"PDF 不存在：{pdf_path.as_posix()}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValidationError("来源必须是 .pdf 文件")
    pdfinfo = _require_tool("pdfinfo")
    result = subprocess.run(
        [pdfinfo, str(pdf_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise ValidationError(f"pdfinfo 无法读取 {pdf_path.as_posix()}")
    match = re.search(r"(?m)^Pages:\s*(\d+)\s*$", result.stdout)
    if not match:
        raise ValidationError(f"无法从 pdfinfo 输出解析页数：{pdf_path.as_posix()}")
    page_count = int(match.group(1))
    if page_count < 1:
        raise ValidationError(f"PDF 没有页面：{pdf_path.as_posix()}")
    return PdfInfo(page_count=page_count, path=pdf_path)


def _clean_pages(values: list[int] | tuple[int, ...] | None, field: str, page_count: int) -> list[int]:
    pages: list[int] = []
    for value in values or []:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > page_count:
            raise ValidationError(f"{field} 中的页码 {value!r} 超出 1-{page_count}")
        if value not in pages:
            pages.append(value)
    return sorted(pages)


class PdfCaptureService:
    """把来源 PDF 渲染为 capture 页面证据。"""

    def __init__(self, context: ServiceContext) -> None:
        self.ctx = context

    def available(self) -> tuple[bool, str]:
        """返回渲染是否可用及原因。"""

        missing = [name for name in ("pdfinfo", "pdftoppm") if not shutil.which(name)]
        if missing:
            return False, f"缺少 PDF 工具：{', '.join(missing)}（需要 Poppler）"
        return True, ""

    def capture_pdf(
        self,
        series_key: str,
        year: int,
        subject: str,
        capture_id: str,
        pdf_path: str | Path,
        *,
        page_from: int = 1,
        page_to: int | None = None,
        answer_pages: list[int] | None = None,
        exclude_pages: list[int] | None = None,
        dpi: int = DEFAULT_DPI,
        source_id: str | None = None,
        register_source: bool = True,
        notes: str | None = None,
    ) -> CaptureResult:
        """把 PDF 渲染为 capture，并登记来源。

        ``question_pages`` 由 ``page_from``/``page_to`` 减去 ``answer_pages`` 与
        ``exclude_pages`` 得到；答案页与排除页永不渲染，也不会进入 capture。
        """

        if not (MIN_DPI <= int(dpi) <= MAX_DPI):
            raise ValidationError(f"dpi 必须在 {MIN_DPI}-{MAX_DPI} 之间")
        resolved = Path(pdf_path).resolve()
        info = read_pdf_info(resolved)
        page_from = int(page_from)
        if page_from < 1 or page_from > info.page_count:
            raise ValidationError(f"page_from 必须在 1-{info.page_count} 之间")
        page_to = info.page_count if page_to is None else int(page_to)
        if page_to < page_from or page_to > info.page_count:
            raise ValidationError(f"page_to 必须在 {page_from}-{info.page_count} 之间")
        answers = _clean_pages(answer_pages, "answer_pages", info.page_count)
        excludes = _clean_pages(exclude_pages, "exclude_pages", info.page_count)
        removed = set(answers) | set(excludes)
        question_pages = [page for page in range(page_from, page_to + 1) if page not in removed]
        if not question_pages:
            raise ValidationError("所选范围在移除答案/排除页后没有题面页")

        source_summary: dict = {}
        if register_source:
            source_summary = self.ctx.sources.register(
                series_key,
                year,
                subject,
                resolved,
                source_id=source_id,
                page_count=info.page_count,
                notes=notes,
                move=False,
            ).summary()

        capture = self.ctx.captures.prepare(
            series_key,
            year,
            subject,
            capture_id,
            question_pages=question_pages,
            answer_pages=answers,
            exclude_pages=excludes,
            source_id=source_id,
            notes=notes,
        )

        rendered = self._render_pages(
            resolved, series_key, year, subject, capture_id, page_from, page_to, question_pages, dpi
        )
        self.ctx.captures.set_status(series_key, year, subject, capture_id, "prepared")
        return CaptureResult(
            source=source_summary,
            capture=self.ctx.captures.get(series_key, year, subject, capture_id).summary(),
            rendered_pages=rendered,
        )

    def _render_pages(
        self,
        pdf_path: Path,
        series_key: str,
        year: int,
        subject: str,
        capture_id: str,
        page_from: int,
        page_to: int,
        question_pages: list[int],
        dpi: int,
    ) -> list[int]:
        """渲染 PDF 页面并只保留题面页。"""

        pdftoppm = _require_tool("pdftoppm")
        target = self.ctx.captures.capture_dir(series_key, year, subject, capture_id) / "pages"
        target.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="npee-render-") as temp_dir:
            prefix = Path(temp_dir) / "render"
            result = subprocess.run(
                [
                    pdftoppm,
                    "-png",
                    "-r",
                    str(int(dpi)),
                    "-f",
                    str(page_from),
                    "-l",
                    str(page_to),
                    str(pdf_path),
                    str(prefix),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
                check=False,
            )
            if result.returncode != 0:
                raise ValidationError(f"pdftoppm 渲染失败：{result.stderr[-300:] or '未知错误'}")
            rendered: list[int] = []
            for png in sorted(Path(temp_dir).glob("render-*.png")):
                match = re.match(r"^render-(\d+)$", png.stem)
                if not match:
                    continue
                number = int(match.group(1))
                if number not in question_pages:
                    continue
                shutil.copy2(png, target / f"p{number:04d}.png")
                rendered.append(number)
        missing = [page for page in question_pages if page not in rendered]
        if missing:
            raise ValidationError(f"以下题面页没有渲染成功：{missing}")
        return sorted(rendered)
