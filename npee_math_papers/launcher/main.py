"""本地启动命令：一条命令拉起后端与前端，并打印前端网址。

用法::

    python -m npee_math_papers                # 本地启动（默认）
    python -m npee_math_papers --host 0.0.0.0 # 绑定到所有网卡
    python -m npee_math_papers --no-browser   # 不自动打开浏览器

前端形态
--------
- 若 ``npee_math_papers/frontend/dist`` 存在，用 ``python -m http.server`` 提供静态
  构建产物（无需 Node 即可运行，适合分发）。
- 否则回退到 Vite 开发服务器（需要 ``npm install``），适合开发。

MCP 不在此启动：Agent 通过 stdio 按需拉起。
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from npee_math_papers.launcher.supervisor import ServiceSpec, ServiceSupervisor

DEFAULT_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8766
DEFAULT_WEB_PORT = 5173

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = Path(__file__).resolve().parents[1] / "frontend"


def _frontend_service(host: str, port: int, environment: dict[str, str]) -> ServiceSpec:
    """选择静态产物或 Vite 开发服务器来提供前端。"""

    dist = FRONTEND_ROOT / "dist"
    if (dist / "index.html").is_file():
        # A plain static server cannot proxy /api, so the bundle is told where the
        # API lives by injecting the origin into index.html at request time.
        return ServiceSpec(
            "前端界面",
            host,
            port,
            f"http://{host}:{port}/",
            [
                sys.executable,
                "-m",
                "npee_math_papers.launcher.static_server",
                "--directory",
                str(dist),
                "--port",
                str(port),
                "--bind",
                host,
                "--api-url",
                environment.get("NPEE_API_URL", ""),
            ],
            REPOSITORY_ROOT,
            environment,
        )
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise RuntimeError(
            "前端尚未构建且未找到 npm。请先运行：\n"
            "  cd npee_math_papers/frontend && npm install && npm run build"
        )
    return ServiceSpec(
        "前端界面",
        host,
        port,
        f"http://{host}:{port}/",
        [npm, "run", "dev", "--", "--host", host, "--port", str(port)],
        FRONTEND_ROOT,
        environment,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="npee-math-papers",
        description="NPEE 数学试卷库本地启动器：拉起后端与前端并打印前端网址。",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="绑定地址")
    parser.add_argument("--api-port", type=int, default=DEFAULT_API_PORT, help="后端 API 端口")
    parser.add_argument("--web-port", type=int, default=DEFAULT_WEB_PORT, help="前端端口")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    environment = os.environ.copy()
    # The gateways call paths such as ``/overview`` and ``/papers``; the API
    # mounts every route under ``/api``. The injected base must therefore include
    # that prefix, exactly like the development proxy target does.
    environment["NPEE_API_URL"] = f"http://{args.host}:{args.api_port}/api"
    # The frontend and API are separate origins (different ports), so the API must
    # allow the frontend origin. Derive it from the actual web port rather than
    # relying on the API's default list, which only knows 5173.
    front_origin = f"http://{args.host}:{args.web_port}"
    existing = environment.get("NPEE_CORS_ORIGINS", "")
    origins = [item for item in (existing.split(",") if existing else []) if item.strip()]
    if front_origin not in origins:
        origins.append(front_origin)
    environment["NPEE_CORS_ORIGINS"] = ",".join(origins)

    services = [
        ServiceSpec(
            "后端 API",
            args.host,
            args.api_port,
            f"http://{args.host}:{args.api_port}/docs",
            [sys.executable, "-m", "uvicorn", "npee_math_papers.api.main:app", "--host", args.host, "--port", str(args.api_port)],
            REPOSITORY_ROOT,
            environment,
        ),
        _frontend_service(args.host, args.web_port, environment),
    ]
    supervisor = ServiceSupervisor(services)
    browser_url = None if args.no_browser else f"http://{args.host}:{args.web_port}/"
    try:
        return supervisor.run(open_browser_url=browser_url)
    except RuntimeError as error:
        print(f"[NPEE 错误] {error}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
