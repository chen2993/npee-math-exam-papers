/**
 * Which paper's drawer is open, and the `?paper=<natural key>` hand-off.
 *
 * A search hit links to `/papers?paper=2024/math1/zhangyu8/7`; opening that
 * paper's drawer on arrival is what makes the link land on the paper the user
 * searched for instead of an unfiltered list.
 *
 * This hook deliberately knows nothing about compositions: browsing papers and
 * building a draft are separate features, and the catalogue only reads.
 */

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import type { PaperSummary } from "../../domain/catalog/models";

export function usePaperDrawer() {
  const [detail, setDetail] = useState<PaperSummary | null>(null);
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

  return { detail, openDetail: setDetail };
}
