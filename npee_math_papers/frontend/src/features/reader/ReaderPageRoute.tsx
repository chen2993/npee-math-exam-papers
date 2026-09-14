/**
 * The standalone paper reader: series → papers in one 卷 → the 22 questions.
 *
 * Deliberately **decoupled from composition**: there is no checkbox, no "add to
 * draft", no compile action. The catalogue page is where papers are selected;
 * this page exists to read them, and mixing the two made "just look at a paper"
 * require wading through selection controls.
 *
 * All three levels live in the URL (`#/reader?series=…&year=…&subject=…&paper=…`),
 * so a paper can be linked to and reloaded, and the browser back button walks the
 * hierarchy instead of leaving the page.
 */

import { BookOpenText, ChevronLeft, ListTree, Search as SearchIcon, X } from "lucide-react";
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { useBundles, usePapers } from "../../application/query/hooks";
import { useAppServices } from "../../app/AppServices";
import type { PaperSummary, Subject } from "../../domain/catalog/models";
import { subjectNames } from "../../domain/catalog/models";
import { Button, EmptyState, SearchField, Surface, SurfaceHeading, classNames } from "../../shared/ui";
import { PaperReader } from "./PaperReader";

/** Parse the four identity parts from the URL; `null` means "no paper chosen". */
function paperFromParams(params: URLSearchParams): PaperSummary | null {
  const seriesKey = params.get("series");
  const paperNo = Number(params.get("paper"));
  const year = Number(params.get("year"));
  const subject = params.get("subject") as Subject | null;
  if (!seriesKey || !year || !subject || !paperNo) return null;
  return {
    natural_key: `${year}/${subject}/${seriesKey}/${paperNo}`,
    bundle: `${seriesKey}-${year}-${subject}`,
    series_key: seriesKey,
    series_name: seriesKey,
    year,
    subject,
    paper_no: paperNo,
    question_count: 0,
    section_counts: {},
    content_hash: "",
  };
}

