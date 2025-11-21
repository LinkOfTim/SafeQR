"""Точка входа для приложения SafeQR."""

from __future__ import annotations

import argparse
import sys
import threading
import time
import webbrowser

import uvicorn

from safeqr.utils.logger import log_error

try:  # pragma: no cover - среда без Tk
    import tkinter as tk
    from tkinter import messagebox
except ModuleNotFoundError:  # pragma: no cover - fallback для web-режима
    tk = None
    messagebox = None


def main() -> None:
    """Запускает FastAPI либо Tk-интерфейс в зависимости от режима."""
    parser = argparse.ArgumentParser(
        description="SafeQR – защищённый генератор и сканер QR-кодов"
    )
    parser.add_argument(
        "--mode",
        choices=["web", "tk"],
        default="web",
        help="Интерфейс: web (FastAPI) или tk.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Хост для FastAPI.")
    parser.add_argument("--port", type=int, default=8000, help="Порт для FastAPI.")
    parser.add_argument(
        "--no-browser", action="store_true", help="Не открывать браузер автоматически."
    )
    args = parser.parse_args()

    if args.mode == "tk":
        _run_tk()
        return

    _run_web(host=args.host, port=args.port, open_browser=not args.no_browser)


def _run_web(*, host: str, port: int, open_browser: bool) -> None:
    """Стартует uvicorn и по желанию открывает браузер."""
    try:
        url = f"http://{host}:{port}"
        if open_browser:
            threading.Thread(
                target=_open_browser_later, args=(url,), daemon=True
            ).start()
        config = uvicorn.Config(
            "safeqr.web:app", host=host, port=port, reload=False, log_level="info"
        )
        server = uvicorn.Server(config)
        server.run()
    except KeyboardInterrupt:
        print("SafeQR: сервер остановлен. Хорошего дня!", file=sys.stderr)
        return
    except Exception as exc:  # pragma: no cover
        log_error("WEB_CRASH", str(exc))
        _show_fatal_error(exc)
        raise


def _open_browser_later(url: str) -> None:
    """Небольшая задержка перед попыткой открыть браузер."""
    time.sleep(1.5)
    webbrowser.open(url)


def _run_tk() -> None:
    """Запускает классический Tk-интерфейс."""
    if tk is None:
        raise RuntimeError(
            "Tkinter недоступен в этой среде. Установите python3-tk или используйте режим web."
        )
    try:
        from safeqr import ui

        ui.run_app()
    except Exception as exc:  # pragma: no cover
        log_error("APP_CRASH", str(exc))
        _show_fatal_error(exc)
        raise


def _show_fatal_error(exc: Exception) -> None:
    """Выводит дружелюбное сообщение об ошибке."""
    if tk is None or messagebox is None:
        print(f"Критическая ошибка SafeQR: {exc}", file=sys.stderr)
        return
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Критическая ошибка SafeQR", str(exc))
        root.destroy()
    except tk.TclError:
        print(f"Критическая ошибка SafeQR: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
