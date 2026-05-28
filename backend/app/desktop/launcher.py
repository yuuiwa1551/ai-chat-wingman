from __future__ import annotations

import argparse
import socket
import threading
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import uvicorn

from app.main import app


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(base_url: str, timeout_seconds: float = 10.0) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(f"{base_url}/healthz", timeout=1) as response:
                if response.status == 200:
                    return
        except URLError as exc:
            last_error = exc
        time.sleep(0.1)
    raise RuntimeError(f"FastAPI server did not become ready: {last_error}")


def start_api_server(port: int) -> threading.Thread:
    thread = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": app, "host": "127.0.0.1", "port": port, "log_level": "info"},
        daemon=True,
    )
    thread.start()
    return thread


def build_window_url(api_base_url: str, dev_server_url: str | None) -> str:
    query = urlencode({"apiBase": api_base_url})
    if dev_server_url:
        return f"{dev_server_url.rstrip('/')}?{query}"
    return f"{api_base_url}/?{query}"


def run_desktop(dev_server_url: str | None = None, api_port: int | None = None) -> None:
    from app.desktop.window import start_window

    port = api_port or find_free_port()
    api_base_url = f"http://127.0.0.1:{port}"
    start_api_server(port)
    wait_for_health(api_base_url)
    start_window(build_window_url(api_base_url, dev_server_url))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI Chat Wingman desktop shell")
    parser.add_argument("--dev-server", help="Vite dev server URL, for example http://localhost:5173")
    parser.add_argument("--api-port", type=int, help="Fixed FastAPI port. Defaults to a free local port.")
    args = parser.parse_args()
    run_desktop(dev_server_url=args.dev_server, api_port=args.api_port)


if __name__ == "__main__":
    main()
