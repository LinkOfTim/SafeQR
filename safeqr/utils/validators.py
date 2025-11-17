"""Набор валидаторов и вспомогательных функций для обработки URL."""
from __future__ import annotations

import ipaddress
import re
from typing import Final
from urllib.parse import quote, unquote, urlsplit, urlunsplit

_ALLOWED_SCHEMES: Final[set[str]] = {"http", "https"}


def is_ip_address(value: str) -> bool:
    """Проверяет, является ли строка валидным IP-адресом."""
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def contains_punycode(domain: str) -> bool:
    """Ищет punycode-ярлыки внутри домена."""
    return any(part.startswith("xn--") for part in domain.lower().split("."))


def to_unicode_domain(domain: str) -> str:
    """Преобразует punycode-домен в привычное представление."""
    try:
        return domain.encode("ascii").decode("idna")
    except (UnicodeError, ValueError):
        return domain


def is_valid_url(value: str) -> bool:
    """Проверяет минимальные требования к URL."""
    if not value:
        return False
    parsed = urlsplit(value.strip())
    if not parsed.scheme or not parsed.netloc:
        return False
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return False
    return True


def normalize_url(url: str) -> str:
    """Нормализует URL: добавляет схему, кодирует path и убирает мусор."""
    if not url:
        return ""
    url = url.strip()
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc or parsed.path
    path = parsed.path if parsed.netloc else ""
    query = parsed.query
    fragment = ""

    safe_path = quote(unquote(path), safe="/:%")
    normalized = urlunsplit((scheme, netloc, safe_path, query, fragment))
    return normalized


def extract_domain(url: str) -> str:
    """Возвращает доменную часть URL без учёта схемы и пути."""
    parsed = urlsplit(url)
    netloc = parsed.netloc.lower()
    if ":" in netloc:
        netloc = netloc.split(":", 1)[0]
    return netloc


def has_suspicious_unicode(domain: str) -> bool:
    """Находит очевидные признаки подмены домена за счёт Unicode."""
    clean = to_unicode_domain(domain)
    return bool(re.search(r"[\u0400-\u04FF\u03B1-\u03C9]", clean))
