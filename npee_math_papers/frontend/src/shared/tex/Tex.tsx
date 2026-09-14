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
  "\\ExamSelection": "\\;\\square\\;",
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

function normalizeOperatorLimits(expression: string): string {
  return expression.replace(
    /\\(limsup|liminf|iiiint|iiint|iint|oiiint|oiint|max|min|sup|inf|lim|sum|prod|bigcap|bigcup)(?![A-Za-z@])(?:\\limits)*/g,
    (match) => `${match.replace(/\\limits/g, "")}\\limits`,
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
export function containsUnsupportedEnvironment(source: string): boolean {
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
    result += escapeHtml(folded.slice(cursor, match.index));
    const raw = match[0].startsWith("\\(") ? match[0].slice(2, -2) : match[0].slice(1, -1);
    result += katex.renderToString(normalizeOperatorLimits(raw), {
      throwOnError: false,
      displayMode: false,
      macros: EXAM_MACROS,
    });
    cursor = match.index + match[0].length;
  }
  result += escapeHtml(folded.slice(cursor));
  return result;
}

export function Tex({ source, compact = false }: { source: string; compact?: boolean }) {
  const html = useMemo(() => renderTex(source), [source]);
  if (html === null) {
    return <span className={compact ? "tex tex-compact tex-figure" : "tex tex-figure"}>[图形]</span>;
  }
  return <span className={compact ? "tex tex-compact" : "tex"} dangerouslySetInnerHTML={{ __html: html }} />;
}
