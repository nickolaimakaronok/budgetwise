"""
main.py — BudgetWise Desktop entry point
Run with: python main.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
from db.migrations import run as init_db
from utils.constants import APP_NAME, APP_VERSION


def main():
    print(f"🚀 Starting {APP_NAME} v{APP_VERSION}")

    # 1. Init database
    init_db()

    # 2. Get or create default user
    from models.models import User
    user = User.get_or_none(User.id == 1)
    if user is None:
        user = User.create(name="Me", currency="USD")

    # 3. Launch UI
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.withdraw()  # hide blank window

    from ui.app import App
    main_window = App(user)
    main_window.mainloop()


if __name__ == "__main__":
    main()