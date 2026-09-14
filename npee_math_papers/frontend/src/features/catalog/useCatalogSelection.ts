/**
 * Selection behaviour shared by the catalogue and the search page.
 *
 * Both screens let the user inspect one paper and add papers to the active
 * draft; the drawer target and the toggle/navigate actions are identical, so
 * they live here rather than being duplicated per page.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useWorkspace } from "../../app/CompositionWorkspace";
import type { PaperSummary } from "../../domain/catalog/models";

export function useCatalogSelection() {
  const workspace = useWorkspace();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<PaperSummary | null>(null);

  // A search hit links to `/papers?paper=<natural key>`; opening that paper's
  // drawer on arrival is what makes the link land on the question the user
  // searched for instead of an unfiltered list.
  const [params, setParams] = useSearchParams();
  const requested = params.get("paper") ?? "";
  const consumedRef = useRef<string | null>(null);

  useEffect(() => {
    if (!requested) return;
    // Mark it consumed before the URL is rewritten; otherwise this effect would
    // re-run against the pre-update `params` and clear the drawer it just opened.
    if (consumedRef.current === requested) return;
    consumedRef.current = requested;
    const [year, subject, seriesKey, paperNo] = requested.split("/");
    if (!year || !subject || !seriesKey || !paperNo) return;
    setDetail({
      natural_key: requested,
      bundle: `${seriesKey}-${year}-${subject}`,
      series_key: seriesKey,
      series_name: seriesKey,
      year: Number(year),
      subject: subject as PaperSummary["subject"],
      paper_no: Number(paperNo),
      question_count: 0,
      section_counts: {},
      content_hash: "",
    });
    // Drop the parameter so closing the drawer does not reopen it on the next
    // render, and so the URL stays a description of the visible page.
    const next = new URLSearchParams(params);
    next.delete("paper");
    setParams(next, { replace: true });
  }, [requested, params, setParams]);

  const toggle = useCallback((paper: PaperSummary) => workspace.togglePaper(paper), [workspace]);
  const isSelected = useCallback((naturalKey: string) => workspace.isSelected(naturalKey), [workspace]);
  const openCompose = useCallback(() => navigate("/compose"), [navigate]);
  /** Add a whole page / series to the draft; returns how many were really added. */
  const addMany = useCallback((papers: PaperSummary[]) => workspace.addPapers(papers), [workspace]);
  const removeMany = useCallback((naturalKeys: string[]) => workspace.removePapers(naturalKeys), [workspace]);

  return {
    detail,
    openDetail: setDetail,
    toggle,
    addMany,
    removeMany,
    isSelected,
    openCompose,
    selectedCount: workspace.activeDraft?.papers.length ?? 0,
  };
}
