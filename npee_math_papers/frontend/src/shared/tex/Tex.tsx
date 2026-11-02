import { useMemo } from "react";
import katex from "katex";

/**
 * 项目自定义命令的 KaTeX 宏。
 *
 * 题库使用少量排版类提供的命令，KaTeX 不认识它们；若不定义，每个命令都会报
 * 「未定义控制序列」。在这里给出等价定义，使预览忠实而非满屏报错。
 *
 * 只列 KaTeX **确实缺少**的命令。
 *
 * 此前这里把 `\mathrm`、`\operatorname`、`\boldsymbol`、`\dfrac` 定义成它们
 * 自己（如 `"\\mathrm": "\\mathrm{#1}"`）。那是**自引用宏**：KaTeX 会不断展开
 * 直到触发 `Too many expansions` 抛错，而 `throwOnError:false` 又把异常吞掉，
 * 于是这些片段在界面上被渲染成**红色的原始源码**。全库 8258 个数学片段里有
 * **608 个（7.4%）** 命中该问题——`\mathrm{d}x` 这种最常见的写法都在其中。
 * 四个命令 KaTeX 本就原生支持，删除这些条目即可，实测失败数 608 → 0。
 */
const EXAM_MACROS: Record<string, string> = {
  // 原卷的选择题在题末印一对全角括号留空（`（　　　）`）。此前映射成 `\square`，
  // 浏览器里就显示成一个方框——与卷面不符，读者会以为题目漏排了。
  "\\ExamSelection": "\\text{（\\hspace{1.5em}）}",
  "\\ExamBlank": "\\;\\underline{\\hphantom{0000}}\\;",
  "\\ExamCircledNumber": "\\textcircled{#1}",
  "\\ExamStatementMarker": "\\textcircled{#1}",
  // `\unicode` is not a KaTeX primitive, and this corpus writes
  // `\oiint\limits_S`, so the stand-in has to be a math operator that can carry
  // `\limits`.
  "\\oiint": "\\mathop{\\int\\!\\!\\!\\!\\!\\!\\!\\bigcirc}",
  "\\oiiint": "\\mathop{\\int\\!\\!\\!\\!\\!\\!\\!\\bigcirc\\!\\!\\!\\!\\!\\!\\!\\bigcirc}",
};

function cleanTex(source: string): string {
  return String(source || "")
    .replace(/%[^\n]*/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] || char);
}

/**
 * 存储层的换行标记 `\n` 在界面上应该断行，而不是显示成两个字符。
 *
 * 题库把「命题序列 / 末尾换行」记成 `\n`（见 docs/EXTRACTION.md），排版类把它
 * 编成 `\NPEEQuestionContinuation`；浏览器此前只是转义，于是题干里会印出字面量
 * `\n`。判据必须与两个迁移工具一致：**前面不是反斜杠、后面不跟字母**才算换行，
 * 否则 `\nu`、`\ne`、`\nabla` 会被拦腰截断。行尾的换行不产生空行。
 */
function escapeTextWithBreaks(value: string): string {
  return escapeHtml(value)
    .replace(/(?<!\\)\\n(?![A-Za-z])/g, "<br />")
    .replace(/(?:<br \/>\s*)+$/, "");
}

/**
 * 分式大小必须与所处位置匹配。
 *
 * TeX/KaTeX 按**当前数学样式**决定分式大小。在上下标或积分上下限里样式已是
 * script，此时 `\dfrac` 会把分式重新放大，反而撑出行高：本类实测
 * `x^{\dfrac{a}{b}}` 高 24.3pt，而正文 `\dfrac{a}{b}` 只有 14.8pt，
 * `x^{\frac{a}{b}}` 则是 13.3pt。正文位置反之——`\frac` 在展示数学旁显得过小。
 *
 * 因此判据是**位置**而不是命令：script 位置用 `\frac`，正文位置用 `\dfrac`。
 * 服务端 `core/tex.py` 的 `fraction_positions` 与
 * `service/rendering/inline_tex.py` 的 `repair_fraction_sizes` 是同一套判据的
 * 实现，保证 PDF 与浏览器一致。
 */
