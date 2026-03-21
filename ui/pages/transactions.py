"""
ui/pages/transactions.py
Transactions page — table with all transactions + add/edit/delete/filter/export.
"""

import csv
import os
import customtkinter as ctk
from datetime import date
from tkinter import messagebox, filedialog
from services.transaction_service import get_transactions, delete_transaction, update_transaction
from models.models import Category
from utils.formatters import format_money_short, format_date, set_currency, parse_money, parse_date


class TransactionsPage(ctk.CTkFrame):

    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="#F8FAFC", corner_radius=0)
        self.user = user
        self.app  = app
        set_currency(user.currency)

        # Active filters
        self.filter_type     = "all"     # "all" | "income" | "expense"
        self.filter_category = None      # Category object or None
        self.filter_date_from = None
        self.filter_date_to   = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_filters()
        self._build_table()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        ctk.CTkLabel(
            header, text="Transactions",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#1E293B",
        ).grid(row=0, column=0, padx=32, pady=20, sticky="w")

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=32, pady=16, sticky="e")

        # Export CSV button
        ctk.CTkButton(
            btn_frame, text="⬇ Export CSV",
            width=130, height=36, corner_radius=8,
            fg_color="#F1F5F9", hover_color="#E2E8F0",
            text_color="#1E293B",
            font=ctk.CTkFont(size=13),
            command=self._export_csv,
        ).grid(row=0, column=0, padx=(0, 8))

        # Add transaction button
        ctk.CTkButton(
            btn_frame, text="+ Add Transaction",
            width=160, height=36, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._open_add_dialog,
        ).grid(row=0, column=1)

    # ── Filters ───────────────────────────────────────────────────────────────

    def _build_filters(self):
        filters = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=56)
        filters.grid(row=1, column=0, sticky="ew")
        filters.grid_propagate(False)
        filters.grid_columnconfigure(4, weight=1)

        # Type filter
        self.type_var = ctk.StringVar(value="All")
        ctk.CTkSegmentedButton(
            filters,
            values=["All", "Income", "Expense"],
            variable=self.type_var,
            font=ctk.CTkFont(size=12),
            width=200, height=32,
            command=self._on_type_filter,
        ).grid(row=0, column=0, padx=(32, 12), pady=12)

        # Category filter
        categories = list(Category.select().where(
            (Category.user == self.user) | (Category.user.is_null())
        ).order_by(Category.name))
        self.cat_options = {"All categories": None}
        for c in categories:
            self.cat_options[f"{c.icon} {c.name}"] = c

        self.cat_var = ctk.StringVar(value="All categories")
        ctk.CTkOptionMenu(
            filters,
            values=list(self.cat_options.keys()),
            variable=self.cat_var,
            width=180, height=32, corner_radius=6,
            font=ctk.CTkFont(size=12),
            command=self._on_category_filter,
        ).grid(row=0, column=1, padx=(0, 12), pady=12)

        # Date from
        ctk.CTkLabel(
            filters, text="From:",
            font=ctk.CTkFont(size=12), text_color="#64748B",
        ).grid(row=0, column=2, padx=(0, 4), pady=12)

        self.date_from_entry = ctk.CTkEntry(
            filters, placeholder_text="DD.MM.YYYY",
            width=110, height=32, corner_radius=6,
            font=ctk.CTkFont(size=12),
        )
        self.date_from_entry.grid(row=0, column=3, padx=(0, 8), pady=12)

        # Date to
        ctk.CTkLabel(
            filters, text="To:",
            font=ctk.CTkFont(size=12), text_color="#64748B",
        ).grid(row=0, column=4, padx=(0, 4), pady=12, sticky="e")

        self.date_to_entry = ctk.CTkEntry(
            filters, placeholder_text="DD.MM.YYYY",
            width=110, height=32, corner_radius=6,
            font=ctk.CTkFont(size=12),
        )
        self.date_to_entry.grid(row=0, column=5, padx=(0, 8), pady=12)

        # Apply filter button
        ctk.CTkButton(
            filters, text="Apply",
            width=70, height=32, corner_radius=6,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._apply_date_filter,
        ).grid(row=0, column=6, padx=(0, 8), pady=12)

        # Reset filters button
        ctk.CTkButton(
            filters, text="Reset",
            width=70, height=32, corner_radius=6,
            fg_color="#F1F5F9", hover_color="#E2E8F0",
            text_color="#64748B",
            font=ctk.CTkFont(size=12),
            command=self._reset_filters,
        ).grid(row=0, column=7, padx=(0, 32), pady=12)

    def _on_type_filter(self, value):
        self.filter_type = value.lower()
        self._load_rows()

    def _on_category_filter(self, value):
        self.filter_category = self.cat_options.get(value)
        self._load_rows()

    def _apply_date_filter(self):
        from_text = self.date_from_entry.get().strip()
        to_text   = self.date_to_entry.get().strip()
        try:
            self.filter_date_from = parse_date(from_text) if from_text else None
        except ValueError:
            messagebox.showerror("Error", "Invalid 'From' date. Use DD.MM.YYYY")
            return
        try:
            self.filter_date_to = parse_date(to_text) if to_text else None
        except ValueError:
            messagebox.showerror("Error", "Invalid 'To' date. Use DD.MM.YYYY")
            return
        self._load_rows()

    def _reset_filters(self):
        self.filter_type      = "all"
        self.filter_category  = None
        self.filter_date_from = None
        self.filter_date_to   = None
        self.type_var.set("All")
        self.cat_var.set("All categories")
        self.date_from_entry.delete(0, "end")
        self.date_to_entry.delete(0, "end")
        self._load_rows()

    # ── Table ─────────────────────────────────────────────────────────────────

    def _build_table(self):
        headers_frame = ctk.CTkFrame(self, fg_color="#F1F5F9", corner_radius=0, height=40)
        headers_frame.grid(row=2, column=0, sticky="ew", padx=32, pady=(8, 0))
        headers_frame.grid_propagate(False)
        headers_frame.grid_columnconfigure(1, weight=1)

        for col, (text, width) in enumerate([
            ("",         40),
            ("Category",  0),
            ("Date",    100),
            ("Note",    180),
            ("Amount",  120),
            ("",        120),  # actions column — wider for two buttons
        ]):
            ctk.CTkLabel(
                headers_frame, text=text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#64748B", width=width, anchor="w",
            ).grid(row=0, column=col, padx=(12 if col == 0 else 8, 8), pady=10, sticky="w")

        self.rows_frame = ctk.CTkScrollableFrame(
            self, fg_color="#FFFFFF", corner_radius=12
        )
        self.rows_frame.grid(row=3, column=0, sticky="nsew", padx=32, pady=(0, 32))
        self.rows_frame.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._load_rows()

    def _load_rows(self):
        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        type_filter = None if self.filter_type == "all" else self.filter_type

        txs = get_transactions(
            self.user,
            date_from=self.filter_date_from,
            date_to=self.filter_date_to,
            type=type_filter,
            category=self.filter_category,
        )

        if not txs:
            ctk.CTkLabel(
                self.rows_frame,
                text="No transactions found.",
                font=ctk.CTkFont(size=14),
                text_color="#94A3B8",
            ).grid(row=0, column=0, columnspan=6, pady=48)
            return

        for i, tx in enumerate(txs):
            bg = "#FFFFFF" if i % 2 == 0 else "#F8FAFC"
            self._transaction_row(i, tx, bg)

    def _transaction_row(self, row_idx, tx, bg):
        f = ctk.CTkFrame(self.rows_frame, fg_color=bg, corner_radius=0, height=52)
        f.grid(row=row_idx, column=0, columnspan=6, sticky="ew", pady=0)
        f.grid_columnconfigure(1, weight=1)
        f.grid_propagate(False)

        icon = tx.category.icon if tx.category else "💳"
        name = tx.category.name if tx.category else "Uncategorized"

        ctk.CTkLabel(f, text=icon, font=ctk.CTkFont(size=18), width=40
                     ).grid(row=0, column=0, padx=(16, 4), pady=14)
        ctk.CTkLabel(f, text=name, font=ctk.CTkFont(size=14),
                     text_color="#1E293B", anchor="w"
                     ).grid(row=0, column=1, padx=8, sticky="w")
        ctk.CTkLabel(f, text=format_date(tx.date), font=ctk.CTkFont(size=13),
                     text_color="#64748B", width=100
                     ).grid(row=0, column=2, padx=8)
        ctk.CTkLabel(f, text=tx.note[:28] + "…" if len(tx.note) > 28 else tx.note,
                     font=ctk.CTkFont(size=13), text_color="#94A3B8", width=180, anchor="w"
                     ).grid(row=0, column=3, padx=8, sticky="w")

        color = "#16A34A" if tx.type == "income" else "#DC2626"
        sign  = "+" if tx.type == "income" else "-"
        ctk.CTkLabel(
            f, text=f"{sign}{format_money_short(tx.amount_cents)}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=color, width=120,
        ).grid(row=0, column=4, padx=8)

        # Action buttons frame
        action_frame = ctk.CTkFrame(f, fg_color="transparent")
        action_frame.grid(row=0, column=5, padx=(4, 16))

        # Edit button
        ctk.CTkButton(
            action_frame, text="✏️", width=32, height=28,
            corner_radius=6, fg_color="transparent",
            hover_color="#EFF6FF", text_color="#2563EB",
            command=lambda t=tx: self._open_edit_dialog(t),
        ).grid(row=0, column=0, padx=(0, 4))

        # Delete button
        ctk.CTkButton(
            action_frame, text="🗑", width=32, height=28,
            corner_radius=6, fg_color="transparent",
            hover_color="#FEE2E2", text_color="#DC2626",
            command=lambda t=tx: self._delete(t),
        ).grid(row=0, column=1)

    # ── Export CSV ────────────────────────────────────────────────────────────

    def _export_csv(self):
        # Ask user where to save
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="transactions.csv",
            title="Export transactions to CSV",
        )
        if not filepath:
            return  # user cancelled

        type_filter = None if self.filter_type == "all" else self.filter_type
        txs = get_transactions(
            self.user,
            date_from=self.filter_date_from,
            date_to=self.filter_date_to,
            type=type_filter,
            category=self.filter_category,
        )

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Header row
            writer.writerow(["Date", "Type", "Category", "Amount", "Note"])
            # Data rows
            for tx in txs:
                writer.writerow([
                    format_date(tx.date),
                    tx.type,
                    tx.category.name if tx.category else "Uncategorized",
                    tx.amount_cents / 100,
                    tx.note,
                ])

        messagebox.showinfo("Export complete", f"Saved {len(txs)} transactions to:\n{filepath}")

    # ── Dialogs ───────────────────────────────────────────────────────────────

    def _open_add_dialog(self):
        AddTransactionDialog(self, self.user, on_save=self._load_rows)

    def _open_edit_dialog(self, tx):
        EditTransactionDialog(self, self.user, tx, on_save=self._load_rows)

    def _delete(self, tx):
        ok = messagebox.askyesno(
            "Delete transaction",
            f"Delete this transaction?\n"
            f"{tx.category.name if tx.category else 'Uncategorized'} "
            f"— {format_money_short(tx.amount_cents)}",
        )
        if ok:
            delete_transaction(tx)
            self._load_rows()


