"""Тесты для утилит валидаторов URL."""

from __future__ import annotations

from safeqr.utils import validators


def test_normalize_url_encodes_path_and_keeps_scheme() -> None:
    raw = "HTTPS://Example.com/Path With Space?q=1"
    normalized = validators.normalize_url(raw)
    assert normalized == "https://Example.com/Path%20With%20Space?q=1"


def test_is_valid_url_accepts_https_and_rejects_ftp() -> None:
    assert validators.is_valid_url("https://example.com/page")
    assert not validators.is_valid_url("ftp://example.com/page")


def test_ascii_skeleton_handles_confusables_and_unicode() -> None:
    # Первая буква — кириллическая "а"
    skeleton = validators.ascii_skeleton("аpple.com")
    assert skeleton == "apple.com"
    assert validators.has_suspicious_unicode("xn--e1afmkfd.xn--p1ai")
