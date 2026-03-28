"""
ui/pages/analytics.py
Analytics page — pie chart by category, bar chart by days, yearly overview.
"""

import customtkinter as ctk
from datetime import date
from calendar import monthrange

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from services.analytics_service import (
    get_spending_by_category, get_daily_totals, get_month_summary
)
from utils.formatters import format_money_short, set_currency
from utils.i18n import t, months_list

# ── Theme colors — (light, dark) tuples ──────────────────────────────────────
BG_PAGE        = ("#F8FAFC", "#1A1A2E")
BG_CARD        = ("#FFFFFF", "#16213E")
BG_HEADER      = ("#FFFFFF", "#0F0F23")
BG_ROW_EVEN    = ("#FFFFFF", "#16213E")
BG_ROW_ODD     = ("#F8FAFC", "#1A1A2E")
BG_BAR         = ("#F1F5F9", "#0F3460")
TEXT_PRIMARY   = ("#1E293B", "#E2E8F0")
TEXT_SECONDARY = ("#64748B", "#94A3B8")
TEXT_MUTED     = ("#94A3B8", "#64748B")

def _is_dark():
    return ctk.get_appearance_mode() == "Dark"

def _chart_bg():
    return "#1A1A2E" if _is_dark() else "white"

def _chart_text():
    return "#94A3B8" if _is_dark() else "#64748B"

def _chart_grid():
    return "#2D2D44" if _is_dark() else "#F1F5F9"

def _chart_spine():
    return "#2D2D44" if _is_dark() else "#E2E8F0"