function normalizeFractionSizes(expression: string): string {
  // Mirror of core/tex.py's fraction_positions + fraction_size_corrections: a
  // fraction's size must match the style TeX will set it in, and both a script
  // slot and a fraction argument are already one level down.
  const groups: Array<"script" | "frac" | "other"> = [];
  const argCounts: number[] = [];   // outstanding brace args; \dfrac takes two
  let pendingScript = false;
  const edits: Array<{ start: number; end: number; text: string }> = [];
  let i = 0;
  while (i < expression.length) {
    const char = expression[i];
    if (char === "\\") {
      const match = /^\\([A-Za-z]+)/.exec(expression.slice(i));
      if (match) {
        const name = match[1];
        const isFraction = name === "dfrac" || name === "tfrac" || name === "frac";
        const isBareFrac = name === "frac" && expression[i - 1] !== "d" && expression[i - 1] !== "t";
        if (isFraction && (name !== "frac" || isBareFrac)) {
          const reduced = groups.includes("script") || groups.includes("frac");
          if (reduced && (name === "dfrac" || name === "tfrac")) {
            edits.push({ start: i, end: i + match[0].length, text: "\\frac" });
          } else if (!reduced && isBareFrac) {
            edits.push({ start: i, end: i + match[0].length, text: "\\dfrac" });
          }
          argCounts.push(2);
        }
        i += match[0].length;
        pendingScript = false;
        continue;
      }
      i += 2;
      continue;
    }
    if (char === "^" || char === "_") { pendingScript = true; i += 1; continue; }
    if (char === "{") {
      if (argCounts.length && argCounts[argCounts.length - 1] > 0) {
        groups.push("frac");
        argCounts[argCounts.length - 1] -= 1;
        if (argCounts[argCounts.length - 1] === 0) argCounts.pop();
      } else if (pendingScript) {
        groups.push("script");
      } else {
        groups.push("other");
      }
      pendingScript = false;
      i += 1;
      continue;
    }
    if (char === "}") { groups.pop(); i += 1; continue; }
    if (!/\s/.test(char)) pendingScript = false;
    i += 1;
  }
  // Apply from the end so earlier offsets stay valid.
  for (const edit of edits.reverse()) {
    expression = expression.slice(0, edit.start) + edit.text + expression.slice(edit.end);
  }
  return expression;
}

function normalizeOperatorLimits(expression: string): string {
  return expression.replace(
    // Must stay in step with the class, which forces \limits on exactly these
    // operators (see the begindocument/end hook in npee-math-exam.cls). `oint`
    // was missing here, so `\oint_L` rendered its label at the side in the
    // browser while the PDF centred it below.
    /\\(limsup|liminf|iiiint|iiint|iint|oiiint|oiint|oint|max|min|sup|inf|lim|sum|prod|bigcap|bigcup)(?![A-Za-z@])(?:\\limits)*/g,
    (match) => `${match.replace(/\\limits/g, "")}\\limits`,
  );
}

/**
 * 积分区域的上下限放在积分号正下方。
 *
 * 参考卷对**数值上下限**沿用期刊惯例写在右下角（`\int_0^1`、`\int_a^b`）——
 * 这也让嵌在分式或矩阵格里的积分不会撑高行距，因此保持原样。**区域名**不同：
 * `\int_L`、`\oint_\Gamma` 读作「在 L 上的积分」，考研卷把它排在积分号正下方。
 *
 * 类文件已为除 `\int` 以外的全部算子强制 `\limits`（见 `operators/int-limits`
 * 开关），只有 `\int` 留给来源显式指定，所以这里补上。服务端
 * `service/rendering/inline_tex.py` 的同名规则保证 PDF 与浏览器呈现一致。
 */
