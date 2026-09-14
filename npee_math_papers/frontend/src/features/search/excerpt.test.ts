import { describe, expect, it } from "vitest";

import { balancedExcerpt } from "./excerpt";

describe("balancedExcerpt", () => {
  it("keeps a short excerpt unchanged", () => {
    expect(balancedExcerpt("设 $x>0$，求 $f(x)$。")).toBe("设 $x>0$，求 $f(x)$。");
  });

  it("collapses whitespace", () => {
    expect(balancedExcerpt("a\n\n  b")).toBe("a b");
  });

  it("cuts back to the last balanced math run when truncated mid-math", () => {
    const raw = `设 $x>0$，则 ${"很长的中文描述".repeat(30)} $\\sum_{n=1}^{\\infty}a_n$`;
    const result = balancedExcerpt(raw, 60);
    // It must not leave an odd number of dollar signs (which would leak LaTeX).
    expect((result.match(/\$/g) ?? []).length % 2).toBe(0);
    expect(result.endsWith("…")).toBe(true);
  });

  it("rebalances even when the input is within the length limit", () => {
    // Simulates the API truncating at 120 chars in the middle of math.
    const raw = "答案 $\\sum_{n=1}^{\\infty}u_n$ 收敛，因为";
    const cut = raw.slice(0, 12);
    const result = balancedExcerpt(cut, 200);
    expect((result.match(/\$/g) ?? []).length % 2).toBe(0);
  });

  it("handles an excerpt with no math at all", () => {
    const raw = "纯粹的中文题干".repeat(40);
    const result = balancedExcerpt(raw, 40);
    expect(result.endsWith("…")).toBe(true);
    expect(result).not.toContain("$");
  });

  it("does not treat an escaped dollar as a delimiter", () => {
    const result = balancedExcerpt("价格 \\$100 与 $x$", 200);
    expect((result.match(/[^\\]\$/g) ?? []).length % 2).toBe(0);
  });
});
