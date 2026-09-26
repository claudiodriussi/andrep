"""
Locale of the formatters: r.locale → template page.locale → ANDREP_LOCALE → en-US.
"""
import datetime

import pytest

from andrep import AndRepRenderer
from andrep.locales import currency_symbol, get_locale, register_locale
from conftest import emitted_values, make_template

CELLS = ["[v | .2]", "[v | +.2]", "[v | 10.2]", "[v | currency]", "[d | date]", "[d | yyyy-mm-dd]"]


def formatted(page=None, **attrs) -> list:
    """The CELLS formatted for v=1234.5 and d=2026-09-25."""
    template = make_template({"band": CELLS}, page=page or {})
    r = AndRepRenderer(template)
    for key, value in attrs.items():
        setattr(r, key, value)
    v, d = 1234.5, datetime.date(2026, 9, 25)  # noqa: F841
    r.emit("band")
    html = r.to_html()
    return [text for text in _cell_texts(html)]


def _cell_texts(html: str) -> list:
    import re
    return re.findall(r'<div style="[^"]*">([^<]*)</div>', html)


@pytest.fixture(autouse=True)
def no_env_locale(monkeypatch):
    monkeypatch.delenv("ANDREP_LOCALE", raising=False)


def test_default_is_en_us():
    assert formatted() == ["1,234.50", "+1,234.50", "  1,234.50", "$ 1,234.50",
                           "09/25/2026", "2026-09-25"]


def test_template_locale_and_currency():
    assert formatted({"locale": "it-IT", "currency": "EUR"}) == [
        "1.234,50", "+1.234,50", "  1.234,50", "€ 1.234,50", "25/09/2026", "2026-09-25"]


def test_currency_follows_the_locale_when_not_set():
    assert formatted({"locale": "de-DE"})[3] == "€ 1.234,50"
    assert formatted({"locale": "en-GB"})[3] == "£ 1,234.50"


def test_renderer_overrides_template():
    assert formatted({"locale": "it-IT"}, locale="en-US", currency="CHF")[:4] == [
        "1,234.50", "+1,234.50", "  1,234.50", "CHF 1,234.50"]


def test_environment_variable(monkeypatch):
    monkeypatch.setenv("ANDREP_LOCALE", "de-DE")
    assert formatted()[4] == "25.09.2026"
    assert formatted({"locale": "en-US"})[4] == "09/25/2026"   # the template wins


def test_system_date_follows_the_locale():
    r = AndRepRenderer(make_template({"band": ["[_date]"]}, page={"locale": "de-DE"}))
    r.emit("band")
    assert emitted_values(r) == [datetime.date.today().strftime("%d.%m.%Y")]


@pytest.mark.parametrize("code, expected", [
    ("it_IT", "it-IT"), ("IT-it", "it-IT"), ("it", "it-IT"), ("it-SM", "it-IT"),
    ("xx-YY", "en-US"), ("", "en-US"),
])
def test_locale_codes(code, expected):
    assert get_locale(code).code == expected


def test_register_locale():
    register_locale("sv-SE", ",", " ", "%Y-%m-%d", "SEK")
    loc = get_locale("sv-SE")
    assert loc.number(1234.5, 2) == "1 234,50" and currency_symbol(loc.currency) == "kr"
