"""
ui/pages/transactions.py
Transactions page — full CRUD for transactions with filters and CSV export.

Layout (top to bottom):
  Row 0 — Header bar (title + Export CSV + Add Transaction buttons)
  Row 1 — Filter bar (type toggle, category dropdown, date range, Apply/Reset)
  Row 2 — Column headers (grey bar)
  Row 3 — Scrollable transaction rows
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
    """
    Main transactions page.
    Shows all transactions in a scrollable table.
    Supports filtering by type, category and date range.
    Supports adding, editing, deleting and exporting transactions.
    """

    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="#F8FAFC", corner_radius=0)
        self.user = user
        self.app  = app

        # Apply user's currency symbol to all money formatters
        set_currency(user.currency)

        # ── Active filter state ───────────────────────────────────────────────
        # These are read by _load_rows() every time the table refreshes.
        # Filters are combined — all active filters apply simultaneously.
        self.filter_type      = "all"   # "all" | "income" | "expense"
        self.filter_category  = None    # Category object or None (= show all)
        self.filter_date_from = None    # date object or None (= no lower bound)
        self.filter_date_to   = None    # date object or None (= no upper bound)
        self.search_var = ctk.StringVar()

        # Column 0 stretches to fill the window width
        self.grid_columnconfigure(0, weight=1)
        # Row 3 (scrollable table) takes all remaining vertical space
        self.grid_rowconfigure(3, weight=1)

        self._build_header()
        self._build_filters()
        self._build_table()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        """
        White top bar with page title and two action buttons:
        - Export CSV: saves the currently filtered transactions to a .csv file
        - Add Transaction: opens the AddTransactionDialog popup
        """
        header = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)  # keeps header fixed at 72px

        ctk.CTkLabel(
            header, text="Transactions",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#1E293B",
        ).grid(row=0, column=0, padx=32, pady=20, sticky="w")

        # Group both buttons together on the right side
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=32, pady=16, sticky="e")

        # Export CSV — grey secondary button
        ctk.CTkButton(
            btn_frame, text="⬇ Export CSV",
            width=130, height=36, corner_radius=8,
            fg_color="#F1F5F9", hover_color="#E2E8F0",
            text_color="#1E293B",
            font=ctk.CTkFont(size=13),
            command=self._export_csv,
        ).grid(row=0, column=0, padx=(0, 8))

        # Add Transaction — primary blue button
        ctk.CTkButton(
            btn_frame, text="+ Add Transaction",
            width=160, height=36, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._open_add_dialog,
        ).grid(row=0, column=1)

    # ── Filters ───────────────────────────────────────────────────────────────

    def _build_filters(self):
        filters = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=100)
        filters.grid(row=1, column=0, sticky="ew")
        filters.grid_propagate(False)
        filters.grid_columnconfigure(4, weight=1)

        # ── Search bar ────────────────────────────────────────────────────────────
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

        # ── Type / Category / Date filters ────────────────────────────────────────
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
            font=ctk.CTkFont(size=12), text_color="#64748B",
        ).grid(row=1, column=2, padx=(0, 4), pady=(8, 12))

        self.date_from_entry = ctk.CTkEntry(
            filters, placeholder_text="DD.MM.YYYY",
            width=110, height=32, corner_radius=6,
            font=ctk.CTkFont(size=12),
        )
        self.date_from_entry.grid(row=1, column=3, padx=(0, 8), pady=(8, 12))

        ctk.CTkLabel(
            filters, text="To:",
            font=ctk.CTkFont(size=12), text_color="#64748B",
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
            fg_color="#F1F5F9", hover_color="#E2E8F0",
            text_color="#64748B",
            font=ctk.CTkFont(size=12),
            command=self._reset_filters,
        ).grid(row=1, column=7, padx=(0, 32), pady=(8, 12))

    def _on_type_filter(self, value: str):
        """Called instantly when user clicks All / Income / Expense."""
        self.filter_type = value.lower()  # "all" | "income" | "expense"
        self._load_rows()

    def _on_category_filter(self, value: str):
        """Called instantly when user selects a category from the dropdown."""
        self.filter_category = self.cat_options.get(value)  # Category or None
        self._load_rows()

    def _apply_date_filter(self):
        """
        Reads the From/To date fields, validates them, and refreshes the table.
        Empty field = no bound on that side (e.g. empty From = from the beginning).
        Shows an error dialog if the format is wrong.
        """
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
        text = self.search_entry.get().strip().lower()
        print(f"Search text: '{text}'")
        self._load_rows()

    def _reset_filters(self):
        """Clears all active filters including search."""
        self.filter_type = "all"
        self.filter_category = None
        self.filter_date_from = None
        self.filter_date_to = None
        self.type_var.set("All")
        self.cat_var.set("All categories")
        self.date_from_entry.delete(0, "end")
        self.date_to_entry.delete(0, "end")
        self.search_entry.delete(0, "end")
        self._load_rows()

    # ── Table ─────────────────────────────────────────────────────────────────

    def _build_table(self):
        """
        Builds the static column header row and the scrollable rows container.
        The header row is a fixed-height grey bar, never scrolls.
        The rows container is a CTkScrollableFrame that fills remaining space.
        """
        # Fixed grey header row with column labels
        headers_frame = ctk.CTkFrame(self, fg_color="#F1F5F9", corner_radius=0, height=40)
        headers_frame.grid(row=2, column=0, sticky="ew", padx=32, pady=(8, 0))
        headers_frame.grid_propagate(False)
        headers_frame.grid_columnconfigure(1, weight=1)  # Category column stretches

        for col, (text, width) in enumerate([
            ("",         40),   # emoji icon — no label needed
            ("Category",  0),   # stretches to fill available space
            ("Date",    100),
            ("Note",    180),
            ("Amount",  120),
            ("",        120),   # actions column — wider to fit two buttons
        ]):
            ctk.CTkLabel(
                headers_frame, text=text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#64748B", width=width, anchor="w",
            ).grid(row=0, column=col, padx=(12 if col == 0 else 8, 8), pady=10, sticky="w")

        # Scrollable container for transaction rows
        # Fills all remaining vertical space (row 3 has weight=1)
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

        # ── Apply search filter ───────────────────────────────────────────────────
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
                text_color="#94A3B8",
            ).grid(row=0, column=0, columnspan=6, pady=48)
            return

        for i, tx in enumerate(txs):
            bg = "#FFFFFF" if i % 2 == 0 else "#F8FAFC"
            self._transaction_row(i, tx, bg)

    def _transaction_row(self, row_idx: int, tx, bg: str):
        """
        Renders a single transaction as a fixed-height row with 6 columns:
          0 — Category emoji icon
          1 — Category name (stretches)
          2 — Date
          3 — Note (truncated at 28 chars)
          4 — Amount (green for income, red for expense)
          5 — Action buttons: Edit (✏️) and Delete (🗑)
        """
        # Fixed-height frame for this row — prevents rows from changing size
        f = ctk.CTkFrame(self.rows_frame, fg_color=bg, corner_radius=0, height=52)
        f.grid(row=row_idx, column=0, columnspan=6, sticky="ew", pady=0)
        f.grid_columnconfigure(1, weight=1)  # category name stretches
        f.grid_propagate(False)              # keeps height fixed at 52px

        # Fall back to generic icon/name if no category is set
        icon = tx.category.icon if tx.category else "💳"
        name = tx.category.name if tx.category else "Uncategorized"

        # Col 0 — Category emoji
        ctk.CTkLabel(f, text=icon, font=ctk.CTkFont(size=18), width=40
                     ).grid(row=0, column=0, padx=(16, 4), pady=14)

        # Col 1 — Category name (stretches to fill space)
        ctk.CTkLabel(f, text=name, font=ctk.CTkFont(size=14),
                     text_color="#1E293B", anchor="w"
                     ).grid(row=0, column=1, padx=8, sticky="w")

        # Col 2 — Date formatted as DD.MM.YYYY
        ctk.CTkLabel(f, text=format_date(tx.date), font=ctk.CTkFont(size=13),
                     text_color="#64748B", width=100
                     ).grid(row=0, column=2, padx=8)

        # Col 3 — Note truncated at 28 characters to avoid overflow
        note_text = tx.note[:28] + "…" if len(tx.note) > 28 else tx.note

        # Recurring indicator
        if tx.is_recurring:
            note_text = f"🔄 {note_text}"

        ctk.CTkLabel(f, text=note_text,
                     font=ctk.CTkFont(size=13), text_color="#94A3B8", width=180, anchor="w"
                     ).grid(row=0, column=3, padx=8, sticky="w")

        # Col 4 — Amount: green + prefix for income, red - prefix for expense
        color = "#16A34A" if tx.type == "income" else "#DC2626"
        sign  = "+" if tx.type == "income" else "-"
        ctk.CTkLabel(
            f, text=f"{sign}{format_money_short(tx.amount_cents)}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=color, width=120,
        ).grid(row=0, column=4, padx=8)

        # Col 5 — Action buttons (Edit + Delete) side by side
        action_frame = ctk.CTkFrame(f, fg_color="transparent")
        action_frame.grid(row=0, column=5, padx=(4, 16))

        # Edit button — opens EditTransactionDialog pre-filled with this tx's data
        ctk.CTkButton(
            action_frame, text="✏️", width=32, height=28,
            corner_radius=6, fg_color="transparent",
            hover_color="#EFF6FF", text_color="#2563EB",
            command=lambda t=tx: self._open_edit_dialog(t),
        ).grid(row=0, column=0, padx=(0, 4))

        # Delete button — asks for confirmation before permanently deleting
        ctk.CTkButton(
            action_frame, text="🗑", width=32, height=28,
            corner_radius=6, fg_color="transparent",
            hover_color="#FEE2E2", text_color="#DC2626",
            command=lambda t=tx: self._delete(t),
        ).grid(row=0, column=1)

    # ── Export CSV ────────────────────────────────────────────────────────────

    def _export_csv(self):
        """
        Exports the currently visible (filtered) transactions to a CSV file.
        Steps:
          1. Opens a save-file dialog to let the user pick a location
          2. Fetches transactions using the same active filters as the table
          3. Writes CSV with columns: Date, Type, Category, Amount, Note
          4. Shows a success message with the file path and row count

        Respects all active filters — if the user filtered by March expenses,
        only March expenses will appear in the exported file.
        """
        # Ask user where to save — returns empty string if cancelled
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="transactions.csv",
            title="Export transactions to CSV",
        )
        if not filepath:
            return  # user clicked Cancel

        # Fetch same transactions that are currently shown in the table
        type_filter = None if self.filter_type == "all" else self.filter_type
        txs = get_transactions(
            self.user,
            date_from=self.filter_date_from,
            date_to=self.filter_date_to,
            type=type_filter,
            category=self.filter_category,
        )

        # Write CSV using Python's built-in csv module (no extra libraries needed)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Type", "Category", "Amount", "Note"])  # header
            for tx in txs:
                writer.writerow([
                    format_date(tx.date),
                    tx.type,
                    tx.category.name if tx.category else "Uncategorized",
                    tx.amount_cents / 100,  # convert cents back to decimal for readability
                    tx.note,
                ])

        messagebox.showinfo(
            "Export complete",
            f"Saved {len(txs)} transactions to:\n{filepath}"
        )

    # ── Dialog openers ────────────────────────────────────────────────────────

    def _open_add_dialog(self):
        """Opens the Add dialog. Passes _load_rows as callback to refresh after save."""
        AddTransactionDialog(self, self.user, on_save=self._load_rows)

    def _open_edit_dialog(self, tx):
        """Opens the Edit dialog pre-filled with the given transaction's data."""
        EditTransactionDialog(self, self.user, tx, on_save=self._load_rows)

    def _delete(self, tx):
        """
        Shows a confirmation dialog before permanently deleting the transaction.
        Refreshes the table if the user confirms.
        """
        ok = messagebox.askyesno(
            "Delete transaction",
            f"Delete this transaction?\n"
            f"{tx.category.name if tx.category else 'Uncategorized'} "
            f"— {format_money_short(tx.amount_cents)}",
        )
        if ok:
            delete_transaction(tx)
            self._load_rows()  # refresh table after deletion


