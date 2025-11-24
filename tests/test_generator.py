"""Тесты генерации QR-кодов."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("qrcode")

from safeqr import generator


def test_generate_qr_creates_png_in_target_path(tmp_path: Path) -> None:
    target = tmp_path / "qr_output"
    result_path = generator.generate_qr(
        " https://Example.com/Path With Space ", str(target)
    )
    result = Path(result_path)
    assert result.exists()
    assert result.suffix == ".png"


def test_generate_qr_rejects_empty_payload(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        generator.generate_qr("   ", str(tmp_path / "qr.png"))
