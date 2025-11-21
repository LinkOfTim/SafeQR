"""FastAPI-приложение SafeQR."""

from __future__ import annotations

import base64
import tempfile
from collections import deque
from pathlib import Path
from typing import Deque, Dict, Optional

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from safeqr import generator, scanner, security
from safeqr.utils import validators
from safeqr.utils.logger import get_log_path, log_error

app = FastAPI(title="SafeQR", description="Генератор и сканер безопасных QR-кодов")
_templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)
_recent_checks: Deque[Dict[str, str]] = deque(maxlen=10)


def _read_log_tail(limit: int = 200) -> str:
    log_path = get_log_path()
    if not log_path.exists():
        return "Журнал пока пуст."
    content = log_path.read_text(encoding="utf-8").strip().splitlines()
    return "\n".join(content[-limit:]) if content else "Журнал пока пуст."


def _build_context(request: Request, **extra) -> dict:
    context = {
        "request": request,
        "qr_image": None,
        "qr_payload": None,
        "scan_result": None,
        "security_report": None,
        "error": None,
        "recent_checks": list(_recent_checks),
        "log_content": _read_log_tail(),
    }
    context.update({key: value for key, value in extra.items() if value is not None})
    return context


def _encode_image(path: str) -> str:
    raw = Path(path).read_bytes()
    return base64.b64encode(raw).decode("ascii")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Отображает главную страницу."""
    return _templates.TemplateResponse("index.html", _build_context(request))


@app.post("/generate", response_class=HTMLResponse)
async def generate_qr_route(request: Request, data: str = Form(...)) -> HTMLResponse:
    """Создаёт QR и отображает результат на странице."""
    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
            tmp_path = tmp_file.name
        result_path = generator.generate_qr(data, tmp_path)
        image_b64 = _encode_image(result_path)
        Path(result_path).unlink(missing_ok=True)
        context = {"qr_image": image_b64, "qr_payload": data}
    except Exception as exc:
        log_error("WEB_GENERATE", str(exc))
        context = {"error": str(exc)}
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
    return _templates.TemplateResponse("index.html", _build_context(request, **context))


@app.post("/scan", response_class=HTMLResponse)
async def scan_route(request: Request, qr_file: UploadFile = File(...)) -> HTMLResponse:
    """Принимает изображение QR и выводит найденный текст и отчёт."""
    tmp_path: Optional[str] = None
    try:
        contents = await qr_file.read()
        if not contents:
            raise ValueError("Загружен пустой файл.")
        suffix = Path(qr_file.filename or "qr.png").suffix or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(contents)
            tmp_path = tmp_file.name
        payload = scanner.scan_from_file(tmp_path)
        if not payload:
            context = {"scan_result": "QR-код не найден"}
        else:
            report = security.check_url_safety(payload)
            normalized = validators.normalize_url(payload)
            _recent_checks.appendleft(
                {"url": normalized, "risk": report["risk_level"].upper()}
            )
            context = {"scan_result": payload, "security_report": report}
    except Exception as exc:
        log_error("WEB_SCAN", str(exc))
        context = {"error": str(exc)}
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
    return _templates.TemplateResponse("index.html", _build_context(request, **context))


@app.get("/health")
async def healthcheck() -> dict:
    """Простая проверка здоровья."""
    return {"status": "ok"}
