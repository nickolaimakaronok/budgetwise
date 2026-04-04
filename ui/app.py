"""
ui/app.py
Main application window with sidebar navigation.
"""

import customtkinter as ctk
from utils.constants import (
    APP_NAME, WINDOW_WIDTH, WINDOW_HEIGHT, SIDEBAR_WIDTH, NAV_ITEMS, COLOR
)
from utils.i18n import t


class App(ctk.CTk):

    def __init__(self, user):
        super().__init__()
        self.user = user

        self.title(APP_NAME)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(900, 600)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()

        self.nav_buttons = {}
        self._build_nav_buttons()
        self.show_page("dashboard")

        # ── Keyboard shortcuts ────────────────────────────────────────────
        self.bind("<Command-n>", self._quick_add_transaction)
        self.bind("<Command-N>", self._quick_add_transaction)

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, width=SIDEBAR_WIDTH, corner_radius=0,
            fg_color="#1E293B"
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(8, weight=1)
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="💰 BudgetWise",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#F8FAFC",
        ).grid(row=0, column=0, padx=20, pady=(28, 24), sticky="w")

    def _build_nav_buttons(self):
        """Creates one nav button per NAV_ITEM using t() for labels."""
        for i, (page_id, emoji, i18n_key) in enumerate(NAV_ITEMS):
            label = t(i18n_key)
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {emoji}  {label}",
                anchor="w",
                height=44,
                corner_radius=8,
                border_spacing=8,
                fg_color="transparent",
                text_color="#94A3B8",
                hover_color="#334155",
                font=ctk.CTkFont(size=14),
                command=lambda pid=page_id: self.show_page(pid),
            )
            row = 9 if page_id == "settings" else i + 1
            btn.grid(row=row, column=0, padx=12, pady=3, sticky="ew")
            self.nav_buttons[page_id] = btn

    def rebuild_nav(self):
        """Rebuilds nav buttons with updated language labels."""
        for btn in self.nav_buttons.values():
            btn.destroy()
        self.nav_buttons = {}
        self._build_nav_buttons()

    # ── Main area ─────────────────────────────────────────────────────────────

    def _build_main_area(self):
        self.main_area = ctk.CTkFrame(
            self, corner_radius=0,
            fg_color="#F8FAFC"
        )
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(0, weight=1)

        self.current_frame = None

    # ── Navigation ────────────────────────────────────────────────────────────

    def show_page(self, page_id: str):
        for pid, btn in self.nav_buttons.items():
            if pid == page_id:
                btn.configure(fg_color="#2563EB", text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color="#94A3B8")

        if self.current_frame is not None:
            self.current_frame.destroy()

        self.current_frame = self._load_page(page_id)
        if self.current_frame:
            self.current_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

    def _load_page(self, page_id: str) -> ctk.CTkFrame:

        if page_id == "dashboard":
            from ui.pages.dashboard import DashboardPage
            return DashboardPage(self.main_area, self.user, self)

        if page_id == "transactions":
            from ui.pages.transactions import TransactionsPage
            return TransactionsPage(self.main_area, self.user, self)

        if page_id == "budget":
            from ui.pages.budget import BudgetPage
            return BudgetPage(self.main_area, self.user, self)

        if page_id == "analytics":
            from ui.pages.analytics import AnalyticsPage
            return AnalyticsPage(self.main_area, self.user, self)

        if page_id == "goals":
            from ui.pages.goals import GoalsPage
            return GoalsPage(self.main_area, self.user, self)

        if page_id == "settings":
            from ui.pages.settings import SettingsPage
            return SettingsPage(self.main_area, self.user, self)

        return None

    # ── Keyboard shortcuts ────────────────────────────────────────────────────

    def _quick_add_transaction(self, event=None):
        """
        Cmd+N — opens Add Transaction dialog from any page.
        After saving, navigates to Transactions page to show the new entry.
        """
        from ui.pages.transactions import AddTransactionDialog

        def _on_save():
            self.show_page("transactions")

        AddTransactionDialog(self, self.user, on_save=_on_save)