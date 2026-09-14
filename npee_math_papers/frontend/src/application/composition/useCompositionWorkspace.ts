/**
 * Composition workspace: drafts, the active draft and its ordered selection.
 *
 * Selections are stored as self-contained {@link PaperRef}s, so the workspace
 * never has to resolve them against "the currently loaded page". Adding a paper
 * that is already selected is a no-op; the array order is the print order.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import type { PaperSummary } from "../../domain/catalog/models";
import {
  createDraft,
  normalizeSpacing,
  paperRefFromSummary,
  paperSummaryFromRef,
  type CompositionDraft,
  type PaperRef,
} from "../../domain/composition/models";
import type { CompositionDraftRepository } from "./ports";

function normalizeLayout(value: unknown): CompositionDraft["layout"] {
  return value === "a3" || value === "a4" || value === "both" ? value : "both";
}

function normalizeRef(value: unknown): PaperRef | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Partial<PaperRef> & { natural_key?: string };
  if (
    typeof raw.series_key !== "string" ||
    typeof raw.year !== "number" ||
    typeof raw.subject !== "string" ||
    typeof raw.paper_no !== "number"
  ) {
    return null;
  }
  return {
    series_key: raw.series_key,
    year: raw.year,
    subject: raw.subject as PaperRef["subject"],
    paper_no: raw.paper_no,
    series_name: typeof raw.series_name === "string" ? raw.series_name : raw.series_key,
    question_count: typeof raw.question_count === "number" ? raw.question_count : 0,
    natural_key:
      typeof raw.natural_key === "string"
        ? raw.natural_key
        : `${raw.year}/${raw.subject}/${raw.series_key}/${raw.paper_no}`,
  };
}

/**
 * Bring a persisted draft up to the current shape.
 *
 * Older drafts stored bare natural keys (`selected: string[]`). They cannot be
 * resolved without the API, so they are kept as references with a placeholder
 * display name; the paper list fills in real names the first time it is loaded.
 */
export function normalizeDraft(value: Partial<CompositionDraft> & { selected?: unknown }): CompositionDraft {
  const defaults = createDraft();
  const spacing = normalizeSpacing(value.spacing);

  let papers: PaperRef[] = [];
  if (Array.isArray(value.papers)) {
    papers = value.papers.map(normalizeRef).filter((ref): ref is PaperRef => ref !== null);
  } else if (Array.isArray(value.selected)) {
    papers = (value.selected as unknown[])
      .map((key) => (typeof key === "string" ? key.split("/") : []))
      .filter((parts) => parts.length === 4)
      .map(([year, subject, series_key, paper_no]) => ({
        series_key,
        year: Number(year),
        subject: subject as PaperRef["subject"],
        paper_no: Number(paper_no),
        series_name: series_key,
        question_count: 0,
        natural_key: `${year}/${subject}/${series_key}/${paper_no}`,
      }));
  }

  return {
    ...defaults,
    ...value,
    id: typeof value.id === "string" && value.id ? value.id : defaults.id,
    name: typeof value.name === "string" ? value.name : defaults.name,
    layout: spacing === "a4-blank" ? "a4" : normalizeLayout(value.layout),
    spacing,
    papers,
    opening: { ...defaults.opening, ...(value.opening ?? {}) },
    watermark: { ...defaults.watermark, ...(value.watermark ?? {}) },
  };
}

