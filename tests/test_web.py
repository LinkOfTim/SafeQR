"""Тесты веб-слоя FastAPI с моками тяжёлых зависимостей."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("cv2")
pytest.importorskip("pyzbar.pyzbar")

from safeqr import web


@pytest.fixture(autouse=True)
def _reset_recent_checks() -> None:
    web._recent_checks.clear()
    yield
    web._recent_checks.clear()


def test_healthcheck_endpoint() -> None:
    client = TestClient(web.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_endpoint_returns_embedded_image(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y8lgtwAAAAASUVORK5CYII="
    )

    def fake_generate(data: str, filename: str, **_: object) -> str:
        path = Path(filename)
        path.write_bytes(png_bytes)
        return str(path)

    monkeypatch.setattr(web.generator, "generate_qr", fake_generate)
    client = TestClient(web.app)
    response = client.post("/generate", data={"data": "https://example.com"})

    assert response.status_code == 200
    body = response.text
    assert "https://example.com" in body
    assert "data:image/png;base64" in body


def test_scan_endpoint_renders_security_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_scan_from_file(_: str) -> str:
        return "http://example.com/login"

    monkeypatch.setattr(web.scanner, "scan_from_file", fake_scan_from_file)
    client = TestClient(web.app)
    response = client.post(
        "/scan",
        files={"qr_file": ("qr.png", b"binary", "image/png")},
    )

    assert response.status_code == 200
    html = response.text
    assert "http://example.com/login" in html
    assert "risk-medium" in html or "RISK" in html
