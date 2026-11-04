"""
services/csv_export_service.py
Writes transactions to a CSV file.

Columns: Date | Type | Category | Amount | Note | Tags
  - Amount is signed: expenses negative, income positive, "." as decimal
    separator — the file can be summed in a spreadsheet and imported back
    with "Minus = expense, plus = income".
  - Saved as UTF-8 with BOM ("utf-8-sig"): Excel on Windows needs the BOM
    to show Cyrillic/Hebrew correctly; our own importer strips it.
"""

import csv

from utils.formatters import format_date
from utils.i18n import t


def signed_amount_text(tx) -> str:
    """45050 cents expense → "-450.50". Integer math — no float rounding."""
    cents = tx.amount_cents if tx.type == "income" else -tx.amount_cents
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def export_transactions_csv(txs, filepath: str) -> int:
    """
    Writes txs to filepath and returns how many rows were written.
    Uses tx.tag_names when present (filter_transactions preloads it),
    otherwise loads the tags of each transaction.
    """
    from services.tag_service import get_transaction_tags

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([t("date"), t("type"), t("category"), t("amount"), t("note"), t("tags")])
        for tx in txs:
            tag_names = getattr(tx, "tag_names", None)
            if tag_names is None:
                tag_names = [tg.name for tg in get_transaction_tags(tx)]
            writer.writerow([
                format_date(tx.date),
                t("type_income") if tx.type == "income" else t("type_expense"),
                tx.category.name if tx.category else t("uncategorized"),
                signed_amount_text(tx),
                tx.note,
                " ".join(f"#{name}" for name in tag_names),
            ])
    return len(txs)