# ── Add Transaction Dialog ────────────────────────────────────────────────────

class AddTransactionDialog(ctk.CTkToplevel):

    def __init__(self, parent, user, on_save):
        super().__init__(parent)
        self.user    = user
        self.on_save = on_save

        self.title("Add Transaction")
        self.geometry("420x520")
        self.resizable(False, False)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        pad = {"padx": 28, "sticky": "ew"}

        self.type_var = ctk.StringVar(value="expense")
        toggle = ctk.CTkFrame(self, fg_color="#F1F5F9", corner_radius=8)
        toggle.grid(row=0, column=0, padx=28, pady=(28, 0), sticky="ew")
        toggle.grid_columnconfigure((0, 1), weight=1)
        for col, (label, val) in enumerate([("Expense", "expense"), ("Income", "income")]):
            ctk.CTkRadioButton(
                toggle, text=label, variable=self.type_var, value=val,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=col, padx=16, pady=12)

        ctk.CTkLabel(self, text="Amount", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=1, column=0, padx=28, pady=(20, 4), sticky="w")
        self.amount_entry = ctk.CTkEntry(
            self, placeholder_text="0.00",
            font=ctk.CTkFont(size=22, weight="bold"),
            height=52, corner_radius=8,
        )
        self.amount_entry.grid(row=2, column=0, **pad)
        self.amount_entry.focus()

        ctk.CTkLabel(self, text="Category", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=3, column=0, padx=28, pady=(16, 4), sticky="w")
        categories = list(Category.select().where(
            (Category.user == self.user) | (Category.user.is_null())
        ).order_by(Category.name))
        self.cat_map = {f"{c.icon} {c.name}": c for c in categories}
        self.cat_var = ctk.StringVar(value=list(self.cat_map.keys())[0])
        ctk.CTkOptionMenu(
            self, values=list(self.cat_map.keys()),
            variable=self.cat_var,
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        ).grid(row=4, column=0, **pad)

        ctk.CTkLabel(self, text="Date", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=5, column=0, padx=28, pady=(16, 4), sticky="w")
        self.date_entry = ctk.CTkEntry(
            self, placeholder_text="DD.MM.YYYY",
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.date_entry.insert(0, date.today().strftime("%d.%m.%Y"))
        self.date_entry.grid(row=6, column=0, **pad)

        ctk.CTkLabel(self, text="Note (optional)", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=7, column=0, padx=28, pady=(16, 4), sticky="w")
        self.note_entry = ctk.CTkEntry(
            self, placeholder_text="e.g. Weekly groceries",
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.note_entry.grid(row=8, column=0, **pad)

        ctk.CTkButton(
            self, text="Save Transaction",
            height=48, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._save,
        ).grid(row=9, column=0, padx=28, pady=28, sticky="ew")

    def _save(self):
        from services.transaction_service import add_transaction
        try:
            amount_cents = parse_money(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid amount. Enter a number like 150.50")
            return
        try:
            tx_date = parse_date(self.date_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid date. Use DD.MM.YYYY format")
            return

        category = self.cat_map.get(self.cat_var.get())
        add_transaction(
            user=self.user,
            type=self.type_var.get(),
            amount_cents=amount_cents,
            category=category,
            tx_date=tx_date,
            note=self.note_entry.get(),
        )
        self.on_save()
        self.destroy()


# ── Edit Transaction Dialog ───────────────────────────────────────────────────

class EditTransactionDialog(ctk.CTkToplevel):

    def __init__(self, parent, user, tx, on_save):
        super().__init__(parent)
        self.user    = user
        self.tx      = tx
        self.on_save = on_save

        self.title("Edit Transaction")
        self.geometry("420x520")
        self.resizable(False, False)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        pad = {"padx": 28, "sticky": "ew"}

        # Type toggle — pre-filled with current type
        self.type_var = ctk.StringVar(value=self.tx.type)
        toggle = ctk.CTkFrame(self, fg_color="#F1F5F9", corner_radius=8)
        toggle.grid(row=0, column=0, padx=28, pady=(28, 0), sticky="ew")
        toggle.grid_columnconfigure((0, 1), weight=1)
        for col, (label, val) in enumerate([("Expense", "expense"), ("Income", "income")]):
            ctk.CTkRadioButton(
                toggle, text=label, variable=self.type_var, value=val,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=col, padx=16, pady=12)

        # Amount — pre-filled
        ctk.CTkLabel(self, text="Amount", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=1, column=0, padx=28, pady=(20, 4), sticky="w")
        self.amount_entry = ctk.CTkEntry(
            self, font=ctk.CTkFont(size=22, weight="bold"),
            height=52, corner_radius=8,
        )
        self.amount_entry.insert(0, str(self.tx.amount_cents / 100))
        self.amount_entry.grid(row=2, column=0, **pad)
        self.amount_entry.focus()

        # Category — pre-filled
        ctk.CTkLabel(self, text="Category", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=3, column=0, padx=28, pady=(16, 4), sticky="w")
        categories = list(Category.select().where(
            (Category.user == self.user) | (Category.user.is_null())
        ).order_by(Category.name))
        self.cat_map = {f"{c.icon} {c.name}": c for c in categories}

        # Find current category in options
        current_cat_key = list(self.cat_map.keys())[0]
        if self.tx.category:
            for key, cat in self.cat_map.items():
                if cat.id == self.tx.category_id:
                    current_cat_key = key
                    break

        self.cat_var = ctk.StringVar(value=current_cat_key)
        ctk.CTkOptionMenu(
            self, values=list(self.cat_map.keys()),
            variable=self.cat_var,
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        ).grid(row=4, column=0, **pad)

        # Date — pre-filled
        ctk.CTkLabel(self, text="Date", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=5, column=0, padx=28, pady=(16, 4), sticky="w")
        self.date_entry = ctk.CTkEntry(
            self, font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.date_entry.insert(0, self.tx.date.strftime("%d.%m.%Y"))
        self.date_entry.grid(row=6, column=0, **pad)

        # Note — pre-filled
        ctk.CTkLabel(self, text="Note (optional)", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=7, column=0, padx=28, pady=(16, 4), sticky="w")
        self.note_entry = ctk.CTkEntry(
            self, font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.note_entry.insert(0, self.tx.note)
        self.note_entry.grid(row=8, column=0, **pad)

        ctk.CTkButton(
            self, text="Save Changes",
            height=48, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._save,
        ).grid(row=9, column=0, padx=28, pady=28, sticky="ew")

    def _save(self):
        try:
            amount_cents = parse_money(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid amount. Enter a number like 150.50")
            return
        try:
            tx_date = parse_date(self.date_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid date. Use DD.MM.YYYY format")
            return

        category = self.cat_map.get(self.cat_var.get())
        update_transaction(
            self.tx,
            amount_cents=amount_cents,
            category=category,
            tx_date=tx_date,
            note=self.note_entry.get(),
            type=self.type_var.get(),
        )
        self.on_save()
        self.destroy()