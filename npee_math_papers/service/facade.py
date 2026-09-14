"""用例层门面。

``NpeeService`` 汇合题库、提取/捕获、组卷与 TeX 渲染四类用例。所有对外表面
（``npee_math_papers.mcp``、``npee_math_papers.api``、``npee_math_papers.cli``）都构造同一个 ``NpeeService``，因此
不存在第二份实现。
"""

from __future__ import annotations

from pathlib import Path

from npee_math_papers.service.capture import PdfCaptureService
from npee_math_papers.service.composition import CompositionService
from npee_math_papers.service.context import ServiceContext
from npee_math_papers.service.extraction import ExtractionService
from npee_math_papers.service.library import LibraryService
from npee_math_papers.service.tex_quality import TexQualityService

# 仓库根目录：本文件位于 npee_math_papers/service/facade.py，故向上三级。
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class NpeeService:
    """把全部用例收在一个对象后面。"""

    def __init__(self, context: ServiceContext, *, repository_root: Path | None = None) -> None:
        self.context = context
        self.repository_root = Path(repository_root).resolve() if repository_root else REPOSITORY_ROOT
        self.library = LibraryService(context)
        self.extraction = ExtractionService(context)
        self.capture = PdfCaptureService(context)
        self.composition = CompositionService(context, repository_root=self.repository_root)
        self.tex = TexQualityService(context)

    @classmethod
    def create(cls, root: str | Path | None = None, *, repository_root: Path | None = None) -> "NpeeService":
        repo = Path(repository_root).resolve() if repository_root else REPOSITORY_ROOT
        context = ServiceContext.create(root, repository_root=repo)
        return cls(context, repository_root=repo)
