"""
utils/logging_config.py
Centralized logging configuration for BudgetWise.
Replaces all print() calls with proper logging.

Log levels:
  DEBUG   — detailed info for development
  INFO    — normal app events (goal created, backup saved)
  WARNING — something unexpected but not critical
  ERROR   — something failed
"""

import logging
import os
from datetime import datetime

# Log file location — same folder as the database
LOG_DIR  = os.path.expanduser("~/Documents/BudgetWise")
LOG_FILE = os.path.join(LOG_DIR, "budgetwise.log")


def setup_logging(debug: bool = False) -> None:
    """
    Sets up logging for the entire application.
    Call once at the start of main.py before anything else.

    Args:
        debug: If True, sets level to DEBUG (very verbose).
               If False, sets level to INFO (normal).
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    level = logging.DEBUG if debug else logging.INFO

    # Format: 2025-03-21 10:30:00 | INFO     | module_name | message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── File handler — writes to budgetwise.log ───────────────────────────────
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # ── Console handler — prints to terminal ──────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # ── Root logger — applies to all modules ─────────────────────────────────
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.info(f"Logging started → {LOG_FILE}")