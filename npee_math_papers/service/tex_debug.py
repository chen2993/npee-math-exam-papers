r"""诊断与调试：把题面字段渲染出来，用可观测证据判断对错。

为什么需要它
------------
"能通过编译"不等于"渲染正确"。审计中发现的最典型例子：

    存储原文：$\begin{pmatrix}\\lambda+k_1&0\\0&\\lambda\end{pmatrix}$

``\\`` 是合法换行、``lambda`` 是合法文本，因此 LaTeX **编译通过**，却把 λ 符号渲染成了
五个斜体字母 ``lambda``。只检查"是否编译成功"或"是否含 ASCII 关键词"都会漏掉它，
因为 PDF 文本层里是数学斜体 Unicode（``𝑙𝑎𝑚𝑏𝑑𝑎``）。

本模块提供可观测证据：

- :meth:`TexDebugger.render_field` 用真实排版类渲染单个字段并返回
  PDF / PNG / 文本层，供人或 Agent 直接查看；
- :meth:`TexDebugger.diagnose_field` 在渲染基础上做启发式判定：命令名是否泄漏成
  字面字母、数学模式是否泄漏、是否残留待核标记等；
- :meth:`TexDebugger.compile_source` 编译任意片段，用于最小复现。

所有方法都返回结构化结果，因此可直接被 MCP 工具与前端消费。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from npee_math_papers.core.errors import ValidationError
from npee_math_papers.core.tex_audit import KNOWN_COMMANDS, iter_fields

# 若这些命令名以字面字母出现在渲染结果里，说明命令丢了反斜杠。
# 复用静态检查器的命令表，避免两处列表不一致导致漏报。
COMMAND_NAMES = KNOWN_COMMANDS

# 命令名泄漏检测：渲染文本里出现"连续小写字母词"，且其中含这些命令名片段。
ASCII_WORD_RE = re.compile(r"[A-Za-z]{3,}")
PENDING_MARKER = "[待核]"


@dataclass
class RenderedField:
    """一次字段渲染的全部可观测产物。"""

    ok: bool
    text: str = ""
    error: str | None = None
    work_dir: str | None = None
    pdf_path: str | None = None
    png_paths: list[str] = field(default_factory=list)
    extracted_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "text": self.text,
            "error": self.error,
            "work_dir": self.work_dir,
            "pdf_path": self.pdf_path,
            "png_paths": list(self.png_paths),
            "extracted_text": self.extracted_text,
        }


@dataclass
class Diagnosis:
    """一次字段诊断的结论。"""

    ok: bool
    issues: list[dict[str, str]]
    rendered: RenderedField

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "issues": list(self.issues), "rendered": self.rendered.to_dict()}


def _find_leaked_commands(extracted: str) -> list[str]:
    """在渲染文本中找出疑似泄漏的命令名。

    关键在于数学斜体：``\\lambda`` 丢反斜杠后会被排成斜体字母，PDF 文本层里是
    U+1D459 等数学字母，看起来不像 "lambda"。用 NFKC 归一化可把它们还原成 ASCII
    （``𝑙𝑎𝑚𝑏𝑑𝑎`` → ``lambda``），因此无论文本模式还是数学模式下的泄漏都能识别。

    只匹配长度 ≥4 的完整命令名，避免把正常的单字母数学（如 ``$f(x)$``）误判。
    """

    import unicodedata

    normalized = unicodedata.normalize("NFKC", extracted)
    found: set[str] = set()
    for word in ASCII_WORD_RE.findall(normalized):
        lowered = word.lower()
        for name in COMMAND_NAMES:
            if len(name) >= 4 and lowered == name.lower():
                found.add(name)
    # 连写粘连的情况（如 "lambdak"）单独兜底。
    for name in COMMAND_NAMES:
        if len(name) >= 5 and name.lower() in normalized.lower():
            found.add(name)
    return sorted(found)


class TexDebugger:
    """用真实排版类渲染题面字段并诊断。

    构造时需要仓库根目录：排版类位于 ``npee_math_papers/tex/``，诊断报告的 pdf/png
    写入 ``build/debug/``，两者都不进入题库。
    """

    def __init__(self, repository_root: Path, output_root: Path | None = None, dpi: int = 150) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.class_dir = self.repository_root / "npee_math_papers" / "tex"
        self.output_root = Path(output_root) if output_root else self.repository_root / "build" / "debug"
        self.dpi = int(dpi)

    def available(self) -> tuple[bool, str]:
        """检查渲染所需的可执行文件与排版类。"""

        if not (self.class_dir / "npee-math-exam.cls").is_file():
            return False, f"排版类不存在：{self.class_dir / 'npee-math-exam.cls'}（请把 repository_root 指向仓库根目录）"
        missing = [name for name in ("xelatex", "pdftotext") if not shutil.which(name)]
        if missing:
            return False, f"缺少可执行文件：{', '.join(missing)}"
        return True, ""

    # --- 渲染 -------------------------------------------------------------

    def _document(self, body: str) -> str:
        """把一段字段包进最小题目文档。

        用真实类而非替身：项目自定义命令是模式感知的，替身会造成误报。
        """

        return (
            "\\documentclass[a4paper]{npee-math-exam}\n"
            "\\begin{document}\n"
            "\\NPEESetup{candidateinfo=false,notices=false,toc=false}\n"
            "\\begin{ExamChoiceQuestion}[id=debug,points=5,show-points=false]\n"
            f"{body}\n"
            "\\ExamChoices{$0$}{$1$}{$2$}{$3$}\n"
            "\\end{ExamChoiceQuestion}\n"
            "\\end{document}\n"
        )

    def render_field(self, text: str, *, label: str = "field", keep: bool = True, raster: bool = True) -> RenderedField:
        """渲染一段字段文本，返回 PDF、PNG 与文本层。

        ``label`` 用于输出目录命名，便于人工查找。``keep=False`` 时用临时目录，
        适合只关心结论的场景。
        """

        if not text or not text.strip():
            raise ValidationError("text must be non-empty")
        ok, reason = self.available()
        if not ok:
            return RenderedField(ok=False, text=text, error=reason)

        if keep:
            safe = re.sub(r"[^A-Za-z0-9_-]+", "-", label)[:60] or "field"
            work = Path(tempfile.mkdtemp(prefix=f"{safe}-", dir=_ensure(self.output_root)))
        else:
            work = Path(tempfile.mkdtemp(prefix="npee-debug-"))

        tex_path = work / "probe.tex"
        tex_path.write_text(self._document(text), encoding="utf-8")
        env = os.environ.copy()
        # TEXINPUTS 需要以路径分隔符结尾，才会继续搜索后续默认路径；同时把类目录
        # 放在最前，确保用的是仓库里的 npee-math-exam.cls。
        env["TEXINPUTS"] = str(self.class_dir) + os.pathsep + env.get("TEXINPUTS", "") + os.pathsep

        compiled = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "-output-directory", str(work), str(tex_path)],
            cwd=work,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=120,
            check=False,
        )
        if compiled.returncode != 0:
            lines = [line.strip() for line in (compiled.stdout or "").splitlines() if line.strip()]
            detail = next((line for line in lines if line.startswith("!")), "")
            if not detail:
                detail = next((line for line in lines if "rror" in line), lines[-1] if lines else "unknown")
            return RenderedField(ok=False, text=text, error=detail[:300], work_dir=str(work))

        pdf_path = work / "probe.pdf"
        png_paths: list[str] = []
        if raster and shutil.which("pdftoppm"):
            subprocess.run(
                ["pdftoppm", "-png", "-r", str(self.dpi), str(pdf_path), str(work / "page")],
                cwd=work,
                capture_output=True,
                timeout=120,
                check=False,
            )
            png_paths = sorted(str(path) for path in work.glob("page*.png"))

        extracted = ""
        if shutil.which("pdftotext"):
            result = subprocess.run(
                ["pdftotext", "-layout", str(pdf_path), "-"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            extracted = result.stdout or ""

        return RenderedField(
            ok=True,
            text=text,
            work_dir=str(work),
            pdf_path=str(pdf_path),
            png_paths=png_paths,
            extracted_text=extracted,
        )

    def compile_source(self, snippet: str, *, label: str = "snippet") -> RenderedField:
        """编译任意 LaTeX 片段，用于最小复现。

        片段作为完整文档主体传入，适合验证"我以为能渲染"的写法。
        """

        return self.render_field(snippet, label=label, raster=True)

    # --- 诊断 -------------------------------------------------------------

    def diagnose_field(self, text: str, *, label: str = "field") -> Diagnosis:
        """渲染并诊断一个字段，返回结构化问题清单。"""

        issues: list[dict[str, str]] = []
        if not text or not text.strip():
            return Diagnosis(ok=False, issues=[{"kind": "empty", "detail": "字段为空"}], rendered=RenderedField(ok=False, text=text))

        if PENDING_MARKER in text:
            issues.append({"kind": "pending_marker", "detail": f"残留 {PENDING_MARKER}"})

        rendered = self.render_field(text, label=label)
        if not rendered.ok:
            issues.append({"kind": "compile_failed", "detail": rendered.error or "编译失败"})
            return Diagnosis(ok=False, issues=issues, rendered=rendered)

        leaked = _find_leaked_commands(rendered.extracted_text)
        if leaked:
            issues.append({"kind": "leaked_command", "detail": "；".join(leaked)})

        if "$" in rendered.extracted_text:
            issues.append({"kind": "math_leak", "detail": "渲染结果出现字面 $，可能有未闭合的数学模式"})

        return Diagnosis(ok=not issues, issues=issues, rendered=rendered)

    def diagnose_question(self, question: Mapping[str, Any], *, label: str = "question") -> dict[str, Any]:
        """诊断一道题的所有字段，返回逐字段结论。

        只返回有问题的字段，保持结果紧凑；``checked`` 给出检查总数。
        """

        fields = [(name, text) for name, text in iter_fields(dict(question)) if text]
        problems: list[dict[str, Any]] = []
        for index, (name, text) in enumerate(fields):
            diagnosis = self.diagnose_field(text, label=f"{label}-{index:02d}")
            if not diagnosis.ok:
                problems.append({"field": name, "issues": diagnosis.issues, "rendered": diagnosis.rendered.to_dict()})
        return {"checked": len(fields), "problem_count": len(problems), "problems": problems}


def _ensure(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    return str(path)
