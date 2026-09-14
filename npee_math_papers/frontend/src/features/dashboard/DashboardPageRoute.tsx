/**
 * Dashboard: library totals, per-series inventory and the most recent activity.
 *
 * All three panels read from the query cache, so arriving here after browsing
 * the catalogue re-uses the data instead of refetching.
 */

import { Activity, Database, FileArchive, Layers3, ListTree, PanelTop, ScrollText } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useLogs, useOverview, useReleaseManifest } from "../../application/query/hooks";
import { useAppServices } from "../../app/AppServices";
import { usePreferences } from "../../preferences";
import { EmptyState, MetricCard, Surface, SurfaceHeading } from "../../shared/ui";
import { formatDuration, formatRelativeTime } from "../logs/format";

export default function DashboardPageRoute() {
  const { gateway } = useAppServices();
  const { preferences } = usePreferences();
  const navigate = useNavigate();
  const overview = useOverview(gateway);
  const release = useReleaseManifest(gateway);
  const logs = useLogs(gateway, { limit: 6 }, Math.max(preferences.logRefreshSeconds, 5));

  const stats = overview.data?.stats;
  const series = overview.data?.series ?? [];
  const events = logs.data?.events ?? [];

  return (
    <div className="page-stack">
      <section className="metric-grid">
        <MetricCard
          tone="green"
          icon={<Activity size={18} />}
          label="套卷"
          value={stats?.papers ?? "—"}
          detail={`${stats?.bundles ?? 0} 个套卷分组`}
          loading={overview.isLoading}
        />
        <MetricCard
          tone="blue"
          icon={<PanelTop size={18} />}
          label="题目"
          value={stats?.questions ?? "—"}
          detail={`${stats?.figures ?? 0} 个图形`}
          loading={overview.isLoading}
        />
        <MetricCard
          tone="amber"
          icon={<Layers3 size={18} />}
          label="系列"
          value={series.length || "—"}
          detail={(stats?.years ?? []).length ? `${Math.min(...(stats?.years ?? [0]))}–${Math.max(...(stats?.years ?? [0]))}` : ""}
          loading={overview.isLoading}
        />
        <MetricCard
          tone="red"
          icon={<Database size={18} />}
          label="库级哈希"
          value={release.data ? release.data.library_hash.slice(0, 8) : "—"}
          detail={release.data ? `${release.data.paper_count} 套已封印` : ""}
          loading={release.isLoading}
        />
      </section>

      <div className="overview-grid">
        <Surface>
          <SurfaceHeading
            eyebrow="PAPER LIBRARY"
            title="内置题库"
            count={overview.isLoading ? "正在加载" : `${series.length} 个系列`}
            actions={
              <button type="button" className="plain-button" onClick={() => navigate("/papers")}>
                <ListTree size={14} />浏览套卷
              </button>
            }
          />
          <div className="series-table">
            <div className="series-table-head">
              <span>系列</span>
              <span>年份</span>
              <span>套卷</span>
              <span>题目</span>
            </div>
            {series.map((item) => (
              <button
                type="button"
                className="series-table-row"
                key={item.series_key}
                onClick={() => navigate(`/papers?series=${encodeURIComponent(item.series_key)}`)}
              >
                <span className="series-table-name">
                  <span className="catalog-source-dot" />
                  <strong>{item.series_name}</strong>
                  <small>{item.series_key}</small>
                </span>
                <span>{item.years.join(", ")}</span>
                <span>{item.paper_count}</span>
                <span>{item.question_count}</span>
              </button>
            ))}
            {!series.length && !overview.isLoading ? (
              <EmptyState icon={<Database size={20} />} title="题库为空" hint="请先运行迁移或导入题目" />
            ) : null}
          </div>
        </Surface>

        <Surface>
          <SurfaceHeading
            eyebrow="RECENT ACTIVITY"
            title="近期活动"
            actions={
              <button type="button" className="plain-button" onClick={() => navigate("/logs")}>
                <ScrollText size={14} />全部日志
              </button>
            }
          />
          <ul className="activity-list">
            {events.map((event, index) => (
              <li key={`${event.ts}-${index}`} className={event.status === "error" ? "is-error" : ""}>
                <span className={`log-surface log-surface-${event.surface}`}>
                  {event.surface === "mcp" ? "MCP" : "HTTP"}
                </span>
                <span className="activity-name">{event.name}</span>
                <span className="activity-meta">
                  {formatDuration(event.duration_ms)} · {formatRelativeTime(event.ts)}
                </span>
              </li>
            ))}
            {!events.length ? (
              <EmptyState icon={<FileArchive size={20} />} title="暂无活动记录" hint="操作后这里会出现调用记录" />
            ) : null}
          </ul>
        </Surface>
      </div>
    </div>
  );
}
