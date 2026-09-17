r"""Compile every stored paper on its own and verify it renders without command leaks.

This is the strongest per-paper guarantee: a batch proves papers compile
*together*, while this proves each paper compiles and renders *alone*.

For every paper it:

1. builds a one-paper composition and compiles it with the real class;
2. extracts the PDF text layer and checks for *leaked command names* — a missing
   backslash turns ``\lambda`` into the literal word ``lambda`` while still
   compiling, so "compiles" is not enough.

Leak detection uses math-italic Unicode: legitimate operators (``\arcsin`` etc.)
render upright ASCII, whereas a leaked command renders its letters in math-italic
(``𝑎𝑟𝑐𝑠𝑖𝑛``), which NFKC-normalisation exposes without false positives.

Usage::

   python -m npee_math_papers.maintenance.verify_compile            # all papers
   python -m npee_math_papers.maintenance.verify_compile --limit 20
   python -m npee_math_papers.maintenance.verify_compile --json build/compile-verify.json
   python -m npee_math_papers.maintenance.verify_compile --matrix   # a4/a3 x compact/spaced/print
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from npee_math_papers.core.tex_audit import KNOWN_COMMANDS  # noqa: E402
from npee_math_papers.service import NpeeService  # noqa: E402

# 这些是"运算符名"，正确写法（\arcsin 等）本身就会渲染成同样的 ASCII 词，
# 因此不能仅凭词出现判定泄漏；只在数学斜体上下文里才算泄漏。
OPERATOR_WORDS = frozenset({
    "sin", "cos", "tan", "cot", "sec", "csc", "sinh", "cosh", "tanh",
    "arcsin", "arccos", "arctan", "ln", "log", "exp", "lim", "max", "min",
    "sup", "inf", "det", "dim", "gcd", "deg",
})
# 同时是普通英文词的命令，避免误报。
EXCLUDE = frozenset({"text", "end", "begin", "left", "right", "quad", "qquad", "dot", "bar"})
LEAK_NAMES = tuple(sorted({n for n in KNOWN_COMMANDS if len(n) >= 4 and n not in EXCLUDE and n not in OPERATOR_WORDS}))

# 单套验证默认只编 a4-紧凑版；--matrix 覆盖全部版式（a4/a3 × 紧凑/宽松/打印版）。
# ``spaced``（宽松版）已退役但仍被 schema 接受，因此保留在诊断矩阵里：
# 它验证旧组卷包依然能编译，而不是产品线的一部分。
BASE_TARGETS = [
    {"layout": "a4", "theme": "print", "spacing": "compact", "enabled": True, "answers": False, "output_suffix": None},
]
MATRIX_TARGETS = [
    # output_suffix 让每份产物文件名唯一（{layout}-{spacing} 不足以区分 theme/answers）。
    {"layout": "a4", "theme": "print", "spacing": "compact", "enabled": True, "answers": False, "output_suffix": "-a4-print-compact"},
    {"layout": "a4", "theme": "print", "spacing": "spaced", "enabled": True, "answers": False, "output_suffix": "-a4-print-spaced"},
    {"layout": "a4", "theme": "print", "spacing": "a4-blank", "enabled": True, "answers": False, "output_suffix": "-a4-print-blank"},
    {"layout": "a3", "theme": "print", "spacing": "a4-blank", "enabled": True, "answers": False, "output_suffix": "-a3-print-blank"},
    {"layout": "a3", "theme": "print", "spacing": "compact", "enabled": True, "answers": False, "output_suffix": "-a3-print-compact"},
    {"layout": "a3", "theme": "print", "spacing": "spaced", "enabled": True, "answers": False, "output_suffix": "-a3-print-spaced"},
    {"layout": "a4", "theme": "cream", "spacing": "compact", "enabled": True, "answers": False, "output_suffix": "-a4-cream-compact"},
    {"layout": "a4", "theme": "print", "spacing": "compact", "enabled": True, "answers": True, "output_suffix": "-a4-print-compact-answers"},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-root", type=Path, help="覆盖 .npee-math-papers 数据根")
    parser.add_argument("--limit", type=int, default=0, help="只验证前 N 套（0 = 全部）")
    parser.add_argument("--json", type=Path, help="把逐套结果写入 JSON")
    parser.add_argument("--keep", action="store_true", help="保留中间构建产物")
    parser.add_argument("--matrix", action="store_true", help="覆盖全部版式（a4/a3 × 紧凑/宽松/打印版）")
    parser.add_argument("--collections", action="store_true", help="同时编译 collections/ 下的正式组卷包")
    return parser.parse_args()


def _italic_letters(window: str) -> bool:
    """窗口内是否含数学斜体字母（U+1D400–U+1D7FF）。"""

    return any(0x1D400 <= ord(ch) <= 0x1D7FF for ch in window)


def _leaks(text_layer: str) -> list[str]:
    """在 PDF 文本层里找出真正的命令名泄漏（数学斜体上下文）。"""

    found: set[str] = set()
    for name in LEAK_NAMES:
        for match in re.finditer(re.escape(name), text_layer, re.IGNORECASE):
            window = text_layer[max(0, match.start() - 2) : match.end() + 2]
            if _italic_letters(window):
                found.add(name)
                break
    return sorted(found)


def _verify_one(job: tuple[int, int, str, str]) -> dict[str, object]:
    """在子进程里编译一套卷并检测泄漏；返回该套的结果字典。

    ``job`` 为 ``(序号, 总数, 自然键, 临时根目录)``。放在模块层是为了能被
    :class:`ProcessPoolExecutor` pickle；子进程各自构造 :class:`NpeeService`。
    """

    index, total, natural_key, temp_root_text = job
    temp_root = Path(temp_root_text)
    from npee_math_papers.service import NpeeService

    service = NpeeService.create()
    record = service.context.store.read_paper(*_natural_key_parts(natural_key))
    targets = MATRIX_TARGETS if _MATRIX_FLAG else BASE_TARGETS
    compile_config = {
        "engine": "xelatex",
        "passes": 1,
        "targets": targets,
        "output": {
            "directory": str(temp_root / f"{index:03d}" / "output"),
            "filename_template": "{composition_id}-{layout}-{spacing}.pdf",
            "overwrite": True,
        },
    }
    entry: dict[str, object] = {"natural_key": natural_key}
    selection = [{"series_key": record.series_key, "year": record.year, "subject": record.subject, "paper_no": record.paper_no}]
    try:
        composition = service.composition.build(f"verify-{index:03d}", natural_key, selection, compile_config=compile_config, pin_hashes=False)
        result = service.composition.compile(
            composition,
            dry_run=False,
            check_bindings=False,
            work_dir=temp_root / f"{index:03d}" / "generated",
            output_dir=temp_root / f"{index:03d}" / "output",
        )
    except Exception as error:  # noqa: BLE001 - report, do not abort the sweep
        entry["ok"] = False
        entry["error"] = f"{type(error).__name__}: {error}"
        return entry
    if not result.ok or not result.artifacts:
        entry["ok"] = False
        entry["error"] = result.error or "no artifact"
        return entry
    entry["pdfs"] = result.artifacts
    entry_leaks: dict[str, list[str]] = {}
    for pdf in result.artifacts:
        text_layer = subprocess.run(
            ["pdftotext", "-layout", str(pdf), "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        ).stdout or ""
        leaks = _leaks(text_layer)
        if leaks:
            entry_leaks[Path(pdf).name] = leaks
    entry["ok"] = not entry_leaks
    if entry_leaks:
        entry["leaks"] = entry_leaks
    return entry


def _natural_key_parts(natural_key: str) -> tuple[int, str, str, int]:
    """把 ``year/subject/series/paper_no`` 拆成 ``store.read_paper`` 的实参。

    ``read_paper`` 的签名是 ``(series_key, year, subject, paper_no)``。
    """

    year, subject, series_key, paper_no = natural_key.split("/")
    return series_key, int(year), subject, int(paper_no)


# 子进程无法收到命令行参数，用模块级标志把"是否覆盖全部版式"传给 worker。
_MATRIX_FLAG = False


def main() -> int:
    global _MATRIX_FLAG

    args = parse_args()
    service = NpeeService.create(args.data_root)
    records = list(service.context.store.iter_records())
    if args.limit and args.limit > 0:
        records = records[: args.limit]

    temp_root = Path(tempfile.mkdtemp(prefix="npee-verify-", dir=str(ROOT / "build")))
    _MATRIX_FLAG = bool(args.matrix)
    targets = MATRIX_TARGETS if args.matrix else BASE_TARGETS

    results: list[dict[str, object]] = []
    compile_fail = 0
    leak_fail = 0
    jobs = [(index, len(records), record.natural_key, str(temp_root)) for index, record in enumerate(records)]
    workers = max(1, min(16, (os.cpu_count() or 4)))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_verify_one, job): job for job in jobs}
        for done, future in enumerate(as_completed(futures), start=1):
            entry = future.result()
            if not entry.get("ok"):
                if entry.get("leaks"):
                    leak_fail += 1
                    print(f"[LEAK] {entry['natural_key']}: {entry['leaks']}", flush=True)
                else:
                    compile_fail += 1
                    print(f"[COMPILE-FAIL] {entry['natural_key']}: {entry.get('error')}", flush=True)
            results.append(entry)
            if done % 25 == 0:
                print(f"  ... {done}/{len(jobs)} checked", flush=True)

    passed = len(results) - compile_fail - leak_fail
    collection_fail = 0
    collections_report: list[dict[str, object]] = []
    if args.collections:
        collections_root = ROOT / "collections"
        collection_paths = sorted(collections_root.glob("*/composition.json"))
        for collection_path in collection_paths:
            entry = {"collection": collection_path.parent.name}
            try:
                result = service.composition.compile_collection(
                    collection_path,
                    dry_run=False,
                    check_bindings=False,
                    work_dir=temp_root / "collections" / collection_path.parent.name / "generated",
                    output_dir=temp_root / "collections" / collection_path.parent.name / "output",
                )
            except Exception as error:  # noqa: BLE001
                entry["ok"] = False
                entry["error"] = f"{type(error).__name__}: {error}"
                collection_fail += 1
                collections_report.append(entry)
                print(f"[COLLECTION-FAIL] {collection_path.parent.name}: {entry['error']}", flush=True)
                continue
            entry["ok"] = result.ok
            entry["artifacts"] = len(result.artifacts)
            if not result.ok:
                entry["error"] = result.error
                collection_fail += 1
                print(f"[COLLECTION-FAIL] {collection_path.parent.name}: {result.error}", flush=True)
            collections_report.append(entry)
        results.extend(collections_report)  # type: ignore[arg-type]

    print("")
    print(f"papers checked : {len(records)}")
    print(f"compile ok     : {len(records) - compile_fail}")
    print(f"compile failed : {compile_fail}")
    print(f"leaks          : {leak_fail}")
    print(f"fully ok       : {passed}")
    if args.collections:
        print(f"collections    : {len(collections_report)} checked, {collection_fail} failed")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {"papers": results[: len(records)], "collections": collections_report},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"report written : {args.json.as_posix()}")

    if not args.keep:
        import shutil

        shutil.rmtree(temp_root, ignore_errors=True)

    return 1 if (compile_fail or leak_fail or collection_fail) else 0


if __name__ == "__main__":
    raise SystemExit(main())
