"""Тесты эвристик безопасности ссылок."""

from __future__ import annotations

from safeqr import security


def test_safe_https_url_has_no_warnings() -> None:
    result = security.check_url_safety("https://example.com/path")
    assert result["safe"] is True
    assert result["warnings"] == []
    assert result["risk_level"] == "low"


def test_risky_http_with_redirect_and_keyword() -> None:
    url = "http://192.168.0.1/login?redirect=http://evil.com"
    result = security.check_url_safety(url)
    warnings = " ".join(result["warnings"])
    assert result["safe"] is False
    assert result["risk_level"] == "high"
    assert "HTTPS" in warnings
    assert "IP-адрес" in warnings
    assert "redirect" in warnings
    assert "Подозрительное слово" in warnings


def test_brand_spoof_with_unicode_letters() -> None:
    result = security.check_url_safety("https://mícrosoft.com")
    assert result["safe"] is False
    assert result["risk_level"] == "medium"
    assert any("похож" in item for item in result["warnings"])
