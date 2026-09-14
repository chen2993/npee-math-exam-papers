"""NPEE service 用例层入口。

``NpeeService`` 汇合题库、提取/捕获、组卷与 TeX 渲染四类用例，供 ``npee_math_papers.mcp``、
``npee_math_papers.api`` 与 ``npee_math_papers.cli`` 共同调用。
"""

from __future__ import annotations

from npee_math_papers.service.capture import CaptureResult, PdfCaptureService
from npee_math_papers.service.composition import CompositionService
from npee_math_papers.service.context import ServiceContext
from npee_math_papers.service.extraction import ExtractionService
from npee_math_papers.service.facade import NpeeService
from npee_math_papers.service.library import LibraryService
from npee_math_papers.service.tex_quality import TexQualityService

__all__ = [
    "CaptureResult",
    "CompositionService",
    "ExtractionService",
    "LibraryService",
    "NpeeService",
    "PdfCaptureService",
    "ServiceContext",
    "TexQualityService",
]
