import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PaperSummary } from "../../domain/catalog/models";
import type { CompositionDraftRepository } from "./ports";
import { normalizeDraft, useCompositionWorkspace } from "./useCompositionWorkspace";

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

function repository(seed: unknown[] = []): CompositionDraftRepository {
  return { load: () => seed as never, save: vi.fn() };
}

describe("normalizeDraft", () => {
  it("migrates the legacy natural-key selection into references", () => {
    const draft = normalizeDraft({ name: "旧组卷", selected: ["2024/math1/demo/1"] } as never);
    expect(draft.papers).toHaveLength(1);
    expect(draft.papers[0]).toMatchObject({ series_key: "demo", year: 2024, paper_no: 1 });
  });

  it("drops unusable entries instead of throwing", () => {
    const draft = normalizeDraft({ papers: [null, { junk: true }, { series_key: "a" }] } as never);
    expect(draft.papers).toHaveLength(0);
  });

  it("keeps the stored stock for a restored print draft", () => {
    // 间距与纸张无关：恢复一份 A3 草稿不该把它改写成 A4（那会丢掉 A3 产物）。
    expect(normalizeDraft({ spacing: "compact", printBlank: true, layout: "a3" } as never).layout).toBe("a3");
  });

  it("keeps the spaced rhythm now that it is a first-class mode", () => {
    // 宽松版回到间距词表：解答题独占页面，与留白无关。
    const draft = normalizeDraft({ spacing: "spaced" } as never);
    expect(draft.spacing).toBe("spaced");
    expect(draft.printBlank).toBe(true);
  });

  it("reads the old combined keys as compact plus blank space", () => {
    // 旧草稿用 `print` / `a4-blank` 同时表达「紧凑 + 留白」，拆分后要还原成两个轴。
    const legacyPrint = normalizeDraft({ spacing: "print" } as never);
    expect(legacyPrint.spacing).toBe("compact");
    expect(legacyPrint.printBlank).toBe(true);

    const legacyBlank = normalizeDraft({ spacing: "a4-blank" } as never);
    expect(legacyBlank.spacing).toBe("compact");
    expect(legacyBlank.printBlank).toBe(true);

    const tight = normalizeDraft({ spacing: "compact", printBlank: false } as never);
    expect(tight.printBlank).toBe(false);
  });
});

describe("useCompositionWorkspace", () => {
  it("starts with one draft even when storage is empty", () => {
    const { result } = renderHook(() => useCompositionWorkspace(repository()));
    expect(result.current.drafts).toHaveLength(1);
    expect(result.current.activeDraft).toBeTruthy();
  });

  it("toggles a paper on and off", () => {
    const { result } = renderHook(() => useCompositionWorkspace(repository()));
    act(() => result.current.togglePaper(paper(1)));
    expect(result.current.isSelected("2024/math1/demo/1")).toBe(true);
    act(() => result.current.togglePaper(paper(1)));
    expect(result.current.isSelected("2024/math1/demo/1")).toBe(false);
  });

  it("moves a paper up and down", () => {
    const { result } = renderHook(() => useCompositionWorkspace(repository()));
    act(() => result.current.togglePaper(paper(1)));
    act(() => result.current.togglePaper(paper(2)));
    act(() => result.current.movePaper(1, -1));
    expect(result.current.activeDraft.papers.map((item) => item.paper_no)).toEqual([2, 1]);
  });

  it("reorders by index for drag-and-drop", () => {
    const { result } = renderHook(() => useCompositionWorkspace(repository()));
    act(() => result.current.togglePaper(paper(1)));
    act(() => result.current.togglePaper(paper(2)));
    act(() => result.current.togglePaper(paper(3)));
    act(() => result.current.reorderPapers(2, 0));
    expect(result.current.activeDraft.papers.map((item) => item.paper_no)).toEqual([3, 1, 2]);
  });

  it("keeps at least one draft", () => {
    const { result } = renderHook(() => useCompositionWorkspace(repository()));
    let removed = true;
    act(() => {
      removed = result.current.deleteActiveDraft();
    });
    expect(removed).toBe(false);
    expect(result.current.drafts).toHaveLength(1);
  });

  it("duplicates the active draft with its papers", () => {
    const { result } = renderHook(() => useCompositionWorkspace(repository()));
    act(() => result.current.togglePaper(paper(1)));
    act(() => result.current.duplicateActiveDraft());
    expect(result.current.drafts).toHaveLength(2);
    expect(result.current.activeDraft.papers).toHaveLength(1);
  });

  it("adds a batch without flipping already-selected papers off", () => {
    // "Add this whole page" goes through addPapers rather than repeated toggles,
    // because toggling a paper that is already selected would *remove* it.
    const { result } = renderHook(() => useCompositionWorkspace(repository()));
    act(() => result.current.togglePaper(paper(1)));
    let added = 0;
    act(() => {
      added = result.current.addPapers([paper(1), paper(2), paper(3)]);
    });
    expect(added).toBe(2);
    expect(result.current.activeDraft.papers.map((item) => item.paper_no)).toEqual([1, 2, 3]);
  });

  it("counts a duplicated paper only once when adding a batch", () => {
    const { result } = renderHook(() => useCompositionWorkspace(repository()));
    let added = 0;
    act(() => {
      added = result.current.addPapers([paper(1), paper(1), paper(2)]);
    });
    expect(added).toBe(2);
    expect(result.current.activeDraft.papers).toHaveLength(2);
  });

  it("removes a batch by natural key", () => {
    const { result } = renderHook(() => useCompositionWorkspace(repository()));
    act(() => result.current.addPapers([paper(1), paper(2), paper(3)]));
    act(() => result.current.removePapers(["2024/math1/demo/2", "2024/math1/demo/3"]));
    expect(result.current.activeDraft.papers.map((item) => item.paper_no)).toEqual([1]);
  });
});
