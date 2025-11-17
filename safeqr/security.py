"""Проверки безопасности ссылок, извлечённых из QR-кода."""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Final, List
from urllib.parse import urlsplit, parse_qsl

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
    "account",
    "auth",
]

_KNOWN_BRANDS: Final[list[str]] = [
    "microsoft.com",
    "google.com",
    "apple.com",
    "facebook.com",
    "paypal.com",
    "amazon.com",
    "instagram.com",
    "netflix.com",
    "steamcommunity.com",
    "kaspibank.kz",
    "bank.kz",
]

_SUSPICIOUS_PARAMS: Final[set[str]] = {
    "redirect",
    "redir",
    "return",
    "next",
    "continue",
    "url",
    "target",
    "dest",
    "destination",
    "goto",
}


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


def _contains_brand_fragment(domain_skeleton: str, brand_label: str) -> bool:
    brand_skeleton = validators.ascii_skeleton(brand_label)
    domain_compact = "".join(ch for ch in domain_skeleton if ch.isalnum())
    brand_compact = "".join(ch for ch in brand_skeleton if ch.isalnum())
    if not domain_compact or not brand_compact:
        return False
    if brand_compact in domain_compact:
        return True
    if len(domain_compact) < len(brand_compact):
        domain_compact, brand_compact = brand_compact, domain_compact
    for idx in range(len(domain_compact) - len(brand_compact) + 1):
        chunk = domain_compact[idx : idx + len(brand_compact)]
        if SequenceMatcher(None, chunk, brand_compact).ratio() >= 0.85:
            return True
    return False


def _check_query_params(parsed, warnings: List[str]) -> None:
    if not parsed.query:
        return
    try:
        params = parse_qsl(parsed.query, keep_blank_values=True)
    except ValueError:
        return
    for key, value in params:
        key_lower = key.lower()
        if key_lower in _SUSPICIOUS_PARAMS:
            warnings.append(f"Параметр '{key}' может использоваться для редиректа или подмены.")
        if value and "http://" in value.lower():
            warnings.append(f"Параметр '{key}' перенаправляет на небезопасный HTTP: {value}.")


def _check_domain_spoof(domain: str, warnings: List[str]) -> None:
    unicode_domain = validators.to_unicode_domain(domain)
    domain_skeleton = validators.ascii_skeleton(unicode_domain)
    for brand in _KNOWN_BRANDS:
        ratio = SequenceMatcher(None, unicode_domain, brand).ratio()
        if unicode_domain.endswith(brand):
            continue
        if 0.82 < ratio < 1:
            warnings.append(
                f"Домен '{unicode_domain}' похож на '{brand}' (возможная подмена)."
            )
            break
        brand_label = brand.split(".", 1)[0]
        if _contains_brand_fragment(domain_skeleton, brand_label):
            warnings.append(
                f"В домене '{unicode_domain}' обнаружен фрагмент, похожий на бренд '{brand_label}'."
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

    if len(normalized) > 150:
        warnings.append("Слишком длинная ссылка (более 150 символов) — возможна маскировка параметров.")

    _check_keywords(url_lower, warnings)
    _check_redirects(url_lower, warnings)
    _check_query_params(parsed, warnings)
    _check_domain_spoof(domain, warnings)

    safe = not warnings
    risk = _assess_risk(warnings)
    return SecurityReport(safe=safe, warnings=warnings, risk_level=risk).as_dict()
