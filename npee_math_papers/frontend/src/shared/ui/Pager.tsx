/**
 * Pagination control for server-side paged lists.
 *
 * Takes offset/count/total rather than a page number, because the API pages by
 * offset; deriving the page here keeps that detail out of every page component.
 */

import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "./Button";

export function Pager({
  offset,
  count,
  total,
  pageSize,
  onChange,
  disabled = false,
}: {
  offset: number;
  count: number;
  total: number;
  pageSize: number;
  onChange: (offset: number) => void;
  disabled?: boolean;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const current = Math.floor(offset / pageSize) + 1;
  const first = total === 0 ? 0 : offset + 1;
  const last = offset + count;

  return (
    <nav className="pager" aria-label="分页">
      <Button
        size="sm"
        icon={<ChevronLeft size={15} />}
        disabled={disabled || current <= 1}
        onClick={() => onChange(Math.max(0, offset - pageSize))}
      >
        上一页
      </Button>
      <span className="pager-status">
        第 {current} / {pages} 页 · {first}-{last} / {total}
      </span>
      <Button
        size="sm"
        disabled={disabled || current >= pages}
        onClick={() => onChange(offset + pageSize)}
      >
        下一页
        <ChevronRight size={15} />
      </Button>
    </nav>
  );
}