# ── Add Transaction Dialog ────────────────────────────────────────────────────

class AddTransactionDialog(ctk.CTkToplevel):
    """
    Modal dialog for creating a new transaction.
    Fields: Type (Expense/Income), Amount, Category, Date, Note.
    All fields start empty (Date is pre-filled with today).
    Calls on_save() after successfully saving to refresh the parent table.
    """

    def __init__(self, parent, user, on_save):
        super().__init__(parent)
        self.user    = user
        self.on_save = on_save  # callback — called after successful save

        self.title("Add Transaction")
        self.geometry("420x600")
        self.resizable(False, False)
        self.grab_set()  # modal — blocks interaction with the main window
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        """Builds all form fields."""
        pad = {"padx": 28, "sticky": "ew"}

        # ── Type toggle: Expense / Income ─────────────────────────────────────
        self.type_var = ctk.StringVar(value="expense")  # default to expense
        toggle = ctk.CTkFrame(self, fg_color="#F1F5F9", corner_radius=8)
        toggle.grid(row=0, column=0, padx=28, pady=(28, 0), sticky="ew")
        toggle.grid_columnconfigure((0, 1), weight=1)

        for col, (label, val) in enumerate([("Expense", "expense"), ("Income", "income")]):
            ctk.CTkRadioButton(
                toggle, text=label, variable=self.type_var, value=val,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=col, padx=16, pady=12)

        # ── Amount field (large font — most important input) ──────────────────
        ctk.CTkLabel(self, text="Amount", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=1, column=0, padx=28, pady=(20, 4), sticky="w")
        self.amount_entry = ctk.CTkEntry(
            self, placeholder_text="0.00",
            font=ctk.CTkFont(size=22, weight="bold"),
            height=52, corner_radius=8,
        )
        self.amount_entry.grid(row=2, column=0, **pad)
        self.amount_entry.focus()  # cursor jumps here when dialog opens

        # ── Category dropdown ─────────────────────────────────────────────────
        # Loads both system categories (user=NULL) and user's own categories
        ctk.CTkLabel(self, text="Category", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=3, column=0, padx=28, pady=(16, 4), sticky="w")
        categories = list(Category.select().where(
            (Category.user == self.user) | (Category.user.is_null())
        ).order_by(Category.name))

        # Map "🛒 Groceries" → Category object for easy lookup on save
        self.cat_map = {f"{c.icon} {c.name}": c for c in categories}
        self.cat_var = ctk.StringVar(value=list(self.cat_map.keys())[0])
        ctk.CTkOptionMenu(
            self, values=list(self.cat_map.keys()),
            variable=self.cat_var,
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        ).grid(row=4, column=0, **pad)

        # ── Date field ────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="Date", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=5, column=0, padx=28, pady=(16, 4), sticky="w")
        self.date_entry = ctk.CTkEntry(
            self, placeholder_text="DD.MM.YYYY",
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        # Pre-fill with today so user doesn't have to type it most of the time
        self.date_entry.insert(0, date.today().strftime("%d.%m.%Y"))
        self.date_entry.grid(row=6, column=0, **pad)

        # ── Note field (optional) ─────────────────────────────────────────────
        ctk.CTkLabel(self, text="Note (optional)", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=7, column=0, padx=28, pady=(16, 4), sticky="w")
        self.note_entry = ctk.CTkEntry(
            self, placeholder_text="e.g. Weekly groceries",
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.note_entry.grid(row=8, column=0, **pad)

        # ── Repeat monthly checkbox ───────────────────────────────────────────
        self.recurring_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self,
            text="🔄 Repeat monthly — auto-create every month",
            variable=self.recurring_var,
            font=ctk.CTkFont(size=13),
            text_color="#1E293B",
            checkbox_width=20,
            checkbox_height=20,
        ).grid(row=9, column=0, padx=28, pady=(16, 0), sticky="w")

        # ── Save button ───────────────────────────────────────────────────────
        ctk.CTkButton(
            self, text="Save Transaction",
            height=48, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._save,
        ).grid(row=10, column=0, padx=28, pady=28, sticky="ew")

    def _save(self):
        """
        Validates all inputs, creates the transaction, then closes the dialog.
        Shows an error popup if amount or date is invalid.
        """
        from services.transaction_service import add_transaction

        # Validate amount — parse_money raises ValueError on bad input
        try:
            amount_cents = parse_money(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid amount. Enter a number like 150.50")
            return

        # Validate date — parse_date raises ValueError on wrong format
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
            is_recurring=self.recurring_var.get(),
        )

        self.on_save()   # tell the parent page to refresh its table
        self.destroy()   # close this dialog


# ── Edit Transaction Dialog ───────────────────────────────────────────────────

class EditTransactionDialog(ctk.CTkToplevel):
    """
    Modal dialog for editing an existing transaction.
    Identical layout to AddTransactionDialog but all fields are pre-filled
    with the transaction's current values.
    Calls update_transaction() instead of add_transaction() on save.
    Calls on_save() after successfully saving to refresh the parent table.
    """

    def __init__(self, parent, user, tx, on_save):
        super().__init__(parent)
        self.user    = user
        self.tx      = tx       # the existing Transaction object being edited
        self.on_save = on_save  # callback — called after successful save

        self.title("Edit Transaction")
        self.geometry("420x520")
        self.resizable(False, False)
        self.grab_set()  # modal — blocks interaction with the main window
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        """Builds all form fields pre-filled with the transaction's current data."""
        pad = {"padx": 28, "sticky": "ew"}

        # ── Type toggle — pre-selected to current type ────────────────────────
        self.type_var = ctk.StringVar(value=self.tx.type)  # "income" or "expense"
        toggle = ctk.CTkFrame(self, fg_color="#F1F5F9", corner_radius=8)
        toggle.grid(row=0, column=0, padx=28, pady=(28, 0), sticky="ew")
        toggle.grid_columnconfigure((0, 1), weight=1)

        for col, (label, val) in enumerate([("Expense", "expense"), ("Income", "income")]):
            ctk.CTkRadioButton(
                toggle, text=label, variable=self.type_var, value=val,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=col, padx=16, pady=12)

        # ── Amount — pre-filled with current amount ───────────────────────────
        ctk.CTkLabel(self, text="Amount", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=1, column=0, padx=28, pady=(20, 4), sticky="w")
        self.amount_entry = ctk.CTkEntry(
            self, font=ctk.CTkFont(size=22, weight="bold"),
            height=52, corner_radius=8,
        )
        # Convert cents back to decimal for display: 150050 → "1500.5"
        self.amount_entry.insert(0, str(self.tx.amount_cents / 100))
        self.amount_entry.grid(row=2, column=0, **pad)
        self.amount_entry.focus()

        # ── Category — pre-selected to current category ───────────────────────
        ctk.CTkLabel(self, text="Category", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=3, column=0, padx=28, pady=(16, 4), sticky="w")
        categories = list(Category.select().where(
            (Category.user == self.user) | (Category.user.is_null())
        ).order_by(Category.name))
        self.cat_map = {f"{c.icon} {c.name}": c for c in categories}

        # Find the display key that matches the transaction's current category
        current_cat_key = list(self.cat_map.keys())[0]  # fallback to first
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

        # ── Date — pre-filled with current date ──────────────────────────────
        ctk.CTkLabel(self, text="Date", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=5, column=0, padx=28, pady=(16, 4), sticky="w")
        self.date_entry = ctk.CTkEntry(
            self, font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.date_entry.insert(0, self.tx.date.strftime("%d.%m.%Y"))
        self.date_entry.grid(row=6, column=0, **pad)

        # ── Note — pre-filled with current note ──────────────────────────────
        ctk.CTkLabel(self, text="Note (optional)", font=ctk.CTkFont(size=13),
                     text_color="#64748B").grid(row=7, column=0, padx=28, pady=(16, 4), sticky="w")
        self.note_entry = ctk.CTkEntry(
            self, font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.note_entry.insert(0, self.tx.note)
        self.note_entry.grid(row=8, column=0, **pad)



        # ── Save button ───────────────────────────────────────────────────────
        ctk.CTkButton(
            self, text="Save Changes",
            height=48, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._save,
        ).grid(row=9, column=0, padx=28, pady=28, sticky="ew")

    def _save(self):
        """
        Validates all inputs, updates the existing transaction, then closes.
        Uses update_transaction() which only changes fields that are passed in.
        Shows an error popup if amount or date is invalid.
        """
        # Validate amount
        try:
            amount_cents = parse_money(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid amount. Enter a number like 150.50")
            return

        # Validate date
        try:
            tx_date = parse_date(self.date_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid date. Use DD.MM.YYYY format")
            return

        # Look up the Category object from the display string
        category = self.cat_map.get(self.cat_var.get())

        # update_transaction patches only the fields we pass in
        update_transaction(
            self.tx,
            amount_cents=amount_cents,
            category=category,
            tx_date=tx_date,
            note=self.note_entry.get(),
            type=self.type_var.get(),
        )

        self.on_save()   # tell the parent page to refresh its table
        self.destroy()   # close this dialog
