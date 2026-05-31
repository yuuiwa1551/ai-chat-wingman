from __future__ import annotations


class WindowControlApi:
    def __init__(self) -> None:
        self._window = None

    def bind(self, window: object) -> None:
        self._window = window

    def set_on_top(self, enabled: bool) -> dict[str, bool]:
        if self._window is None:
            raise RuntimeError("Desktop window is not ready")
        self._window.on_top = bool(enabled)
        return {"on_top": bool(self._window.on_top)}

    def minimize(self) -> dict[str, bool]:
        if self._window is None:
            raise RuntimeError("Desktop window is not ready")
        self._window.minimize()
        return {"minimized": True}


def start_window(url: str) -> None:
    import webview

    api = WindowControlApi()
    window = webview.create_window(
        "AI Chat Wingman",
        url,
        js_api=api,
        width=1100,
        height=760,
        min_size=(920, 640),
        resizable=True,
        on_top=False,
        frameless=False,
    )
    if window is not None:
        api.bind(window)
    webview.start()
