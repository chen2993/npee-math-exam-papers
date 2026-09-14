"""本地启动器：拉起 API 与前端，并在命令行窗口打印前端网址。

启动后这个命令行窗口只做两件事：

1. 拉起后端 API（FastAPI）与前端（Vite 开发服务器，或内置构建产物）；
2. 打印人类要用的前端网址。

MCP 不在此启动：Agent 每次会话通过 stdio 拉起它，随用随起。
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class ServiceSpec:
    """一个本地服务。"""

    label: str
    host: str
    port: int
    url: str
    command: list[str]
    working_directory: Path
    environment: Mapping[str, str] | None = None
    required: bool = True


class ServiceSupervisor:
    """顺序启动本地服务，等待端口就绪，然后守护进程。"""

    def __init__(self, services: list[ServiceSpec]) -> None:
        self._services = services
        self._processes: list[subprocess.Popen[bytes]] = []

    def run(self, *, open_browser_url: str | None = None) -> int:
        try:
            self._assert_ports_available()
            self._start_all()
            self._wait_for_all()
            self._print_ready(open_browser_url)
            if open_browser_url:
                _open_browser(open_browser_url)
            self._watch()
        except KeyboardInterrupt:
            print("\n[NPEE] 收到中断，正在停止服务...", flush=True)
            return 0
        finally:
            self._stop_all()
        return 0

    # --- 端口与进程 -------------------------------------------------------

    def _assert_ports_available(self) -> None:
        for service in self._services:
            if not 1 <= service.port <= 65535:
                raise RuntimeError(f"{service.label} 端口无效：{service.port}")
            if self._port_is_busy(service.port):
                raise RuntimeError(f"{service.label} 端口已被占用：{service.port}，请换端口后重试")

    def _start_all(self) -> None:
        for service in self._services:
            try:
                self._processes.append(
                    subprocess.Popen(
                        service.command,
                        cwd=service.working_directory,
                        env=dict(service.environment) if service.environment else None,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                )
            except OSError as error:
                if service.required:
                    raise RuntimeError(f"无法启动 {service.label}：{error}") from error
                print(f"[NPEE] 跳过 {service.label}：{error}", flush=True)

    def _wait_for_all(self) -> None:
        for service, process in zip(self._services, self._processes, strict=True):
            if process.poll() is not None or not self._wait_for_port(service.host, service.port):
                if service.required:
                    raise RuntimeError(f"{service.label} 未能在端口 {service.port} 就绪")
                print(f"[NPEE] {service.label} 未就绪，继续", flush=True)

    def _watch(self) -> None:
        while True:
            for service, process in zip(self._services, self._processes, strict=True):
                code = process.poll()
                if code is not None and service.required:
                    raise RuntimeError(f"{service.label} 已退出，退出码 {code}")
            time.sleep(1)

    def _stop_all(self) -> None:
        for process in self._processes:
            if process.poll() is None:
                process.terminate()
        for process in self._processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        self._processes.clear()

    def _print_ready(self, browser_url: str | None) -> None:
        print("", flush=True)
        print("  NPEE 数学试卷库已启动", flush=True)
        print("  " + "-" * 46, flush=True)
        for service in self._services:
            print(f"  {service.label:<10} {service.url}", flush=True)
        if browser_url:
            print("", flush=True)
            print(f"  请在浏览器打开： {browser_url}", flush=True)
        print("", flush=True)
        print("  按 Ctrl+C 停止服务", flush=True)
        print("", flush=True)

    # --- 端口探测 ---------------------------------------------------------

    @staticmethod
    def _port_is_busy(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.2)
            return probe.connect_ex(("127.0.0.1", port)) == 0

    @staticmethod
    def _wait_for_port(host: str, port: int, timeout_seconds: float = 20.0) -> bool:
        probe_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                with socket.create_connection((probe_host, port), timeout=0.35):
                    return True
            except OSError:
                time.sleep(0.25)
        return False


def _open_browser(url: str) -> None:
    """尽力打开浏览器；失败不影响服务。"""

    try:
        webbrowser.open(url)
    except Exception:
        pass
