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
from utils.formatters import format_money_short, set_currency, percent


class BudgetPage(ctk.CTkFrame):

    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="#F8FAFC", corner_radius=0)
        self.user  = user
        self.app   = app
        set_currency(user.currency)

        today        = date.today()
        self.year    = today.year
        self.month   = today.month

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)

        ctk.CTkLabel(
            header, text="Budget",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#1E293B",
        ).grid(row=0, column=0, padx=32, pady=20, sticky="w")

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=32, pady=12, sticky="e")

        ctk.CTkButton(
            btn_frame, text="Copy last month",
            width=140, height=36, corner_radius=8,
            fg_color="#F1F5F9", hover_color="#E2E8F0",
            text_color="#1E293B",
            font=ctk.CTkFont(size=13),
            command=self._copy_last_month,
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="+ Set Limit",
            width=120, height=36, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._open_set_limit_dialog,
        ).grid(row=0, column=1)

    # ── Body ──────────────────────────────────────────────────────────────────

    def _build_body(self):
        self.body = ctk.CTkScrollableFrame(
            self, fg_color="#F8FAFC", corner_radius=0
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
                text="No budget limits set.\nClick '+ Set Limit' to add one.",
                font=ctk.CTkFont(size=14),
                text_color="#94A3B8",
                justify="center",
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

        card = ctk.CTkFrame(self.body, fg_color="#FFFFFF", corner_radius=12)
        card.grid(row=idx, column=0, sticky="ew", pady=(0, 12))
        card.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, padx=20, pady=(16, 8), sticky="ew")
        top.grid_columnconfigure(1, weight=1)

        # Icon + name
        cat   = row["category"]
        color = status_colors[row["status"]]

        ctk.CTkLabel(
            top, text=f"{cat.icon}  {cat.name}",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#1E293B",
        ).grid(row=0, column=0, sticky="w")

        # Spent / Limit
        ctk.CTkLabel(
            top,
            text=f"{format_money_short(row['spent_cents'])} / {format_money_short(row['limit_cents'])}",
            font=ctk.CTkFont(size=13),
            text_color=color,
        ).grid(row=0, column=1, sticky="e")

        # Delete button
        ctk.CTkButton(
            top, text="✕", width=28, height=28,
            corner_radius=6, fg_color="transparent",
            hover_color="#FEE2E2", text_color="#94A3B8",
            command=lambda b=row["budget"]: self._delete_budget(b),
        ).grid(row=0, column=2, padx=(8, 0))

        # Progress bar
        pct        = min(row["percent"] / 100, 1.0)
        bar_color  = bar_colors[row["status"]]

        bar_bg = ctk.CTkFrame(card, fg_color="#F1F5F9", corner_radius=4, height=8)
        bar_bg.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="ew")
        bar_bg.grid_propagate(False)
        bar_bg.grid_columnconfigure(0, weight=1)

        if pct > 0:
            bar_fill = ctk.CTkFrame(bar_bg, fg_color=bar_color, corner_radius=4, height=8)
            bar_fill.place(relx=0, rely=0, relwidth=pct, relheight=1)

        # Bottom: left + percent
        ctk.CTkLabel(
            card,
            text=f"Left: {format_money_short(row['left_cents'])}  ·  {row['percent']}%",
            font=ctk.CTkFont(size=12),
            text_color="#64748B",
        ).grid(row=2, column=0, padx=20, pady=(0, 16), sticky="w")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _open_set_limit_dialog(self):
        SetLimitDialog(self, self.user, self.year, self.month, on_save=self._load_rows)

    def _copy_last_month(self):
        copied = copy_budgets_from_previous_month(self.user, self.year, self.month)
        if copied:
            self._load_rows()
        else:
            messagebox.showinfo("Copy last month", "No budget limits found in previous month.")

    def _delete_budget(self, budget):
        ok = messagebox.askyesno("Delete limit", "Remove this budget limit?")
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

        self.title("Set Budget Limit")
        self.geometry("380x320")
        self.resizable(False, False)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        pad = {"padx": 28, "sticky": "ew"}

        ctk.CTkLabel(self, text="Category", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=0, column=0, padx=28, pady=(28, 4), sticky="w")

        categories  = list(Category.select().where(
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

        ctk.CTkLabel(self, text="Monthly Limit", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=2, column=0, padx=28, pady=(16, 4), sticky="w")

        self.limit_entry = ctk.CTkEntry(
            self, placeholder_text="500.00",
            font=ctk.CTkFont(size=22, weight="bold"),
            height=52, corner_radius=8,
        )
        self.limit_entry.grid(row=3, column=0, **pad)
        self.limit_entry.focus()

        ctk.CTkButton(
            self, text="Save Limit",
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
            messagebox.showerror("Error", "Invalid amount. Enter a number like 500.00")
            return

        category = self.cat_map.get(self.cat_var.get())
        set_budget(self.user, category, limit_cents, self.year, self.month)
        self.on_save()
        self.destroy()