"""事件日志：跨进程汇总 HTTP 请求与 MCP 工具调用。

问题
----
MCP 服务与 API 服务是两个独立进程，内存缓冲无法共享。前端要统一查看「工具调用」，
就需要一个进程外的共同落点。

方案
----
追加式 JSONL（``.npee-math-papers/logs/events.jsonl``）：

- 每个进程各自追加一行事件，天然支持并发追加（单行写入 + 足够小的行）；
- 读取时按时间倒序返回尾部若干条，超量自动截断，避免前端一次拉全量；
- 日志按大小轮转，保留 ``events.jsonl`` 与 ``events.1.jsonl``，防止无限增长；
- 该目录被 git 忽略，不污染仓库。

事件结构（单行 JSON）::

    {
      "ts": "2026-09-13T02:48:02.123Z",   # UTC ISO8601
      "surface": "http" | "mcp",           # 来源表面
      "kind": "request" | "tool",          # 事件类型
      "name": "GET /api/papers" | "npee_list_papers",
      "status": "ok" | "error",
      "status_code": 200,                  # 仅 HTTP：真实状态码
      "duration_ms": 12.3,
      "detail": { ... },                   # 元信息：query、慢请求、错误等
      "request": { ... },                  # 请求体 / 工具入参
      "response": { ... }                  # 响应体 / 工具返回值
    }

``request`` / ``response`` 是同一种结构（见 :class:`Payload`）：既保留解析后的
JSON（便于前端折叠查看），也记录原始字节数与是否被截断，因此在日志页能直接看到
「这次调用到底发了什么、回了什么」。二进制响应（如 PDF 产物）只记录大小与类型，
不会把文件内容写进日志。

本模块是纯标准库实现，可被 API、MCP 与维护脚本共同导入。
"""

from __future__ import annotations

from collections import deque
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# 单文件上限（字节）：超过则轮转到 events.1.jsonl。
MAX_BYTES = 4 * 1024 * 1024
# 读取时最多返回的事件条数。
MAX_READ = 2000
# 单条事件 detail 的最大字符数，防止把巨大载荷写进日志。
MAX_DETAIL_CHARS = 2000
# 单侧载荷（请求体或响应体）保存的最大字符数。
MAX_PAYLOAD_CHARS = 6000
# 载荷内单个字符串保留的最大长度。
MAX_PAYLOAD_STRING = 400
# 载荷内集合（列表 / 字典）保留的最大条目数。
MAX_PAYLOAD_ITEMS = 40


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class Event:
    """一条日志事件。"""

    ts: str
    surface: str
    kind: str
    name: str
    status: str = "ok"
    duration_ms: float | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    request: dict[str, Any] = field(default_factory=dict)
    response: dict[str, Any] = field(default_factory=dict)
    # HTTP 的真实状态码；MCP 事件为 None。
    status_code: int | None = None
    # 冗余的毫秒时间戳，前端无需解析时间字符串即可排序与分桶。
    epoch_ms: int | None = None

    def to_line(self) -> str:
        payload: dict[str, Any] = {
            "ts": self.ts,
            "surface": self.surface,
            "kind": self.kind,
            "name": self.name,
            "status": self.status,
        }
        if self.status_code is not None:
            payload["status_code"] = self.status_code
        if self.epoch_ms is not None:
            payload["epoch_ms"] = self.epoch_ms
        if self.duration_ms is not None:
            payload["duration_ms"] = round(self.duration_ms, 1)
        if self.detail:
            payload["detail"] = self.detail
        if self.request:
            payload["request"] = self.request
        if self.response:
            payload["response"] = self.response
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_line(cls, line: str) -> "Event | None":
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(raw, dict):
            return None
        status_code = raw.get("status_code")
        epoch_ms = raw.get("epoch_ms")
        return cls(
            ts=str(raw.get("ts", "")),
            surface=str(raw.get("surface", "unknown")),
            kind=str(raw.get("kind", "event")),
            name=str(raw.get("name", "")),
            status=str(raw.get("status", "ok")),
            duration_ms=raw.get("duration_ms") if isinstance(raw.get("duration_ms"), (int, float)) else None,
            detail=raw.get("detail") if isinstance(raw.get("detail"), dict) else {},
            request=raw.get("request") if isinstance(raw.get("request"), dict) else {},
            response=raw.get("response") if isinstance(raw.get("response"), dict) else {},
            status_code=status_code if isinstance(status_code, int) else None,
            epoch_ms=epoch_ms if isinstance(epoch_ms, int) else None,
        )