export default function ReaderPageRoute() {
  const { gateway } = useAppServices();
  const [params, setParams] = useSearchParams();

  const subjectFilter = (params.get("subject") as Subject | null) ?? "";
  const seriesFilter = params.get("series") ?? "";
  const query = params.get("q") ?? "";
  const selected = useMemo(() => paperFromParams(params), [params]);

  // Level two is a *bundle*, not a loose paper list: one 卷 (系列 + 年份 + 科目)
  // holds the numbered 套, and those are what the user picks from.
  const bundles = useBundles(gateway, {
    seriesKeys: seriesFilter ? [seriesFilter] : [],
    subjects: subjectFilter ? [subjectFilter] : [],
  });
  const papers = usePapers(gateway, {
    seriesKeys: seriesFilter ? [seriesFilter] : [],
    subjects: subjectFilter ? [subjectFilter] : [],
    query,
    order: "year-desc",
    limit: 500,
  });

  /** Write a navigation step, dropping everything below it in the hierarchy. */
  function go(patch: Record<string, string | null>) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(patch)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    // Choosing a different 卷 or filter invalidates the open paper.
    if (!("paper" in patch)) next.delete("paper");
    setParams(next, { replace: false });
  }

  const bundleRows = bundles.data ?? [];
  const paperRows = papers.data?.papers ?? [];
  const years = useMemo(() => {
    const seen = new Set(paperRows.map((paper) => paper.year));
    return [...seen].sort((left, right) => right - left);
  }, [paperRows]);

  const shownPaper = selected
    ? papers.data?.papers.find((paper) => paper.natural_key === selected.natural_key) ?? selected
    : null;

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div>
          <span className="eyebrow">PAPER READER</span>
          <h2>套卷查看</h2>
          <p>按系列 → 套卷 → 逐题阅读，纯查看，不影响组卷。</p>
        </div>
        {shownPaper ? (
          <div className="page-title-actions">
            <Button icon={<ChevronLeft size={15} />} onClick={() => go({ paper: null })}>
              返回套卷列表
            </Button>
          </div>
        ) : null}
      </div>

      {shownPaper ? (
        <div className="reader-head">
          <div className="reader-crumbs" aria-label="阅读位置">
            <button type="button" onClick={() => go({ paper: null })}>
              {subjectNames[shownPaper.subject]} · {shownPaper.year}
            </button>
            <span>{shownPaper.series_key}</span>
            <strong>第 {shownPaper.paper_no} 套</strong>
          </div>
          <p className="muted-line">
            共 {shownPaper.question_count || "—"} 题 · 题面实时来自题库；本页不接受任何写入。
          </p>
          <PaperReader paper={shownPaper} gateway={gateway} />
        </div>
      ) : (
        <div className="reader-layout">
          <Surface className="reader-side">
            <SurfaceHeading
              eyebrow="LEVEL 1 · 卷"
              title="选一套卷"
              count={`${bundleRows.length} 卷`}
              actions={
                seriesFilter ? (
                  <Button size="sm" variant="quiet" icon={<X size={13} />} onClick={() => go({ series: null })}>
                    清除
                  </Button>
                ) : null
              }
            />
            <div className="reader-side-filter">
              <SearchField
                label=""
                value={query}
                onChange={(value) => go({ q: value || null })}
                placeholder="搜索系列或年份"
              />
            </div>
            <div className="reader-bundle-list">
              {bundleRows.map((bundle) => {
                const isActive = bundle.series_key === seriesFilter && String(bundle.year) === params.get("year");
                return (
                  <button
                    key={bundle.bundle}
                    type="button"
                    className={classNames("reader-bundle", isActive && "is-active")}
                    onClick={() => go({ series: bundle.series_key, year: String(bundle.year), subject: bundle.subject })}
                  >
                    <span className={classNames("subject-mark", bundle.subject)}>
                      {bundle.subject.replace("math", "数")}
                    </span>
                    <span className="reader-bundle-text">
                      <strong>{bundle.series_name}</strong>
                      <small>
                        {bundle.year} · {subjectNames[bundle.subject]}
                      </small>
                    </span>
                    <span className="reader-bundle-count">{bundle.paper_count} 套</span>
                  </button>
                );
              })}
              {!bundleRows.length && !bundles.isLoading ? (
                <EmptyState icon={<ListTree size={20} />} title="没有匹配的卷" hint="换一个关键词，或清除筛选" />
              ) : null}
            </div>
          </Surface>

          <Surface className="reader-main">
            <SurfaceHeading
              eyebrow="LEVEL 2 · 套"
              title={seriesFilter ? "这一卷里的套卷" : "全部套卷"}
              count={`${papers.data?.total ?? 0} 套`}
            />
            {seriesFilter ? null : (
              <p className="reader-hint">从左侧选一卷，这里会列出它的套卷。</p>
            )}
            <div className="reader-paper-grid">
              {paperRows.map((paper) => (
                <button
                  key={paper.natural_key}
                  type="button"
                  className="reader-paper-card"
                  onClick={() =>
                    go({
                      series: paper.series_key,
                      subject: paper.subject,
                      year: String(paper.year),
                      paper: String(paper.paper_no),
                    })
                  }
                >
                  <span className="reader-paper-no">第 {paper.paper_no} 套</span>
                  <span className="reader-paper-name">{paper.series_name}</span>
                  <span className="reader-paper-meta">
                    {paper.year} · {subjectNames[paper.subject]} · {paper.question_count} 题
                  </span>
                </button>
              ))}
            </div>
            {!paperRows.length && !papers.isLoading ? (
              <EmptyState
                icon={<SearchIcon size={20} />}
                title={query ? "没有匹配的套卷" : "没有可查看的套卷"}
                hint={query ? "换一个关键词" : "请先在题库中导入题目"}
              />
            ) : null}
            {years.length ? (
              <div className="reader-year-row">
                <span className="eyebrow">按年份</span>
                {years.map((year) => (
                  <button key={year} type="button" onClick={() => go({ q: String(year) })}>
                    {year}
                  </button>
                ))}
              </div>
            ) : null}
          </Surface>
        </div>
      )}

      <p className="reader-footnote">
        <BookOpenText size={14} />
        本页只读；要把套卷加入组卷，请到「套卷」页勾选。
      </p>
    </div>
  );
}
