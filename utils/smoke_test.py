"""
utils/smoke_test.py
Self-check of the built app, run by the release workflow with
BUDGETWISE_SMOKE_TEST=1: opens every page, builds a PDF report, checks that
the notification module is bundled, then closes the window.

PyInstaller leaves out anything it can't see being imported, and that only
shows up when the packaged app runs. This catches it before a release goes out.
"""

import importlib
import logging
import os
import tempfile
import traceback
from datetime import date

from utils.constants import NAV_ITEMS

logger = logging.getLogger(__name__)

ENV_VAR = "BUDGETWISE_SMOKE_TEST"

errors: list[str] = []


def enabled() -> bool:
    return os.environ.get(ENV_VAR) == "1"


def schedule(app) -> None:
    """Runs the checks once the window is up; errors from Tk callbacks are collected too."""
    def on_tk_error(exc_type, exc, tb):
        errors.append("".join(traceback.format_exception(exc_type, exc, tb)))

    app.report_callback_exception = on_tk_error
    app.after(500, lambda: _run_checks(app))


def _run_checks(app) -> None:
    try:
        for page_id, _icon, _key in NAV_ITEMS:
            app.show_page(page_id)
            app.update()
        _check_pdf_report(app.user)
        _check_notification_module()
    except Exception:
        errors.append(traceback.format_exc())
    finally:
        for error in errors:
            logger.error(f"Smoke test: {error}")
        logger.info("Smoke test: FAILED" if errors else "Smoke test: OK")
        app.quit()       # leave mainloop even if a half-built chart window is left over
        app.destroy()


def _check_pdf_report(user) -> None:
    from services.pdf_service import generate_monthly_report
    today = date.today()
    path = os.path.join(tempfile.mkdtemp(), "report.pdf")
    generate_monthly_report(user, today.year, today.month, path)
    if os.path.getsize(path) == 0:
        raise RuntimeError("PDF report is empty")


def _check_notification_module() -> None:
    from utils.platform_utils import is_mac
    if is_mac():
        return                                   # osascript is part of macOS
    from plyer.utils import platform
    importlib.import_module(f"plyer.platforms.{platform}.notification")