const REGION_SUBSCRIPT =
  /^(?:[A-Z](?:\s*(?:_\{?[^{}\s]*\}?|\^\{?[^{}\s]*\}?))?|\\(?:Gamma|Sigma|Omega|Lambda|Phi|Pi|Theta|Delta|Xi|Psi|Upsilon)(?:\s*(?:_\{?[^{}\s]*\}?|\^\{?[^{}\s]*\}?))?)$/;

function placeIntegralRegionLimits(expression: string): string {
  return expression.replace(
    // The lookbehind rejects only a preceding backslash: that is what separates a
    // real `\int` from a `\\int` row separator plus literal text. A preceding
    // *letter* must be allowed, because `\displaystyle\int_L` is legitimate; the
    // trailing guard already prevents matching inside a longer control word.
    /(?<!\\)\\int(?![A-Za-z@])(?:\\limits)*(?<sub>_\s*(?:\{[^{}]*\}|[^\s{]))/g,
    (match, sub: string) => {
      const raw = String(sub);
      let body = raw.replace(/^_\s*/, "");
      if (body.startsWith("{") && body.endsWith("}")) body = body.slice(1, -1);
      return REGION_SUBSCRIPT.test(body.trim()) ? `\\int\\limits${raw}` : match;
    },
  );
}

/**
 * 行间自定义命令的正则。
 *
 * `\ExamSelection` / `\ExamBlank` 在题库里**大多写在 `$...$` 之外**（各 3076 /
 * 1516 处，仅 134 / 411 处在数学段内：例如 `...则 $(a,b)=$\ExamSelection。`）。
 * 此前它们落在纯文本分支里，于是界面上直接显示字面量 `\ExamSelection`，而不是
 * 答题框/填空线。
 */
const BARE_COMMAND = /\\(ExamSelection|ExamBlank)/g;

/** TeX 片段是否包含 KaTeX 无法渲染的绘图环境。 */
function containsUnsupportedEnvironment(source: string): boolean {
  return /\\(begin|end)\{(tikzpicture|pspicture|asy)\}/.test(source);
}

/**
 * 把行内 TeX 渲染为 HTML，并映射项目自定义命令。
 *
 * ``$...$`` 或 ``\(...\)`` 内容交给 KaTeX，外围文字做转义。若片段含绘图环境，
 * 返回 ``null``，由调用方改用服务端渲染的图片展示。
 */
export function renderTex(source: string): string | null {
  const tex = cleanTex(source);
  if (!tex) return "";
  if (containsUnsupportedEnvironment(tex)) return null;
  // 把裸露的自定义命令先折进数学段，后面的解析就不再需要区分两种写法。
  const folded = tex.replace(BARE_COMMAND, (_match, name: string) => `$${EXAM_MACROS[`\\${name}`]}$`);
  const pattern = /(\$[\s\S]*?\$|\\\([\s\S]*?\\\))/g;
  let cursor = 0;
  let result = "";
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(folded))) {
    result += escapeTextWithBreaks(folded.slice(cursor, match.index));
    const raw = match[0].startsWith("\\(") ? match[0].slice(2, -2) : match[0].slice(1, -1);
    result += katex.renderToString(normalizeFractionSizes(placeIntegralRegionLimits(normalizeOperatorLimits(raw))), {
      throwOnError: false,
      displayMode: false,
      macros: EXAM_MACROS,
    });
    cursor = match.index + match[0].length;
  }
  result += escapeTextWithBreaks(folded.slice(cursor));
  return result;
}

export function Tex({ source, compact = false }: { source: string; compact?: boolean }) {
  const html = useMemo(() => renderTex(source), [source]);
  if (html === null) {
    return <span className={compact ? "tex tex-compact tex-figure" : "tex tex-figure"}>[图形]</span>;
  }
  return <span className={compact ? "tex tex-compact" : "tex"} dangerouslySetInnerHTML={{ __html: html }} />;
}
