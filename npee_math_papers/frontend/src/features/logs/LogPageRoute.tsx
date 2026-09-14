/**
 * Activity log: MCP tool calls and HTTP requests on one timeline.
 *
 * Reads through the query cache, so the auto-refresh interval is a preference
 * rather than a hard-coded 3 seconds, and a background refresh never resets the
 * open detail rows.
 */

import { AlertCircle, Check, ChevronDown, ChevronRight, RefreshCw, Trash2, Zap } from "lucide-react";
import { useMemo, useState } from "react";

import { useClearLogs, useLogs } from "../../application/query/hooks";
import { useAppServices } from "../../app/AppServices";
import type { LogEvent } from "../../domain/catalog/models";
import { usePreferences } from "../../preferences";
import { Button, ConfirmDialog, EmptyState, IconButton, Segmented, Surface, TextField, classNames, useToast } from "../../shared/ui";
import { PayloadView } from "./PayloadView";
import { formatDuration, formatTime } from "./format";

type OutcomeFilter = "all" | "ok" | "error";
type SurfaceFilter = "all" | "mcp" | "http";

const SURFACE_LABEL: Record<string, string> = { mcp: "MCP 工具", http: "HTTP 请求" };

/** HTTP verbs get a fixed colour per method, so a scan finds the writes first. */
const METHOD_CLASS: Record<string, string> = {
  GET: "method-get",
  POST: "method-post",
  PUT: "method-put",
  PATCH: "method-patch",
  DELETE: "method-delete",
};

const OUTCOME_OPTIONS = [
  { value: "all", label: "全部" },
  { value: "ok", label: "成功" },
  { value: "error", label: "失败" },
] as const;

const SURFACE_OPTIONS = [
  { value: "all", label: "全部来源" },
  { value: "mcp", label: "MCP" },
  { value: "http", label: "HTTP" },
] as const;

/**
 * React keys that survive the 3-second auto-refresh.
 *
 * The previous key carried the row index, so each new event shifted every index
 * and React remounted the list — collapsing whatever row the user had expanded.
 * `ts` has millisecond precision, so it identifies an event on its own; the
 * occurrence counter only disambiguates genuine duplicates within one render,
 * and is assigned in list order so it does not shift when new events arrive.
 */
export function eventKeys(events: LogEvent[]): string[] {
  const seen = new Map<string, number>();
  return events.map((event) => {
    const base = `${event.ts}|${event.name}`;
    const occurrence = seen.get(base) ?? 0;
    seen.set(base, occurrence + 1);
    return occurrence === 0 ? base : `${base}#${occurrence}`;
  });
}

export default function LogPageRoute() {
  const { gateway } = useAppServices();
  const { preferences } = usePreferences();
  const toast = useToast();
  const [surface, setSurface] = useState<SurfaceFilter>("all");
  const [outcome, setOutcome] = useState<OutcomeFilter>("all");
  const [query, setQuery] = useState("");
  const [confirmClear, setConfirmClear] = useState(false);

  const filters = useMemo(
    () => ({
      limit: 300,
      surface: surface === "all" ? undefined : surface,
      status: outcome === "all" ? undefined : outcome,
      q: query.trim() || undefined,
    }),
    [surface, outcome, query],
  );
  const logs = useLogs(gateway, filters, preferences.logRefreshSeconds);
  const clearLogs = useClearLogs(gateway);

  const events = logs.data?.events ?? [];
  const keys = useMemo(() => eventKeys(events), [events]);
  const summary = useMemo(
    () => ({
      mcp: events.filter((event) => event.surface === "mcp").length,
      http: events.filter((event) => event.surface === "http").length,
      errors: events.filter((event) => event.status === "error").length,
      slow: events.filter((event) => (event.duration_ms ?? 0) >= 1500).length,
      // Only HTTP events carry a status code; the split by class is what makes
      // "is anything 500ing?" a one-glance question.
      server5xx: events.filter((event) => (event.status_code ?? 0) >= 500).length,
      client4xx: events.filter((event) => 400 <= (event.status_code ?? 0) && (event.status_code ?? 0) < 500).length,
      withBody: events.filter(
        (event) => event.request?.json || event.request?.text || event.response?.json || event.response?.text,
      ).length,
    }),
    [events],
  );

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div>
          <span className="eyebrow">ACTIVITY LOG</span>
          <h2>操作日志</h2>
          <p>统一查看 Agent 的 MCP 工具调用与前端发起的 HTTP 请求。</p>
        </div>
        <div className="page-title-actions">
          <Button
            icon={<RefreshCw size={15} className={logs.isFetching ? "is-spinning" : undefined} />}
            onClick={() => void logs.refetch()}
            disabled={logs.isFetching}
          >
            刷新
          </Button>
          <IconButton
            label="清空日志"
            tone="danger"
            onClick={() => setConfirmClear(true)}
          >
            <Trash2 size={16} />
          </IconButton>
        </div>
      </div>

      <section className="metric-grid">
        <div className="metric-card">
          <span className="metric-icon metric-blue">
            <Zap size={18} />
          </span>
          <div>
            <small>日志文件事件总数</small>
            <strong>{logs.data?.stats.events ?? events.length}</strong>
            <span>{logs.data ? `${(logs.data.stats.bytes / 1024).toFixed(1)} KB` : ""}</span>
          </div>
        </div>
        <div className="metric-card">
          <span className="metric-icon metric-green">
            <Check size={18} />
          </span>
          <div>
            <small>本窗口 MCP / HTTP</small>
            <strong>
              {summary.mcp}
              <span className="metric-split"> / {summary.http}</span>
            </strong>
            <span>其中 {summary.withBody} 条含正文</span>
          </div>
        </div>
        <div className="metric-card">
          <span className="metric-icon metric-red">
            <AlertCircle size={18} />
          </span>
          <div>
            <small>失败</small>
            <strong>{summary.errors}</strong>
            <span>
              {summary.server5xx} 个 5xx · {summary.client4xx} 个 4xx
            </span>
          </div>
        </div>
        <div className="metric-card">
          <span className="metric-icon metric-amber">
            <Zap size={18} />
          </span>
          <div>
            <small>慢调用 ≥1.5s</small>
            <strong>{summary.slow}</strong>
          </div>
        </div>
      </section>

      <div className="catalog-tools">
        <TextField
          label=""
          wrapperClassName="tool-field tool-field-grow"
          id="log-search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="搜索工具名、路径或请求/响应正文"
        />
        <Segmented label="按来源筛选" options={SURFACE_OPTIONS} value={surface} onChange={setSurface} />
        <Segmented label="按结果筛选" options={OUTCOME_OPTIONS} value={outcome} onChange={setOutcome} />
        <span className="tool-count">{events.length} 条</span>
      </div>

      {logs.isError ? <p className="muted-line is-error">读取日志失败：{String(logs.error)}</p> : null}

      <Surface className="log-list">
        <ul>
          {events.map((event, index) => (
            <EventRow key={keys[index]} event={event} />
          ))}
          {!events.length && !logs.isLoading ? <EmptyState title="暂无日志记录" hint="操作后这里会出现调用记录" /> : null}
        </ul>
      </Surface>

      <ConfirmDialog
        open={confirmClear}
        title="清空全部操作日志？"
        message={
          <>
            将删除日志文件中的 {logs.data?.stats.events ?? events.length} 条记录，包含 Agent 的 MCP 调用与前端请求，此操作无法撤销。
          </>
        }
        confirmLabel="清空"
        onCancel={() => setConfirmClear(false)}
        onConfirm={() => {
          setConfirmClear(false);
          clearLogs.mutate(undefined, {
            onSuccess: () => toast.notify("日志已清空"),
            onError: (error) => toast.notify(error instanceof Error ? error.message : "清空失败", "error"),
          });
        }}
      />
    </div>
  );
}

