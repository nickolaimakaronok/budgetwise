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

        # Set currency from user profile
        set_currency(user.currency)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        today = date.today()
        ctk.CTkLabel(
            header,
            text=f"Dashboard",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#1E293B",
        ).grid(row=0, column=0, padx=32, pady=20, sticky="w")

        ctk.CTkLabel(
            header,
            text=today.strftime("%B %Y"),
            font=ctk.CTkFont(size=14),
            text_color="#94A3B8",
        ).grid(row=0, column=1, padx=32, pady=20, sticky="e")

    # ── Body ──────────────────────────────────────────────────────────────────

    def _build_body(self):
        body = ctk.CTkScrollableFrame(
            self, fg_color="#F8FAFC", corner_radius=0
        )
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        today   = date.today()
        summary = get_month_summary(self.user, today.year, today.month)

        self._build_balance_card(body, summary)
        self._build_stat_cards(body, summary)
        self._build_recent_transactions(body)

    # ── Balance card ──────────────────────────────────────────────────────────

    def _build_balance_card(self, parent, summary: dict):
        card = ctk.CTkFrame(parent, fg_color="#1E293B", corner_radius=16)
        card.grid(row=0, column=0, padx=32, pady=(28, 16), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="Monthly Balance",
            font=ctk.CTkFont(size=13),
            text_color="#94A3B8",
        ).grid(row=0, column=0, padx=28, pady=(24, 4), sticky="w")

        balance = summary["balance_cents"]
        color   = "#4ADE80" if balance >= 0 else "#F87171"

        ctk.CTkLabel(
            card,
            text=format_money(balance),
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=color,
        ).grid(row=1, column=0, padx=28, pady=(0, 4), sticky="w")

        ctk.CTkLabel(
            card,
            text=f"{summary['days_left']} days left this month  ·  "
                 f"Daily avg: {format_money_short(summary['daily_avg_cents'])}",
            font=ctk.CTkFont(size=12),
            text_color="#64748B",
        ).grid(row=2, column=0, padx=28, pady=(0, 24), sticky="w")

    # ── Stat cards ────────────────────────────────────────────────────────────

    def _build_stat_cards(self, parent, summary: dict):
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
        card = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=12)
        card.grid(row=0, column=col, padx=(0 if col == 0 else 12, 0), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text=f"{emoji}  {label}",
            font=ctk.CTkFont(size=12),
            text_color="#64748B",
        ).grid(row=0, column=0, padx=20, pady=(18, 4), sticky="w")

        ctk.CTkLabel(
            card,
            text=format_money_short(amount_cents),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=color,
        ).grid(row=1, column=0, padx=20, pady=(0, 18), sticky="w")

    # ── Recent transactions ───────────────────────────────────────────────────

    def _build_recent_transactions(self, parent):
        # Title row
        title_row = ctk.CTkFrame(parent, fg_color="transparent")
        title_row.grid(row=2, column=0, padx=32, pady=(8, 12), sticky="ew")
        title_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_row,
            text="Recent Transactions",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#1E293B",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            title_row,
            text="See all →",
            width=80,
            height=28,
            corner_radius=6,
            fg_color="transparent",
            text_color="#2563EB",
            hover_color="#EFF6FF",
            font=ctk.CTkFont(size=13),
            command=lambda: self.app.show_page("transactions"),
        ).grid(row=0, column=1, sticky="e")

        # Transactions list
        txs = get_recent_transactions(self.user, limit=5)

        container = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=12)
        container.grid(row=3, column=0, padx=32, pady=(0, 32), sticky="ew")
        container.grid_columnconfigure(0, weight=1)

        if not txs:
            ctk.CTkLabel(
                container,
                text="No transactions yet.\nAdd your first one!",
                font=ctk.CTkFont(size=14),
                text_color="#94A3B8",
                justify="center",
            ).grid(row=0, column=0, padx=20, pady=40)
            return

        for i, tx in enumerate(txs):
            self._transaction_row(container, i, tx, is_last=(i == len(txs) - 1))

    def _transaction_row(self, parent, row_idx, tx, is_last: bool):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=row_idx, column=0, padx=20, pady=0, sticky="ew")
        row.grid_columnconfigure(1, weight=1)

        # Divider (not on first row)
        if row_idx > 0:
            divider = ctk.CTkFrame(parent, fg_color="#F1F5F9", height=1)
            divider.grid(row=row_idx, column=0, padx=20, sticky="ew")
            row.grid(row=row_idx, column=0, padx=20, pady=0, sticky="ew")

        # Emoji icon
        icon = tx.category.icon if tx.category else "💳"
        ctk.CTkLabel(
            row,
            text=icon,
            font=ctk.CTkFont(size=22),
            width=40,
        ).grid(row=0, column=0, padx=(0, 12), pady=14)

        # Category + note
        name = tx.category.name if tx.category else "Uncategorized"
        note = f"  {tx.note}" if tx.note else ""
        ctk.CTkLabel(
            row,
            text=f"{name}{note}",
            font=ctk.CTkFont(size=14),
            text_color="#1E293B",
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        # Date
        ctk.CTkLabel(
            row,
            text=format_date_short(tx.date),
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8",
        ).grid(row=0, column=2, padx=16)

        # Amount
        color  = "#16A34A" if tx.type == "income" else "#DC2626"
        sign   = "+" if tx.type == "income" else "-"
        ctk.CTkLabel(
            row,
            text=f"{sign}{format_money_short(tx.amount_cents)}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=color,
        ).grid(row=0, column=3, padx=(0, 0))