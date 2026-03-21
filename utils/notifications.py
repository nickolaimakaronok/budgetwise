"""
utils/notifications.py
Background notification service — checks budget limits every hour
and sends a macOS system notification when a category exceeds its limit.

How it works:
  1. main.py calls start_notification_worker(user) on app startup
  2. A daemon thread starts and runs _worker() in the background
  3. Every hour the worker calls _check_and_notify(user)
  4. _check_and_notify fetches budget status for the current month
  5. For each category in "danger" or "warning" status — sends a notification
  6. Already-notified categories are tracked to avoid spamming
  7. The thread is a daemon — it stops automatically when the app closes
"""

import threading
import time
from datetime import date
from plyer import notification


# How often to check budget limits (in seconds)
# 3600 = 1 hour. Set to 60 for testing.
CHECK_INTERVAL_SECONDS = 3600

# Tracks which categories have already been notified this session.
# Key: category_id, Value: status that was notified ("warning" or "danger")
# Prevents sending the same notification every hour for the same category.
_notified: dict[int, str] = {}

# Controls whether the worker loop keeps running.
# Set to False to stop the background thread gracefully.
_running = False


def start_notification_worker(user) -> None:
    """
    Starts the background budget-check thread.
    Call this once from main.py after the database is initialized.

    The thread is a daemon — it stops automatically when the main app exits.
    Safe to call multiple times (won't start duplicate threads).

    Usage:
        from utils.notifications import start_notification_worker
        start_notification_worker(user)
    """
    global _running

    if _running:
        return  # already started — don't create a second thread

    _running = True

    thread = threading.Thread(
        target=_worker,
        args=(user,),
        daemon=True,   # daemon = dies when the main window closes
        name="BudgetNotificationWorker",
    )
    thread.start()
    print("🔔 Notification worker started")


def stop_notification_worker() -> None:
    """
    Signals the background thread to stop after its current sleep.
    Called automatically when the app exits (daemon thread handles this).
    """
    global _running
    _running = False


def _worker(user) -> None:
    """
    Main loop of the background thread.
    Checks budget immediately on start, then waits CHECK_INTERVAL_SECONDS
    between each subsequent check.
    """
    while _running:
        try:
            _check_and_notify(user)
        except Exception as e:
            # Never crash the background thread — just log and continue
            print(f"⚠️ Notification worker error: {e}")

        # Sleep in small increments so we can respond to _running=False quickly
        # instead of sleeping the full hour at once
        for _ in range(CHECK_INTERVAL_SECONDS):
            if not _running:
                break
            time.sleep(1)


def _check_and_notify(user) -> None:
    """
    Fetches the current month's budget status and sends notifications
    for any category that is in "warning" (≥80%) or "danger" (≥100%) status.

    Notification logic:
      - "danger"  (≥100%): "🚨 Budget exceeded — Category: 120% used"
      - "warning" (≥80%):  "⚠️ Budget warning — Category: 85% used"
      - Already notified at the same or higher level → skip (no spam)
      - Resets notification memory each month (new month = fresh start)
    """
    from services.budget_service import get_budget_status

    today = date.today()
    rows  = get_budget_status(user, today.year, today.month)

    for row in rows:
        cat    = row["category"]
        status = row["status"]
        pct    = row["percent"]

        # Only notify for warning or danger — skip "ok" categories
        if status not in ("warning", "danger"):
            # If this category was previously in warning/danger but recovered
            # (user deleted a transaction) — reset its notification state
            _notified.pop(cat.id, None)
            continue

        # Skip if we already sent this exact status for this category
        # (avoids repeating "danger" every hour once it's been sent)
        if _notified.get(cat.id) == status:
            continue

        # Skip if already notified at "danger" and current is only "warning"
        # (don't downgrade severity of notification)
        if _notified.get(cat.id) == "danger" and status == "warning":
            continue

        # Send the notification
        _send_notification(cat.name, status, pct, row)

        # Remember that we notified this category at this status level
        _notified[cat.id] = status


def _send_notification(cat_name: str, status: str, pct: float, row: dict) -> None:
    """
    Sends a macOS system notification via plyer.

    Args:
        cat_name: Category name e.g. "Groceries"
        status:   "warning" or "danger"
        pct:      Percentage used e.g. 85.0 or 120.0
        row:      Full budget status dict with spent/limit cents
    """
    from utils.formatters import format_money_short

    spent = format_money_short(row["spent_cents"])
    limit = format_money_short(row["limit_cents"])

    if status == "danger":
        title   = f"🚨 Budget exceeded: {cat_name}"
        message = (
            f"You spent {spent} of {limit} limit.\n"
            f"{pct:.0f}% used — over budget!"
        )
    else:  # warning
        title   = f"⚠️ Budget warning: {cat_name}"
        message = (
            f"You spent {spent} of {limit} limit.\n"
            f"{pct:.0f}% used — approaching limit."
        )

    try:
        notification.notify(
            title=title,
            message=message,
            app_name="BudgetWise",
            timeout=8,   # notification disappears after 8 seconds
        )
        print(f"🔔 Notification sent: {title}")
    except Exception as e:
        # plyer may fail silently on some macOS configurations — just log it
        print(f"⚠️ Could not send notification: {e}")


def check_now(user) -> int:
    """
    Manually triggers a budget check right now.
    Returns the number of notifications sent.
    Useful for testing from the Settings page.

    Usage:
        from utils.notifications import check_now
        sent = check_now(user)
        print(f"Sent {sent} notifications")
    """
    from services.budget_service import get_budget_status
    from utils.formatters import format_money_short

    today = date.today()
    rows  = get_budget_status(user, today.year, today.month)
    sent  = 0

    for row in rows:
        if row["status"] in ("warning", "danger"):
            _send_notification(
                row["category"].name,
                row["status"],
                row["percent"],
                row,
            )
            sent += 1

    return sent