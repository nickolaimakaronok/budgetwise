"""
main.py — BudgetWise Desktop entry point
Run with: python main.py
"""

import sys
import os

# Add project root to path so imports work correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.migrations import run as init_db
from utils.constants import APP_NAME, APP_VERSION


def main():
    # 1. Initialize database (creates tables and seeds categories on first run)
    print(f"🚀 Starting {APP_NAME} v{APP_VERSION}")
    init_db()

    # 2. Launch the GUI
    # TODO (Stage 1): uncomment after creating ui/app.py
    # import customtkinter as ctk
    # from ui.app import App
    # ctk.set_appearance_mode("System")   # "Light" | "Dark" | "System"
    # ctk.set_default_color_theme("blue")
    # app = App()
    # app.mainloop()

    print("\n✅ Database ready. UI will be added in Stage 1.")
    print(f"   Database file: {os.path.join(os.path.dirname(__file__), 'budget.db')}")


if __name__ == "__main__":
    main()
