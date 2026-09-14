"""请求日志中间件：把每次 HTTP 请求的**请求体与响应体**写入共享事件日志。

前端「操作日志」页读取同一份事件日志，因此人类看到的调用记录与 Agent 的 MCP
调用记录是同一时间线，且两边都能展开查看实际收发的载荷。

为什么是纯 ASGI，而不是 ``BaseHTTPMiddleware``
---------------------------------------------
``BaseHTTPMiddleware`` 用一个「响应包装器」把 body 重新流式化，一旦上游是
``StreamingResponse``，它可能把响应拆成多次发送、丢失 ``Content-Length``，甚至让
后台任务在响应结束后才执行。要读 body 就必须碰这条路径，所以这里直接实现 ASGI
协议：只在 ``http.request`` 消息上做缓冲、在 ``http.response.body`` 上做记录，
不改变消息的顺序与分段之外的任何语义。

载荷记录受 ``events.build_payload`` 约束：JSON 结构化裁剪、二进制只记大小，
因此即使有人 GET 一个 PDF 产物，日志也不会被写爆。
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Awaitable, Callable, Iterable, MutableMapping

from npee_math_papers.service.events import EventLog, build_payload, decode_body

SLOW_REQUEST_SECONDS = 1.5
# 默认不记录这些路径，避免前端轮询把日志刷满。
QUIET_PATHS = {"/api/health", "/api/logs"}
# 太大或明显是流式的响应不缓冲，只记大小。
MAX_CAPTURE_BYTES = 256 * 1024

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


def _should_log(path: str) -> bool:
    if os.environ.get("NPEE_LOG_REQUESTS", "").strip().lower() == "full":
        return True
    return path not in QUIET_PATHS


def _headers(raw: Iterable[tuple[bytes, bytes]]) -> dict[str, str]:
    """Lower-case header names into a plain dict."""

    return {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in raw}


def _request_detail(
    *,
    method: str,
    path: str,
    query: str,
    headers: dict[str, str],
    elapsed_ms: float,
    status_code: int,
) -> dict[str, Any]:
    """Metadata about a request: what it addressed and how it went."""

    detail: dict[str, Any] = {"method": method, "path": path}
    if query:
        detail["query"] = query[:600]
    if elapsed_ms >= SLOW_REQUEST_SECONDS * 1000:
        detail["slow"] = True
    user_agent = headers.get("user-agent")
    if user_agent:
        detail["user_agent"] = user_agent[:160]
    if status_code >= 400:
        detail["status_code"] = status_code
    return detail


class RequestLogMiddleware:
    """纯 ASGI 中间件：记录 ``方法 路径 -> 状态码 耗时`` 以及两侧载荷。"""

    def __init__(self, app: Callable[..., Awaitable[None]], event_log: EventLog) -> None:
        self.app = app
        self.event_log = event_log

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path", ""))
        if not _should_log(path):
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", "GET"))
        query = (scope.get("query_string") or b"").decode("latin-1")
        request_headers = _headers(scope.get("headers") or [])

        # --- buffer the request body, replayed to the app unchanged -----------
        #
        # The body is drained up front whenever the request declares one. Reading
        # it lazily only when the app asks would miss two real cases: an endpoint
        # that ignores its body, and a request rejected during dependency
        # resolution before the handler ever runs — exactly the failures whose
        # payload you most want on record.
        request_chunks: list[bytes] = []
        request_bytes = 0
        buffered: list[Message] = []
        drained = False

        declares_body = "content-length" in request_headers or "transfer-encoding" in request_headers

        async def drain_request() -> None:
            nonlocal drained, request_bytes
            if drained:
                return
            drained = True
            while True:
                message = await receive()
                buffered.append(message)
                if message.get("type") != "http.request":
                    break
                body = message.get("body", b"")
                request_bytes += len(body)
                if len(body) and request_bytes <= MAX_CAPTURE_BYTES:
                    request_chunks.append(body)
                if not message.get("more_body", False):
                    break

        async def receive_wrapper() -> Message:
            if not drained:
                await drain_request()
            if buffered:
                return buffered.pop(0)
            # The app asked for more than the client sent: hand it the standard
            # end-of-body message rather than blocking forever.
            return {"type": "http.request", "body": b"", "more_body": False}

        if declares_body:
            await drain_request()

        # --- capture the response body as it streams out ----------------------
        response_chunks: list[bytes] = []
        response_bytes = 0
        response_status = 0
        response_headers: dict[str, str] = {}

        async def send_wrapper(message: Message) -> None:
            nonlocal response_bytes, response_status, response_headers
            if message.get("type") == "http.response.start":
                response_status = int(message.get("status", 0))
                response_headers = _headers(message.get("headers") or [])
            elif message.get("type") == "http.response.body":
                body = message.get("body", b"")
                response_bytes += len(body)
                if response_bytes <= MAX_CAPTURE_BYTES:
                    response_chunks.append(body)
            await send(message)

        started = time.perf_counter()
        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        except Exception as error:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self._record(
                method=method,
                path=path,
                query=query,
                request_headers=request_headers,
                request_body=b"".join(request_chunks),
                request_bytes=request_bytes,
                response_status=500,
                response_headers={},
                response_body=b"",
                response_bytes=0,
                elapsed_ms=elapsed_ms,
                error=str(error),
            )
            raise

        elapsed_ms = (time.perf_counter() - started) * 1000
        self._record(
            method=method,
            path=path,
            query=query,
            request_headers=request_headers,
            request_body=b"".join(request_chunks),
            request_bytes=request_bytes,
            response_status=response_status,
            response_headers=response_headers,
            response_body=b"".join(response_chunks),
            response_bytes=response_bytes,
            elapsed_ms=elapsed_ms,
            error="",
        )

    def _record(
        self,
        *,
        method: str,
        path: str,
        query: str,
        request_headers: dict[str, str],
        request_body: bytes,
        request_bytes: int,
        response_status: int,
        response_headers: dict[str, str],
        response_body: bytes,
        response_bytes: int,
        elapsed_ms: float,
        error: str,
    ) -> None:
        detail = _request_detail(
            method=method,
            path=path,
            query=query,
            headers=request_headers,
            elapsed_ms=elapsed_ms,
            status_code=response_status,
        )
        if error:
            detail["error"] = error[:300]

        request_value, _ = decode_body(request_body, request_headers.get("content-type", ""))
        response_value, _ = decode_body(response_body, response_headers.get("content-type", ""))

        # A body that was never fully buffered is reported by size only, so the
        # log never claims to show a payload it only partly saw.
        request_payload = build_payload(
            request_value,
            content_type=request_headers.get("content-type", ""),
            raw_bytes=request_bytes,
        ) if request_bytes else {}
        response_payload = build_payload(
            response_value,
            content_type=response_headers.get("content-type", ""),
            raw_bytes=response_bytes,
        ) if response_bytes else {}

        self.event_log.record(
            surface="http",
            kind="request",
            name=f"{method} {path}",
            status="ok" if 0 < response_status < 400 and not error else "error",
            status_code=response_status or None,
            duration_ms=elapsed_ms,
            detail=detail,
            request=request_payload,
            response=response_payload,
        )


def summarize_payload(payload: dict[str, Any]) -> str:
    """One-line summary of a captured payload, for compact log rows."""

    if not payload:
        return ""
    if "binary" in payload:
        return f"{payload.get('content_type', 'binary')} · {payload.get('bytes', 0)} 字节"
    value = payload.get("json", payload.get("text"))
    try:
        text = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(value)
    return text[:120] + ("…" if len(text) > 120 else "")
