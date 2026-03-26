"""
ui/pages/transactions.py
Transactions page — full CRUD for transactions with filters and CSV export.
"""

import csv
import customtkinter as ctk
from datetime import date
from tkinter import messagebox, filedialog
from services.transaction_service import get_transactions, delete_transaction, update_transaction
from models.models import Category
from utils.formatters import format_money_short, format_date, set_currency, parse_money, parse_date

# ── Theme colors — (light, dark) tuples ──────────────────────────────────────
BG_PAGE        = ("#F8FAFC", "#1A1A2E")
BG_CARD        = ("#FFFFFF", "#16213E")
BG_HEADER      = ("#FFFFFF", "#0F0F23")
BG_INPUT       = ("#F1F5F9", "#0F3460")
BG_ROW_EVEN    = ("#FFFFFF", "#16213E")
BG_ROW_ODD     = ("#F8FAFC", "#1A1A2E")
BG_TOGGLE      = ("#F1F5F9", "#0F3460")
TEXT_PRIMARY   = ("#1E293B", "#E2E8F0")
TEXT_SECONDARY = ("#64748B", "#94A3B8")
TEXT_MUTED     = ("#94A3B8", "#64748B")
HOVER_BLUE     = ("#EFF6FF", "#1E3A5F")
HOVER_RED      = ("#FEE2E2", "#3D1A1A")
BTN_SECONDARY  = ("#F1F5F9", "#0F3460")
BTN_SECONDARY_HOVER = ("#E2E8F0", "#1A4A7A")


