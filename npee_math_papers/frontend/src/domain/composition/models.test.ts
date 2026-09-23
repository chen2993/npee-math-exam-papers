import { describe, expect, it } from "vitest";

import type { PaperSummary } from "../catalog/models";
import {
  buildCompilePayload,
  createDraft,
  draftFromCompilePayload,
  outputTargetCount,
  paperRefFromSummary,
  paperSummaryFromRef,
} from "./models";

function paper(no: number): PaperSummary {
  return {
    natural_key: `2024/math1/demo/${no}`,
    bundle: "demo-2024-math1",
    series_key: "demo",
    series_name: "示例系列",
    year: 2024,
    subject: "math1",
    paper_no: no,
    question_count: 22,
    section_counts: {},
    content_hash: "abc",
  };
}

describe("paper references", () => {
  it("round-trips a summary through a reference", () => {
    const ref = paperRefFromSummary(paper(3));
    expect(ref).toMatchObject({ series_key: "demo", year: 2024, paper_no: 3, natural_key: "2024/math1/demo/3" });
    const back = paperSummaryFromRef(ref);
    expect(back.natural_key).toBe("2024/math1/demo/3");
    expect(back.series_name).toBe("示例系列");
  });
});

describe("buildCompilePayload", () => {
  it("uses the draft's own references without needing loaded papers", () => {
    const draft = { ...createDraft("测试卷"), papers: [paperRefFromSummary(paper(1)), paperRefFromSummary(paper(2))] };
    const payload = buildCompilePayload(draft);
    expect(payload.selections).toEqual([
      { series_key: "demo", year: 2024, subject: "math1", paper_no: 1 },
      { series_key: "demo", year: 2024, subject: "math1", paper_no: 2 },
    ]);
    expect(payload.title).toBe("测试卷");
  });

  it("preserves print order", () => {
    const draft = { ...createDraft(), papers: [paperRefFromSummary(paper(5)), paperRefFromSummary(paper(2))] };
    const payload = buildCompilePayload(draft);
    expect(payload.selections.map((item: { paper_no: number }) => item.paper_no)).toEqual([5, 2]);
  });

  it("expands layout/theme/spacing into explicit targets", () => {
    const draft = { ...createDraft(), layout: "both" as const, theme: "both" as const, spacing: "both" as const };
    const payload = buildCompilePayload(draft);
    // a3/a4 × print/cream × (紧凑 + 宽松)
    expect(payload.compile.targets).toHaveLength(8);
    expect(payload.compile.targets.some((target: { spacing: string }) => target.spacing === "spaced")).toBe(true);
  });

  it("keeps the chosen stock on every spacing", () => {
    // 间距与纸张无关：宽松版同样能在 A3 上出，不该被悄悄改写成 A4。
    const draft = { ...createDraft(), layout: "a3" as const, spacing: "spaced" as const };
    const payload = buildCompilePayload(draft);
    expect(payload.compile.targets.every((target: { layout: string }) => target.layout === "a3")).toBe(true);
  });

  it("sends spacing and blank space as two independent fields", () => {
    // 留白不再藏在间距里：两者各写各的，后端按两个轴解释。
    const draft = { ...createDraft(), spacing: "spaced" as const, printBlank: true };
    for (const target of buildCompilePayload(draft).compile.targets as { spacing: string; print: boolean }[]) {
      expect(target.spacing).toBe("spaced");
      expect(target.print).toBe(true);
    }
    const tight = { ...createDraft(), spacing: "compact" as const, printBlank: false };
    for (const target of buildCompilePayload(tight).compile.targets as { print: boolean }[]) {
      expect(target.print).toBe(false);
    }
  });

  it("keeps the composition id lowercase and dash-separated", () => {
    const draft = { ...createDraft(), id: "Composition_ABC_123" };
    expect(buildCompilePayload(draft).composition_id).toMatch(/^[a-z0-9][a-z0-9-]*$/);
  });
});

describe("outputTargetCount", () => {
  it("counts one file per layout × theme × spacing", () => {
    expect(outputTargetCount(createDraft())).toBe(2); // a3 + a4 print, one theme, one spacing
  });

  it("reports the silent multiplication of 'both' on every axis", () => {
    const draft = { ...createDraft(), layout: "both" as const, theme: "both" as const, spacing: "both" as const };
    expect(outputTargetCount(draft)).toBe(8);
  });
});

describe("draftFromCompilePayload", () => {
  it("is the inverse of buildCompilePayload", () => {
    const draft = {
      ...createDraft("往返"),
      papers: [paperRefFromSummary(paper(1)), paperRefFromSummary(paper(2))],
      layout: "a4" as const,
      theme: "cream" as const,
      spacing: "spaced" as const,
      printBlank: false,
      toc: false,
    };
    const restored = draftFromCompilePayload(buildCompilePayload(draft));
    expect(restored.name).toBe("往返");
    expect(restored.papers.map((item) => item.natural_key)).toEqual(["2024/math1/demo/1", "2024/math1/demo/2"]);
    expect(restored.layout).toBe("a4");
    expect(restored.theme).toBe("cream");
    expect(restored.spacing).toBe("spaced");
    expect(restored.printBlank).toBe(false);
    expect(restored.toc).toBe(false);
  });

  it("rejects a payload without selections", () => {
    expect(() => draftFromCompilePayload({ title: "空" })).toThrow();
  });

  it("rejects an entry missing a required identity field", () => {
    expect(() => draftFromCompilePayload({ selections: [{ series_key: "demo", year: 2024 }] })).toThrow();
  });

  it("falls back to defaults for unknown document values instead of throwing", () => {
    const restored = draftFromCompilePayload({
      selections: [{ series_key: "demo", year: 2024, subject: "math1", paper_no: 1 }],
      document: { layout: "bogus", structure: "bogus" },
    });
    expect(restored.layout).toBe("both");
    expect(restored.spacing).toBe("compact");
    expect(restored.printBlank).toBe(true);
  });
});
