from __future__ import annotations

import argparse
import queue
import socket
import threading
import time
import traceback
from pathlib import Path
from types import TracebackType
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import uvicorn

from app.main import app
from app.paths import LOGS_DIR


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _write_launcher_log(message: str) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = Path(LOGS_DIR) / "desktop-launcher.log"
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(message.rstrip() + "\n")


def _format_exception(exc: BaseException, traceback_value: TracebackType | None) -> str:
    return "".join(traceback.format_exception(type(exc), exc, traceback_value))


def wait_for_health(
    base_url: str,
    server_thread: threading.Thread,
    errors: queue.Queue[str],
    timeout_seconds: float = 30.0,
) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        if not errors.empty():
            raise RuntimeError(f"FastAPI server failed during startup:\n{errors.get()}")
        if not server_thread.is_alive():
            raise RuntimeError("FastAPI server thread exited before becoming ready")
        try:
            with urlopen(f"{base_url}/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (TimeoutError, URLError) as exc:
            last_error = exc
        time.sleep(0.1)
    raise RuntimeError(f"FastAPI server did not become ready: {last_error}")


def wait_for_dev_server(dev_server_url: str, timeout_seconds: float = 30.0) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(dev_server_url, timeout=0.5) as response:
                if response.status == 200:
                    return
        except (TimeoutError, URLError) as exc:
            last_error = exc
        time.sleep(0.1)
    raise RuntimeError(f"Vite dev server did not become ready at {dev_server_url}: {last_error}")


def start_api_server(port: int) -> tuple[threading.Thread, queue.Queue[str]]:
    errors: queue.Queue[str] = queue.Queue(maxsize=1)

    def run_server() -> None:
        try:
            uvicorn.run(
                app=app,
                host="127.0.0.1",
                port=port,
                log_level="info",
                log_config=None,
                loop="asyncio",
                http="h11",
                access_log=False,
            )
        except BaseException as exc:
            formatted = _format_exception(exc, exc.__traceback__)
            _write_launcher_log(formatted)
            if errors.empty():
                errors.put(formatted)

    thread = threading.Thread(
        target=run_server,
        name="ai-chat-wingman-fastapi",
        daemon=True,
    )
    thread.start()
    return thread, errors


def build_window_url(api_base_url: str, dev_server_url: str | None) -> str:
    query = urlencode({"apiBase": api_base_url})
    if dev_server_url:
        return f"{dev_server_url.rstrip('/')}?{query}"
    return f"{api_base_url}/?{query}"


def run_desktop(dev_server_url: str | None = None, api_port: int | None = None) -> None:
    from app.desktop.window import start_window

    port = api_port or find_free_port()
    api_base_url = f"http://127.0.0.1:{port}"
    server_thread, errors = start_api_server(port)
    wait_for_health(api_base_url, server_thread, errors)
    if dev_server_url:
        wait_for_dev_server(dev_server_url)
    start_window(build_window_url(api_base_url, dev_server_url))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI Chat Wingman desktop shell")
    parser.add_argument("--dev-server", help="Vite dev server URL, for example http://localhost:5173")
    parser.add_argument("--api-port", type=int, help="Fixed FastAPI port. Defaults to a free local port.")
    args = parser.parse_args()
    run_desktop(dev_server_url=args.dev_server, api_port=args.api_port)


if __name__ == "__main__":
    main()
