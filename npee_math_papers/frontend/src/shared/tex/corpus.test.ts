/**
 * Render every field of the real library through the app's own renderer.
 *
 * The unit tests cover individual constructs; this covers the corpus, so a
 * regression that only shows up on, say, `\oiint\limits` is still caught. It
 * skips silently when the data store is absent (a checkout without papers).
 */

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { renderTex } from "./Tex";

const PAPERS = join(process.cwd(), "..", "..", ".npee-math-papers", "papers");

/** Pull every `text:` block scalar out of a paper YAML. */
function textBlocks(source: string): string[] {
  const blocks: string[] = [];
  const pattern = /text: \|-\n((?: {6}.*\n)+)/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(source))) blocks.push(match[1].trimEnd());
  return blocks;
}

function paperFiles(): string[] {
  if (!existsSync(PAPERS)) return [];
  const files: string[] = [];
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) walk(path);
      else if (entry.name.endsWith(".yaml")) files.push(path);
    }
  };
  walk(PAPERS);
  return files;
}

/**
 * Remove KaTeX's `<annotation>` nodes, which echo the *input* LaTeX.
 *
 * Without this, any assertion about the rendered output would also match the
 * original source text sitting invisibly inside the MathML tree.
 */
function visibleHtml(html: string): string {
  return html.replace(/<annotation[\s\S]*?<\/annotation>/g, "");
}

describe("corpus rendering", () => {
  const files = paperFiles();

  // These two cases render the whole library (321 papers, ~14k blocks) through
  // KaTeX, so their cost is inherent and scales with the corpus rather than with
  // the code under test. They were already running at 3.7s / 4.8s against the
  // 5s default, which made the suite flaky on a loaded machine. The timeout is
  // therefore a property of the test, not a workaround for a slow regression.
  const CORPUS_TIMEOUT = 60_000;

  it.skipIf(files.length === 0)("renders every text block without a KaTeX error", () => {
    const failures: string[] = [];
    let blocks = 0;
    for (const file of files) {
      for (const block of textBlocks(readFileSync(file, "utf-8"))) {
        blocks++;
        const html = renderTex(block);
        // null means "contains a drawing environment", which is handled by the
        // server-side SVG path rather than by KaTeX.
        if (html === null) continue;
        if (visibleHtml(html).includes("katex-error")) {
          failures.push(`${file}: ${block.slice(0, 90)}`);
        }
      }
    }
    expect(blocks).toBeGreaterThan(1000);
    expect(failures.slice(0, 5)).toEqual([]);
  }, CORPUS_TIMEOUT);

  it.skipIf(files.length === 0)("never leaves a project command as literal text", () => {
    const leaked: string[] = [];
    for (const file of files) {
      for (const block of textBlocks(readFileSync(file, "utf-8"))) {
        const html = renderTex(block);
        if (html === null) continue;
        const visible = visibleHtml(html);
        for (const command of ["\\ExamSelection", "\\ExamBlank"]) {
          if (visible.includes(command)) leaked.push(`${file}: ${command}`);
        }
      }
    }
    expect(leaked.slice(0, 5)).toEqual([]);
  }, CORPUS_TIMEOUT);
});
