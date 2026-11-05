"""
tests/test_currency_texts.py
Every text of the exchange-rate card and the currency-change window exists
in all three languages and takes the same number of {} values.
"""

from utils.i18n import TRANSLATIONS

KEYS = [
    "exchange_rates", "rates_hint", "no_rates", "rate_updated", "rate_save",
    "rate_delete_confirm", "currency_code_invalid", "rate_invalid", "rate_is_main",
    "change_currency_title", "change_currency_from_to", "mode_relabel", "mode_relabel_hint",
    "mode_convert", "mode_convert_hint", "backup_note", "currency_converted", "currency_relabelled",
]


def test_texts_exist_in_every_language():
    for lang, strings in TRANSLATIONS.items():
        for key in KEYS:
            assert strings.get(key), (lang, key)


def test_same_placeholders_in_every_language():
    for key in KEYS:
        counts = {lang: strings[key].count("{}") for lang, strings in TRANSLATIONS.items()}
        assert len(set(counts.values())) == 1, (key, counts)