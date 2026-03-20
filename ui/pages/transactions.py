"""
ui/pages/transactions.py
Transactions page — table with all transactions + add/edit/delete.
"""

import customtkinter as ctk
from datetime import date
from tkinter import messagebox
from services.transaction_service import get_transactions, delete_transaction
from models.models import Category
from utils.formatters import format_money_short, format_date, set_currency


class TransactionsPage(ctk.CTkFrame):

    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="#F8FAFC", corner_radius=0)
        self.user = user
        self.app  = app
        set_currency(user.currency)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_table()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        # White top bar with page title and Add button
        header = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        ctk.CTkLabel(
            header,
            text="Transactions",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#1E293B",
        ).grid(row=0, column=0, padx=32, pady=20, sticky="w")

        # Opens the AddTransactionDialog popup
        ctk.CTkButton(
            header,
            text="+ Add Transaction",
            width=160, height=36, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._open_add_dialog,
        ).grid(row=0, column=1, padx=32, pady=16, sticky="e")

    # ── Table ─────────────────────────────────────────────────────────────────

    def _build_table(self):
        # Fixed-height grey row showing column names
        headers_frame = ctk.CTkFrame(self, fg_color="#F1F5F9", corner_radius=0, height=40)
        headers_frame.grid(row=1, column=0, sticky="ew", padx=32, pady=(16, 0))
        headers_frame.grid_propagate(False)
        headers_frame.grid_columnconfigure(1, weight=1)  # Category column stretches

        for col, (text, width) in enumerate([
            ("",         40),   # icon column — no label needed
            ("Category",  0),   # stretches to fill remaining space
            ("Date",     100),
            ("Note",     180),
            ("Amount",   120),
            ("",          80),  # delete button column
        ]):
            ctk.CTkLabel(
                headers_frame,
                text=text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#64748B",
                width=width,
                anchor="w",
            ).grid(row=0, column=col, padx=(12 if col == 0 else 8, 8), pady=10, sticky="w")

        # Scrollable area that holds the actual transaction rows
        self.rows_frame = ctk.CTkScrollableFrame(
            self, fg_color="#FFFFFF", corner_radius=12
        )
        self.rows_frame.grid(row=2, column=0, sticky="nsew", padx=32, pady=(0, 32))
        self.rows_frame.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)  # rows_frame expands to fill the window

        self._load_rows()

    def _load_rows(self):
        # Clear all existing rows before re-rendering
        # Called on first load and after every add / delete
        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        txs = get_transactions(self.user)

        if not txs:
            # Empty state shown when there are no transactions yet
            ctk.CTkLabel(
                self.rows_frame,
                text="No transactions yet. Click '+ Add Transaction' to get started.",
                font=ctk.CTkFont(size=14),
                text_color="#94A3B8",
            ).grid(row=0, column=0, columnspan=6, pady=48)
            return

        # Alternate row background for readability (zebra striping)
        for i, tx in enumerate(txs):
            bg = "#FFFFFF" if i % 2 == 0 else "#F8FAFC"
            self._transaction_row(i, tx, bg)

    def _transaction_row(self, row_idx, tx, bg):
        # Fixed-height frame for one transaction row
        f = ctk.CTkFrame(self.rows_frame, fg_color=bg, corner_radius=0, height=52)
        f.grid(row=row_idx, column=0, columnspan=6, sticky="ew", pady=0)
        f.grid_columnconfigure(1, weight=1)
        f.grid_propagate(False)  # keeps row height fixed at 52px

        icon = tx.category.icon if tx.category else "💳"
        name = tx.category.name if tx.category else "Uncategorized"

        # Category emoji icon
        ctk.CTkLabel(f, text=icon, font=ctk.CTkFont(size=18), width=40
                     ).grid(row=0, column=0, padx=(16, 4), pady=14)

        # Category name — stretches to fill available space
        ctk.CTkLabel(f, text=name, font=ctk.CTkFont(size=14),
                     text_color="#1E293B", anchor="w"
                     ).grid(row=0, column=1, padx=8, sticky="w")

        # Date formatted as DD.MM.YYYY
        ctk.CTkLabel(f, text=format_date(tx.date), font=ctk.CTkFont(size=13),
                     text_color="#64748B", width=100
                     ).grid(row=0, column=2, padx=8)

        # Note truncated at 28 characters to avoid overflow
        ctk.CTkLabel(f, text=tx.note[:28] + "…" if len(tx.note) > 28 else tx.note,
                     font=ctk.CTkFont(size=13), text_color="#94A3B8", width=180, anchor="w"
                     ).grid(row=0, column=3, padx=8, sticky="w")

        # Amount: green for income, red for expense
        color = "#16A34A" if tx.type == "income" else "#DC2626"
        sign  = "+" if tx.type == "income" else "-"
        ctk.CTkLabel(
            f, text=f"{sign}{format_money_short(tx.amount_cents)}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=color, width=120,
        ).grid(row=0, column=4, padx=8)

        # Delete button — asks for confirmation before deleting
        ctk.CTkButton(
            f, text="🗑", width=32, height=28, corner_radius=6,
            fg_color="transparent", hover_color="#FEE2E2", text_color="#DC2626",
            command=lambda t=tx: self._delete(t),
        ).grid(row=0, column=5, padx=(4, 16))

    # ── Add dialog ────────────────────────────────────────────────────────────

    def _open_add_dialog(self):
        # Opens modal dialog; passes _load_rows as callback to refresh after save
        AddTransactionDialog(self, self.user, on_save=self._load_rows)

    # ── Delete ────────────────────────────────────────────────────────────────

    def _delete(self, tx):
        # Show confirmation dialog before permanently deleting
        ok = messagebox.askyesno(
            "Delete transaction",
            f"Delete this transaction?\n"
            f"{tx.category.name if tx.category else 'Uncategorized'} "
            f"— {format_money_short(tx.amount_cents)}",
        )
        if ok:
            delete_transaction(tx)
            self._load_rows()  # refresh the table


