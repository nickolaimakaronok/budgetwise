"""
services/csv_import_service.py
Parses bank CSV files and imports transactions.

Supports flexible column mapping — user picks which column is date,
amount, description/note. Handles multiple date formats and
positive/negative amount conventions.
"""

import csv
import io
import logging
from datetime import datetime, date
from typing import Optional

from models.models import Category, User
from utils.currencies import CURRENCIES
from services.currency_service import (
    add_transaction_in_currency, get_rate, normalize_currency_code, parse_rate,
)
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

# How to read the sign of the amount column (chosen in the import dialog)
SIGN_SIGNED      = "signed"    # "-45.50" → expense, "45.50" → income
SIGN_ALL_EXPENSE = "expense"   # every row is an expense, sign ignored
SIGN_ALL_INCOME  = "income"    # every row is income, sign ignored
SIGN_MODES       = (SIGN_SIGNED, SIGN_ALL_EXPENSE, SIGN_ALL_INCOME)


# Text encodings a bank CSV can come in → names shown in the import dialog
ENCODING_LABELS = {
    "utf-8-sig": "UTF-8",
    "utf-16":    "UTF-16",
    "cp1255":    "Windows-1255 (עברית)",
    "cp1251":    "Windows-1251 (кириллица)",
    "latin-1":   "Latin-1",
}


def _looks_hebrew(raw: bytes) -> bool:
    """
    The old Windows code pages for Hebrew (cp1255) and Cyrillic (cp1251) use
    the same bytes, so a file decodes "without errors" both ways.
    Telling them apart: Hebrew letters are bytes 0xE0–0xFA, which in cp1251
    are only the lowercase letters а..ъ. Real Russian text practically always
    also has capitals (Д, С …) or ы ь э ю я ё — bytes Hebrew text never has.
    """
    try:
        as_hebrew = raw.decode("cp1255")
    except UnicodeDecodeError:
        return False                       # contains bytes that cp1255 doesn't have
    if not any("\u05d0" <= ch <= "\u05ea" for ch in as_hebrew):
        return False                       # no Hebrew letters at all
    as_cyrillic = raw.decode("cp1251", errors="replace")
    return all("\u0430" <= ch <= "\u044a"        # only а..ъ
               for ch in as_cyrillic if "\u0400" <= ch <= "\u04ff")


def detect_encoding(raw: bytes) -> str:
    """
    Picks the text encoding of a CSV file from its raw bytes:
      1. UTF-16 (Excel "Unicode text") — recognised by its BOM
      2. UTF-8, with or without BOM — what modern exports use
      3. Windows-1255 (Hebrew) vs Windows-1251 (Cyrillic) — see _looks_hebrew
      4. Latin-1 — decodes anything, last resort
    """
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    try:
        raw.decode("utf-8-sig")
        return "utf-8-sig"
    except UnicodeDecodeError:
        pass
    if _looks_hebrew(raw):
        return "cp1255"
    try:
        raw.decode("cp1251")
        return "cp1251"
    except UnicodeDecodeError:
        return "latin-1"


def load_csv_text(filepath: str) -> dict:
    """
    Reads the file once and returns its decoded text, encoding and delimiter.
    Both the preview and the import use it, so they always read the file
    the same way.
    """
    with open(filepath, "rb") as f:
        raw = f.read()
    encoding = detect_encoding(raw)
    text = raw.decode(encoding)
    try:
        delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
    except csv.Error:
        delimiter = ","                    # e.g. a file with a single column
    return {"text": text, "encoding": encoding, "delimiter": delimiter}


def read_csv_preview(filepath: str, max_rows: int = 5) -> dict:
    """
    Reads a CSV file and returns headers + preview rows.

    Returns:
        {
            "headers":    ["Date", "Description", "Amount", "Balance"],
            "rows":       [["01.03.2025", "Grocery store", "-45.50", "1234.00"], ...],
            "total_rows": 156,
            "encoding":   "utf-8-sig",
            "delimiter":  ",",
        }
    """
    loaded = load_csv_text(filepath)
    reader = csv.reader(io.StringIO(loaded["text"]), delimiter=loaded["delimiter"])

    headers = next(reader, None)
    if not headers:
        raise ValueError("The CSV file is empty.")

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
        "encoding":   loaded["encoding"],
        "delimiter":  loaded["delimiter"],
    }


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
    # also accept the typographic minus "−" (U+2212) some exports use
    cleaned = text.strip().replace(" ", "").replace("\u2212", "-")

    # Remove currency codes and symbols ("ILS", "₪", "BYN", "Br", …) and "CHF"
    for code, (symbol, _name) in CURRENCIES.items():
        cleaned = cleaned.replace(code, "").replace(symbol, "")
    cleaned = cleaned.replace("CHF", "")

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


