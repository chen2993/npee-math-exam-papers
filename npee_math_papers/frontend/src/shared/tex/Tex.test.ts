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
});
