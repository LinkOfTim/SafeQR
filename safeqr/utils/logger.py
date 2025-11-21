"""Утилиты логирования для SafeQR."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Final

_LOG_FILE: Final[Path] = Path(__file__).resolve().parent.parent / "safeqr.log"


def _write(message: str) -> None:
    """Сохраняет строку сообщения в файл журнала."""
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _LOG_FILE.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")


def _format_entry(event: str, details: str) -> str:
    """Формирует строку журнала в соответствии с требованиями."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{timestamp}] {event.upper()}: {details}"


def log_event(event: str, details: str) -> None:
    """Логирует общее событие (например, успешное сканирование)."""
    _write(_format_entry(event, details))


def log_warning(event: str, details: str) -> None:
    """Логирует предупреждение."""
    _write(_format_entry(f"WARNING/{event}", details))


def log_error(event: str, details: str) -> None:
    """Логирует ошибку."""
    _write(_format_entry(f"ERROR/{event}", details))


def get_log_path() -> Path:
    """Возвращает путь к файлу журнала."""
    return _LOG_FILE