# ── Add Transaction Dialog ────────────────────────────────────────────────────

class AddTransactionDialog(ctk.CTkToplevel):

    def __init__(self, parent, user, on_save):
        super().__init__(parent)
        self.user    = user
        self.on_save = on_save  # callback — called after successful save

        self.title("Add Transaction")
        self.geometry("420x520")
        self.resizable(False, False)
        self.grab_set()  # modal — blocks interaction with the main window

        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        pad = {"padx": 28, "sticky": "ew"}

        # ── Type toggle ───────────────────────────────────────────────────────
        # Radio buttons to switch between Expense and Income
        self.type_var = ctk.StringVar(value="expense")

        toggle = ctk.CTkFrame(self, fg_color="#F1F5F9", corner_radius=8)
        toggle.grid(row=0, column=0, padx=28, pady=(28, 0), sticky="ew")
        toggle.grid_columnconfigure((0, 1), weight=1)

        for col, (label, val) in enumerate([("Expense", "expense"), ("Income", "income")]):
            ctk.CTkRadioButton(
                toggle, text=label, variable=self.type_var, value=val,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=col, padx=16, pady=12)

        # ── Amount ────────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="Amount", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=1, column=0, padx=28, pady=(20, 4), sticky="w")

        # Large font entry — amount is the most important field
        self.amount_entry = ctk.CTkEntry(
            self, placeholder_text="0.00",
            font=ctk.CTkFont(size=22, weight="bold"),
            height=52, corner_radius=8,
        )
        self.amount_entry.grid(row=2, column=0, **pad)
        self.amount_entry.focus()  # cursor jumps here when dialog opens

        # ── Category ──────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="Category", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=3, column=0, padx=28, pady=(16, 4), sticky="w")

        # Load both system categories (user=NULL) and user's own categories
        categories = list(Category.select().where(
            (Category.user == self.user) | (Category.user.is_null())
        ).order_by(Category.name))

        # Map display string "🛒 Groceries" → Category object for easy lookup on save
        self.cat_map = {f"{c.icon} {c.name}": c for c in categories}
        self.cat_var = ctk.StringVar(value=list(self.cat_map.keys())[0])

        ctk.CTkOptionMenu(
            self, values=list(self.cat_map.keys()),
            variable=self.cat_var,
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        ).grid(row=4, column=0, **pad)

        # ── Date ──────────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="Date", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=5, column=0, padx=28, pady=(16, 4), sticky="w")

        self.date_entry = ctk.CTkEntry(
            self, placeholder_text="DD.MM.YYYY",
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        # Pre-fill with today's date so the user doesn't have to type it
        self.date_entry.insert(0, date.today().strftime("%d.%m.%Y"))
        self.date_entry.grid(row=6, column=0, **pad)

        # ── Note ──────────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="Note (optional)", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=7, column=0, padx=28, pady=(16, 4), sticky="w")

        self.note_entry = ctk.CTkEntry(
            self, placeholder_text="e.g. Weekly groceries",
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.note_entry.grid(row=8, column=0, **pad)

        # ── Save button ───────────────────────────────────────────────────────
        ctk.CTkButton(
            self, text="Save Transaction",
            height=48, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._save,
        ).grid(row=9, column=0, padx=28, pady=28, sticky="ew")

    def _save(self):
        from services.transaction_service import add_transaction
        from utils.formatters import parse_money, parse_date

        # Validate amount — parse_money raises ValueError on bad input
        try:
            amount_cents = parse_money(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid amount. Enter a number like 150.50")
            return

        # Validate date — parse_date raises ValueError on bad format
        try:
            tx_date = parse_date(self.date_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid date. Use DD.MM.YYYY format")
            return

        # Look up the Category object from the display string
        category = self.cat_map.get(self.cat_var.get())

        add_transaction(
            user=self.user,
            type=self.type_var.get(),
            amount_cents=amount_cents,
            category=category,
            tx_date=tx_date,
            note=self.note_entry.get(),
        )

        self.on_save()   # tell the parent page to refresh its table
        self.destroy()   # close the dialog