class AnalyticsPage(ctk.CTkFrame):

    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color=BG_PAGE, corner_radius=0)
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

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=BG_HEADER, corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        ctk.CTkLabel(
            header, text=t("analytics"),
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=32, pady=20, sticky="w")

        self.month_var = ctk.StringVar(value=months_list()[self.month - 1])

        ctk.CTkOptionMenu(
            header,
            values=months_list(),
            variable=self.month_var,
            width=140, height=34, corner_radius=8,
            font=ctk.CTkFont(size=13),
            command=self._on_month_change,
        ).grid(row=0, column=1, padx=32, pady=16, sticky="e")

    def _on_month_change(self, value):
        self.month = months_list().index(value) + 1
        self._refresh()

    def _build_body(self):
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_PAGE, corner_radius=0
        )
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll.grid_columnconfigure(0, weight=1)
        self.update_idletasks()
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
        self._build_yearly_chart(self.scroll)

    def _build_summary_cards(self, summary):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.grid(row=0, column=0, padx=32, pady=(24, 16), sticky="ew")
        row.grid_columnconfigure((0, 1, 2), weight=1)

        cards = [
            (f"📥 {t('income')}",   summary["income_cents"],  "#16A34A"),
            (f"📤 {t('expenses')}", summary["expense_cents"], "#DC2626"),
            (f"🏦 {t('saved')}",    summary["balance_cents"], "#2563EB"),
        ]
        for i, (label, cents, color) in enumerate(cards):
            card = ctk.CTkFrame(row, fg_color=BG_CARD, corner_radius=12)
            card.grid(row=0, column=i, padx=(0 if i == 0 else 12, 0), sticky="ew")

            ctk.CTkLabel(
                card, text=label,
                font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
            ).grid(row=0, column=0, padx=20, pady=(16, 4), sticky="w")

            ctk.CTkLabel(
                card, text=format_money_short(cents),
                font=ctk.CTkFont(size=20, weight="bold"), text_color=color,
            ).grid(row=1, column=0, padx=20, pady=(0, 16), sticky="w")

    def _build_pie_chart(self, categories):
        card = ctk.CTkFrame(self.scroll, fg_color=BG_CARD, corner_radius=12)
        card.grid(row=1, column=0, padx=32, pady=(0, 16), sticky="ew")

        ctk.CTkLabel(
            card, text=t("spending_by_category"),
            font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=24, pady=(20, 12), sticky="w")

        if not categories:
            ctk.CTkLabel(
                card, text=t("no_expense_data"),
                font=ctk.CTkFont(size=13), text_color=TEXT_MUTED,
            ).grid(row=1, column=0, padx=24, pady=(0, 24))
            return

        bg     = _chart_bg()
        labels = [c['category'].name for c in categories]
        sizes  = [c["spent_cents"] for c in categories]
        colors = [c["color"] for c in categories]

        fig, ax = plt.subplots(figsize=(7, 3.6), facecolor=bg)
        ax.set_facecolor(bg)
        wedges, texts, autotexts = ax.pie(
            sizes, labels=None, colors=colors,
            autopct="%1.0f%%", startangle=90,
            pctdistance=0.75,
            wedgeprops={"width": 0.6, "edgecolor": bg, "linewidth": 2},
        )
        for at in autotexts:
            at.set_fontsize(9)
            at.set_color("white")
            at.set_fontweight("bold")

        ax.legend(
            wedges, labels,
            loc="center left", bbox_to_anchor=(1.05, 0.5),
            fontsize=9, frameon=False,
            labelcolor=_chart_text(),
        )
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, padx=24, pady=(0, 20), sticky="ew")
        plt.close(fig)

    def _build_bar_chart(self, daily):
        card = ctk.CTkFrame(self.scroll, fg_color=BG_CARD, corner_radius=12)
        card.grid(row=2, column=0, padx=32, pady=(0, 16), sticky="ew")

        ctk.CTkLabel(
            card, text=t("daily_expenses"),
            font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=24, pady=(20, 12), sticky="w")

        amounts = [d["amount_cents"] / 100 for d in daily]
        labels  = [str(d["date"].day) for d in daily]
        bg      = _chart_bg()
        grid_c  = _chart_grid()
        text_c  = _chart_text()
        empty_c = "#2D2D44" if _is_dark() else "#F1F5F9"

        fig, ax = plt.subplots(figsize=(7, 2.8), facecolor=bg)
        ax.set_facecolor(bg)

        ax.bar(
            range(len(amounts)), amounts,
            color=["#DC2626" if a > 0 else empty_c for a in amounts],
            width=0.7, zorder=2,
        )

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=8, color=text_c)
        ax.tick_params(axis="y", labelsize=8, colors=text_c)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color(grid_c)
        ax.yaxis.grid(True, color=grid_c, zorder=1)
        ax.set_axisbelow(True)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, padx=24, pady=(0, 20), sticky="ew")
        plt.close(fig)

    def _build_category_table(self, categories):
        if not categories:
            return

        card = ctk.CTkFrame(self.scroll, fg_color=BG_CARD, corner_radius=12)
        card.grid(row=3, column=0, padx=32, pady=(0, 16), sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text=t("breakdown"),
            font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, columnspan=3, padx=24, pady=(20, 12), sticky="w")

        for i, c in enumerate(categories):
            bg = BG_ROW_EVEN if i % 2 == 0 else BG_ROW_ODD

            row_f = ctk.CTkFrame(card, fg_color=bg, corner_radius=0)
            row_f.grid(row=i + 1, column=0, columnspan=3, padx=0, pady=0, sticky="ew")
            row_f.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                row_f,
                text=f"{c['icon']}  {c['category'].name}",
                font=ctk.CTkFont(size=13), text_color=TEXT_PRIMARY,
            ).grid(row=0, column=0, padx=24, pady=12, sticky="w")

            bar_bg = ctk.CTkFrame(row_f, fg_color=BG_BAR, corner_radius=3, height=6)
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
                font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_PRIMARY,
                width=160,
            ).grid(row=0, column=2, padx=24, pady=12, sticky="e")

    def _build_yearly_chart(self, parent):
        from services.analytics_service import get_yearly_totals

        data    = get_yearly_totals(self.user, self.year)
        months  = [d["month"] for d in data]
        income  = [d["income"]  / 100 for d in data]
        expense = [d["expense"] / 100 for d in data]

        # Short month labels (always in English for chart axis)
        month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        bg      = _chart_bg()
        text_c  = _chart_text()
        grid_c  = _chart_grid()
        spine_c = _chart_spine()

        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=12)
        card.grid(row=4, column=0, padx=32, pady=(0, 32), sticky="ew")

        ctk.CTkLabel(
            card, text=t("year_overview", self.year),
            font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=24, pady=(20, 12), sticky="w")

        fig, ax = plt.subplots(figsize=(7, 3.5), facecolor=bg)
        ax.set_facecolor(bg)

        ax.plot(months, income,  color="#16A34A", linewidth=2.5,
                marker="o", markersize=5, label=t("income"))
        ax.plot(months, expense, color="#DC2626", linewidth=2.5,
                marker="o", markersize=5, label=t("expenses"))

        ax.fill_between(months, income,  alpha=0.08, color="#16A34A")
        ax.fill_between(months, expense, alpha=0.08, color="#DC2626")

        ax.set_xticks(months)
        ax.set_xticklabels(month_labels, fontsize=9, color=text_c)
        ax.tick_params(axis="y", labelsize=9, colors=text_c)
        ax.yaxis.set_major_formatter(
            ticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " "))
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(spine_c)
        ax.spines["bottom"].set_color(spine_c)
        ax.yaxis.grid(True, color=grid_c, linewidth=1)
        ax.legend(loc="upper right", fontsize=10, framealpha=0, labelcolor=text_c)
        fig.tight_layout(pad=1.5)

        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, padx=24, pady=(0, 20), sticky="ew")
        plt.close(fig)
