"""编译任务：把耗时的组卷编译放到后台，用任务 ID 轮询结果。

问题
----
一次组卷编译要跑 XeLaTeX 多趟，通常十几秒到数分钟。MCP 工具是请求/响应式的，
同步等待容易超时，也占住调用方。

方案
----
``CompileJobStore`` 在后台线程里执行编译，立即返回 ``job_id``。调用方随后用
``get(job_id)`` 轮询状态：

    queued -> running -> succeeded | failed

任务状态保存在内存中（进程内），因此 MCP 与 API 各自维护自己的任务表；这足够
覆盖「发起编译 → 轮询 → 取产物」的单次会话流程。产物是磁盘上的 PDF 路径，
跨进程可读，所以任务表本身不需要持久化。

后台线程由 :class:`threading.Thread` 提供，编译期间不阻塞任何请求。
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class CompileJob:
    """一次后台编译任务。"""

    job_id: str
    composition_id: str
    status: str = "queued"
    created_at: str = field(default_factory=_now)
    started_at: str | None = None
    finished_at: str | None = None
    artifacts: list[str] = field(default_factory=list)
    error: str | None = None
    report: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "composition_id": self.composition_id,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "artifacts": list(self.artifacts),
            "error": self.error,
            "report": self.report,
        }


class CompileJobStore:
    """在后台线程执行编译，并跟踪任务状态。"""

    def __init__(self, max_jobs: int = 200) -> None:
        self._jobs: dict[str, CompileJob] = {}
        self._lock = threading.Lock()
        self._max_jobs = max_jobs

    def submit(
        self,
        composition_id: str,
        runner: Callable[[], tuple[bool, list[str], dict[str, Any], str | None]],
    ) -> CompileJob:
        """登记一个任务并立即在后台启动。

        ``runner`` 返回 ``(ok, artifacts, report, error)``。它在后台线程执行，
        异常被捕获并写入任务状态，不会让请求失败。
        """

        job = CompileJob(job_id=uuid.uuid4().hex[:12], composition_id=composition_id)
        with self._lock:
            self._jobs[job.job_id] = job
            self._prune_locked()

        thread = threading.Thread(target=self._run, args=(job, runner), daemon=True, name=f"npee-compile-{job.job_id}")
        thread.start()
        return job

    def _run(self, job: CompileJob, runner: Callable[[], tuple[bool, list[str], dict[str, Any], str | None]]) -> None:
        with self._lock:
            job.status = "running"
            job.started_at = _now()
        try:
            ok, artifacts, report, error = runner()
        except Exception as exc:  # 后台线程内绝不让异常逃逸
            ok, artifacts, report, error = False, [], {}, str(exc)
        with self._lock:
            job.finished_at = _now()
            job.status = "succeeded" if ok else "failed"
            job.artifacts = list(artifacts)
            job.report = report
            job.error = error

    def get(self, job_id: str) -> CompileJob | None:
        """按 ID 取任务；不存在返回 ``None``。"""

        with self._lock:
            return self._jobs.get(job_id)

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        """返回最近任务，新到旧。"""

        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda item: item.created_at, reverse=True)
        return [job.to_dict() for job in jobs[: max(1, limit)]]

    def wait(self, job_id: str, timeout_seconds: float = 1.0) -> CompileJob | None:
        """短暂等待任务结束，用于「提交后立即看一下」的场景。

        不用于长等待；调用方应改为轮询 :meth:`get`。
        """

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            job = self.get(job_id)
            if job is None or job.status in {"succeeded", "failed"}:
                return job
            time.sleep(0.1)
        return self.get(job_id)

    def _prune_locked(self) -> None:
        """保留最近的任务，防止内存无限增长。"""

        if len(self._jobs) <= self._max_jobs:
            return
        ordered = sorted(self._jobs.values(), key=lambda item: item.created_at)
        for job in ordered[: len(self._jobs) - self._max_jobs]:
            self._jobs.pop(job.job_id, None)
