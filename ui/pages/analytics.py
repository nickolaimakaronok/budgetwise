"""
ui/pages/analytics.py
Analytics page — pie chart by category, bar chart by days.
"""

import customtkinter as ctk
from datetime import date
from calendar import monthrange

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from services.analytics_service import (
    get_spending_by_category, get_daily_totals, get_month_summary
)
from utils.formatters import format_money_short, set_currency


class AnalyticsPage(ctk.CTkFrame):

    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="#F8FAFC", corner_radius=0)
        self.user  = user
        self.app   = app
        set_currency(user.currency)

        today      = date.today()
        self.year  = today.year
        self.month = today.month

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

        ctk.CTkLabel(
            header, text="Analytics",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#1E293B",
        ).grid(row=0, column=0, padx=32, pady=20, sticky="w")

        # Month selector
        months = [
            "January","February","March","April","May","June",
            "July","August","September","October","November","December"
        ]
        self.month_var = ctk.StringVar(value=months[self.month - 1])

        ctk.CTkOptionMenu(
            header,
            values=months,
            variable=self.month_var,
            width=140, height=34, corner_radius=8,
            font=ctk.CTkFont(size=13),
            command=self._on_month_change,
        ).grid(row=0, column=1, padx=32, pady=16, sticky="e")

    def _on_month_change(self, value):
        months = [
            "January","February","March","April","May","June",
            "July","August","September","October","November","December"
        ]
        self.month = months.index(value) + 1
        self._refresh()

    # ── Body ──────────────────────────────────────────────────────────────────

    def _build_body(self):
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color="#F8FAFC", corner_radius=0
        )
        self.scroll.grid(row=1, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)
        self._render_charts()

    def _refresh(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self._render_charts()

    def _render_charts(self):
        last_day  = monthrange(self.year, self.month)[1]
        date_from = date(self.year, self.month, 1)
        date_to   = date(self.year, self.month, last_day)

        summary    = get_month_summary(self.user, self.year, self.month)
        categories = get_spending_by_category(self.user, date_from, date_to)
        daily      = get_daily_totals(self.user, date_from, date_to)

        self._build_summary_cards(summary)
        self._build_pie_chart(categories)
        self._build_bar_chart(daily)
        self._build_category_table(categories)

    # ── Summary cards ─────────────────────────────────────────────────────────

    def _build_summary_cards(self, summary):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.grid(row=0, column=0, padx=32, pady=(24, 16), sticky="ew")
        row.grid_columnconfigure((0, 1, 2), weight=1)

        cards = [
            ("📥 Income",   summary["income_cents"],  "#16A34A"),
            ("📤 Expenses", summary["expense_cents"], "#DC2626"),
            ("🏦 Saved",    summary["balance_cents"], "#2563EB"),
        ]
        for i, (label, cents, color) in enumerate(cards):
            card = ctk.CTkFrame(row, fg_color="#FFFFFF", corner_radius=12)
            card.grid(row=0, column=i, padx=(0 if i == 0 else 12, 0), sticky="ew")

            ctk.CTkLabel(
                card, text=label,
                font=ctk.CTkFont(size=12), text_color="#64748B",
            ).grid(row=0, column=0, padx=20, pady=(16, 4), sticky="w")

            ctk.CTkLabel(
                card, text=format_money_short(cents),
                font=ctk.CTkFont(size=20, weight="bold"), text_color=color,
            ).grid(row=1, column=0, padx=20, pady=(0, 16), sticky="w")

    # ── Pie chart ─────────────────────────────────────────────────────────────

    def _build_pie_chart(self, categories):
        card = ctk.CTkFrame(self.scroll, fg_color="#FFFFFF", corner_radius=12)
        card.grid(row=1, column=0, padx=32, pady=(0, 16), sticky="ew")

        ctk.CTkLabel(
            card, text="Spending by Category",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#1E293B",
        ).grid(row=0, column=0, padx=24, pady=(20, 12), sticky="w")

        if not categories:
            ctk.CTkLabel(
                card, text="No expense data for this month.",
                font=ctk.CTkFont(size=13), text_color="#94A3B8",
            ).grid(row=1, column=0, padx=24, pady=(0, 24))
            return

        labels = [f"{c['icon']} {c['category'].name}" for c in categories]
        sizes  = [c["spent_cents"] for c in categories]
        colors = [c["color"] for c in categories]

        fig, ax = plt.subplots(figsize=(7, 3.6), facecolor="white")
        wedges, texts, autotexts = ax.pie(
            sizes, labels=None, colors=colors,
            autopct="%1.0f%%", startangle=90,
            pctdistance=0.75,
            wedgeprops={"width": 0.6, "edgecolor": "white", "linewidth": 2},
        )
        for t in autotexts:
            t.set_fontsize(9)
            t.set_color("white")
            t.set_fontweight("bold")

        ax.legend(
            wedges, labels,
            loc="center left", bbox_to_anchor=(0.85, 0.5),
            fontsize=9, frameon=False,
        )
        ax.set_title("")
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, padx=24, pady=(0, 20), sticky="ew")
        plt.close(fig)

    # ── Bar chart ─────────────────────────────────────────────────────────────

    def _build_bar_chart(self, daily):
        card = ctk.CTkFrame(self.scroll, fg_color="#FFFFFF", corner_radius=12)
        card.grid(row=2, column=0, padx=32, pady=(0, 16), sticky="ew")

        ctk.CTkLabel(
            card, text="Daily Expenses",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#1E293B",
        ).grid(row=0, column=0, padx=24, pady=(20, 12), sticky="w")

        amounts = [d["amount_cents"] / 100 for d in daily]
        labels  = [str(d["date"].day) for d in daily]

        fig, ax = plt.subplots(figsize=(7, 2.8), facecolor="white")

        bars = ax.bar(
            range(len(amounts)), amounts,
            color=["#DC2626" if a > 0 else "#F1F5F9" for a in amounts],
            width=0.7, zorder=2,
        )

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=8, color="#64748B")
        ax.tick_params(axis="y", labelsize=8, colors="#64748B")
        ax.spines[["top","right","left"]].set_visible(False)
        ax.spines["bottom"].set_color("#F1F5F9")
        ax.yaxis.grid(True, color="#F1F5F9", zorder=1)
        ax.set_axisbelow(True)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, padx=24, pady=(0, 20), sticky="ew")
        plt.close(fig)

    # ── Category breakdown table ──────────────────────────────────────────────

    def _build_category_table(self, categories):
        if not categories:
            return

        card = ctk.CTkFrame(self.scroll, fg_color="#FFFFFF", corner_radius=12)
        card.grid(row=3, column=0, padx=32, pady=(0, 32), sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text="Breakdown",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#1E293B",
        ).grid(row=0, column=0, columnspan=3, padx=24, pady=(20, 12), sticky="w")

        for i, c in enumerate(categories):
            bg = "#FFFFFF" if i % 2 == 0 else "#F8FAFC"

            row_f = ctk.CTkFrame(card, fg_color=bg, corner_radius=0)
            row_f.grid(row=i + 1, column=0, columnspan=3,
                       padx=0, pady=0, sticky="ew")
            row_f.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                row_f,
                text=f"{c['icon']}  {c['category'].name}",
                font=ctk.CTkFont(size=13), text_color="#1E293B",
            ).grid(row=0, column=0, padx=24, pady=12, sticky="w")

            # Mini progress bar
            bar_bg = ctk.CTkFrame(row_f, fg_color="#F1F5F9", corner_radius=3, height=6)
            bar_bg.grid(row=0, column=1, padx=16, sticky="ew")
            bar_bg.grid_propagate(False)

            pct = c["percent"] / 100
            if pct > 0:
                ctk.CTkFrame(
                    bar_bg, fg_color=c["color"], corner_radius=3, height=6
                ).place(relx=0, rely=0, relwidth=pct, relheight=1)

            ctk.CTkLabel(
                row_f,
                text=f"{format_money_short(c['spent_cents'])}  ·  {c['percent']}%",
                font=ctk.CTkFont(size=13, weight="bold"), text_color="#1E293B",
                width=160,
            ).grid(row=0, column=2, padx=24, pady=12, sticky="e")