def _truncate_detail(detail: dict[str, Any]) -> dict[str, Any]:
    """把 detail 压缩到可读、可控的大小。"""

    # `detail` is metadata (query string, slow flag, error text), never the body
    # itself — bodies go through `build_payload`, which trims structurally.

    text = json.dumps(detail, ensure_ascii=False)
    if len(text) <= MAX_DETAIL_CHARS:
        return detail
    return {"_truncated": True, "preview": text[:MAX_DETAIL_CHARS]}


def _snip(value: str, limit: int = MAX_PAYLOAD_STRING) -> str:
    """Shorten a string, marking that it was shortened."""

    if len(value) <= limit:
        return value
    return value[:limit] + f"…（另 {len(value) - limit} 字符）"


def _trim_payload(value: Any, *, depth: int = 0) -> Any:
    """Recursively shrink a decoded payload to a loggable size.

    Trimming is *structural* rather than a truncation of the serialised JSON: one
    enormous ``stem.text`` must not swallow the rest of the object, so long
    strings are snipped in place and long collections are cut with an explicit
    count. The result stays valid JSON the log page can fold open, which a
    mid-string cut would not.
    """

    if depth > 6:
        return "…（层级过深）"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _snip(value)
    if isinstance(value, (list, tuple)):
        items = [_trim_payload(item, depth=depth + 1) for item in value[:MAX_PAYLOAD_ITEMS]]
        if len(value) > MAX_PAYLOAD_ITEMS:
            items.append(f"…（另 {len(value) - MAX_PAYLOAD_ITEMS} 项）")
        return items
    if isinstance(value, dict):
        trimmed: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= MAX_PAYLOAD_ITEMS:
                trimmed["…"] = f"（另 {len(value) - MAX_PAYLOAD_ITEMS} 个键）"
                break
            trimmed[str(key)] = _trim_payload(item, depth=depth + 1)
        return trimmed
    return _snip(str(value))


def build_payload(
    value: Any,
    *,
    content_type: str = "",
    raw_bytes: int | None = None,
) -> dict[str, Any]:
    """Describe one request or response body for the log.

    Returns ``{}`` when there is nothing worth recording, so a bare GET does not
    grow the log. Non-text bodies (PDFs, images) are summarised by size and type
    only: the log must never become a second copy of the artifact store.
    """

    if value is None and not raw_bytes:
        return {}

    payload: dict[str, Any] = {}
    media_type = content_type.split(";")[0].strip().lower()
    if media_type:
        payload["content_type"] = media_type

    if value is None:
        # Binary or otherwise unparsed: size only.
        payload["bytes"] = raw_bytes or 0
        payload["binary"] = True
        return payload

    if isinstance(value, str):
        payload["text"] = _snip(value)
        if raw_bytes is not None:
            payload["bytes"] = raw_bytes
        return payload

    trimmed = _trim_payload(value)
    serialised = json.dumps(trimmed, ensure_ascii=False)
    if len(serialised) > MAX_PAYLOAD_CHARS:
        # Still oversized after structural trimming (a very wide table, say):
        # keep a preview and say so, rather than emitting an unreadable blob.
        payload["json"] = {"_trimmed": True, "preview": serialised[:MAX_PAYLOAD_CHARS]}
    else:
        payload["json"] = trimmed
    if raw_bytes is not None:
        payload["bytes"] = raw_bytes
    return payload


def decode_body(body: bytes, content_type: str = "") -> tuple[Any, int]:
    """Decode a body for logging, or return ``(None, size)`` when it is binary.

    JSON is parsed (the log page renders it as a tree); any other valid UTF-8
    text is kept as text; everything else is reported by size only.
    """

    size = len(body)
    if not body:
        return None, 0
    media_type = content_type.split(";")[0].strip().lower()
    looks_json = "json" in media_type or body.lstrip()[:1] in (b"{", b"[")
    if looks_json:
        try:
            return json.loads(body), size
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    if media_type.startswith("text/") or media_type in ("application/x-www-form-urlencoded", ""):
        try:
            return body.decode("utf-8"), size
        except UnicodeDecodeError:
            pass
    return None, size


def _matches_query(event: Event, query: str) -> bool:
    """Return whether the free-text filter matches this event.

    The search covers the name *and* the recorded bodies, so "查一下哪个请求带了
    math3" works — searching only the name would miss exactly the cases the body
    capture exists for.
    """

    needle = query.lower()
    if needle in event.name.lower():
        return True
    for part in (event.detail, event.request, event.response):
        if part and needle in json.dumps(part, ensure_ascii=False).lower():
            return True
    return False


