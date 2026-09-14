#!/usr/bin/env python3
"""Check the local NPEE runtime and print actionable installation hints."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PYPI_MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"
CTAN_MIRROR = "https://mirrors.tuna.tsinghua.edu.cn/CTAN/systems/texlive/tlnet/"
TEXLIVE_DOWNLOAD_MIRROR = "https://mirrors.tuna.tsinghua.edu.cn/CTAN/systems/texlive/Images/"
NODE_MIRROR = "https://registry.npmmirror.com"
NODE_DOWNLOAD_MIRROR = "https://mirrors.tuna.tsinghua.edu.cn/nodejs-release/"


@dataclass(frozen=True)
class CheckResult:
    label: str
    status: str
    detail: str
    hint: str = ""


def command_version(command: str, *args: str) -> str | None:
    executable = shutil.which(command)
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    line = next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")
    return line or "available"


def module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def required_python_packages() -> list[CheckResult]:
    packages = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("ruamel.yaml", "ruamel.yaml"),
        ("mcp", "mcp"),
    ]
    results: list[CheckResult] = []
    for import_name, package_name in packages:
        if module_available(import_name):
            results.append(CheckResult(f"Python package {package_name}", "PASS", "installed"))
        else:
            results.append(
                CheckResult(
                    f"Python package {package_name}",
                    "FAIL",
                    "not installed",
                    f'"{sys.executable}" -m pip install -i {PYPI_MIRROR} -r npee_math_papers/api/requirements.txt',
                )
            )
    return results


def database_result() -> CheckResult:
    """Check the `.npee-math-papers` paper store."""

    data_root = Path(os.environ.get("NPEE_DATA_ROOT", "") or (ROOT / ".npee-math-papers"))
    papers_dir = data_root / "papers"
    if papers_dir.is_dir() and any(papers_dir.iterdir()):
        bundles = [item for item in papers_dir.iterdir() if item.is_dir()]
        paper_files = sum(len(list(bundle.glob("*.yaml"))) for bundle in bundles)
        return CheckResult("Paper store (.npee-math-papers)", "PASS", f"{len(bundles)} bundles / {paper_files} papers")
    return CheckResult(
        "Paper store (.npee-math-papers)",
        "FAIL",
        f"missing {papers_dir.as_posix()}",
        "Run: python -m npee_math_papers.maintenance.migrate_papers --apply",
    )


def check_environment() -> list[CheckResult]:
    results: list[CheckResult] = []
    version = sys.version_info
    if version >= (3, 10):
        results.append(CheckResult("Python", "PASS", f"{platform.python_version()} ({sys.executable})"))
    else:
        results.append(
            CheckResult(
                "Python",
                "FAIL",
                f"{platform.python_version()} is older than 3.10",
                "Install Python 3.10+ from https://www.python.org/downloads/ or use the TUNA Anaconda mirror: https://mirrors.tuna.tsinghua.edu.cn/anaconda/archive/",
            )
        )
    pip_version = command_version(sys.executable, "-m", "pip", "--version")
    results.append(
        CheckResult(
            "pip",
            "PASS" if pip_version else "FAIL",
            pip_version or "not available for the selected Python",
            f'"{sys.executable}" -m ensurepip --upgrade; "{sys.executable}" -m pip install -i {PYPI_MIRROR} -r npee_math_papers/api/requirements.txt',
        )
    )
    results.extend(required_python_packages())

    node = command_version("node", "--version")
    if node is None:
        results.append(
            CheckResult(
                "Node.js",
                "FAIL",
                "not found on PATH",
                "Install Node.js 18+ from https://nodejs.org/en/download/ or " + NODE_DOWNLOAD_MIRROR + "; npm packages can use " + NODE_MIRROR,
            )
        )
    else:
        results.append(CheckResult("Node.js", "PASS", node))
    npm = command_version("npm.cmd" if os.name == "nt" else "npm", "--version")
    results.append(
        CheckResult(
            "npm",
            "PASS" if npm else "FAIL",
            npm or "not found on PATH",
            "Install Node.js 18+; npm is included with Node.js.",
        )
    )
    frontend_modules = ROOT / "npee_math_papers" / "frontend" / "node_modules"
    vite_bin = frontend_modules / ".bin" / ("vite.cmd" if os.name == "nt" else "vite")
    results.append(
        CheckResult(
            "Frontend dependencies",
            "PASS" if vite_bin.is_file() else "FAIL",
            "node_modules is ready" if vite_bin.is_file() else "node_modules is missing or incomplete",
            f"cd npee_math_papers/frontend; npm ci --registry={NODE_MIRROR}",
        )
    )

    xelatex = command_version("xelatex", "--version")
    results.append(
        CheckResult(
            "XeLaTeX",
            "PASS" if xelatex else "FAIL",
            xelatex or "not found on PATH",
            f"Install TeX Live from {TEXLIVE_DOWNLOAD_MIRROR} (package mirror: {CTAN_MIRROR}) or install MiKTeX and add xelatex to PATH.",
        )
    )
    kpsewhich = shutil.which("kpsewhich")
    tex_files = ["ctexart.cls", "xeCJK.sty", "geometry.sty", "unicode-math.sty", "tikz.sty", "tasks.sty", "pdfpages.sty"]
    if not kpsewhich:
        results.append(
            CheckResult(
                "TeX packages",
                "FAIL",
                "kpsewhich not found, so required packages cannot be verified",
                f"After installing TeX Live, run: tlmgr option repository {CTAN_MIRROR}; tlmgr install ctex xecjk geometry unicode-math pgf tasks pdfpages",
            )
        )
    else:
        missing_tex = []
        for filename in tex_files:
            try:
                result = subprocess.run([kpsewhich, filename], capture_output=True, text=True, timeout=8, check=False)
            except (OSError, subprocess.TimeoutExpired):
                result = None
            if result is None or not result.stdout.strip():
                missing_tex.append(filename)
        results.append(
            CheckResult(
                "TeX packages",
                "PASS" if not missing_tex else "FAIL",
                "all required packages found" if not missing_tex else f"missing {', '.join(missing_tex)}",
                f"tlmgr option repository {CTAN_MIRROR}; tlmgr install ctex xecjk geometry unicode-math pgf tasks pdfpages",
            )
        )

    font_candidates = []
    if os.name == "nt":
        windows_fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        font_candidates = [windows_fonts / name for name in ("simsun.ttc", "simhei.ttf", "msyh.ttc", "arial.ttf")]
    has_cjk_font = any(path.is_file() for path in font_candidates)
    results.append(
        CheckResult(
            "Chinese font",
            "PASS" if has_cjk_font else "WARN",
            "SimSun/SimHei/Microsoft YaHei detected" if has_cjk_font else "Windows CJK font was not detected; TeX fallback may be used",
            "Install SimSun, SimHei, or Microsoft YaHei; see https://mirrors.tuna.tsinghua.edu.cn/ for mirror resources.",
        )
    )
    results.append(database_result())
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="write the check result to a repository-relative report file")
    args = parser.parse_args()
    results = check_environment()
    lines = ["NPEE environment check", f"Python executable: {sys.executable}", ""]
    for result in results:
        lines.append(f"[{result.status}] {result.label}: {result.detail}")
        if result.status in {"FAIL", "WARN"} and result.hint:
            lines.append(f"  Hint: {result.hint}")
    failures = sum(result.status == "FAIL" for result in results)
    lines.append("")
    lines.append("Environment is ready." if failures == 0 else f"Environment is not ready: {failures} required check(s) failed.")
    output = "\n".join(lines) + "\n"
    print(output, end="")
    if args.report:
        report = args.report if args.report.is_absolute() else ROOT / args.report
        report = report.resolve()
        try:
            report.relative_to(ROOT)
        except ValueError as error:
            raise SystemExit("--report must stay inside the repository") from error
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(output, encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
