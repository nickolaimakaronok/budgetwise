"""
ui/pages/transactions.py
Transactions page — full CRUD for transactions with filters, tags, and CSV export.
"""

import csv
import customtkinter as ctk
from datetime import date
from tkinter import messagebox, filedialog
from services.transaction_service import get_transactions, delete_transaction, update_transaction
from services.tag_service import (
    get_all_tags, get_transaction_tags, set_transaction_tags,
    parse_tags_string, format_tags_display, format_tags_edit,
)
from models.models import Category
from utils.formatters import format_money_short, format_date, set_currency, parse_money, parse_date
from utils.i18n import t, months_list

# ── Theme colors — (light, dark) tuples ──────────────────────────────────────
BG_PAGE        = ("#F8FAFC", "#1A1A2E")
BG_CARD        = ("#FFFFFF", "#16213E")
BG_HEADER      = ("#FFFFFF", "#0F0F23")
BG_INPUT       = ("#F1F5F9", "#0F3460")
BG_ROW_EVEN    = ("#FFFFFF", "#16213E")
BG_ROW_ODD     = ("#F8FAFC", "#1A1A2E")
BG_TOGGLE      = ("#F1F5F9", "#0F3460")
BG_TAG         = ("#EFF6FF", "#1E3A5F")
TEXT_PRIMARY   = ("#1E293B", "#E2E8F0")
TEXT_SECONDARY = ("#64748B", "#94A3B8")
TEXT_MUTED     = ("#94A3B8", "#64748B")
TEXT_TAG       = ("#2563EB", "#3B82F6")
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
        self.filter_tag       = None
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
            header, text=t("transactions"),
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=32, pady=20, sticky="w")

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=32, pady=16, sticky="e")

        ctk.CTkButton(
            btn_frame, text=t("import_csv"),
            width=130, height=36, corner_radius=8,
            fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
            command=self._open_import_dialog,
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text=t("export_csv"),
            width=130, height=36, corner_radius=8,
            fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
            command=self._export_csv,
        ).grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text=t("export_pdf"),
            width=130, height=36, corner_radius=8,
            fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
            command=self._export_pdf,
        ).grid(row=0, column=2, padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text=t("add_transaction"),
            width=160, height=36, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._open_add_dialog,
        ).grid(row=0, column=3)

    def _build_filters(self):
        filters = ctk.CTkFrame(self, fg_color=BG_HEADER, corner_radius=0, height=100)
        filters.grid(row=1, column=0, sticky="ew")
        filters.grid_propagate(False)
        filters.grid_columnconfigure(4, weight=1)

        search_row = ctk.CTkFrame(filters, fg_color="transparent")
        search_row.grid(row=0, column=0, columnspan=9, padx=32, pady=(10, 0), sticky="ew")
        search_row.grid_columnconfigure(0, weight=1)

        self.search_var.trace("w", lambda *args: self._on_search())

        self.search_entry = ctk.CTkEntry(
            search_row,
            textvariable=self.search_var,
            placeholder_text=t("search_placeholder"),
            height=34, corner_radius=8,
            font=ctk.CTkFont(size=13),
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            search_row, text=t("search"),
            width=80, height=34, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_search,
        ).grid(row=0, column=1)

        self.type_var = ctk.StringVar(value=t("all"))
        ctk.CTkSegmentedButton(
            filters,
            values=[t("all"), t("income"), t("expense")],
            variable=self.type_var,
            font=ctk.CTkFont(size=12),
            width=200, height=32,
            command=self._on_type_filter,
        ).grid(row=1, column=0, padx=(32, 12), pady=(8, 12))

        categories = list(Category.select().where(
            (Category.user == self.user) | (Category.user.is_null())
        ).order_by(Category.name))

        self.cat_options = {t("all_categories"): None}
        for c in categories:
            self.cat_options[f"{c.icon} {c.name}"] = c

        self.cat_var = ctk.StringVar(value=t("all_categories"))
        ctk.CTkOptionMenu(
            filters,
            values=list(self.cat_options.keys()),
            variable=self.cat_var,
            width=180, height=32, corner_radius=6,
            font=ctk.CTkFont(size=12),
            command=self._on_category_filter,
        ).grid(row=1, column=1, padx=(0, 12), pady=(8, 12))

        # ── Tag filter ────────────────────────────────────────────────────────
        user_tags = get_all_tags(self.user)
        self.tag_options = {t("all_tags"): None}
        for tg in user_tags:
            self.tag_options[f"#{tg.name}"] = tg

        self.tag_var = ctk.StringVar(value=t("all_tags"))
        ctk.CTkOptionMenu(
            filters,
            values=list(self.tag_options.keys()),
            variable=self.tag_var,
            width=140, height=32, corner_radius=6,
            font=ctk.CTkFont(size=12),
            command=self._on_tag_filter,
        ).grid(row=1, column=2, padx=(0, 12), pady=(8, 12))

        ctk.CTkLabel(
            filters, text=t("date_from"),
            font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
        ).grid(row=1, column=3, padx=(0, 4), pady=(8, 12))

        self.date_from_entry = ctk.CTkEntry(
            filters, placeholder_text="DD.MM.YYYY",
            width=110, height=32, corner_radius=6,
            font=ctk.CTkFont(size=12),
        )
        self.date_from_entry.grid(row=1, column=4, padx=(0, 8), pady=(8, 12))

        ctk.CTkLabel(
            filters, text=t("date_to"),
            font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
        ).grid(row=1, column=5, padx=(0, 4), pady=(8, 12), sticky="e")

        self.date_to_entry = ctk.CTkEntry(
            filters, placeholder_text="DD.MM.YYYY",
            width=110, height=32, corner_radius=6,
            font=ctk.CTkFont(size=12),
        )
        self.date_to_entry.grid(row=1, column=6, padx=(0, 8), pady=(8, 12))

        ctk.CTkButton(
            filters, text=t("apply"),
            width=70, height=32, corner_radius=6,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._apply_date_filter,
        ).grid(row=1, column=7, padx=(0, 8), pady=(8, 12))

        ctk.CTkButton(
            filters, text=t("reset"),
            width=70, height=32, corner_radius=6,
            fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=12),
            command=self._reset_filters,
        ).grid(row=1, column=8, padx=(0, 32), pady=(8, 12))

    def _on_type_filter(self, value: str):
        mapping = {
            t("all"):     "all",
            t("income"):  "income",
            t("expense"): "expense",
        }
        self.filter_type = mapping.get(value, "all")
        self._load_rows()

    def _on_category_filter(self, value: str):
        self.filter_category = self.cat_options.get(value)
        self._load_rows()

    def _on_tag_filter(self, value: str):
        self.filter_tag = self.tag_options.get(value)
        self._load_rows()

    def _apply_date_filter(self):
        from_text = self.date_from_entry.get().strip()
        to_text   = self.date_to_entry.get().strip()

        try:
            self.filter_date_from = parse_date(from_text) if from_text else None
        except ValueError:
            messagebox.showerror(t("error"), "Invalid 'From' date. Use DD.MM.YYYY")
            return

        try:
            self.filter_date_to = parse_date(to_text) if to_text else None
        except ValueError:
            messagebox.showerror(t("error"), "Invalid 'To' date. Use DD.MM.YYYY")
            return

        self._load_rows()

    def _on_search(self):
        self._load_rows()

    def _reset_filters(self):
        self.filter_type      = "all"
        self.filter_category  = None
        self.filter_date_from = None
        self.filter_date_to   = None
        self.filter_tag       = None
        self.type_var.set(t("all"))
        self.cat_var.set(t("all_categories"))
        self.tag_var.set(t("all_tags"))
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
            ("",              40),
            (t("category"),    0),
            (t("date"),      100),
            (t("note"),      180),
            (t("amount"),    120),
            ("",             120),
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

        # Tag filter
        if self.filter_tag is not None:
            from services.tag_service import get_transactions_by_tag
            tag_tx_ids = set(get_transactions_by_tag(self.user, self.filter_tag.name))
            txs = [tx for tx in txs if tx.id in tag_tx_ids]

        # Search filter — also searches tags
        search_text = self.search_entry.get().strip().lower()
        if search_text:
            filtered = []
            for tx in txs:
                cat_name = tx.category.name.lower() if tx.category else ""
                note = tx.note.lower()
                tags = format_tags_display(get_transaction_tags(tx)).lower()
                if search_text in cat_name or search_text in note or search_text in tags:
                    filtered.append(tx)
            txs = filtered

        if not txs:
            ctk.CTkLabel(
                self.rows_frame,
                text=t("no_transactions_found"),
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
        name = tx.category.name if tx.category else t("uncategorized")

        ctk.CTkLabel(f, text=icon, font=ctk.CTkFont(size=18), width=40
                     ).grid(row=0, column=0, padx=(16, 4), pady=14)

        # Category name + tags inline
        tags = get_transaction_tags(tx)
        tag_str = ""
        if tags:
            tag_str = "  " + " ".join(f"#{tg.name}" for tg in tags[:3])

        cat_label = ctk.CTkFrame(f, fg_color="transparent")
        cat_label.grid(row=0, column=1, padx=8, sticky="w")

        ctk.CTkLabel(cat_label, text=name, font=ctk.CTkFont(size=14),
                     text_color=TEXT_PRIMARY, anchor="w"
                     ).grid(row=0, column=0, sticky="w")

        if tag_str:
            ctk.CTkLabel(cat_label, text=tag_str, font=ctk.CTkFont(size=11),
                         text_color=TEXT_TAG, anchor="w"
                         ).grid(row=0, column=1, padx=(4, 0), sticky="w")

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
            command=lambda tx=tx: self._open_edit_dialog(tx),
        ).grid(row=0, column=0, padx=(0, 4))

        ctk.CTkButton(
            action_frame, text="🗑", width=32, height=28,
            corner_radius=6, fg_color="transparent",
            hover_color=HOVER_RED, text_color="#DC2626",
            command=lambda tx=tx: self._delete(tx),
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
            writer.writerow([t("date"), t("category"), t("amount"), t("note"), t("tags")])
            for tx in txs:
                tags = get_transaction_tags(tx)
                writer.writerow([
                    format_date(tx.date),
                    tx.category.name if tx.category else t("uncategorized"),
                    tx.amount_cents / 100,
                    tx.note,
                    format_tags_display(tags),
                ])

        messagebox.showinfo(
            t("export_complete"),
            t("saved_to", len(txs), filepath),
        )

    def _export_pdf(self):
        from services.pdf_service import generate_monthly_report
        today        = date.today()
        month_name   = months_list()[today.month - 1]
        default_name = f"BudgetWise_{month_name}_{today.year}.pdf"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=default_name,
            title="Export PDF Report",
        )
        if not filepath:
            return

        generate_monthly_report(self.user, today.year, today.month, filepath)
        messagebox.showinfo(t("export_complete"), f"Report saved to:\n{filepath}")

    def _open_import_dialog(self):
        ImportCSVDialog(self, self.user, on_save=self._on_dialog_save)

    def _open_add_dialog(self):
        AddTransactionDialog(self, self.user, on_save=self._on_dialog_save)

    def _open_edit_dialog(self, tx):
        EditTransactionDialog(self, self.user, tx, on_save=self._on_dialog_save)

    def _on_dialog_save(self):
        """Reload rows and refresh tag filter options."""
        # Refresh tag filter dropdown
        user_tags = get_all_tags(self.user)
        self.tag_options = {t("all_tags"): None}
        for tg in user_tags:
            self.tag_options[f"#{tg.name}"] = tg
        # Note: CTkOptionMenu doesn't support updating values easily,
        # so we just reload. Full page rebuild would be heavier.
        self._load_rows()

    def _delete(self, tx):
        ok = messagebox.askyesno(
            t("delete_transaction"),
            f"{t('delete_confirm')}\n"
            f"{tx.category.name if tx.category else t('uncategorized')} "
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

        self.title(t("add_transaction_title"))
        self.geometry("420x660")
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

        for col, (label, val) in enumerate([
            (t("expense"), "expense"),
            (t("income"),  "income"),
        ]):
            ctk.CTkRadioButton(
                toggle, text=label, variable=self.type_var, value=val,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=col, padx=16, pady=12)

        ctk.CTkLabel(self, text=t("amount_label"), font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=1, column=0, padx=28, pady=(20, 4), sticky="w")
        self.amount_entry = ctk.CTkEntry(
            self, placeholder_text="0.00",
            font=ctk.CTkFont(size=22, weight="bold"),
            height=52, corner_radius=8,
        )
        self.amount_entry.grid(row=2, column=0, **pad)
        self.amount_entry.focus()

        ctk.CTkLabel(self, text=t("category_label"), font=ctk.CTkFont(size=13),
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

        ctk.CTkLabel(self, text=t("date_label"), font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=5, column=0, padx=28, pady=(16, 4), sticky="w")
        self.date_entry = ctk.CTkEntry(
            self, placeholder_text="DD.MM.YYYY",
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.date_entry.insert(0, date.today().strftime("%d.%m.%Y"))
        self.date_entry.grid(row=6, column=0, **pad)

        ctk.CTkLabel(self, text=t("note_label"), font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=7, column=0, padx=28, pady=(16, 4), sticky="w")
        self.note_entry = ctk.CTkEntry(
            self, placeholder_text=t("note_placeholder"),
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.note_entry.grid(row=8, column=0, **pad)

        # ── Tags field ────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text=t("tags_label"), font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=9, column=0, padx=28, pady=(16, 4), sticky="w")
        self.tags_entry = ctk.CTkEntry(
            self, placeholder_text=t("tags_placeholder"),
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.tags_entry.grid(row=10, column=0, **pad)

        self.recurring_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self,
            text=t("recurring"),
            variable=self.recurring_var,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY,
            checkbox_width=20, checkbox_height=20,
        ).grid(row=11, column=0, padx=28, pady=(16, 0), sticky="w")

        ctk.CTkButton(
            self, text=t("save_transaction"),
            height=48, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._save,
        ).grid(row=12, column=0, padx=28, pady=28, sticky="ew")

    def _save(self):
        from services.transaction_service import add_transaction

        try:
            amount_cents = parse_money(self.amount_entry.get())
        except ValueError:
            messagebox.showerror(t("error"), t("invalid_amount"))
            return

        try:
            tx_date = parse_date(self.date_entry.get())
        except ValueError:
            messagebox.showerror(t("error"), t("invalid_date"))
            return

        category = self.cat_map.get(self.cat_var.get())

        tx = add_transaction(
            user=self.user,
            type=self.type_var.get(),
            amount_cents=amount_cents,
            category=category,
            tx_date=tx_date,
            note=self.note_entry.get(),
            is_recurring=self.recurring_var.get(),
        )

        # Save tags
        tag_names = parse_tags_string(self.tags_entry.get())
        if tag_names:
            set_transaction_tags(tx, self.user, tag_names)

        self.on_save()
        self.destroy()


# ── Edit Transaction Dialog ───────────────────────────────────────────────────

class EditTransactionDialog(ctk.CTkToplevel):

    def __init__(self, parent, user, tx, on_save):
        super().__init__(parent)
        self.user    = user
        self.tx      = tx
        self.on_save = on_save

        self.title(t("edit_transaction_title"))
        self.geometry("420x580")
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

        for col, (label, val) in enumerate([
            (t("expense"), "expense"),
            (t("income"),  "income"),
        ]):
            ctk.CTkRadioButton(
                toggle, text=label, variable=self.type_var, value=val,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=col, padx=16, pady=12)

        ctk.CTkLabel(self, text=t("amount_label"), font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=1, column=0, padx=28, pady=(20, 4), sticky="w")
        self.amount_entry = ctk.CTkEntry(
            self, font=ctk.CTkFont(size=22, weight="bold"),
            height=52, corner_radius=8,
        )
        self.amount_entry.insert(0, str(self.tx.amount_cents / 100))
        self.amount_entry.grid(row=2, column=0, **pad)
        self.amount_entry.focus()

        ctk.CTkLabel(self, text=t("category_label"), font=ctk.CTkFont(size=13),
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

        ctk.CTkLabel(self, text=t("date_label"), font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=5, column=0, padx=28, pady=(16, 4), sticky="w")
        self.date_entry = ctk.CTkEntry(
            self, font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.date_entry.insert(0, self.tx.date.strftime("%d.%m.%Y"))
        self.date_entry.grid(row=6, column=0, **pad)

        ctk.CTkLabel(self, text=t("note_label"), font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=7, column=0, padx=28, pady=(16, 4), sticky="w")
        self.note_entry = ctk.CTkEntry(
            self, font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.note_entry.insert(0, self.tx.note)
        self.note_entry.grid(row=8, column=0, **pad)

        # ── Tags field (pre-filled with existing tags) ────────────────────────
        ctk.CTkLabel(self, text=t("tags_label"), font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=9, column=0, padx=28, pady=(16, 4), sticky="w")
        self.tags_entry = ctk.CTkEntry(
            self, placeholder_text=t("tags_placeholder"),
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        existing_tags = get_transaction_tags(self.tx)
        if existing_tags:
            self.tags_entry.insert(0, format_tags_edit(existing_tags))
        self.tags_entry.grid(row=10, column=0, **pad)

        ctk.CTkButton(
            self, text=t("save_changes"),
            height=48, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._save,
        ).grid(row=11, column=0, padx=28, pady=28, sticky="ew")

    def _save(self):
        try:
            amount_cents = parse_money(self.amount_entry.get())
        except ValueError:
            messagebox.showerror(t("error"), t("invalid_amount"))
            return

        try:
            tx_date = parse_date(self.date_entry.get())
        except ValueError:
            messagebox.showerror(t("error"), t("invalid_date"))
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

        # Update tags
        tag_names = parse_tags_string(self.tags_entry.get())
        set_transaction_tags(self.tx, self.user, tag_names)

        self.on_save()
        self.destroy()


# ── Import CSV Dialog ─────────────────────────────────────────────────────────

class ImportCSVDialog(ctk.CTkToplevel):
    """
    CSV import wizard:
    1. Pick file → preview first rows
    2. Map columns (date, amount, note) via dropdowns
    3. Pick date format
    4. Import
    """

    def __init__(self, parent, user, on_save):
        super().__init__(parent)
        self.user    = user
        self.on_save = on_save
        self.preview = None

        self.title(t("import_csv_title"))
        self.geometry("620x580")
        self.resizable(False, False)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self._build_step1()

    def _build_step1(self):
        """Step 1: Pick file."""
        for w in self.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self, text=t("import_csv_title"),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=28, pady=(28, 4), sticky="w")

        ctk.CTkLabel(
            self, text=t("import_csv_sub"),
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
        ).grid(row=1, column=0, padx=28, pady=(0, 20), sticky="w")

        ctk.CTkButton(
            self, text=t("choose_file"),
            height=48, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._pick_file,
        ).grid(row=2, column=0, padx=28, pady=(0, 12), sticky="ew")

        self.status_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=12), text_color=TEXT_MUTED,
        )
        self.status_label.grid(row=3, column=0, padx=28, pady=(0, 8), sticky="w")

    def _pick_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title=t("choose_file"),
        )
        if not filepath:
            return

        self.filepath = filepath

        try:
            from services.csv_import_service import read_csv_preview
            self.preview = read_csv_preview(filepath, max_rows=5)
        except Exception as e:
            messagebox.showerror(t("error"), str(e))
            return

        self._build_step2()

    def _build_step2(self):
        """Step 2: Map columns + preview + import."""
        for w in self.winfo_children():
            w.destroy()

        headers = self.preview["headers"]
        col_options = [f"{i}: {h}" for i, h in enumerate(headers)]

        ctk.CTkLabel(
            self, text=t("import_csv_title"),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=28, pady=(28, 4), sticky="w")

        info_text = t("import_file_info", self.preview["total_rows"])
        ctk.CTkLabel(
            self, text=info_text,
            font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
        ).grid(row=1, column=0, padx=28, pady=(0, 16), sticky="w")

        # ── Column mapping ────────────────────────────────────────────────
        mapping = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12)
        mapping.grid(row=2, column=0, padx=28, pady=(0, 12), sticky="ew")
        mapping.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            mapping, text=t("column_mapping"),
            font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, columnspan=2, padx=16, pady=(12, 8), sticky="w")

        # Date column
        ctk.CTkLabel(mapping, text=t("date_column"),
                     font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
                     ).grid(row=1, column=0, padx=16, pady=4, sticky="w")
        self.date_col_var = ctk.StringVar(value=col_options[0])
        ctk.CTkOptionMenu(
            mapping, values=col_options, variable=self.date_col_var,
            font=ctk.CTkFont(size=12), height=32, corner_radius=6,
        ).grid(row=1, column=1, padx=16, pady=4, sticky="ew")

        # Amount column
        ctk.CTkLabel(mapping, text=t("amount_column"),
                     font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
                     ).grid(row=2, column=0, padx=16, pady=4, sticky="w")
        amt_default = col_options[min(1, len(col_options) - 1)]
        self.amount_col_var = ctk.StringVar(value=amt_default)
        ctk.CTkOptionMenu(
            mapping, values=col_options, variable=self.amount_col_var,
            font=ctk.CTkFont(size=12), height=32, corner_radius=6,
        ).grid(row=2, column=1, padx=16, pady=4, sticky="ew")

        # Note/description column
        ctk.CTkLabel(mapping, text=t("note_column"),
                     font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
                     ).grid(row=3, column=0, padx=16, pady=4, sticky="w")
        note_options = [t("skip_column")] + col_options
        note_default = note_options[min(2, len(note_options) - 1)]
        self.note_col_var = ctk.StringVar(value=note_default)
        ctk.CTkOptionMenu(
            mapping, values=note_options, variable=self.note_col_var,
            font=ctk.CTkFont(size=12), height=32, corner_radius=6,
        ).grid(row=3, column=1, padx=16, pady=4, sticky="ew")

        # Date format
        ctk.CTkLabel(mapping, text=t("date_format"),
                     font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
                     ).grid(row=4, column=0, padx=16, pady=(4, 12), sticky="w")
        from services.csv_import_service import DATE_FORMATS
        fmt_options = [label for _, label in DATE_FORMATS]
        self.date_fmt_var = ctk.StringVar(value=fmt_options[0])
        ctk.CTkOptionMenu(
            mapping, values=fmt_options, variable=self.date_fmt_var,
            font=ctk.CTkFont(size=12), height=32, corner_radius=6,
        ).grid(row=4, column=1, padx=16, pady=(4, 12), sticky="ew")

        # ── Preview table ─────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text=t("preview"),
            font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_PRIMARY,
        ).grid(row=3, column=0, padx=28, pady=(0, 4), sticky="w")

        preview_frame = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=8)
        preview_frame.grid(row=4, column=0, padx=28, pady=(0, 12), sticky="ew")

        # Header row
        for i, h in enumerate(headers[:6]):  # max 6 columns shown
            ctk.CTkLabel(
                preview_frame, text=h,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=TEXT_SECONDARY, width=90,
            ).grid(row=0, column=i, padx=6, pady=6)

        # Data rows
        for r, row in enumerate(self.preview["rows"][:4]):
            for i, cell in enumerate(row[:6]):
                display = cell[:15] + "…" if len(cell) > 15 else cell
                ctk.CTkLabel(
                    preview_frame, text=display,
                    font=ctk.CTkFont(size=11),
                    text_color=TEXT_PRIMARY, width=90,
                ).grid(row=r + 1, column=i, padx=6, pady=3)

        # ── Import button ─────────────────────────────────────────────────
        self.result_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
        )
        self.result_label.grid(row=5, column=0, padx=28, pady=(0, 4), sticky="w")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=6, column=0, padx=28, pady=(0, 28), sticky="ew")
        btn_row.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_row, text=t("back"),
            width=100, height=44, corner_radius=8,
            fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=14),
            command=self._build_step1,
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            btn_row, text=t("import_btn", self.preview["total_rows"]),
            height=48, corner_radius=8,
            fg_color="#16A34A", hover_color="#15803D",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._do_import,
        ).grid(row=0, column=1, sticky="ew")

    def _do_import(self):
        from services.csv_import_service import import_transactions, DATE_FORMATS

        # Parse column indices from dropdown values ("0: Date" → 0)
        date_col   = int(self.date_col_var.get().split(":")[0])
        amount_col = int(self.amount_col_var.get().split(":")[0])

        note_val = self.note_col_var.get()
        note_col = None
        if note_val != t("skip_column"):
            note_col = int(note_val.split(":")[0])

        # Find date format string
        fmt_label = self.date_fmt_var.get()
        date_format = "%d.%m.%Y"  # default
        for fmt_str, label in DATE_FORMATS:
            if label == fmt_label:
                date_format = fmt_str
                break

        try:
            result = import_transactions(
                user=self.user,
                filepath=self.filepath,
                date_col=date_col,
                amount_col=amount_col,
                note_col=note_col,
                date_format=date_format,
            )
        except Exception as e:
            messagebox.showerror(t("error"), str(e))
            return

        # Show result
        msg = t("import_result", result["imported"], result["skipped"], len(result["errors"]))
        if result["errors"]:
            msg += "\n\n" + "\n".join(result["errors"][:10])

        messagebox.showinfo(t("import_complete"), msg)
        self.on_save()
        self.destroy()