class EventLog:
    """追加式事件日志。

    线程安全：追加使用全局锁，保证同一进程内多线程写行不交错。跨进程追加依赖
    单行写入较小（远小于系统 PIPE_BUF 与文件块），在本地单机场景足够可靠。
    """

    _lock = threading.Lock()

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: Event) -> None:
        """追加一条事件，必要时轮转。"""

        line = event.to_line() + "\n"
        with self._lock:
            try:
                if self.path.is_file() and self.path.stat().st_size + len(line.encode("utf-8")) > MAX_BYTES:
                    rotated = self.path.with_suffix(".1.jsonl")
                    if rotated.exists():
                        rotated.unlink()
                    os.replace(self.path, rotated)
                with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(line)
            except OSError:
                # 日志失败绝不能影响主流程。
                pass

    def record(
        self,
        *,
        surface: str,
        kind: str,
        name: str,
        status: str = "ok",
        duration_ms: float | None = None,
        detail: dict[str, Any] | None = None,
        request: dict[str, Any] | None = None,
        response: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        """便捷方法：构造并追加一条事件。"""

        self.append(
            Event(
                ts=_utc_now(),
                surface=surface,
                kind=kind,
                name=name,
                status=status,
                duration_ms=duration_ms,
                detail=_truncate_detail(detail or {}),
                request=request or {},
                response=response or {},
                status_code=status_code,
                epoch_ms=int(time.time() * 1000),
            )
        )

    def read(
        self,
        *,
        limit: int = 200,
        surface: str | None = None,
        kind: str | None = None,
        status: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        """读取最近事件（新到旧），可按来源/类型/状态/关键字过滤。"""

        limit = max(1, min(int(limit), MAX_READ))
        # Keep a sliding window of the *last* `limit` matches.
        #
        # The previous implementation appended matches until it reached `limit`
        # and stopped, so on a long log it returned the oldest events and
        # reversed them — the page showed day-old traffic while new requests were
        # never displayed. Files are visited oldest-first so the window ends up
        # holding the newest matches, which are then reversed for display.
        window: deque[Event] = deque(maxlen=limit)
        for path in self._files_oldest_first():
            if not path.is_file():
                continue
            try:
                with path.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        event = Event.from_line(line)
                        if event is None:
                            continue
                        if surface and event.surface != surface:
                            continue
                        if kind and event.kind != kind:
                            continue
                        if status and event.status != status:
                            continue
                        if query and not _matches_query(event, query):
                            continue
                        window.append(event)
            except OSError:
                continue
        # 文件内是旧到新；这里整体反转成新到旧。
        events = list(window)
        events.reverse()
        return [
            {
                "ts": event.ts,
                "surface": event.surface,
                "kind": event.kind,
                "name": event.name,
                "status": event.status,
                "status_code": event.status_code,
                "duration_ms": event.duration_ms,
                "detail": event.detail,
                "request": event.request,
                "response": event.response,
            }
            for event in events
        ]

    def stats(self) -> dict[str, Any]:
        """返回日志文件概况，供前端页头展示。"""

        total = 0
        size = 0
        for path in self._files_newest_first():
            if not path.is_file():
                continue
            size += path.stat().st_size
            try:
                with path.open("r", encoding="utf-8") as handle:
                    total += sum(1 for _ in handle)
            except OSError:
                continue
        return {"path": self.path.as_posix(), "events": total, "bytes": size, "max_bytes": MAX_BYTES}

    def clear(self) -> None:
        """清空日志文件（保留归档文件）。"""

        with self._lock:
            if self.path.is_file():
                self.path.write_text("", encoding="utf-8")

    def _files_newest_first(self) -> Iterable[Path]:
        yield self.path
        rotated = self.path.with_suffix(".1.jsonl")
        yield rotated

    def _files_oldest_first(self) -> Iterable[Path]:
        """Yield the rotated archive before the live file.

        Reading in this order is what lets a single bounded window collect the
        newest events without holding the whole log in memory.
        """

        rotated = self.path.with_suffix(".1.jsonl")
        yield rotated
        yield self.path


def default_event_log(repository_root: Path | None = None) -> EventLog:
    """返回默认事件日志位置：``<repo>/.npee-math-papers/logs/events.jsonl``。"""

    base = repository_root or Path(__file__).resolve().parents[2]
    root_env = os.environ.get("NPEE_DATA_ROOT", "").strip()
    data_root = Path(root_env).resolve() if root_env else (base / ".npee-math-papers")
    return EventLog(data_root / "logs" / "events.jsonl")
