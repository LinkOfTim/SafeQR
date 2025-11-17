"""Набор валидаторов и вспомогательных функций для обработки URL."""
from __future__ import annotations

import ipaddress
import re
from typing import Final
from unicodedata import normalize
from urllib.parse import quote, unquote, urlsplit, urlunsplit

_ALLOWED_SCHEMES: Final[set[str]] = {"http", "https"}
_ASCII_CONFUSABLES: Final[dict[str, str]] = {
    "0": "o",
    "1": "l",
    "3": "e",
    "4": "a",
    "5": "s",
    "6": "g",
    "7": "t",
    "8": "b",
    "9": "g",
    "@": "a",
}
_CYR_TO_LATIN: Final[dict[str, str]] = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "c",
    "ч": "ch",
    "ш": "sh",
    "щ": "sh",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}
_GREEK_TO_LATIN: Final[dict[str, str]] = {
    "α": "a",
    "β": "b",
    "γ": "g",
    "δ": "d",
    "ε": "e",
    "ζ": "z",
    "η": "e",
    "θ": "th",
    "ι": "i",
    "κ": "k",
    "λ": "l",
    "μ": "m",
    "ν": "n",
    "ξ": "x",
    "ο": "o",
    "π": "p",
    "ρ": "r",
    "σ": "s",
    "τ": "t",
    "υ": "y",
    "φ": "f",
    "χ": "x",
    "ψ": "ps",
    "ω": "o",
}
_UNICODE_CONFUSABLES: Final[dict[str, str]] = {}
for source, mapping in (list(_CYR_TO_LATIN.items()) + list(_GREEK_TO_LATIN.items())):
    _UNICODE_CONFUSABLES[source] = mapping
    upper = source.upper()
    if upper != source:
        _UNICODE_CONFUSABLES[upper] = mapping


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


def ascii_skeleton(value: str) -> str:
    """Возвращает ASCII-скелет строки: заменяет популярные гомографы на латиницу."""
    if not value:
        return ""
    clean = to_unicode_domain(value)
    normalized = normalize("NFKC", clean)
    skeleton: list[str] = []
    for char in normalized:
        mapped_ascii = _ASCII_CONFUSABLES.get(char)
        if mapped_ascii is not None:
            skeleton.append(mapped_ascii)
            continue
        if ord(char) < 128:
            skeleton.append(char.lower())
            continue
        mapped = _UNICODE_CONFUSABLES.get(char)
        if mapped:
            skeleton.append(mapped.lower())
            continue
        # unicode.normalize + ascii игнор помогают убрать диакритику
        decomposed = normalize("NFKD", char)
        ascii_equiv = (
            decomposed.encode("ascii", "ignore").decode("ascii", "ignore").lower()
        )
        if ascii_equiv:
            skeleton.append(ascii_equiv)
    return "".join(skeleton)
