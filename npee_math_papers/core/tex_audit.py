"""TeX 静态检查：不跑 LaTeX 也能找出"命令丢了反斜杠"这类真错误。

核心缺陷模式
------------
在矩阵/分段环境里 ``\\`` 是换行。若某个命令丢了一个反斜杠，就会变成
``\\lambda``，即"换行 + 字面文本 lambda"。LaTeX 编译通过（``\\`` 合法、``lambda``
是合法文本），但渲染出来是字母而不是 λ 符号。这类错误只看"能否编译"发现不了。

判定规则
--------
设某位置前有连续的 N 个反斜杠，紧跟一个命令名：

- N = 1：``\\lambda``，正确；
- N = 2：``\\\\lambda``，即换行 + 字面 "lambda"，**错误**；
- N = 3：``\\\\\\lambda``，即换行 + 正确命令，正确；
- N = 4：换行 + 错误，**错误**。

即以 **偶数个反斜杠（≥2）** 紧跟命令名判定为丢失反斜杠。这样不会误报正常的多行
公式，也不会漏掉 ``\\\\lambda``。

本模块只做纯文本分析，因此可在毫秒级扫描全库，适合作为入库校验与 MCP 调试工具。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

# 常见的数学与排版命令；用于判断"一个有意义的词"是否本该是命令。
KNOWN_COMMANDS = (
    "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta",
    "theta", "vartheta", "iota", "kappa", "lambda", "mu", "nu", "xi", "pi",
    "varpi", "rho", "varrho", "sigma", "varsigma", "tau", "upsilon", "phi",
    "varphi", "chi", "psi", "omega",
    "Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma", "Upsilon",
    "Phi", "Psi", "Omega",
    "dfrac", "tfrac", "frac", "sqrt", "mathbb", "mathbf", "mathcal", "mathrm",
    "mathsf", "mathtt", "boldsymbol", "operatorname", "displaystyle", "textstyle",
    "begin", "end", "pmatrix", "bmatrix", "vmatrix", "Bmatrix", "Vmatrix",
    "matrix", "smallmatrix", "cases", "array", "left", "right", "cdot", "times",
    "div", "pm", "mp", "leq", "geq", "neq", "approx", "equiv", "sim", "simeq",
    "propto", "infty", "partial", "nabla", "int", "iint", "iiint", "oint",
    "oiint", "sum", "prod", "lim", "limsup", "liminf", "max", "min", "sup",
    "inf", "log", "ln", "exp", "sin", "cos", "tan", "cot", "sec", "csc",
    "arctan", "arcsin", "arccos", "sinh", "cosh", "tanh", "text", "textbf",
    "textit", "textcircled", "limits", "nolimits", "quad", "qquad", "hline",
    "vdots", "cdots", "ldots", "ddots", "triangle", "cup", "cap", "to",
    "rightarrow", "leftarrow", "mapsto", "forall", "exists", "in", "notin",
    "subset", "supset", "subseteq", "supseteq", "cup", "cap", "emptyset",
    "mathbb", "bar", "hat", "tilde", "vec", "dot", "ddot", "overline",
    "underline", "widehat", "widetilde", "xrightarrow", "overset", "underset",
)

COMMAND_SET = {name.lower(): name for name in KNOWN_COMMANDS}

# 连续反斜杠 + 字母序列
BACKSLASH_RUN_RE = re.compile(r"\\+([A-Za-z]+)")

# 数学模式内直接使用 \textcircled（应包进 \text{}）。
TEXTCIRCLED_RE = re.compile(r"\\textcircled")

# 命令之间有重复转义（如 \\ne 应写作 \ne），但排除行分隔符场景另行处理。
DOUBLED_KNOWN_COMMAND_RE = re.compile(r"(?<!\\)\\\\([A-Za-z]+)")

# 对齐环境：``\\`` 在其中有"行分隔"的特殊语义。
ALIGNMENT_ENVIRONMENTS = (
    "cases", "matrix", "pmatrix", "bmatrix", "Bmatrix", "vmatrix",
    "Vmatrix", "smallmatrix", "array",
)
ALIGNMENT_RE = re.compile(
    r"\\begin\{(?P<environment>" + "|".join(ALIGNMENT_ENVIRONMENTS) + r")\}"
    r"(?P<body>.*?)\\end\{(?P=environment)\}",
    re.DOTALL,
)

# 必须跟在行分隔之后的"行级"命令：偶数个反斜杠是损坏（应为 3）。
ROW_LEVEL_COMMANDS = frozenset({"hline", "cline", "hdashline"})


@dataclass(frozen=True)
class TexIssue:
    """一处静态可判定的 TeX 问题。"""

    kind: str
    field: str
    snippet: str
    detail: str
    position: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "field": self.field,
            "snippet": self.snippet,
            "detail": self.detail,
            "position": self.position,
        }


def iter_fields(question: Mapping[str, Any]) -> Iterable[tuple[str, str]]:
    """产出题目中所有含 TeX 的字段 (字段名, 文本)。

    题干、选项、子问的文本块与其中的图形 latex 都会被展开，字段名与
    :func:`check_question` 的前缀一致，便于跨层（核心/用例/维护）共用同一套
    字段寻址规则。
    """

    stem = question.get("stem") or {}
    yield "stem.text", str(stem.get("text") or "")
    for index, figure in enumerate(stem.get("figures") or []):
        if isinstance(figure, dict) and isinstance(figure.get("latex"), str):
            yield f"stem.figures[{index}].latex", figure["latex"]
    for choice_index, choice in enumerate(question.get("choices") or []):
        if not isinstance(choice, dict):
            continue
        yield f"choices[{choice.get('label', choice_index)}].text", str(choice.get("text") or "")
        for index, figure in enumerate(choice.get("figures") or []):
            if isinstance(figure, dict) and isinstance(figure.get("latex"), str):
                yield f"choices[{choice.get('label', choice_index)}].figures[{index}].latex", figure["latex"]
    for part_index, subpart in enumerate(question.get("subparts") or []):
        if not isinstance(subpart, dict):
            continue
        yield f"subparts[{part_index}].text", str(subpart.get("text") or "")
        for index, figure in enumerate(subpart.get("figures") or []):
            if isinstance(figure, dict) and isinstance(figure.get("latex"), str):
                yield f"subparts[{part_index}].figures[{index}].latex", figure["latex"]


def _in_math_mode(text: str, position: int) -> bool:
    """判断 ``position`` 处是否处于行内数学模式。

    只统计 ``$`` 定界符；``\\text{...}`` 内的内容仍属数学模式，但其中的命令是文本
    命令，因此这里额外跳过 ``\\text{...}`` 覆盖的范围。
    """

    delimiter = False
    index = 0
    while index < position:
        char = text[index]
        if char == "\\":
            # 跳过 \text{...} 整体：其中的命令在文本模式求值。
            command = re.match(r"\\([A-Za-z]+)\*?", text[index:])
            if command and command.group(1) in {"text", "textbf", "textit", "mathrm", "operatorname"}:
                group_start = index + len(command.group(0))
                while group_start < len(text) and text[group_start].isspace():
                    group_start += 1
                if group_start < len(text) and text[group_start] == "{":
                    depth = 0
                    cursor = group_start
                    while cursor < len(text):
                        if text[cursor] == "\\":
                            cursor += 2
                            continue
                        if text[cursor] == "{":
                            depth += 1
                        elif text[cursor] == "}":
                            depth -= 1
                            if depth == 0:
                                break
                        cursor += 1
                    if position < cursor:
                        return False
                    index = cursor + 1
                    continue
            index += 2
            continue
        if char == "$":
            delimiter = not delimiter
        index += 1
    return delimiter


def _is_known_command(word: str) -> bool:
    """命令名不区分大小写匹配（``\\neq`` 与 ``\\Leq`` 均属命令）。"""

    return word.lower() in COMMAND_SET


def _context(text: str, start: int, end: int, radius: int = 24) -> str:
    """截取匹配位置附近的上下文，供人工定位。"""

    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return text[left:right].replace("\n", "\\n")


def check_text(text: str, field: str = "text") -> list[TexIssue]:
    """对一段题面文本做静态检查，返回问题列表。

    只报告**可确定性判定**的问题：丢反斜杠、命令重复转义、待核标记、块级数学、
    ``\\frac``、未闭合数学模式。不做风格建议。
    """

    issues: list[TexIssue] = []
    if not text:
        return issues

    # 1. 命令丢反斜杠：偶数个（≥2）反斜杠紧跟命令名。
    for match in BACKSLASH_RUN_RE.finditer(text):
        run = match.group(0)
        count = len(run) - len(match.group(1))
        word = match.group(1)
        if not _is_known_command(word):
            continue
        if count >= 2 and count % 2 == 0:
            if word.lower() in ROW_LEVEL_COMMANDS:
                # 行级命令（hline/vdots 类）必须跟在行分隔之后：偶数补一个。
                detail = (
                    f"`{'\\\\' * count}{word}` 缺少行分隔，编译会报 Misplaced \\noalign；"
                    f"应为 `{'\\\\' * (count + 1)}{word}`"
                )
            else:
                detail = (
                    f"`{'\\\\' * count}{word}` 会渲染为换行后的字面文本 {word}；"
                    f"应为 `{'\\\\' * (count - 1)}{word}`"
                )
            issues.append(
                TexIssue(
                    kind="missing_backslash",
                    field=field,
                    snippet=_context(text, match.start(), match.end()),
                    detail=detail,
                    position=match.start(),
                )
            )

    # 2. 数学模式内裸用 \textcircled（应包进 \text{}）。
    #    文本模式下的 \textcircled 是合法用法，因此必须判断是否处于数学模式。
    for match in TEXTCIRCLED_RE.finditer(text):
        if not _in_math_mode(text, match.start()):
            continue
        issues.append(
            TexIssue(
                kind="bare_textcircled",
                field=field,
                snippet=_context(text, match.start(), match.end()),
                detail="数学模式内直接使用 \\textcircled；应包进 \\text{...}，否则 LaTeX 会告警且渲染不可靠",
                position=match.start(),
            )
        )

    # 3. 待核标记。
    for marker in ("[待核]", "[待审]"):
        index = text.find(marker)
        if index >= 0:
            issues.append(
                TexIssue(
                    kind="pending_marker",
                    field=field,
                    snippet=_context(text, index, index + len(marker)),
                    detail=f"残留 {marker}",
                    position=index,
                )
            )

    # 4. 块级数学。
    for pattern, label in ((r"\$\$", "$$"), (r"\\\[", "\\["), (r"\\\]", "\\]")):
        match = re.search(pattern, text)
        if match:
            issues.append(
                TexIssue(
                    kind="block_math",
                    field=field,
                    snippet=_context(text, match.start(), match.end()),
                    detail=f"出现块级数学标记 {label}；题库只允许行内数学",
                    position=match.start(),
                )
            )

    # 5. \frac（应为 \dfrac）。
    match = re.search(r"(?<!d)\\frac\b", text)
    if match:
        issues.append(
            TexIssue(
                kind="use_frac",
                field=field,
                snippet=_context(text, match.start(), match.end()),
                detail="使用了 \\frac；题库统一要求 \\dfrac",
                position=match.start(),
            )
        )

    # 6. 未闭合的数学模式（$ 个数为奇数）。
    if text.count("$") % 2 == 1:
        issues.append(
            TexIssue(
                kind="unbalanced_math",
                field=field,
                snippet=text[-40:].replace("\n", "\\n"),
                detail="`$` 数量为奇数，数学模式可能未闭合",
                position=len(text) - 1,
            )
        )

    return issues


def check_question(question: Mapping[str, Any], *, prefix: str = "question") -> list[TexIssue]:
    """检查一道题的全部字段。"""

    issues: list[TexIssue] = []
    for field, text in iter_fields(dict(question)):
        issues.extend(check_text(text, f"{prefix}.{field}"))
    return issues


def check_questions(questions: Iterable[Mapping[str, Any]]) -> list[TexIssue]:
    """按题号检查一个题目数组。"""

    issues: list[TexIssue] = []
    for question in questions:
        number = question.get("number", "?")
        issues.extend(check_question(question, prefix=f"q{number}"))
    return issues


def check_alignment_runs(text: str, field: str = "text") -> list[TexIssue]:
    """只检查对齐环境内的"反斜杠串"异常。

    对齐环境里 ``\\`` 是行分隔符，因此反斜杠串的奇偶与命令位置决定了渲染语义：

    - ``\\hline``（偶数 + 行级命令）→ 缺行分隔，XeLaTeX 报 ``Misplaced \\noalign``；
    - ``\\\\lambda``（偶数 + 行内命令）→ 渲染成"换行 + 字面文本 lambda"；
    - ``\\\\\\\\``（4 个及以上的偶数，后不接命令）→ 矩阵里多出空行。

    本函数只报告**对齐环境内**的上述三类异常，供入库校验、全库扫描与 MCP 调试
    工具复用。它是纯文本分析，可在毫秒级跑完全库。
    """

    issues: list[TexIssue] = []
    if not text:
        return issues

    for environment in ALIGNMENT_RE.finditer(text):
        body = environment.group("body")
        offset = environment.start("body")
        for match in BACKSLASH_RUN_RE.finditer(body):
            word = match.group(1)
            count = len(match.group(0)) - len(word)
            if not _is_known_command(word):
                continue
            if count < 2 or count % 2 == 1:
                continue
            absolute = offset + match.start()
            if word.lower() in ROW_LEVEL_COMMANDS:
                issues.append(
                    TexIssue(
                        kind="alignment_row_command",
                        field=field,
                        snippet=_context(text, absolute, offset + match.end()),
                        detail=(
                            f"对齐环境内 `{'\\\\' * count}{word}` 缺少行分隔；"
                            f"应为 `{'\\\\' * (count + 1)}{word}`，否则编译报 Misplaced \\noalign"
                        ),
                        position=absolute,
                    )
                )
            else:
                issues.append(
                    TexIssue(
                        kind="alignment_command",
                        field=field,
                        snippet=_context(text, absolute, offset + match.end()),
                        detail=(
                            f"对齐环境内 `{'\\\\' * count}{word}` 会渲染为换行后的字面文本；"
                            f"应为 `{'\\\\' * (count - 1)}{word}`"
                        ),
                        position=absolute,
                    )
                )
        for match in re.finditer(r"(?<!\\)(?:\\\\){2,}(?!\\)", body):
            count = len(match.group(0))
            following = re.match(r"[A-Za-z]+", body[match.end():])
            if following and _is_known_command(following.group(0)):
                # 已由上面的"命令前反斜杠"规则覆盖，避免重复报告。
                continue
            absolute = offset + match.start()
            issues.append(
                TexIssue(
                    kind="alignment_blank_row",
                    field=field,
                    snippet=_context(text, absolute, offset + match.end()),
                    detail=(
                        f"对齐环境内出现 {count} 个连续反斜杠（{count // 2} 个行分隔）；"
                        "应为 2 个，否则表格/矩阵会多出空行"
                    ),
                    position=absolute,
                )
            )
    return issues


def scan_alignments(text: str, field: str = "text") -> dict[str, Any]:
    """返回对齐环境扫描的结构化摘要（供 MCP 工具消费）。"""

    issues = check_alignment_runs(text, field)
    return {
        "field": field,
        "alignment_count": len(ALIGNMENT_RE.findall(text)) if text else 0,
        "issue_count": len(issues),
        "issues": [issue.to_dict() for issue in issues],
    }
