"""Render a single figure to SVG using the repository LaTeX class.

KaTeX cannot render TikZ, so the question viewer needs a real LaTeX pass to show a
drawing. Rendering on demand keeps the store free of pre-generated images and keeps
the viewer honest about what it is displaying.

A tiny standalone document is compiled with ``dvisvgm`` (or ``pdftocairo``) into an
SVG. Results are cached on disk by content hash so repeated views are free.

This module shells out to TeX. It is deliberately isolated so the rest of the
service stays a pure library and can be tested without TeX installed.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from npee_math_papers.core.errors import ValidationError

# Preamble mirrors the essential packages the class relies on for a lone figure.
FIGURE_PREAMBLE = r"""
\documentclass[tikz,border=2pt]{standalone}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{unicode-math}
\usepackage{tikz}
\RequirePackage{tikz-3dplot}
\usetikzlibrary{patterns}
\begin{document}
"""


@dataclass(frozen=True)
class RenderedFigure:
    """The result of rendering one figure."""

    svg: str
    cached: bool
    digest: str


class FigureRenderer:
    """Compile standalone LaTeX figures to SVG with a disk cache."""

    def __init__(self, repository_root: Path, cache_dir: Path) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def available(self) -> tuple[bool, str]:
        """Return whether the renderer can run, with a reason when it cannot."""

        if not shutil.which("xelatex"):
            return False, "xelatex is not available on PATH"
        if not (shutil.which("dvisvgm") or shutil.which("pdftocairo")):
            return False, "dvisvgm or pdftocairo is required to produce SVG"
        return True, ""

    def render(self, latex: str) -> RenderedFigure:
        """Render ``latex`` (a TikZ body) to SVG, using the cache when possible."""

        body = (latex or "").strip()
        if not body:
            raise ValidationError("figure latex must be non-empty")
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        cached_path = self.cache_dir / f"{digest}.svg"
        if cached_path.is_file():
            return RenderedFigure(cached_path.read_text(encoding="utf-8"), True, digest)

        ok, reason = self.available()
        if not ok:
            raise ValidationError(f"figure rendering is unavailable: {reason}")

        work = self.cache_dir / digest
        work.mkdir(parents=True, exist_ok=True)
        tex_path = work / "figure.tex"
        tex_path.write_text(
            FIGURE_PREAMBLE + "\\begin{tikzpicture}[line join=round,line cap=round]\n" + body + "\n\\end{tikzpicture}\n\\end{document}\n",
            encoding="utf-8",
        )
        compiled = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", str(work), str(tex_path)],
            cwd=work,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        pdf_path = work / "figure.pdf"
        if compiled.returncode != 0 or not pdf_path.is_file():
            detail = (compiled.stdout or "").strip().splitlines()
            raise ValidationError(f"figure render failed: {detail[-1][-300:] if detail else 'see log'}")

        svg_text = self._to_svg(pdf_path, work)
        cached_path.write_text(svg_text, encoding="utf-8")
        return RenderedFigure(svg_text, False, digest)

    def _to_svg(self, pdf_path: Path, work: Path) -> str:
        """Convert a compiled figure PDF to SVG."""

        dvisvgm = shutil.which("dvisvgm")
        if dvisvgm:
            result = subprocess.run(
                [dvisvgm, "--pdf", "--no-fonts", "--stdout", str(pdf_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        pdftocairo = shutil.which("pdftocairo")
        if pdftocairo:
            svg_path = work / "figure.svg"
            subprocess.run(
                [pdftocairo, "-svg", str(pdf_path), str(svg_path)],
                capture_output=True,
                timeout=60,
                check=False,
            )
            if svg_path.is_file():
                return svg_path.read_text(encoding="utf-8")
        raise ValidationError("no SVG converter succeeded for the rendered figure")
