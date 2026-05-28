from __future__ import annotations


def start_window(url: str) -> None:
    import webview

    webview.create_window(
        "AI Chat Wingman",
        url,
        width=420,
        height=720,
        resizable=True,
        on_top=True,
        frameless=False,
    )
    webview.start()