export function useCompositionWorkspace(repository: CompositionDraftRepository) {
  const [drafts, setDrafts] = useState<CompositionDraft[]>(() => {
    const saved = repository.load();
    const normalized = saved.map(normalizeDraft).filter((draft) => draft.papers.length >= 0);
    return normalized.length ? normalized : [createDraft("数学试卷集")];
  });
  const [activeDraftId, setActiveDraftId] = useState(() => drafts[0]?.id ?? "");

  const activeDraft = useMemo(
    () => drafts.find((draft) => draft.id === activeDraftId) ?? drafts[0],
    [drafts, activeDraftId],
  );

  useEffect(() => {
    repository.save(drafts);
  }, [drafts, repository]);

  const selectedPapers = useMemo(
    () => (activeDraft ? activeDraft.papers.map(paperSummaryFromRef) : []),
    [activeDraft],
  );

  const updateActiveDraft = useCallback(
    (update: (draft: CompositionDraft) => CompositionDraft) => {
      setDrafts((current) =>
        current.map((draft) => (draft.id === activeDraft?.id ? update(draft) : draft)),
      );
    },
    [activeDraft?.id],
  );

  const isSelected = useCallback(
    (naturalKey: string) => Boolean(activeDraft?.papers.some((paper) => paper.natural_key === naturalKey)),
    [activeDraft],
  );

  /** Add or remove a paper; adding an existing paper is a no-op. */
  const togglePaper = useCallback(
    (paper: PaperSummary) => {
      updateActiveDraft((draft) => {
        const exists = draft.papers.some((item) => item.natural_key === paper.natural_key);
        return {
          ...draft,
          papers: exists
            ? draft.papers.filter((item) => item.natural_key !== paper.natural_key)
            : [...draft.papers, paperRefFromSummary(paper)],
        };
      });
    },
    [updateActiveDraft],
  );

  /**
   * Add several papers at once, skipping the ones already selected.
   *
   * "Add the whole page / series" is a common human workflow, and doing it
   * through repeated {@link togglePaper} calls would flip already-selected papers
   * back off. Ids are de-duplicated inside the single update so the order added
   * is the order shown.
   *
   * The count is derived from the current draft *before* the update: reading it
   * from inside the state updater would be unsound, because React may run that
   * updater later (or twice in strict mode) and the value would have leaked out
   * of the render cycle by the time the caller used it.
   */
  const addPapers = useCallback(
    (papers: PaperSummary[]) => {
      if (!papers.length || !activeDraft) return 0;
      const seen = new Set(activeDraft.papers.map((item) => item.natural_key));
      const incoming: PaperSummary[] = [];
      for (const paper of papers) {
        if (seen.has(paper.natural_key)) continue;
        seen.add(paper.natural_key);
        incoming.push(paper);
      }
      if (!incoming.length) return 0;
      const additions = incoming.map(paperRefFromSummary);
      updateActiveDraft((draft) => {
        // Re-check inside the updater so a concurrent change cannot duplicate a
        // paper that was added between the read above and this commit.
        const present = new Set(draft.papers.map((item) => item.natural_key));
        const fresh = additions.filter((item) => !present.has(item.natural_key));
        return fresh.length ? { ...draft, papers: [...draft.papers, ...fresh] } : draft;
      });
      return incoming.length;
    },
    [activeDraft, updateActiveDraft],
  );

  /** Remove several papers by natural key, in one update. */
  const removePapers = useCallback(
    (naturalKeys: string[]) => {
      if (!naturalKeys.length) return;
      const doomed = new Set(naturalKeys);
      updateActiveDraft((draft) => ({ ...draft, papers: draft.papers.filter((item) => !doomed.has(item.natural_key)) }));
    },
    [updateActiveDraft],
  );

  const removePaper = useCallback(
    (naturalKey: string) => {
      updateActiveDraft((draft) => ({
        ...draft,
        papers: draft.papers.filter((item) => item.natural_key !== naturalKey),
      }));
    },
    [updateActiveDraft],
  );

  const movePaper = useCallback(
    (index: number, delta: number) => {
      updateActiveDraft((draft) => {
        const target = index + delta;
        if (target < 0 || target >= draft.papers.length) return draft;
        const papers = [...draft.papers];
        [papers[index], papers[target]] = [papers[target], papers[index]];
        return { ...draft, papers };
      });
    },
    [updateActiveDraft],
  );

  /** Move several papers at once (drag-and-drop, "move to top"). */
  const reorderPapers = useCallback(
    (from: number, to: number) => {
      updateActiveDraft((draft) => {
        if (from === to || from < 0 || to < 0 || from >= draft.papers.length || to >= draft.papers.length) {
          return draft;
        }
        const papers = [...draft.papers];
        const [moved] = papers.splice(from, 1);
        papers.splice(to, 0, moved);
        return { ...draft, papers };
      });
    },
    [updateActiveDraft],
  );

  const clearPapers = useCallback(() => {
    updateActiveDraft((draft) => ({ ...draft, papers: [] }));
  }, [updateActiveDraft]);

  const addDraft = useCallback(
    (name?: string, papers: PaperRef[] = []) => {
      const draft = { ...createDraft(name ?? `组卷 ${drafts.length + 1}`), papers };
      setDrafts((current) => [...current, draft]);
      setActiveDraftId(draft.id);
      return draft;
    },
    [drafts.length],
  );

  const duplicateActiveDraft = useCallback(() => {
    if (!activeDraft) return undefined;
    return addDraft(`${activeDraft.name} 副本`, [...activeDraft.papers]);
  }, [activeDraft, addDraft]);

  const deleteActiveDraft = useCallback(() => {
    if (drafts.length <= 1 || !activeDraft) return false;
    const index = drafts.findIndex((draft) => draft.id === activeDraft.id);
    const remaining = drafts.filter((draft) => draft.id !== activeDraft.id);
    setDrafts(remaining);
    setActiveDraftId(remaining[Math.max(0, index - 1)].id);
    return true;
  }, [drafts, activeDraft]);

  const renameActiveDraft = useCallback(
    (name: string) => updateActiveDraft((draft) => ({ ...draft, name })),
    [updateActiveDraft],
  );

  return {
    drafts,
    activeDraft,
    activeDraftId,
    selectedPapers,
    setActiveDraftId,
    updateActiveDraft,
    isSelected,
    togglePaper,
    addPapers,
    removePapers,
    removePaper,
    movePaper,
    reorderPapers,
    clearPapers,
    addDraft,
    duplicateActiveDraft,
    deleteActiveDraft,
    renameActiveDraft,
  };
}
