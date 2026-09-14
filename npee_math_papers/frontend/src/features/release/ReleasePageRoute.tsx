/**
 * Release manifest: the pinned content hash of every paper.
 *
 * Exposes the ``/release`` endpoint (previously unused). Being able to see the
 * library hash and search individual keys is what makes "why did this
 * composition refuse to compile?" answerable without a terminal.
 */

import { Copy, Search, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";

import { useReleaseManifest } from "../../application/query/hooks";
import { useAppServices } from "../../app/AppServices";
import { Button, EmptyState, Surface, SurfaceHeading, TextField } from "../../shared/ui";
import { useToast } from "../../shared/ui";

export default function ReleasePageRoute() {
  const { gateway } = useAppServices();
  const manifest = useReleaseManifest(gateway);
  const toast = useToast();
  const [filter, setFilter] = useState("");

  const entries = useMemo(() => {
    const papers = manifest.data?.papers ?? {};
    const rows = Object.entries(papers).map(([naturalKey, contentHash]) => ({ naturalKey, contentHash }));
    const needle = filter.trim().toLowerCase();
    const filtered = needle
      ? rows.filter((row) => row.naturalKey.toLowerCase().includes(needle) || row.contentHash.includes(needle))
      : rows;
    return filtered.sort((left, right) => left.naturalKey.localeCompare(right.naturalKey));
  }, [manifest.data?.papers, filter]);

  async function copyHash(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      toast.notify("已复制哈希");
    } catch {
      toast.notify("复制失败：浏览器禁止访问剪贴板", "error");
    }
  }

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div>
          <span className="eyebrow">RELEASE MANIFEST</span>
          <h2>版本清单</h2>
          <p>每套卷在最近一次发布中的内容哈希；组卷编译按此绑定版本。</p>
        </div>
      </div>

      <div className="metric-grid">
        <div className="metric-card">
          <span className="metric-icon metric-green">
            <ShieldCheck size={18} />
          </span>
          <div>
            <small>库级哈希</small>
            <strong className="hash-value">{manifest.data?.library_hash.slice(0, 12) ?? "—"}</strong>
            <span>{manifest.data ? `${manifest.data.paper_count} 套已封印` : ""}</span>
          </div>
        </div>
        <div className="metric-card">
          <span className="metric-icon metric-blue">
            <ShieldCheck size={18} />
          </span>
          <div>
            <small>已封印套卷</small>
            <strong>{manifest.data?.paper_count ?? "—"}</strong>
            <span>schema {manifest.data?.schema_version ?? "—"}</span>
          </div>
        </div>
      </div>

      <Surface>
        <SurfaceHeading
          eyebrow="PAPER HASHES"
          title="套卷哈希"
          count={entries.length}
          actions={
            <TextField
              label=""
              wrapperClassName="tool-field"
              id="release-filter"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              placeholder="按自然键或哈希筛选"
            />
          }
        />
        <div className="hash-table">
          <div className="hash-table-head">
            <span>自然键</span>
            <span>内容哈希</span>
            <span />
          </div>
          {entries.map((row) => (
            <div className="hash-table-row" key={row.naturalKey}>
              <span className="hash-key">{row.naturalKey}</span>
              <code className="hash-value">{row.contentHash}</code>
              <Button size="sm" variant="quiet" icon={<Copy size={13} />} onClick={() => void copyHash(row.contentHash)}>
                复制
              </Button>
            </div>
          ))}
          {!entries.length && !manifest.isLoading ? (
            <EmptyState icon={<Search size={20} />} title="没有匹配的套卷" hint="清空筛选条件查看全部" />
          ) : null}
        </div>
      </Surface>
    </div>
  );
}
