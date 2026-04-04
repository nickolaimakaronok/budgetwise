"""
services/csv_import_service.py
Parses bank CSV files and imports transactions.

Supports flexible column mapping — user picks which column is date,
amount, description/note. Handles multiple date formats and
positive/negative amount conventions.
"""

import csv
import logging
from datetime import datetime, date
from typing import Optional

from models.models import Category, User
from services.transaction_service import add_transaction
from db.database import db

logger = logging.getLogger(__name__)

# Common date formats in bank CSVs
DATE_FORMATS = [
    ("%d.%m.%Y",   "DD.MM.YYYY"),
    ("%d/%m/%Y",   "DD/MM/YYYY"),
    ("%Y-%m-%d",   "YYYY-MM-DD"),
    ("%m/%d/%Y",   "MM/DD/YYYY"),
    ("%d-%m-%Y",   "DD-MM-YYYY"),
    ("%d.%m.%y",   "DD.MM.YY"),
]


def read_csv_preview(filepath: str, max_rows: int = 5) -> dict:
    """
    Reads a CSV file and returns headers + preview rows.

    Returns:
        {
            "headers":  ["Date", "Description", "Amount", "Balance"],
            "rows":     [["01.03.2025", "Grocery store", "-45.50", "1234.00"], ...],
            "total_rows": 156,
            "encoding":   "utf-8",
        }
    """
    # Try different encodings
    for encoding in ["utf-8", "utf-8-sig", "cp1251", "latin-1"]:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                # Detect delimiter
                sample = f.read(4096)
                f.seek(0)

                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                reader = csv.reader(f, dialect)

                headers = next(reader)
                rows = []
                total = 0
                for row in reader:
                    total += 1
                    if len(rows) < max_rows:
                        rows.append(row)

                return {
                    "headers":    headers,
                    "rows":       rows,
                    "total_rows": total,
                    "encoding":   encoding,
                    "delimiter":  dialect.delimiter,
                }
        except (UnicodeDecodeError, csv.Error):
            continue

    raise ValueError("Could not read CSV file. Unsupported encoding or format.")


def parse_amount(text: str) -> tuple[int, str]:
    """
    Parses an amount string from a bank CSV.
    Returns (amount_cents, type).

    Handles:
      "-45.50"   → (4550, "expense")
      "45.50"    → (4550, "income")
      "+45.50"   → (4550, "income")
      "1,234.50" → (123450, "income")
      "1.234,50" → (123450, "income")  # European format
    """
    cleaned = text.strip().replace(" ", "")

    # Remove currency symbols
    for sym in ["$", "€", "£", "₽", "₪", "CHF", "USD", "EUR", "ILS", "RUB"]:
        cleaned = cleaned.replace(sym, "")

    cleaned = cleaned.strip()

    if not cleaned:
        raise ValueError(f"Empty amount: '{text}'")

    # Detect European format: "1.234,50" (dot as thousands, comma as decimal)
    if "," in cleaned and "." in cleaned:
        if cleaned.rindex(",") > cleaned.rindex("."):
            # European: 1.234,50
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # American: 1,234.50
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned and "." not in cleaned:
        # Could be "1234,50" (European decimal) or "1,234" (American thousands)
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Likely European decimal: "1234,50"
            cleaned = cleaned.replace(",", ".")
        else:
            # Likely American thousands: "1,234"
            cleaned = cleaned.replace(",", "")

    # Parse sign
    is_negative = False
    if cleaned.startswith("-"):
        is_negative = True
        cleaned = cleaned[1:]
    elif cleaned.startswith("+"):
        cleaned = cleaned[1:]
    # Some banks use parentheses for negative: (45.50)
    elif cleaned.startswith("(") and cleaned.endswith(")"):
        is_negative = True
        cleaned = cleaned[1:-1]

    try:
        amount = float(cleaned)
    except ValueError:
        raise ValueError(f"Cannot parse amount: '{text}'")

    amount_cents = round(abs(amount) * 100)
    tx_type = "expense" if is_negative else "income"

    return amount_cents, tx_type


def parse_date_flexible(text: str, fmt: str) -> date:
    """Parses a date string using the given format string."""
    cleaned = text.strip()
    return datetime.strptime(cleaned, fmt).date()


def find_category_by_name(user: User, name: str) -> Optional[Category]:
    """
    Tries to find a matching category by name (case-insensitive).
    Searches both system and user categories.
    """
    if not name or not name.strip():
        return None

    clean = name.strip().lower()

    categories = list(Category.select().where(
        (Category.user == user) | (Category.user.is_null()),
        Category.is_archived == False,
    ))

    for cat in categories:
        if cat.name.lower() == clean:
            return cat

    # Partial match — if the CSV description contains a category name
    for cat in categories:
        if cat.name.lower() in clean:
            return cat

    return None


def import_transactions(
    user: User,
    filepath: str,
    date_col: int,
    amount_col: int,
    note_col: Optional[int],
    date_format: str,
    default_type: str = "expense",
    skip_header: bool = True,
) -> dict:
    """
    Imports transactions from a CSV file.

    Args:
        user:         Current user
        filepath:     Path to CSV file
        date_col:     Column index for date (0-based)
        amount_col:   Column index for amount
        note_col:     Column index for description/note (None = skip)
        date_format:  strftime format string (e.g. "%d.%m.%Y")
        default_type: "expense" or "income" — used when amount has no sign
        skip_header:  Skip first row

    Returns:
        {
            "imported": 42,
            "skipped":  3,
            "errors":   ["Row 15: invalid date '32.13.2025'", ...],
        }
    """
    preview = read_csv_preview(filepath, max_rows=0)
    encoding = preview["encoding"]
    delimiter = preview["delimiter"]

    imported = 0
    skipped = 0
    errors = []

    with open(filepath, "r", encoding=encoding) as f:
        reader = csv.reader(f, delimiter=delimiter)

        if skip_header:
            next(reader, None)

        for row_num, row in enumerate(reader, start=2 if skip_header else 1):
            try:
                # Skip empty rows
                if not row or all(cell.strip() == "" for cell in row):
                    skipped += 1
                    continue

                # Parse date
                date_text = row[date_col].strip()
                if not date_text:
                    skipped += 1
                    continue
                tx_date = parse_date_flexible(date_text, date_format)

                # Parse amount
                amount_text = row[amount_col].strip()
                if not amount_text:
                    skipped += 1
                    continue
                amount_cents, detected_type = parse_amount(amount_text)

                if amount_cents == 0:
                    skipped += 1
                    continue

                # Use detected sign if present, otherwise default
                tx_type = detected_type

                # Parse note/description
                note = ""
                if note_col is not None and note_col < len(row):
                    note = row[note_col].strip()

                # Try to auto-match category from note
                category = find_category_by_name(user, note)

                add_transaction(
                    user=user,
                    type=tx_type,
                    amount_cents=amount_cents,
                    category=category,
                    tx_date=tx_date,
                    note=note[:200],  # limit note length
                )
                imported += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                if len(errors) > 50:
                    errors.append("... (too many errors, stopped)")
                    break

    logger.info(f"CSV import: {imported} imported, {skipped} skipped, {len(errors)} errors")
    return {
        "imported": imported,
        "skipped":  skipped,
        "errors":   errors,
    }
