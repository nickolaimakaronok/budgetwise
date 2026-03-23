"""
main.py — BudgetWise Desktop entry point
Run with: python main.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup logging first — before anything else
from utils.logging_config import setup_logging
setup_logging(debug=False)

import logging
logger = logging.getLogger(__name__)

# Import matplotlib early — prevents "cannot load module twice" in PyInstaller
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

import customtkinter as ctk
from db.migrations import run as init_db
from utils.constants import APP_NAME, APP_VERSION


def main():
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")

    # 1. Init database
    init_db()

    # 2. Get or create default user
    from models.models import User
    user = User.get_or_none(User.id == 1)
    if user is None:
        user = User.create(name="Me", currency="USD")
        logger.info("Created default user")

    # 3. Start background notification worker
    from utils.notifications import start_notification_worker
    start_notification_worker(user)

    # 4. Launch UI
    logger.info("Launching UI")
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.withdraw()

    from ui.app import App
    main_window = App(user)
    main_window.mainloop()

    logger.info("Application closed")


if __name__ == "__main__":
    main()