def find_category_by_name(user: User, name: str, tx_type: Optional[str] = None) -> Optional[Category]:
    """
    Tries to find a matching category by name (case-insensitive).
    Searches both system and user categories.
    With tx_type, only categories of that type can match — an expense
    never lands in "Salary", an income never in "Groceries".
    """
    if not name or not name.strip():
        return None

    clean = name.strip().lower()

    query = Category.select().where(
        (Category.user == user) | (Category.user.is_null()),
        Category.is_archived == False,
    )
    if tx_type:
        query = query.where(Category.type == tx_type)
    categories = list(query)

    for cat in categories:
        if cat.name.lower() == clean:
            return cat

    # Partial match — if the CSV description contains a category name
    for cat in categories:
        if cat.name.lower() in clean:
            return cat

    return None


def guess_sign_mode(rows: list[list[str]], amount_col: int) -> str:
    """
    Picks the default for the import dialog from the preview rows:
    any negative amount → the file is signed (minus = expense);
    no negatives at all → it's most likely a card statement that lists
    spending as positive numbers → treat every row as an expense.
    """
    for row in rows:
        if amount_col < len(row):
            text = row[amount_col].strip()
            if text.startswith(("-", "(", "\u2212")):
                return SIGN_SIGNED
    return SIGN_ALL_EXPENSE


def resolve_type(detected_type: str, sign_mode: str) -> str:
    """Final transaction type for one row, given the sign mode the user chose."""
    if sign_mode == SIGN_ALL_EXPENSE:
        return "expense"
    if sign_mode == SIGN_ALL_INCOME:
        return "income"
    return detected_type        # SIGN_SIGNED: minus → expense, otherwise income


def import_transactions(
    user: User,
    filepath: str,
    date_col: int,
    amount_col: int,
    note_col: Optional[int],
    date_format: str,
    sign_mode: str = SIGN_SIGNED,
    skip_header: bool = True,
    currency: Optional[str] = None,
    rate=None,
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
        sign_mode:    how to read the amount column:
                SIGN_SIGNED      — "-45.50" expense, "45.50" income
                SIGN_ALL_EXPENSE — every row is an expense
                SIGN_ALL_INCOME  — every row is income
        skip_header:  Skip first row
        currency:     the currency the file is in (None = main currency) —
                      e.g. the statement of a euro card
        rate:         its rate, the same for every row; None = the saved rate

    Returns:
        {
            "imported": 42,
            "skipped":  3,
            "errors":   ["Row 15: invalid date '32.13.2025'", ...],
        }
    """
    if sign_mode not in SIGN_MODES:
        raise ValueError(f"Unknown sign_mode: {sign_mode!r}")

    # A file in another currency: check the rate ONCE, before any row —
    # not 500 identical "no rate" errors, one per row
    if currency is not None and normalize_currency_code(currency) != user.currency:
        currency = normalize_currency_code(currency)
        if rate is None:
            rate = get_rate(user, currency)
            if rate is None:
                raise ValueError(f"No exchange rate for {currency} — enter one in Settings")
        rate = parse_rate(rate)
    else:
        currency, rate = None, None

    loaded = load_csv_text(filepath)
    delimiter = loaded["delimiter"]

    imported = 0
    skipped = 0
    errors = []

    with io.StringIO(loaded["text"]) as f:
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

                tx_type = resolve_type(detected_type, sign_mode)

                # Parse note/description
                note = ""
                if note_col is not None and note_col < len(row):
                    note = row[note_col].strip()

                # Try to auto-match category from note (same type only)
                category = find_category_by_name(user, note, tx_type)

                # main currency: saved as is; another one: converted with `rate`
                add_transaction_in_currency(
                    user, tx_type, amount_cents, currency, rate,
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
