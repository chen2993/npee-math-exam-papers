/**
 * Paper catalogue.
 *
 * Filters live in the URL query string, so a filtered view is shareable and
 * survives a reload — a capability the previous `useState`-only version could
 * not offer. The table itself is a thin renderer over the server-paged query.
 *
 * The text box searches the **whole library** (it is sent to the server as `q`),
 * not just the loaded page: "find the 2024 张宇卷 with 23 questions" is the
 * question people actually ask, and a page-local filter silently answers a
 * different one. Structured filters and ordering are likewise server-side, so the
 * total and the pager always describe the filtered set.
 */

import { BookOpenText, Check, FileArchive, ListPlus, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import type { PaperOrder } from "../../application/catalog/ports";
import { useBundles, useOverview, usePapers } from "../../application/query/hooks";
import { useAppServices } from "../../app/AppServices";
import type { PaperSummary } from "../../domain/catalog/models";
import { subjectNames } from "../../domain/catalog/models";
import { usePreferences } from "../../preferences";
import { Button, EmptyState, Pager, Surface, classNames, useToast } from "../../shared/ui";
import { PaperFilters, PAPER_ORDER_OPTIONS, type PaperFilterValue } from "./PaperFilters";
import { PaperDetailDrawer } from "./PaperDetailDrawer";
import { useCatalogSelection } from "./useCatalogSelection";

const ORDER_VALUES = new Set<string>(PAPER_ORDER_OPTIONS.map((option) => option.value));

export default function PaperCatalogPageRoute() {
  const { gateway } = useAppServices();
  const { preferences } = usePreferences();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const selection = useCatalogSelection();

  const seriesKey = params.get("series") ?? "";
  const year = params.get("year") ?? "";
  const subject = params.get("subject") ?? "";
  const query = params.get("q") ?? "";
  const orderParam = params.get("order") ?? "";
  const order: PaperOrder = ORDER_VALUES.has(orderParam) ? (orderParam as PaperOrder) : "series";
  const offset = Number(params.get("offset") ?? "0") || 0;

  const overview = useOverview(gateway);
  const series = overview.data?.series ?? [];
  const years = useMemo(
    () => [...(overview.data?.stats.years ?? [])].sort((left, right) => right - left),
    [overview.data?.stats.years],
  );
  // The filters are forwarded so the bundle query narrows the same way the
  // paper query does, instead of always fetching every bundle.
  useBundles(gateway, {
    seriesKeys: seriesKey ? [seriesKey] : [],
    years: year ? [Number(year)] : [],
    subjects: subject ? [subject] : [],
  });

  const paperQuery = useMemo(
    () => ({
      seriesKeys: seriesKey ? [seriesKey] : [],
      years: year ? [Number(year)] : [],
      subjects: subject ? [subject] : [],
      query,
      order,
      offset,
      limit: preferences.pageSize,
    }),
    [seriesKey, year, subject, query, order, offset, preferences.pageSize],
  );
  const papers = usePapers(gateway, paperQuery);

  /** Write one filter back to the URL, resetting paging. */
  const setFilter = useCallback(
    (patch: Record<string, string>) => {
      const next = new URLSearchParams(params);
      for (const [key, value] of Object.entries(patch)) {
        if (value) next.set(key, value);
        else next.delete(key);
      }
      next.delete("offset");
      setParams(next, { replace: true });
    },
    [params, setParams],
  );

  const setOffset = useCallback(
    (value: number) => {
      const next = new URLSearchParams(params);
      if (value > 0) next.set("offset", String(value));
      else next.delete("offset");
      setParams(next, { replace: true });
    },
    [params, setParams],
  );

  // The server already applied every filter and the ordering, so the loaded page
  // is rendered as-is. `placeholderData: previous` keeps the old rows on screen
  // while the next page loads, which is why `rows` must stay the *server's* list.
  const rows = papers.data?.papers ?? [];

  /** Replace the whole filter value in one write, as the shared bar reports patches. */
  const onFiltersChange = useCallback(
    (patch: Partial<PaperFilterValue>) => {
      const next: Record<string, string> = {};
      if (patch.seriesKey !== undefined) next.series = patch.seriesKey;
      if (patch.year !== undefined) next.year = patch.year;
      if (patch.subject !== undefined) next.subject = patch.subject;
      if (patch.query !== undefined) next.q = patch.query;
      setFilter(next);
    },
    [setFilter],
  );

  const selectedOnPage = rows.filter((paper) => selection.isSelected(paper.natural_key)).length;
  const allOnPageSelected = rows.length > 0 && selectedOnPage === rows.length;

  function addPageToDraft() {
    const added = selection.addMany(rows);
    toast.notify(added ? `已加入本页 ${added} 套` : "本页套卷都已在组卷中");
  }

  function togglePageSelection() {
    if (allOnPageSelected) {
      selection.removeMany(rows.map((paper) => paper.natural_key));
      toast.notify(`已从组卷移除本页 ${rows.length} 套`);
      return;
    }
    const added = selection.addMany(rows);
    toast.notify(added ? `已加入本页 ${added} 套` : "本页套卷都已在组卷中");
  }

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div>
          <span className="eyebrow">PAPER CATALOG</span>
          <h2>套卷列表</h2>
          <p>按系列、年份、科目筛选套卷并加入组卷。</p>
        </div>
        <div className="page-title-actions">
          <Button
            icon={<ListPlus size={15} />}
            onClick={addPageToDraft}
            disabled={!rows.length || allOnPageSelected}
          >
            本页加入组卷
          </Button>
          <Button
            icon={<RefreshCw size={15} className={papers.isFetching ? "is-spinning" : undefined} />}
            onClick={() => void papers.refetch()}
            disabled={papers.isFetching}
          >
            刷新
          </Button>
          <Button variant="primary" icon={<FileArchive size={16} />} onClick={selection.openCompose}>
            打开组卷{selection.selectedCount ? ` · ${selection.selectedCount}` : ""}
          </Button>
        </div>
      </div>

      <PaperFilters
        value={{ year, subject, seriesKey, query }}
        series={series}
        years={years}
        onChange={onFiltersChange}
        order={order}
        onOrderChange={(nextOrder) => setFilter({ order: nextOrder === "series" ? "" : nextOrder })}
        trailing={
          <span className="tool-count">
            {papers.isFetching
              ? "读取中…"
              : `${papers.data?.total ?? 0} 套${selection.selectedCount ? ` · 已选 ${selection.selectedCount}` : ""}`}
          </span>
        }
      />

      {papers.isError ? (
        <Surface className="inline-error">
          <strong>读取套卷失败</strong>
          <span>{papers.error instanceof Error ? papers.error.message : "未知错误"}</span>
        </Surface>
      ) : null}

      <Surface className="paper-table">
        {rows.length ? (
          <div className="table-bulk-bar">
            <label className="check-field">
              <input
                type="checkbox"
                checked={allOnPageSelected}
                onChange={togglePageSelection}
                aria-label={allOnPageSelected ? "取消选择本页" : "选择本页全部"}
              />
              <span>
                {allOnPageSelected ? "取消选择本页" : `选择本页全部（${rows.length}）`}
              </span>
            </label>
            {selectedOnPage ? (
              <Button
                size="sm"
                variant="quiet"
                icon={<Trash2 size={13} />}
                onClick={() => {
                  selection.removeMany(rows.map((paper) => paper.natural_key));
                  toast.notify(`已从组卷移除本页 ${selectedOnPage} 套`);
                }}
              >
                移除本页已选（{selectedOnPage}）
              </Button>
            ) : null}
          </div>
        ) : null}
        <div className="paper-table-scroll">
          <table>
            <thead>
              <tr>
                <th className="paper-table-check" aria-label="选择" />
                <th>套卷</th>
                <th>年份</th>
                <th>科目</th>
                <th>系列 ID</th>
                <th>题目</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((paper) => (
                <PaperRow
                  key={paper.natural_key}
                  paper={paper}
                  selected={selection.isSelected(paper.natural_key)}
                  onToggle={selection.toggle}
                  onOpen={selection.openDetail}
                />
              ))}
            </tbody>
          </table>
          {!rows.length && !papers.isLoading ? (
            <EmptyState
              icon={<BookOpenText size={20} />}
              title="没有匹配的套卷"
              hint={query ? "换一个关键词，或清除筛选条件" : "调整筛选条件后再试"}
            />
          ) : null}
        </div>
      </Surface>

      <Pager
        offset={offset}
        count={rows.length}
        total={papers.data?.total ?? 0}
        pageSize={preferences.pageSize}
        onChange={setOffset}
        disabled={papers.isFetching}
      />

      {selection.detail ? (
        <PaperDetailDrawer paper={selection.detail} gateway={gateway} onClose={() => selection.openDetail(null)} />
      ) : null}
    </div>
  );
}

