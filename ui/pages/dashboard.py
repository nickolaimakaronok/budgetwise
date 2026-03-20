"""
ui/pages/dashboard.py
Dashboard page — balance, monthly summary, recent transactions.
"""

import customtkinter as ctk
from datetime import date
from services.analytics_service import get_month_summary
from services.transaction_service import get_recent_transactions
from utils.formatters import format_money, format_money_short, format_date_short, set_currency


class DashboardPage(ctk.CTkFrame):

    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="#F8FAFC", corner_radius=0)
        self.user = user
        self.app  = app

        # Apply the user's chosen currency symbol across all formatters
        set_currency(user.currency)

        # Column stretches to fill the available width
        self.grid_columnconfigure(0, weight=1)
        # Row 1 (body) takes all remaining vertical space
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        # White bar fixed at 72px tall — does not resize with the window
        header = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)  # keeps height fixed at 72px

        today = date.today()

        # Page title on the left
        ctk.CTkLabel(
            header,
            text="Dashboard",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#1E293B",
        ).grid(row=0, column=0, padx=32, pady=20, sticky="w")

        # Current month + year on the right e.g. "March 2025"
        ctk.CTkLabel(
            header,
            text=today.strftime("%B %Y"),
            font=ctk.CTkFont(size=14),
            text_color="#94A3B8",
        ).grid(row=0, column=1, padx=32, pady=20, sticky="e")

    # ── Body ──────────────────────────────────────────────────────────────────

    def _build_body(self):
        # Scrollable area in case content is taller than the window
        body = ctk.CTkScrollableFrame(
            self, fg_color="#F8FAFC", corner_radius=0
        )
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        today   = date.today()
        # Fetch all summary data for the current month in one call
        summary = get_month_summary(self.user, today.year, today.month)

        self._build_balance_card(body, summary)
        self._build_stat_cards(body, summary)
        self._build_recent_transactions(body)

    # ── Balance card ──────────────────────────────────────────────────────────

    def _build_balance_card(self, parent, summary: dict):
        # Dark card that spans the full width — the hero element of the dashboard
        card = ctk.CTkFrame(parent, fg_color="#1E293B", corner_radius=16)
        card.grid(row=0, column=0, padx=32, pady=(28, 16), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        # Small muted label above the balance number
        ctk.CTkLabel(
            card,
            text="Monthly Balance",
            font=ctk.CTkFont(size=13),
            text_color="#94A3B8",
        ).grid(row=0, column=0, padx=28, pady=(24, 4), sticky="w")

        balance = summary["balance_cents"]
        # Green if positive or zero, red if negative
        color = "#4ADE80" if balance >= 0 else "#F87171"

        # Large balance number — most important number on the screen
        ctk.CTkLabel(
            card,
            text=format_money(balance),
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=color,
        ).grid(row=1, column=0, padx=28, pady=(0, 4), sticky="w")

        # Secondary info: days remaining in month + average daily spend
        ctk.CTkLabel(
            card,
            text=f"{summary['days_left']} days left this month  ·  "
                 f"Daily avg: {format_money_short(summary['daily_avg_cents'])}",
            font=ctk.CTkFont(size=12),
            text_color="#64748B",
        ).grid(row=2, column=0, padx=28, pady=(0, 24), sticky="w")

    # ── Stat cards ────────────────────────────────────────────────────────────

    def _build_stat_cards(self, parent, summary: dict):
        # Row that holds three equal-width cards side by side
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=1, column=0, padx=32, pady=(0, 16), sticky="ew")
        row.grid_columnconfigure((0, 1, 2), weight=1)

        cards = [
            ("Income",   summary["income_cents"],  "#16A34A", "📥"),
            ("Expenses", summary["expense_cents"], "#DC2626", "📤"),
            ("Saved",    summary["balance_cents"], "#2563EB", "🏦"),
        ]

        for i, (label, amount, color, emoji) in enumerate(cards):
            self._stat_card(row, i, emoji, label, amount, color)

    def _stat_card(self, parent, col, emoji, label, amount_cents, color):
        # Individual white card with an emoji label and a bold amount
        card = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=12)
        # col > 0 adds left margin so cards don't touch each other
        card.grid(row=0, column=col, padx=(0 if col == 0 else 12, 0), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        # Emoji + label row e.g. "📥  Income"
        ctk.CTkLabel(
            card,
            text=f"{emoji}  {label}",
            font=ctk.CTkFont(size=12),
            text_color="#64748B",
        ).grid(row=0, column=0, padx=20, pady=(18, 4), sticky="w")

        # The actual amount in bold colored text
        ctk.CTkLabel(
            card,
            text=format_money_short(amount_cents),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=color,
        ).grid(row=1, column=0, padx=20, pady=(0, 18), sticky="w")

    # ── Recent transactions ───────────────────────────────────────────────────

    def _build_recent_transactions(self, parent):
        # Title row with a "See all" link on the right
        title_row = ctk.CTkFrame(parent, fg_color="transparent")
        title_row.grid(row=2, column=0, padx=32, pady=(8, 12), sticky="ew")
        title_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_row,
            text="Recent Transactions",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#1E293B",
        ).grid(row=0, column=0, sticky="w")

        # "See all" button navigates to the full Transactions page
        ctk.CTkButton(
            title_row,
            text="See all →",
            width=80, height=28, corner_radius=6,
            fg_color="transparent",
            text_color="#2563EB",
            hover_color="#EFF6FF",
            font=ctk.CTkFont(size=13),
            command=lambda: self.app.show_page("transactions"),
        ).grid(row=0, column=1, sticky="e")

        # Fetch the 5 most recent transactions from the database
        txs = get_recent_transactions(self.user, limit=5)

        # White rounded container for the transaction rows
        container = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=12)
        container.grid(row=3, column=0, padx=32, pady=(0, 32), sticky="ew")
        container.grid_columnconfigure(0, weight=1)

        if not txs:
            # Empty state — shown when the user has no transactions yet
            ctk.CTkLabel(
                container,
                text="No transactions yet.\nAdd your first one!",
                font=ctk.CTkFont(size=14),
                text_color="#94A3B8",
                justify="center",
            ).grid(row=0, column=0, padx=20, pady=40)
            return

        # Render one row per transaction
        for i, tx in enumerate(txs):
            self._transaction_row(container, i, tx, is_last=(i == len(txs) - 1))

    def _transaction_row(self, parent, row_idx, tx, is_last: bool):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=row_idx, column=0, padx=20, pady=0, sticky="ew")
        row.grid_columnconfigure(1, weight=1)

        # Thin grey divider line between rows (skip the first row)
        if row_idx > 0:
            divider = ctk.CTkFrame(parent, fg_color="#F1F5F9", height=1)
            divider.grid(row=row_idx, column=0, padx=20, sticky="ew")
            row.grid(row=row_idx, column=0, padx=20, pady=0, sticky="ew")

        # Category emoji icon — falls back to 💳 if no category set
        icon = tx.category.icon if tx.category else "💳"
        ctk.CTkLabel(
            row,
            text=icon,
            font=ctk.CTkFont(size=22),
            width=40,
        ).grid(row=0, column=0, padx=(0, 12), pady=14)

        # Category name + optional note in one label
        name = tx.category.name if tx.category else "Uncategorized"
        note = f"  {tx.note}" if tx.note else ""
        ctk.CTkLabel(
            row,
            text=f"{name}{note}",
            font=ctk.CTkFont(size=14),
            text_color="#1E293B",
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        # Short date e.g. "19 Mar"
        ctk.CTkLabel(
            row,
            text=format_date_short(tx.date),
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8",
        ).grid(row=0, column=2, padx=16)

        # Amount: green + prefix for income, red - prefix for expense
        color = "#16A34A" if tx.type == "income" else "#DC2626"
        sign  = "+" if tx.type == "income" else "-"
        ctk.CTkLabel(
            row,
            text=f"{sign}{format_money_short(tx.amount_cents)}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=color,
        ).grid(row=0, column=3, padx=(0, 0))