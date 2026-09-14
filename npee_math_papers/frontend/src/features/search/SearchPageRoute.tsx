/**
 * Full-library question search.
 *
 * Uses the server-side ``/search`` endpoint (previously unused by the UI), which
 * scans every paper rather than only the current page. Results are paged by the
 * server's ``limit``, and each hit is a link into its paper.
 *
 * A hit opens the *paper detail drawer* on the catalogue (via `paper=<key>`)
 * rather than dropping the user on an unfiltered list: the question they searched
 * for is the thing they want to read, and re-finding it by hand was the previous
 * behaviour.
 */

import { BookOpenText, Search as SearchIcon, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useSearch } from "../../application/query/hooks";
import { useAppServices } from "../../app/AppServices";
import { subjectNames } from "../../domain/catalog/models";
import { Button, EmptyState, IconButton, Surface, TextField } from "../../shared/ui";
import { Tex } from "../../shared/tex/Tex";
import { balancedExcerpt } from "./excerpt";

export default function SearchPageRoute() {
  const { gateway } = useAppServices();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const initial = params.get("q") ?? "";
  // The input is local so typing stays responsive; the committed query drives the request.
  const [draft, setDraft] = useState(initial);
  const query = params.get("q") ?? "";
  const result = useSearch(gateway, query, { limit: 80 });

  // Keep the box in step when the URL changes underneath us (back/forward, or a
  // link into `/search?q=…`), which previously left stale text in the field.
  useEffect(() => {
    setDraft(initial);
  }, [initial]);

  function commit(value: string) {
    const next = new URLSearchParams();
    if (value.trim()) next.set("q", value.trim());
    setParams(next, { replace: true });
  }

  const matches = result.data?.matches ?? [];
  const total = result.data?.total ?? 0;

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div>
          <span className="eyebrow">FULL-TEXT SEARCH</span>
          <h2>题目检索</h2>
          <p>在题干、选项与子问中检索，结果来自全库而非当前页。</p>
        </div>
        {query ? (
          <div className="page-title-actions">
            <Button
              icon={<BookOpenText size={15} />}
              onClick={() => navigate(`/papers?q=${encodeURIComponent(query)}`)}
            >
              在套卷列表中筛选
            </Button>
          </div>
        ) : null}
      </div>

      <form
        className="search-bar surface"
        onSubmit={(event) => {
          event.preventDefault();
          commit(draft);
        }}
      >
        <TextField
          label=""
          wrapperClassName="search-bar-field"
          id="question-search"
          autoFocus
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="输入关键词，例如：级数、连续、特征值"
        />
        {draft ? (
          <IconButton
            label="清空"
            onClick={() => {
              setDraft("");
              commit("");
            }}
          >
            <X size={15} />
          </IconButton>
        ) : null}
        <Button variant="primary" type="submit" icon={<SearchIcon size={15} />}>
          检索
        </Button>
      </form>

      {result.isFetching ? <p className="muted-line">正在检索…</p> : null}
      {result.isError ? <p className="muted-line is-error">检索失败：{String(result.error)}</p> : null}

      {query ? (
        <p className="muted-line">
          命中 <strong>{total}</strong> 条
          {matches.length < total ? `（显示前 ${matches.length} 条，可用更具体的关键词缩小范围）` : ""}
        </p>
      ) : null}

      <Surface className="search-results">
        <ul>
          {matches.map((match) => (
            <li key={`${match.natural_key}-${match.number}`}>
              <button
                type="button"
                className="search-hit"
                onClick={() =>
                  navigate(`/papers?series=${encodeURIComponent(match.series_key)}&paper=${encodeURIComponent(match.natural_key)}`)
                }
              >
                <span className="search-hit-meta">
                  {match.series_name} · 第 {match.paper_no} 套 · 第 {match.number} 题 · {subjectNames[match.subject]}
                </span>
                <span className="search-hit-excerpt">
                  <Tex source={balancedExcerpt(match.excerpt)} />
                </span>
              </button>
            </li>
          ))}
        </ul>
        {query && !matches.length && !result.isFetching ? (
          <EmptyState icon={<BookOpenText size={20} />} title="没有命中题目" hint="换一个更短或更常见的关键词" />
        ) : null}
        {!query ? (
          <EmptyState icon={<SearchIcon size={20} />} title="输入关键词开始检索" hint="检索覆盖题干、选项与子问" />
        ) : null}
      </Surface>
    </div>
  );
}