function PaperRow({
  paper,
  selected,
  onToggle,
  onOpen,
}: {
  paper: PaperSummary;
  selected: boolean;
  onToggle: (paper: PaperSummary) => void;
  onOpen: (paper: PaperSummary) => void;
}) {
  return (
    <tr className={classNames(selected && "is-selected")}>
      <td className="paper-table-check">
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onToggle(paper)}
          aria-label={`选择 ${paper.natural_key}`}
        />
      </td>
      <td>
        <div className="paper-table-title">
          <span className={classNames("subject-mark", paper.subject)}>{paper.subject.replace("math", "数")}</span>
          <span>
            <strong>
              {paper.series_name} 第 {paper.paper_no} 套
            </strong>
            <small>{paper.natural_key}</small>
          </span>
        </div>
      </td>
      <td data-label="年份">{paper.year}</td>
      <td data-label="科目">{subjectNames[paper.subject]}</td>
      <td data-label="系列" className="paper-table-id">{paper.series_key}</td>
      <td data-label="题目">
        <span className="paper-question-count">
          <BookOpenText size={14} />
          {paper.question_count}
        </span>
      </td>
      <td>
        <div className="row-actions">
          <Button size="sm" variant="quiet" onClick={() => onOpen(paper)}>
            查看
          </Button>
          <Button
            size="sm"
            variant={selected ? "primary" : "default"}
            icon={selected ? <Check size={14} /> : <Plus size={14} />}
            onClick={() => onToggle(paper)}
          >
            {selected ? "已选" : "加入组卷"}
          </Button>
        </div>
      </td>
    </tr>
  );
}
