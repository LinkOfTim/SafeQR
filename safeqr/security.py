"""Проверки безопасности ссылок, извлечённых из QR-кода."""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Final, List
from urllib.parse import urlsplit

from safeqr.utils import validators

_SUSPICIOUS_WORDS: Final[list[str]] = [
    "login",
    "verify",
    "secure",
    "free",
    "gift",
    "confirm",
    "bank",
    "update",
]

_KNOWN_BRANDS: Final[list[str]] = [
    "microsoft.com",
    "google.com",
    "apple.com",
    "facebook.com",
    "paypal.com",
    "amazon.com",
]


@dataclass
class SecurityReport:
    """Структура для итогового отчёта проверки."""

    safe: bool
    warnings: List[str]
    risk_level: str

    def as_dict(self) -> dict:
        """Удобное представление результата в виде словаря."""
        return {
            "safe": self.safe,
            "warnings": self.warnings,
            "risk_level": self.risk_level,
        }


def _assess_risk(warnings: List[str]) -> str:
    if not warnings:
        return "low"
    if len(warnings) <= 2:
        return "medium"
    return "high"


def _check_redirects(url_lower: str, warnings: List[str]) -> None:
    if "?redirect=" in url_lower or "//@" in url_lower:
        warnings.append("Обнаружены признаки редиректов (redirect или //@).")


def _check_keywords(url_lower: str, warnings: List[str]) -> None:
    for word in _SUSPICIOUS_WORDS:
        if word in url_lower:
            warnings.append(f"Подозрительное слово в ссылке: {word}.")


def _check_domain_spoof(domain: str, warnings: List[str]) -> None:
    unicode_domain = validators.to_unicode_domain(domain)
    for brand in _KNOWN_BRANDS:
        ratio = SequenceMatcher(None, unicode_domain, brand).ratio()
        if 0.82 < ratio < 1 and not unicode_domain.endswith(brand):
            warnings.append(
                f"Домен '{unicode_domain}' похож на '{brand}' (возможная подмена)."
            )
            break
    if validators.contains_punycode(domain) or validators.has_suspicious_unicode(domain):
        warnings.append("Обнаружен punycode или необычные символы в домене.")


def check_url_safety(url: str) -> dict:
    """Проводит серию эвристических проверок и возвращает оценку риска."""
    warnings: List[str] = []
    normalized = validators.normalize_url(url)
    parsed = urlsplit(normalized)
    url_lower = normalized.lower()

    if parsed.scheme != "https":
        warnings.append("Ссылка не использует HTTPS.")

    domain = validators.extract_domain(normalized)
    if validators.is_ip_address(domain):
        warnings.append("В качестве домена используется IP-адрес.")

    if len(normalized) > 200:
        warnings.append("Слишком длинная ссылка (более 200 символов).")

    _check_keywords(url_lower, warnings)
    _check_redirects(url_lower, warnings)
    _check_domain_spoof(domain, warnings)

    safe = not warnings
    risk = _assess_risk(warnings)
    return SecurityReport(safe=safe, warnings=warnings, risk_level=risk).as_dict()
