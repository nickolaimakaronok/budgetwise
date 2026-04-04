"""
main.py
Entry point for BudgetWise.
──────────────────────────────────────────────────────────────
WHAT CHANGED for v1.8.0 (onboarding):

1. Added _get_or_create_user() — checks if User exists in DB
2. If no user → runs OnboardingWindow.run() to collect name/currency/language
3. Creates User in DB with onboarding data
4. Sets i18n language from user.language BEFORE building the app
5. If user exists → business as usual
──────────────────────────────────────────────────────────────
"""

import sys
import logging
from datetime import date

from utils.logging_config import setup_logging

setup_logging(debug=False)
logger = logging.getLogger(__name__)

from db.database import db
from db.migrations import run as run_migrations
from models.models import User
from utils.i18n import set_language
from utils.formatters import set_currency


def _get_or_create_user() -> User | None:
    """
    Returns the existing user or runs onboarding to create one.
    Returns None if user closed onboarding without finishing.
    """
    # Check if a user already exists
    user = User.select().first()

    if user is not None:
        return user

    # ── No user → show onboarding ─────────────────────────────────────────
    logger.info("No user found — launching onboarding")

    from ui.pages.onboarding import OnboardingWindow
    result = OnboardingWindow.run()

    if result is None:
        # User closed the window without finishing
        logger.info("Onboarding cancelled by user")
        return None

    # Create user with onboarding data
    with db:
        user = User.create(
            name=result["name"],
            currency=result["currency"],
            language=result["language"],
        )
    logger.info(
        f"Created user '{user.name}' "
        f"(currency={user.currency}, language={user.language})"
    )

    return user


def main():
    # 1. Run migrations (creates tables + seeds categories)
    run_migrations()

    # 2. Get or create user (may show onboarding)
    user = _get_or_create_user()
    if user is None:
        logger.info("No user — exiting")
        sys.exit(0)

    # 3. Set language and currency from user profile
    set_language(user.language)
    set_currency(user.currency)

    # 4. Process recurring transactions for current month
    from services.transaction_service import create_recurring_for_month
    today = date.today()
    created = create_recurring_for_month(user, today.year, today.month)
    if created:
        logger.info(f"Created {created} recurring transactions for {today.month}/{today.year}")

    # 5. Start notification worker
    from utils.notifications import start_notification_worker
    start_notification_worker(user)

    # 6. Launch the app
    from ui.app import App
    app = App(user)
    app.mainloop()


if __name__ == "__main__":
    main()
