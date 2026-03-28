"""
ui/pages/budget.py
Budget page — set limits per category, see spending vs limit.
"""

import customtkinter as ctk
from datetime import date
from tkinter import messagebox
from services.budget_service import (
    get_budget_status, set_budget, delete_budget,
    copy_budgets_from_previous_month
)
from models.models import Category
from utils.formatters import format_money_short, set_currency
from utils.i18n import t, months_list

# ── Theme colors — (light, dark) tuples ──────────────────────────────────────
BG_PAGE        = ("#F8FAFC", "#1A1A2E")
BG_CARD        = ("#FFFFFF", "#16213E")
BG_HEADER      = ("#FFFFFF", "#0F0F23")
BG_BAR         = ("#F1F5F9", "#0F3460")
BG_TOGGLE      = ("#F1F5F9", "#0F3460")
TEXT_PRIMARY   = ("#1E293B", "#E2E8F0")
TEXT_SECONDARY = ("#64748B", "#94A3B8")
TEXT_MUTED     = ("#94A3B8", "#64748B")
HOVER_RED      = ("#FEE2E2", "#3D1A1A")
BTN_SECONDARY  = ("#F1F5F9", "#0F3460")
BTN_SECONDARY_HOVER = ("#E2E8F0", "#1A4A7A")


class BudgetPage(ctk.CTkFrame):

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
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)

        ctk.CTkLabel(
            header, text=t("budget"),
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
        ).grid(row=0, column=1, padx=0, pady=16)

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=32, pady=12, sticky="e")

        ctk.CTkButton(
            btn_frame, text=t("copy_last_month"),
            width=140, height=36, corner_radius=8,
            fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
            command=self._copy_last_month,
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text=t("set_limit"),
            width=120, height=36, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._open_set_limit_dialog,
        ).grid(row=0, column=1)

    def _on_month_change(self, value):
        self.month = months_list().index(value) + 1
        self._load_rows()

    def _build_body(self):
        self.body = ctk.CTkScrollableFrame(
            self, fg_color=BG_PAGE, corner_radius=0
        )
        self.body.grid(row=1, column=0, sticky="nsew", padx=32, pady=16)
        self.body.grid_columnconfigure(0, weight=1)
        self._load_rows()

    def _load_rows(self):
        for w in self.body.winfo_children():
            w.destroy()

        rows = get_budget_status(self.user, self.year, self.month)

        if not rows:
            ctk.CTkLabel(
                self.body,
                text=t("no_budget_limits"),
                font=ctk.CTkFont(size=14), text_color=TEXT_MUTED, justify="center",
            ).grid(row=0, column=0, pady=60)
            return

        for i, row in enumerate(rows):
            self._budget_row(i, row)

    def _budget_row(self, idx, row):
        status_colors = {
            "ok":      "#16A34A",
            "warning": "#D97706",
            "danger":  "#DC2626",
        }
        bar_colors = {
            "ok":      "#16A34A",
            "warning": "#F59E0B",
            "danger":  "#DC2626",
        }

        card = ctk.CTkFrame(self.body, fg_color=BG_CARD, corner_radius=12)
        card.grid(row=idx, column=0, sticky="ew", pady=(0, 12))
        card.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, padx=20, pady=(16, 8), sticky="ew")
        top.grid_columnconfigure(1, weight=1)

        cat   = row["category"]
        color = status_colors[row["status"]]

        ctk.CTkLabel(
            top, text=f"{cat.icon}  {cat.name}",
            font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            top,
            text=f"{format_money_short(row['spent_cents'])} / {format_money_short(row['limit_cents'])}",
            font=ctk.CTkFont(size=13), text_color=color,
        ).grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            top, text="✕", width=28, height=28, corner_radius=6,
            fg_color="transparent", hover_color=HOVER_RED, text_color=TEXT_MUTED,
            command=lambda b=row["budget"]: self._delete_budget(b),
        ).grid(row=0, column=2, padx=(8, 0))

        pct       = min(row["percent"] / 100, 1.0)
        bar_color = bar_colors[row["status"]]

        bar_bg = ctk.CTkFrame(card, fg_color=BG_BAR, corner_radius=4, height=8)
        bar_bg.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="ew")
        bar_bg.grid_propagate(False)
        bar_bg.grid_columnconfigure(0, weight=1)

        if pct > 0:
            bar_fill = ctk.CTkFrame(bar_bg, fg_color=bar_color, corner_radius=4, height=8)
            bar_fill.place(relx=0, rely=0, relwidth=pct, relheight=1)

        ctk.CTkLabel(
            card,
            text=f"{t('left')} {format_money_short(row['left_cents'])}  ·  {row['percent']}%",
            font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
        ).grid(row=2, column=0, padx=20, pady=(0, 16), sticky="w")

    def _open_set_limit_dialog(self):
        SetLimitDialog(self, self.user, self.year, self.month, on_save=self._load_rows)

    def _copy_last_month(self):
        copied = copy_budgets_from_previous_month(self.user, self.year, self.month)
        if copied:
            self._load_rows()
        else:
            messagebox.showinfo(t("copy_last_month_title"), t("no_prev_month"))

    def _delete_budget(self, budget):
        ok = messagebox.askyesno(t("delete_limit"), t("remove_limit_confirm"))
        if ok:
            delete_budget(budget)
            self._load_rows()


# ── Set Limit Dialog ──────────────────────────────────────────────────────────

class SetLimitDialog(ctk.CTkToplevel):

    def __init__(self, parent, user, year, month, on_save):
        super().__init__(parent)
        self.user    = user
        self.year    = year
        self.month   = month
        self.on_save = on_save

        self.title(t("set_budget_title"))
        self.geometry("380x320")
        self.resizable(False, False)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        pad = {"padx": 28, "sticky": "ew"}

        ctk.CTkLabel(self, text=t("category_label"), font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=0, column=0, padx=28, pady=(28, 4), sticky="w")

        categories = list(Category.select().where(
            (Category.user == self.user) | (Category.user.is_null()),
            Category.type == "expense",
        ).order_by(Category.name))

        self.cat_map = {f"{c.icon} {c.name}": c for c in categories}
        self.cat_var = ctk.StringVar(value=list(self.cat_map.keys())[0])

        ctk.CTkOptionMenu(
            self, values=list(self.cat_map.keys()),
            variable=self.cat_var,
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        ).grid(row=1, column=0, **pad)

        ctk.CTkLabel(self, text=t("monthly_limit"), font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=2, column=0, padx=28, pady=(16, 4), sticky="w")

        self.limit_entry = ctk.CTkEntry(
            self, placeholder_text="500.00",
            font=ctk.CTkFont(size=22, weight="bold"),
            height=52, corner_radius=8,
        )
        self.limit_entry.grid(row=3, column=0, **pad)
        self.limit_entry.focus()

        ctk.CTkButton(
            self, text=t("save_limit"),
            height=48, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._save,
        ).grid(row=4, column=0, padx=28, pady=28, sticky="ew")

    def _save(self):
        from utils.formatters import parse_money
        try:
            limit_cents = parse_money(self.limit_entry.get())
        except ValueError:
            messagebox.showerror(t("error"), t("invalid_limit"))
            return

        category = self.cat_map.get(self.cat_var.get())
        set_budget(self.user, category, limit_cents, self.year, self.month)
        self.on_save()
        self.destroy()
