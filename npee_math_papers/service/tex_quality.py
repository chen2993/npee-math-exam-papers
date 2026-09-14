r"""TeX 质量用例：静态检查、全库扫描与单字段渲染诊断。

MCP 与 HTTP 只需要薄适配器，因此所有规则都放在这里：本模块汇总
:mod:`npee_math_papers.core.tex_audit`（纯文本分析）与
:mod:`npee_math_papers.service.tex_debug`（真实排版类渲染），对外提供三类用例：

- :meth:`TexQualityService.check_text`：检查一段文本；
- :meth:`TexQualityService.audit_library`：扫描全库对齐环境；
- :meth:`TexQualityService.diagnose_paper` / :meth:`TexQualityService.render_text`：
  用真实排版类渲染，拿到 PDF/PNG/文本层证据。
"""

from __future__ import annotations

from typing import Any

from npee_math_papers.core.tex_audit import check_text, iter_fields, scan_alignments
from npee_math_papers.service.context import ServiceContext


class TexQualityService:
    """题库的 TeX 质量用例。"""

    def __init__(self, context: ServiceContext) -> None:
        self.ctx = context

    # --- 静态检查 ----------------------------------------------------------

    def check_text(self, text: str, *, field: str = "text") -> dict[str, Any]:
        """检查一段文本，返回全部可确定性判定的问题。"""

        issues = check_text(text, field)
        return {
            "field": field,
            "issue_count": len(issues),
            "issues": [issue.to_dict() for issue in issues],
        }

    def scan_alignments(self, text: str, *, field: str = "text") -> dict[str, Any]:
        """只扫描对齐环境内的反斜杠串异常。"""

        return scan_alignments(text, field)

    def audit_library(
        self,
        *,
        series_keys: list[str] | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """扫描全库对齐环境，返回逐字段的问题清单（按套卷聚合）。

        只扫描 ``papers/`` 的存储原文；这是纯文本分析，可在秒级跑完全库。
        """

        wanted = set(series_keys) if series_keys else None
        findings: list[dict[str, Any]] = []
        papers_scanned = 0
        fields_scanned = 0
        for record in self.ctx.store.iter_records():
            if wanted is not None and record.series_key not in wanted:
                continue
            papers_scanned += 1
            for question in record.questions:
                for field, text in iter_fields(question):
                    if not text:
                        continue
                    fields_scanned += 1
                    report = scan_alignments(text, field)
                    if not report["issues"]:
                        continue
                    findings.append(
                        {
                            "natural_key": record.natural_key,
                            "question_no": int(question["number"]),
                            "field": field,
                            "issues": report["issues"],
                        }
                    )
        affected = sorted({item["natural_key"] for item in findings})
        return {
            "papers_scanned": papers_scanned,
            "fields_scanned": fields_scanned,
            "finding_count": len(findings),
            "affected_paper_count": len(affected),
            "affected_papers": affected,
            "findings": findings[: max(0, int(limit))],
        }

    # --- 渲染诊断 ----------------------------------------------------------

    def _debugger(self) -> Any:
        from npee_math_papers.service.tex_debug import TexDebugger

        repository_root = self.ctx.paths.root.parent
        return TexDebugger(repository_root, output_root=repository_root / "build" / "debug")

    def render_text(self, text: str, *, label: str = "field") -> dict[str, Any]:
        """用真实排版类渲染一段文本，返回 PDF/PNG 路径与文本层。"""

        rendered = self._debugger().render_field(text, label=label)
        return rendered.to_dict()

    def diagnose_field(self, text: str, *, label: str = "field") -> dict[str, Any]:
        """渲染并诊断一个字段。"""

        return self._debugger().diagnose_field(text, label=label).to_dict()

    def diagnose_paper(self, series_key: str, year: int, subject: str, paper_no: int) -> dict[str, Any]:
        """逐字段渲染诊断一套卷。"""

        record = self.ctx.store.read_paper(series_key, year, subject, paper_no)
        debugger = self._debugger()
        problems: list[dict[str, Any]] = []
        checked = 0
        for question in record.questions:
            diagnosis = debugger.diagnose_question(question, label=f"{record.natural_key}-q{question['number']}")
            checked += diagnosis["checked"]
            for problem in diagnosis["problems"]:
                problems.append({"question_no": int(question["number"]), **problem})
        return {
            "natural_key": record.natural_key,
            "checked": checked,
            "problem_count": len(problems),
            "problems": problems,
        }
