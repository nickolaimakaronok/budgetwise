"""
ui/pages/dashboard.py
Dashboard page — balance, monthly summary, recent transactions.
"""

import customtkinter as ctk
from datetime import date
from services.analytics_service import get_month_summary
from services.transaction_service import get_recent_transactions
from utils.formatters import format_money, format_money_short, format_date_short, set_currency

# ── Theme colors — (light, dark) tuples ──────────────────────────────────────
BG_PAGE        = ("#F8FAFC", "#1A1A2E")
BG_CARD        = ("#FFFFFF", "#16213E")
BG_HEADER      = ("#FFFFFF", "#0F0F23")
BG_BALANCE     = ("#1E293B", "#0F0F23")
TEXT_PRIMARY   = ("#1E293B", "#E2E8F0")
TEXT_SECONDARY = ("#64748B", "#94A3B8")
TEXT_MUTED     = ("#94A3B8", "#64748B")
DIVIDER        = ("#F1F5F9", "#2D2D44")
HOVER_BLUE     = ("#EFF6FF", "#1E3A5F")


class DashboardPage(ctk.CTkFrame):

    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color=BG_PAGE, corner_radius=0)
        self.user = user
        self.app  = app

        set_currency(user.currency)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=BG_HEADER, corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        today = date.today()

        ctk.CTkLabel(
            header,
            text="Dashboard",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=32, pady=20, sticky="w")

        ctk.CTkLabel(
            header,
            text=today.strftime("%B %Y"),
            font=ctk.CTkFont(size=14),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=1, padx=32, pady=20, sticky="e")

    # ── Body ──────────────────────────────────────────────────────────────────

    def _build_body(self):
        body = ctk.CTkScrollableFrame(
            self, fg_color=BG_PAGE, corner_radius=0
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
        card = ctk.CTkFrame(parent, fg_color=BG_BALANCE, corner_radius=16)
        card.grid(row=0, column=0, padx=32, pady=(28, 16), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="Monthly Balance",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_MUTED,
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
            text_color=TEXT_SECONDARY,
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
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=12)
        card.grid(row=0, column=col, padx=(0 if col == 0 else 12, 0), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text=f"{emoji}  {label}",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
        ).grid(row=0, column=0, padx=20, pady=(18, 4), sticky="w")

        ctk.CTkLabel(
            card,
            text=format_money_short(amount_cents),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=color,
        ).grid(row=1, column=0, padx=20, pady=(0, 18), sticky="w")

    # ── Recent transactions ───────────────────────────────────────────────────

    def _build_recent_transactions(self, parent):
        title_row = ctk.CTkFrame(parent, fg_color="transparent")
        title_row.grid(row=2, column=0, padx=32, pady=(8, 12), sticky="ew")
        title_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_row,
            text="Recent Transactions",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            title_row,
            text="See all →",
            width=80, height=28, corner_radius=6,
            fg_color="transparent",
            text_color=("#2563EB", "#3B82F6"),
            hover_color=HOVER_BLUE,
            font=ctk.CTkFont(size=13),
            command=lambda: self.app.show_page("transactions"),
        ).grid(row=0, column=1, sticky="e")

        txs = get_recent_transactions(self.user, limit=5)

        container = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=12)
        container.grid(row=3, column=0, padx=32, pady=(0, 32), sticky="ew")
        container.grid_columnconfigure(0, weight=1)

        if not txs:
            ctk.CTkLabel(
                container,
                text="No transactions yet.\nAdd your first one!",
                font=ctk.CTkFont(size=14),
                text_color=TEXT_MUTED,
                justify="center",
            ).grid(row=0, column=0, padx=20, pady=40)
            return

        for i, tx in enumerate(txs):
            self._transaction_row(container, i, tx, is_last=(i == len(txs) - 1))

    def _transaction_row(self, parent, row_idx, tx, is_last: bool):
        grid_row = row_idx * 2

        if row_idx > 0:
            divider = ctk.CTkFrame(parent, fg_color=DIVIDER, height=1)
            divider.grid(row=grid_row - 1, column=0, padx=20, sticky="ew")

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=grid_row, column=0, padx=20, pady=0, sticky="ew")
        row.grid_columnconfigure(1, weight=1)

        icon = tx.category.icon if tx.category else "💳"
        ctk.CTkLabel(
            row, text=icon,
            font=ctk.CTkFont(size=22),
            width=40,
            fg_color="transparent",
        ).grid(row=0, column=0, padx=(0, 12), pady=14)

        name = tx.category.name if tx.category else "Uncategorized"
        note = f"  {tx.note}" if tx.note else ""
        ctk.CTkLabel(
            row, text=f"{name}{note}",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            row, text=format_date_short(tx.date),
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=2, padx=16)

        color = "#16A34A" if tx.type == "income" else "#DC2626"
        sign  = "+" if tx.type == "income" else "\u2212"
        ctk.CTkLabel(
            row,
            text=f"{sign}{format_money_short(tx.amount_cents)}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=color,
        ).grid(row=0, column=3, padx=(0, 0))
