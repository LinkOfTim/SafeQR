"""Модуль генерации безопасных QR-кодов."""

from __future__ import annotations

from pathlib import Path

from safeqr.utils import validators
from safeqr.utils.logger import log_event, log_error

try:
    import qrcode
except ImportError as exc:  # pragma: no cover - окружение без зависимости
    raise ImportError(
        "Не найдена библиотека qrcode. Установите зависимости через 'pip install qrcode[pil]'."
    ) from exc


def _sanitize_payload(data: str) -> str:
    """Проводит минимальную проверку и нормализацию исходных данных."""
    if not data or not data.strip():
        raise ValueError("Пустые данные не могут быть закодированы в QR.")
    cleaned = data.strip()
    if len(cleaned) > 2048:
        raise ValueError(
            "Данные слишком длинные для безопасного QR (ограничение 2048 символов)."
        )
    if validators.is_valid_url(cleaned):
        cleaned = validators.normalize_url(cleaned)
    return cleaned


def generate_qr(
    data: str, filename: str, *, version: int = 4, box_size: int = 10, border: int = 4
) -> str:
    """Создаёт QR-код и сохраняет его в файл, возвращая путь к файлу."""
    payload = _sanitize_payload(data)

    path = Path(filename).expanduser()
    if not path.suffix:
        path = path.with_suffix(".png")
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        qr = qrcode.QRCode(
            version=version,
            error_correction=qrcode.constants.ERROR_CORRECT_Q,
            box_size=box_size,
            border=border,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(path)
        log_event("QR_GENERATED", f"Файл: {path}")
        return str(path)
    except Exception as exc:  # pragma: no cover - защита
        log_error("QR_GENERATION_FAILED", str(exc))
        raise
