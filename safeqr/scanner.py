"""Модуль сканирования QR-кодов из файла или с камеры."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from safeqr.utils.logger import log_error, log_event, log_warning

try:
    import cv2  # type: ignore
except ImportError as exc:  # pragma: no cover - отсутствие cv2
    raise ImportError("Не найдена библиотека opencv-python. Установите зависимости.") from exc

try:
    from pyzbar.pyzbar import decode  # type: ignore
except ImportError as exc:  # pragma: no cover - отсутствие pyzbar
    raise ImportError("Не найдена библиотека pyzbar. Установите зависимости.") from exc


_DEF_CAMERA_INDEX = 0


def _decode_frame(frame) -> Optional[str]:
    """Пытается найти QR-код в кадре и вернуть его данные."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    detections = decode(gray)
    for detection in detections:
        data = detection.data.decode("utf-8", errors="ignore").strip()
        if data:
            return data
    return None


def scan_from_file(path: str) -> Optional[str]:
    """Сканирует QR-код из изображения."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    image = cv2.imread(str(file_path))
    if image is None:
        raise ValueError("Не удалось считать изображение. Поддерживаются форматы PNG/JPEG.")

    payload = _decode_frame(image)
    if payload:
        log_event("QR_SCANNED_FILE", f"Источник: {file_path}")
    else:
        log_warning("QR_NOT_FOUND_FILE", f"Источник: {file_path}")
    return payload


def scan_from_camera(timeout: float = 15.0) -> Optional[str]:
    """Активирует видеопоток камеры и ищет QR-код в реальном времени."""
    backend = getattr(cv2, "CAP_DSHOW", 0)
    capture = cv2.VideoCapture(_DEF_CAMERA_INDEX, backend)
    if not capture.isOpened():
        log_error("CAMERA", "Не удалось открыть камеру")
        raise RuntimeError("Камера недоступна")

    # Простая имитация автофокуса
    capture.set(cv2.CAP_PROP_AUTOFOCUS, 1)

    payload: Optional[str] = None
    frame_count = 0
    max_frames = int(timeout * 30)  # предполагаем 30 FPS

    try:
        while frame_count < max_frames:
            ret, frame = capture.read()
            frame_count += 1
            if not ret:
                log_warning("CAMERA_STREAM", "Не удалось получить кадр")
                continue
            payload = _decode_frame(frame)
            if payload:
                log_event("QR_SCANNED_CAMERA", "QR найден через камеру")
                break
            cv2.waitKey(1)
    finally:
        capture.release()
        cv2.destroyAllWindows()

    if payload is None:
        log_warning("QR_NOT_FOUND_CAMERA", "QR-код не обнаружен в отведённое время")
    return payload
