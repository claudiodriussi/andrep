"""
locales.py — number, date and currency conventions for the formatters.

A small built-in table of common locales, no dependencies.  The locale of a
report is, from the first one set:

    r.locale  →  template page.locale  →  ANDREP_LOCALE env var  →  "en-US"

Codes are BCP 47 ("it-IT"); "it_IT" and "it" are accepted too.  A code that is
not in the table falls back to its language ("it-SM" → "it-IT"), then to the
default.  Add or override one with register_locale().

Public API:
    Locale                       — decimal, group, date pattern, default currency
    register_locale(code, ...)   — add a locale to the table
    get_locale(code)  -> Locale
    currency_symbol(code) -> str — "EUR" → "€"; unknown codes are shown as they are
    DEFAULT_LOCALE
"""
from dataclasses import dataclass

DEFAULT_LOCALE = "en-US"


@dataclass(frozen=True)
class Locale:
    code: str
    decimal: str      # decimal separator
    group: str        # thousands separator
    date: str         # strftime pattern of the `date` formatter and of _date
    currency: str     # ISO 4217 code used when the template sets none

    def number(self, value: float, decimals: int, sign: str = "", grouping: bool = True) -> str:
        """*value* with *decimals* digits, this locale's separators."""
        text = f"{value:{sign}{',' if grouping else ''}.{decimals}f}"
        return text.translate({ord(","): "\0", ord("."): self.decimal}).replace("\0", self.group)


_NBSP = " "         # no-break space
_NNBSP = " "        # narrow no-break space (French grouping)
_APOS = "’"         # right single quotation mark (Swiss grouping)

_LOCALES: dict = {}


def _normalize(code: str) -> str:
    parts = code.strip().replace("_", "-").split("-")
    if len(parts) >= 2:
        return f"{parts[0].lower()}-{parts[1].upper()}"
    return parts[0].lower()


def register_locale(code: str, decimal: str, group: str, date: str, currency: str) -> None:
    """Add or replace a locale, e.g. register_locale("sv-SE", ",", " ", "%Y-%m-%d", "SEK")."""
    _LOCALES[_normalize(code)] = Locale(_normalize(code), decimal, group, date, currency)


for _code, _dec, _grp, _date, _cur in (
    ("en-US", ".", ",",    "%m/%d/%Y", "USD"),
    ("en-GB", ".", ",",    "%d/%m/%Y", "GBP"),
    ("it-IT", ",", ".",    "%d/%m/%Y", "EUR"),
    ("it-CH", ".", _APOS,  "%d.%m.%Y", "CHF"),
    ("de-DE", ",", ".",    "%d.%m.%Y", "EUR"),
    ("de-AT", ",", _NBSP,  "%d.%m.%Y", "EUR"),
    ("de-CH", ".", _APOS,  "%d.%m.%Y", "CHF"),
    ("fr-FR", ",", _NNBSP, "%d/%m/%Y", "EUR"),
    ("fr-CH", ",", _NNBSP, "%d.%m.%Y", "CHF"),
    ("es-ES", ",", ".",    "%d/%m/%Y", "EUR"),
    ("pt-PT", ",", _NBSP,  "%d/%m/%Y", "EUR"),
    ("pt-BR", ",", ".",    "%d/%m/%Y", "BRL"),
    ("nl-NL", ",", ".",    "%d-%m-%Y", "EUR"),
):
    register_locale(_code, _dec, _grp, _date, _cur)

# A bare language code uses its main country
_LANGUAGES = {"en": "en-US", "it": "it-IT", "de": "de-DE", "fr": "fr-FR",
              "es": "es-ES", "pt": "pt-PT", "nl": "nl-NL"}

_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "CHF": "CHF", "JPY": "¥",
            "BRL": "R$", "CAD": "CA$", "AUD": "A$", "SEK": "kr", "NOK": "kr",
            "DKK": "kr", "PLN": "zł", "CZK": "Kč", "CNY": "¥", "INR": "₹"}


def get_locale(code: str = "") -> Locale:
    """The Locale for *code*: exact match, then its language, then the default."""
    if code:
        code = _normalize(code)
        if code in _LOCALES:
            return _LOCALES[code]
        language = _LANGUAGES.get(code.split("-")[0])
        if language in _LOCALES:
            return _LOCALES[language]
    return _LOCALES[DEFAULT_LOCALE]


def currency_symbol(code: str) -> str:
    """Symbol of an ISO 4217 code ("EUR" → "€"); an unknown code is shown as it is."""
    return _SYMBOLS.get(code.strip().upper(), code.strip())