class TransactionsPage(ctk.CTkFrame):

    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color=BG_PAGE, corner_radius=0)
        self.user = user
        self.app  = app

        set_currency(user.currency)

        self.filter_type      = "all"
        self.filter_category  = None
        self.filter_date_from = None
        self.filter_date_to   = None
        self.search_var       = ctk.StringVar()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_header()
        self._build_filters()
        self._build_table()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=BG_HEADER, corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        ctk.CTkLabel(
            header, text="Transactions",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=32, pady=20, sticky="w")

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=32, pady=16, sticky="e")

        ctk.CTkButton(
            btn_frame, text="⬇ Export CSV",
            width=130, height=36, corner_radius=8,
            fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
            command=self._export_csv,
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="+ Add Transaction",
            width=160, height=36, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._open_add_dialog,
        ).grid(row=0, column=1)

    def _build_filters(self):
        filters = ctk.CTkFrame(self, fg_color=BG_HEADER, corner_radius=0, height=100)
        filters.grid(row=1, column=0, sticky="ew")
        filters.grid_propagate(False)
        filters.grid_columnconfigure(4, weight=1)

        search_row = ctk.CTkFrame(filters, fg_color="transparent")
        search_row.grid(row=0, column=0, columnspan=8, padx=32, pady=(10, 0), sticky="ew")
        search_row.grid_columnconfigure(0, weight=1)

        self.search_var.trace("w", lambda *args: self._on_search())

        self.search_entry = ctk.CTkEntry(
            search_row,
            textvariable=self.search_var,
            placeholder_text="🔍 Search by category or note...",
            height=34, corner_radius=8,
            font=ctk.CTkFont(size=13),
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            search_row, text="Search",
            width=80, height=34, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_search,
        ).grid(row=0, column=1)

        self.type_var = ctk.StringVar(value="All")
        ctk.CTkSegmentedButton(
            filters,
            values=["All", "Income", "Expense"],
            variable=self.type_var,
            font=ctk.CTkFont(size=12),
            width=200, height=32,
            command=self._on_type_filter,
        ).grid(row=1, column=0, padx=(32, 12), pady=(8, 12))

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
        ).grid(row=1, column=1, padx=(0, 12), pady=(8, 12))

        ctk.CTkLabel(
            filters, text="From:",
            font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
        ).grid(row=1, column=2, padx=(0, 4), pady=(8, 12))

        self.date_from_entry = ctk.CTkEntry(
            filters, placeholder_text="DD.MM.YYYY",
            width=110, height=32, corner_radius=6,
            font=ctk.CTkFont(size=12),
        )
        self.date_from_entry.grid(row=1, column=3, padx=(0, 8), pady=(8, 12))

        ctk.CTkLabel(
            filters, text="To:",
            font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
        ).grid(row=1, column=4, padx=(0, 4), pady=(8, 12), sticky="e")

        self.date_to_entry = ctk.CTkEntry(
            filters, placeholder_text="DD.MM.YYYY",
            width=110, height=32, corner_radius=6,
            font=ctk.CTkFont(size=12),
        )
        self.date_to_entry.grid(row=1, column=5, padx=(0, 8), pady=(8, 12))

        ctk.CTkButton(
            filters, text="Apply",
            width=70, height=32, corner_radius=6,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._apply_date_filter,
        ).grid(row=1, column=6, padx=(0, 8), pady=(8, 12))

        ctk.CTkButton(
            filters, text="Reset",
            width=70, height=32, corner_radius=6,
            fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=12),
            command=self._reset_filters,
        ).grid(row=1, column=7, padx=(0, 32), pady=(8, 12))

    def _on_type_filter(self, value: str):
        self.filter_type = value.lower()
        self._load_rows()

    def _on_category_filter(self, value: str):
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

    def _on_search(self):
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
        self.search_entry.delete(0, "end")
        self._load_rows()

    def _build_table(self):
        headers_frame = ctk.CTkFrame(self, fg_color=BG_INPUT, corner_radius=0, height=40)
        headers_frame.grid(row=2, column=0, sticky="ew", padx=32, pady=(8, 0))
        headers_frame.grid_propagate(False)
        headers_frame.grid_columnconfigure(1, weight=1)

        for col, (text, width) in enumerate([
            ("",         40),
            ("Category",  0),
            ("Date",    100),
            ("Note",    180),
            ("Amount",  120),
            ("",        120),
        ]):
            ctk.CTkLabel(
                headers_frame, text=text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=TEXT_SECONDARY, width=width, anchor="w",
            ).grid(row=0, column=col, padx=(12 if col == 0 else 8, 8), pady=10, sticky="w")

        self.rows_frame = ctk.CTkScrollableFrame(
            self, fg_color=BG_CARD, corner_radius=12
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

        search_text = self.search_entry.get().strip().lower()
        if search_text:
            txs = [
                tx for tx in txs
                if search_text in (tx.category.name.lower() if tx.category else "")
                   or search_text in tx.note.lower()
            ]

        if not txs:
            ctk.CTkLabel(
                self.rows_frame,
                text="No transactions found.",
                font=ctk.CTkFont(size=14),
                text_color=TEXT_MUTED,
            ).grid(row=0, column=0, columnspan=6, pady=48)
            return

        for i, tx in enumerate(txs):
            bg = BG_ROW_EVEN if i % 2 == 0 else BG_ROW_ODD
            self._transaction_row(i, tx, bg)

    def _transaction_row(self, row_idx: int, tx, bg):
        f = ctk.CTkFrame(self.rows_frame, fg_color=bg, corner_radius=0, height=52)
        f.grid(row=row_idx, column=0, columnspan=6, sticky="ew", pady=0)
        f.grid_columnconfigure(1, weight=1)
        f.grid_propagate(False)

        icon = tx.category.icon if tx.category else "💳"
        name = tx.category.name if tx.category else "Uncategorized"

        ctk.CTkLabel(f, text=icon, font=ctk.CTkFont(size=18), width=40
                     ).grid(row=0, column=0, padx=(16, 4), pady=14)

        ctk.CTkLabel(f, text=name, font=ctk.CTkFont(size=14),
                     text_color=TEXT_PRIMARY, anchor="w"
                     ).grid(row=0, column=1, padx=8, sticky="w")

        ctk.CTkLabel(f, text=format_date(tx.date), font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY, width=100
                     ).grid(row=0, column=2, padx=8)

        note_text = tx.note[:28] + "…" if len(tx.note) > 28 else tx.note
        if tx.is_recurring:
            note_text = f"🔄 {note_text}"

        ctk.CTkLabel(f, text=note_text,
                     font=ctk.CTkFont(size=13), text_color=TEXT_MUTED, width=180, anchor="w"
                     ).grid(row=0, column=3, padx=8, sticky="w")

        color = "#16A34A" if tx.type == "income" else "#DC2626"
        sign  = "+" if tx.type == "income" else "-"
        ctk.CTkLabel(
            f, text=f"{sign}{format_money_short(tx.amount_cents)}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=color, width=120,
        ).grid(row=0, column=4, padx=8)

        action_frame = ctk.CTkFrame(f, fg_color="transparent")
        action_frame.grid(row=0, column=5, padx=(4, 16))

        ctk.CTkButton(
            action_frame, text="✏️", width=32, height=28,
            corner_radius=6, fg_color="transparent",
            hover_color=HOVER_BLUE, text_color=("#2563EB", "#3B82F6"),
            command=lambda t=tx: self._open_edit_dialog(t),
        ).grid(row=0, column=0, padx=(0, 4))

        ctk.CTkButton(
            action_frame, text="🗑", width=32, height=28,
            corner_radius=6, fg_color="transparent",
            hover_color=HOVER_RED, text_color="#DC2626",
            command=lambda t=tx: self._delete(t),
        ).grid(row=0, column=1)

    def _export_csv(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="transactions.csv",
            title="Export transactions to CSV",
        )
        if not filepath:
            return

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
            writer.writerow(["Date", "Type", "Category", "Amount", "Note"])
            for tx in txs:
                writer.writerow([
                    format_date(tx.date),
                    tx.type,
                    tx.category.name if tx.category else "Uncategorized",
                    tx.amount_cents / 100,
                    tx.note,
                ])

        messagebox.showinfo(
            "Export complete",
            f"Saved {len(txs)} transactions to:\n{filepath}"
        )

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
        self.geometry("420x600")
        self.resizable(False, False)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        pad = {"padx": 28, "sticky": "ew"}

        self.type_var = ctk.StringVar(value="expense")
        toggle = ctk.CTkFrame(self, fg_color=BG_TOGGLE, corner_radius=8)
        toggle.grid(row=0, column=0, padx=28, pady=(28, 0), sticky="ew")
        toggle.grid_columnconfigure((0, 1), weight=1)

        for col, (label, val) in enumerate([("Expense", "expense"), ("Income", "income")]):
            ctk.CTkRadioButton(
                toggle, text=label, variable=self.type_var, value=val,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=col, padx=16, pady=12)

        ctk.CTkLabel(self, text="Amount", font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=1, column=0, padx=28, pady=(20, 4), sticky="w")
        self.amount_entry = ctk.CTkEntry(
            self, placeholder_text="0.00",
            font=ctk.CTkFont(size=22, weight="bold"),
            height=52, corner_radius=8,
        )
        self.amount_entry.grid(row=2, column=0, **pad)
        self.amount_entry.focus()

        ctk.CTkLabel(self, text="Category", font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=3, column=0, padx=28, pady=(16, 4), sticky="w")
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
                     text_color=TEXT_SECONDARY).grid(row=5, column=0, padx=28, pady=(16, 4), sticky="w")
        self.date_entry = ctk.CTkEntry(
            self, placeholder_text="DD.MM.YYYY",
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.date_entry.insert(0, date.today().strftime("%d.%m.%Y"))
        self.date_entry.grid(row=6, column=0, **pad)

        ctk.CTkLabel(self, text="Note (optional)", font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=7, column=0, padx=28, pady=(16, 4), sticky="w")
        self.note_entry = ctk.CTkEntry(
            self, placeholder_text="e.g. Weekly groceries",
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.note_entry.grid(row=8, column=0, **pad)

        self.recurring_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self,
            text="🔄 Repeat monthly — auto-create every month",
            variable=self.recurring_var,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY,
            checkbox_width=20,
            checkbox_height=20,
        ).grid(row=9, column=0, padx=28, pady=(16, 0), sticky="w")

        ctk.CTkButton(
            self, text="Save Transaction",
            height=48, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._save,
        ).grid(row=10, column=0, padx=28, pady=28, sticky="ew")

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
            is_recurring=self.recurring_var.get(),
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

        self.type_var = ctk.StringVar(value=self.tx.type)
        toggle = ctk.CTkFrame(self, fg_color=BG_TOGGLE, corner_radius=8)
        toggle.grid(row=0, column=0, padx=28, pady=(28, 0), sticky="ew")
        toggle.grid_columnconfigure((0, 1), weight=1)

        for col, (label, val) in enumerate([("Expense", "expense"), ("Income", "income")]):
            ctk.CTkRadioButton(
                toggle, text=label, variable=self.type_var, value=val,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=col, padx=16, pady=12)

        ctk.CTkLabel(self, text="Amount", font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=1, column=0, padx=28, pady=(20, 4), sticky="w")
        self.amount_entry = ctk.CTkEntry(
            self, font=ctk.CTkFont(size=22, weight="bold"),
            height=52, corner_radius=8,
        )
        self.amount_entry.insert(0, str(self.tx.amount_cents / 100))
        self.amount_entry.grid(row=2, column=0, **pad)
        self.amount_entry.focus()

        ctk.CTkLabel(self, text="Category", font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=3, column=0, padx=28, pady=(16, 4), sticky="w")
        categories = list(Category.select().where(
            (Category.user == self.user) | (Category.user.is_null())
        ).order_by(Category.name))
        self.cat_map = {f"{c.icon} {c.name}": c for c in categories}

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

        ctk.CTkLabel(self, text="Date", font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=5, column=0, padx=28, pady=(16, 4), sticky="w")
        self.date_entry = ctk.CTkEntry(
            self, font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.date_entry.insert(0, self.tx.date.strftime("%d.%m.%Y"))
        self.date_entry.grid(row=6, column=0, **pad)

        ctk.CTkLabel(self, text="Note (optional)", font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=7, column=0, padx=28, pady=(16, 4), sticky="w")
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
