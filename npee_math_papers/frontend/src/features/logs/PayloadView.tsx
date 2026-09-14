/**
 * Request/response body viewer for the activity log.
 *
 * Bodies arrive as parsed JSON (or plain text, or a size-only note for binary
 * content), so this renders a foldable tree rather than a wall of text: the log's
 * whole purpose is answering "what did this call actually send and return", and
 * a raw blob makes that harder, not easier.
 *
 * Large bodies are already trimmed server-side with explicit "…（另 N 项）"
 * markers, so this viewer never has to defend against an unbounded payload.
 */

import { ChevronDown, ChevronRight, Copy } from "lucide-react";
import { useState } from "react";

import type { EventPayload } from "../../domain/catalog/models";
import { IconButton, classNames, useToast } from "../../shared/ui";

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Compact one-line rendering of a leaf value. */
function Leaf({ value }: { value: unknown }) {
  if (value === null) return <span className="pv-null">null</span>;
  if (value === undefined) return <span className="pv-null">—</span>;
  if (typeof value === "boolean") return <span className="pv-bool">{String(value)}</span>;
  if (typeof value === "number") return <span className="pv-num">{value}</span>;
  const text = String(value);
  return <span className="pv-str">{text}</span>;
}

function Node({ name, value, depth }: { name?: string; value: unknown; depth: number }) {
  // Top two levels start open (that is where the identifying fields live); deeper
  // ones stay folded so a big payload does not bury the rest of the log.
  const [open, setOpen] = useState(depth < 2);
  const nester = isPlainObject(value)
    ? { label: `{${Object.keys(value).length}}`, entries: Object.entries(value) }
    : Array.isArray(value)
      ? { label: `[${value.length}]`, entries: value.map((item, index) => [String(index), item] as [string, unknown]) }
      : null;

  if (!nester) {
    return (
      <div className="pv-row" style={{ paddingLeft: depth * 12 }}>
        {name !== undefined ? <span className="pv-key">{name}</span> : null}
        <Leaf value={value} />
      </div>
    );
  }

  return (
    <div className="pv-branch">
      <button
        type="button"
        className="pv-row pv-row-toggle"
        style={{ paddingLeft: depth * 12 }}
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
      >
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        {name !== undefined ? <span className="pv-key">{name}</span> : null}
        <span className="pv-count">{nester.label}</span>
      </button>
      {open ? (
        <div className="pv-children">
          {nester.entries.map(([key, item]) => (
            <Node key={key} name={key} value={item} depth={depth + 1} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function PayloadView({
  title,
  payload,
  tone,
}: {
  title: string;
  payload: EventPayload | undefined;
  tone: "request" | "response";
}) {
  const toast = useToast();

  if (!payload || (!payload.json && !payload.text && !payload.binary)) {
    return (
      <section className={classNames("payload", `payload-${tone}`, "is-empty")}>
        <header className="payload-head">
          <span className="payload-title">{title}</span>
          <span className="payload-meta">无内容</span>
        </header>
      </section>
    );
  }

  const meta = [
    payload.content_type,
    payload.bytes !== undefined ? `${payload.bytes.toLocaleString("zh-CN")} 字节` : null,
  ]
    .filter(Boolean)
    .join(" · ");
  // Captured in a local so the async copy handler does not have to re-narrow the
  // optional prop (TypeScript cannot carry the narrowing into a callback).
  const body = payload;

  async function copy() {
    const text = body.text ?? JSON.stringify(body.json, null, 2);
    try {
      await navigator.clipboard.writeText(text);
      toast.notify(`${title}已复制`);
    } catch {
      toast.notify("复制失败：浏览器禁止访问剪贴板", "error");
    }
  }

  return (
    <section className={classNames("payload", `payload-${tone}`)}>
      <header className="payload-head">
        <span className="payload-title">{title}</span>
        <span className="payload-meta">{meta || (payload.binary ? "二进制" : "")}</span>
        <IconButton label={`复制${title}`} size="sm" onClick={() => void copy()}>
          <Copy size={12} />
        </IconButton>
      </header>
      <div className="payload-body">
        {payload.binary ? (
          <p className="payload-binary">
            二进制内容（{payload.content_type || "未知类型"}），已记录大小但未保存正文。
          </p>
        ) : payload.text !== undefined ? (
          <pre className="pv-text">{payload.text}</pre>
        ) : (
          <Node value={payload.json} depth={0} />
        )}
      </div>
    </section>
  );
}
