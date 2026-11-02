import { describe, expect, it } from "vitest";

import { renderTex } from "./Tex";

/**
 * A KaTeX parse error is invisible in the console because the app renders with
 * `throwOnError: false`; the failure surfaces as red source text in the UI. These
 * cases therefore assert on the *output*, not on a thrown error.
 */
describe("renderTex", () => {
  it("renders the corpus' most common constructs instead of error text", () => {
    // `\mathrm{d}x` appears throughout the library. It used to fail because
    // `\mathrm` was defined as a self-referential macro.
    for (const source of [
      "$\\int_0^1 x\\,\\mathrm{d}x$",
      "$\\operatorname{r}(A)=2$",
      "$\\boldsymbol{\\beta}$",
      "$\\dfrac{a}{b}$",
      "$\\mathrm{d}z$",
    ]) {
      const html = renderTex(source);
      expect(html).toBeTruthy();
      expect(html).not.toContain("katex-error");
      // Not merely "no error marker": the span must produce MathML. (The original
      // source also appears in KaTeX's `<annotation>`, which is not visible text.)
      expect(html).toContain("katex-mathml");
    }
  });

  it("renders matrices and cases environments", () => {
    const html = renderTex("$\\begin{pmatrix}1&2\\\\3&4\\end{pmatrix}$");
    expect(html).not.toContain("katex-error");
    expect(html).toContain("katex");
  });

  it("turns the stored \\n marker into a line break", () => {
    // Stems store the marker (docs/EXTRACTION.md); the browser used to print it.
    const html = renderTex("下列结论正确的个数为\\n① 甲；\\n② 乙。");
    expect(html).toContain("<br />");
    expect(html).not.toContain("\\n");
  });

  it("keeps control words that start with \\n intact", () => {
    // `\nu`, `\ne` and `\nabla` are commands, not line breaks — the guard is the
    // same one the migration tools use.
    const html = renderTex("$\\nu$ 与 $\\nabla f$，且 $a\\ne b$");
    expect(html).not.toContain("<br />");
    expect(html).not.toContain("katex-error");
  });

  it("does not leave a trailing break at the end of a stem", () => {
    expect(renderTex("设 $a=1$。\\n")).not.toMatch(/<br \/>\s*$/);
  });

  it("gives \\oiint a \\limits-capable stand-in", () => {
    // `\oiint\limits_S` needs the macro to expand to a math operator; KaTeX has
    // neither a built-in `\oiint` nor a `\unicode` primitive.
    const html = renderTex("$I=\\oiint\\limits_S x\\,\\mathrm{d}S$");
    expect(html).not.toContain("katex-error");
  });

  it("maps the project-specific exam commands", () => {
    // These only take effect inside `$...$`, which is how the library writes them
    // (e.g. `...则 $(a,b)=$\ExamSelection` — the command sits adjacent to a span).
    expect(renderTex("$\\ExamSelection$")).toContain("katex");
    expect(renderTex("$\\ExamBlank$")).toContain("katex");
  });

  it("draws the choice-question bracket as Chinese parentheses, not a square", () => {
    // The papers print `（　　　）` at the end of a choice stem; `\square` showed
    // up as a box in the browser and read as a missing glyph.
    const html = renderTex("则 $f'(1)=$\\ExamSelection。");
    expect(html).toBeTruthy();
    expect(html).not.toContain("□");
    expect(html).not.toContain("katex-error");
    expect(html).toContain("（");
    expect(html).toContain("）");
  });

  it("renders exam commands written outside a math span", () => {
    // The library writes these outside `$...$` in the large majority of cases
    // (3076 of 3210 `\ExamSelection`, 1516 of 1927 `\ExamBlank`). They used to
    // fall through to the text branch and show up literally in the UI.
    const html = renderTex("则 $(a,b)=$\\ExamSelection。");
    expect(html).not.toContain("\\ExamSelection");
    expect(html).toContain("katex");

    expect(renderTex("该方程为\\ExamBlank。")).not.toContain("\\ExamBlank");
  });

  it("returns null when the span contains a drawing environment", () => {
    // TikZ cannot be rendered by KaTeX; the caller swaps in a server-rendered SVG.
    expect(renderTex("画图：\\begin{tikzpicture}\\draw (0,0)--(1,1);\\end{tikzpicture}")).toBeNull();
  });

  it("escapes the surrounding prose", () => {
    const html = renderTex("若 $a<b$ 则 <成立>");
    expect(html).toContain("&lt;成立&gt;");
  });

  it("puts an integral's region label below the sign", () => {
    // KaTeX marks stacked scripts with `mop op-limits`; a side-set subscript
    // carries no such class. A domain subscript reads as "the integral over L",
    // which an examination paper sets under the sign.
    for (const source of [
      "$\\int_L f$",
      "$\\int_{L_1} f$",
      "$\\int_{\\Gamma} g$",
      // `\displaystyle` may sit between the relation and the integral.
      "$\\displaystyle\\int_L f$",
    ]) {
      expect(renderTex(source)).toContain("mop op-limits");
    }
  });

  it("centres the label of the operators the class forces \\limits on", () => {
    // The class applies \limits to these in its begindocument/end hook, so the
    // browser has to match it. `oint` was missing from the frontend's list, so a
    // contour integral rendered its label at the side in the UI but centred in
    // the PDF.
    for (const source of ["$\\oint_L f$", "$\\oint_{\\Gamma} h$", "$\\iint_D f$", "$\\iiint_\\Omega g$", "$\\sum_{n=1}^{\\infty}a_n$"]) {
      expect(renderTex(source)).toContain("mop op-limits");
    }
  });

  it("leaves a numeric integral bound at the lower right", () => {
    // The reference papers set a numeric range at the side, and keeping it there
    // is what stops an integral inside a fraction from growing tall.
    for (const source of ["$\\int_0^1 f$", "$\\int_a^b f$", "$\\int x\\,\\mathrm{d}x$"]) {
      expect(renderTex(source)).not.toContain("mop op-limits");
    }
  });

  /**
   * KaTeX even echoes the input in an `<annotation>` node, which is how the
   * normalization can be observed: the visible tree alone cannot show whether
   * `\\dfrac` was rewritten, because KaTeX would happily stack either one.
   */
  function mathAnnotation(source: string): string {
    const match = /<annotation[^>]*>([\s\S]*?)<\/annotation>/.exec(renderTex(source) || "");
    return match ? match[1] : "";
  }

  it("gives a fraction the size its position calls for", () => {
    // A script slot is already script style, so `\\dfrac` there re-inflates the
    // fraction and overflows the line; in body text `\\frac` looks shrunken.
    expect(mathAnnotation("$x^{\\dfrac{1}{2}}$")).toContain("^{\\frac{1}{2}}");
    expect(mathAnnotation("$\\int_0^{\\dfrac{\\pi}{2}}f$")).toContain("^{\\frac{\\pi}{2}}");
    // Body positions keep display size.
    expect(mathAnnotation("$\\dfrac{a}{b}$")).toContain("\\dfrac{a}{b}");
    expect(mathAnnotation("$\\frac{a}{b}$")).toContain("\\dfrac{a}{b}");
    // A fraction's numerator/denominator is already a reduced style too, so a
    // nested \\dfrac has to shrink as well -- including the denominator, which
    // is the second of the two arguments a fraction takes.
    expect(mathAnnotation("$\\dfrac{\\arctan\\dfrac{1}{x}}{\\sec x}$")).toContain("\\arctan\\frac{1}{x}");
    expect(mathAnnotation("$\\dfrac{a}{\\frac{b}{c}}$")).toContain("{\\frac{b}{c}}");
    expect(mathAnnotation("$\\dfrac{\\dfrac{a}{b}}{\\dfrac{c}{d}}$")).toContain("{\\frac{a}{b}}");
    // Already-correct input is left alone.
    expect(mathAnnotation("$x^{\\frac{1}{2}}$")).toContain("^{\\frac{1}{2}}");
  });
});
