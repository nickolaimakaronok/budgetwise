"""
services/csv_export_service.py
Writes transactions to a CSV file.

Columns: Date | Type | Category | Amount | Note | Tags | Original amount | Currency | Rate
  - Amount is in the main currency and signed: expenses negative, income
    positive, "." as decimal separator — the file can be summed in a
    spreadsheet and imported back with "Minus = expense, plus = income".
  - The last three are filled only for a purchase in another currency:
    "-20.00" | "EUR" | "3.95" — what was actually paid and the rate used.
    They come after the old six, so files and habits built on those still work.
  - Saved as UTF-8 with BOM ("utf-8-sig"): Excel on Windows needs the BOM
    to show Cyrillic/Hebrew correctly; our own importer strips it.
"""

import csv

from utils.formatters import format_date
from utils.i18n import t


def _signed_text(cents: int, tx_type: str) -> str:
    """45050, "expense" → "-450.50". Integer math — no float rounding."""
    cents = cents if tx_type == "income" else -cents
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def signed_amount_text(tx) -> str:
    """45050 cents expense → "-450.50" (in the main currency)."""
    return _signed_text(tx.amount_cents, tx.type)


def export_transactions_csv(txs, filepath: str) -> int:
    """
    Writes txs to filepath and returns how many rows were written.
    Uses tx.tag_names when present (filter_transactions preloads it),
    otherwise loads the tags of each transaction.
    """
    from services.tag_service import get_transaction_tags

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([t("date"), t("type"), t("category"), t("amount"), t("note"), t("tags"),
                         t("original_amount"), t("currency"), t("exchange_rate")])
        for tx in txs:
            tag_names = getattr(tx, "tag_names", None)
            if tag_names is None:
                tag_names = [tg.name for tg in get_transaction_tags(tx)]
            if tx.is_foreign:
                paid = [_signed_text(tx.original_amount_cents, tx.type), tx.currency, tx.exchange_rate]
            else:
                paid = ["", "", ""]
            writer.writerow([
                format_date(tx.date),
                t("type_income") if tx.type == "income" else t("type_expense"),
                tx.category.name if tx.category else t("uncategorized"),
                signed_amount_text(tx),
                tx.note,
                " ".join(f"#{name}" for name in tag_names),
                *paid,
            ])
    return len(txs)