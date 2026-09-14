/**
 * The paper detail drawer.
 *
 * A modal reading surface on the catalogue and search pages: it shows one paper
 * and offers the "add to composition" action. The question trees themselves come
 * from `shared/question/QuestionView`, which the standalone reader reuses, so the
 * two reading surfaces cannot drift apart.
 *
 * The drawer is the *composition-coupled* path (it can add to a draft). The
 * `/paper` reader is the pure-viewing path that shares none of that state.
 */

import { BookOpenText, Check, LoaderCircle, Plus, X } from "lucide-react";
import { useEffect, useRef } from "react";

import type { CatalogGateway } from "../../application/catalog/ports";
import { usePaperDetail } from "../../application/query/hooks";
import type { PaperDocument, PaperSummary } from "../../domain/catalog/models";
import { subjectNames } from "../../domain/catalog/models";
import { useWorkspace } from "../../app/CompositionWorkspace";
import { QuestionView } from "../../shared/question/QuestionView";
import { Button, IconButton } from "../../shared/ui";

export function PaperDetailDrawer({
  paper,
  gateway,
  onClose,
}: {
  paper: PaperSummary;
  gateway: CatalogGateway;
  onClose: () => void;
}) {
  const workspace = useWorkspace();
  // One query per paper; the cache makes reopening the same paper instant.
  const query = usePaperDetail(gateway, {
    seriesKey: paper.series_key,
    year: paper.year,
    subject: paper.subject,
    paperNo: paper.paper_no,
  });
  const detail = query.data as PaperDocument | undefined;
  const loading = query.isLoading;
  const error = query.isError ? (query.error instanceof Error ? query.error.message : "读取题目失败") : "";
  // The passed summary can be a placeholder (a deep link from a search hit knows
  // the natural key but not the display name); the fetched document always
  // carries the real one in `meta`, so prefer it for the header once it arrives.
  const shown = detail?.meta ?? paper;
  const selected = workspace.isSelected(paper.natural_key);
  const bodyRef = useRef<HTMLDivElement>(null);

  // Escape closes the drawer and the background must not scroll underneath it —
  // both are expected of a panel that covers the page, and their absence is felt
  // most on a long paper.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    bodyRef.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [onClose]);

  return (
    <div className="drawer-backdrop" onClick={onClose} role="presentation">
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label={`${shown.series_name} 第 ${shown.paper_no} 套`}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="drawer-head">
          <div>
            <span className="eyebrow">{subjectNames[shown.subject]} · {shown.year}</span>
            <h3>
              {shown.series_name} 第 {shown.paper_no} 套
            </h3>
          </div>
          <Button
            size="sm"
            variant={selected ? "primary" : "default"}
            icon={selected ? <Check size={14} /> : <Plus size={14} />}
            onClick={() => workspace.togglePaper(shown)}
          >
            {selected ? "已加入" : "加入组卷"}
          </Button>
          <IconButton label="关闭" onClick={onClose}>
            <X size={17} />
          </IconButton>
        </header>
        {/* Focusable so the Escape handler and the scroll container both work. */}
        <div className="drawer-body" ref={bodyRef} tabIndex={-1}>
          {loading && (
            <div className="drawer-state">
              <LoaderCircle className="is-spinning" size={20} />正在读取题目
            </div>
          )}
          {error && <div className="drawer-state drawer-error">{error}</div>}
          {detail && !loading && (
            <>
              <div className="drawer-summary">
                <BookOpenText size={15} />
                共 {detail.meta.question_count} 题
                {detail.meta.figure_count ? ` · ${detail.meta.figure_count} 图` : ""}
              </div>
              {detail.questions.map((question) => (
                <QuestionView key={question.number} question={question} paper={paper} />
              ))}
            </>
          )}
        </div>
      </aside>
    </div>
  );
}