function EventRow({ event }: { event: LogEvent }) {
  const [open, setOpen] = useState(false);
  const isError = event.status === "error";
  const isSlow = (event.duration_ms ?? 0) >= 1500;
  const detailEntries = Object.entries(event.detail ?? {});
  const hasDetail = detailEntries.length > 0;
  const hasPayload = Boolean(event.request?.json || event.request?.text || event.request?.binary || event.response?.json || event.response?.text || event.response?.binary);
  const expandable = hasDetail || hasPayload;

  // HTTP rows carry a method badge and a real status code; MCP rows carry the
  // tool name. Splitting the label this way is what makes the two surfaces
  // distinguishable at a glance instead of both reading as a bare string.
  const isHttp = event.surface === "http";
  const [method, ...pathParts] = isHttp ? event.name.split(" ") : [];
  const path = pathParts.join(" ");
  const statusCode = event.status_code ?? null;
  const codeTone = statusCode === null ? "" : statusCode >= 500 ? "code-5xx" : statusCode >= 400 ? "code-4xx" : "code-2xx";

  return (
    <li
      className={classNames(
        "log-row",
        `surface-${event.surface}`,
        isError && "is-error",
        isSlow && "is-slow",
      )}
    >
      <button
        className="log-row-head"
        onClick={() => setOpen((value) => !value)}
        disabled={!expandable}
        aria-expanded={expandable ? open : undefined}
      >
        <span className="log-caret">
          {expandable ? open ? <ChevronDown size={14} /> : <ChevronRight size={14} /> : <span className="log-caret-dot" />}
        </span>
        <span className={classNames("log-surface", `log-surface-${event.surface}`)}>{SURFACE_LABEL[event.surface] || event.surface}</span>
        {isHttp ? (
          <>
            <span className={classNames("log-method", METHOD_CLASS[method] ?? "method-other")}>{method}</span>
            <span className="log-name log-name-path">{path}</span>
          </>
        ) : (
          <>
            <span className="log-cell log-cell-method" />
            <span className="log-name log-name-tool">{event.name}</span>
          </>
        )}
        {isSlow ? (
          <span className="log-badge log-badge-slow">
            <Zap size={11} />慢
          </span>
        ) : (
          // Every row emits the same cells, empty ones included, so the columns
          // line up across MCP and HTTP rows instead of shifting per surface.
          <span className="log-cell log-cell-slow" />
        )}
        {statusCode !== null ? (
          <span className={classNames("log-code", codeTone)}>{statusCode}</span>
        ) : (
          <span className="log-code" />
        )}
        <span className={classNames("log-status", `log-status-${isError ? "error" : "ok"}`)}>
          {isError ? <AlertCircle size={12} /> : <Check size={12} />}
          {isError ? "失败" : "成功"}
        </span>
        <span className="log-duration">{formatDuration(event.duration_ms)}</span>
        <span className="log-time">{formatTime(event.ts)}</span>
      </button>
      {open ? (
        <div className="log-detail">
          {hasDetail ? (
            <div className="log-detail-meta">
              {detailEntries.map(([key, value]) => (
                <div className="log-detail-row" key={key}>
                  <span className="log-detail-key">{key}</span>
                  <span className="log-detail-value">
                    {typeof value === "object" && value !== null ? JSON.stringify(value, null, 2) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          ) : null}
          {hasPayload ? (
            <div className="payload-grid">
              <PayloadView title="请求体" payload={event.request} tone="request" />
              <PayloadView title="响应体" payload={event.response} tone="response" />
            </div>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}
