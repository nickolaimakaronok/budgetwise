"""
ui/pages/settings.py
Settings page — currency, appearance, categories, backup.
"""

import customtkinter as ctk
import shutil
import os
from datetime import datetime
from tkinter import messagebox
from db.database import db, DB_PATH
from models.models import Category, User
from utils.formatters import set_currency

# ── Theme colors — (light, dark) tuples ──────────────────────────────────────
BG_PAGE        = ("#F8FAFC", "#1A1A2E")
BG_CARD        = ("#FFFFFF", "#16213E")
BG_HEADER      = ("#FFFFFF", "#0F0F23")
BG_ROW         = ("#F8FAFC", "#1A1A2E")
TEXT_PRIMARY   = ("#1E293B", "#E2E8F0")
TEXT_SECONDARY = ("#64748B", "#94A3B8")
TEXT_MUTED     = ("#94A3B8", "#64748B")
HOVER_RED      = ("#FEE2E2", "#3D1A1A")
BTN_SECONDARY  = ("#F1F5F9", "#0F3460")
BTN_SECONDARY_HOVER = ("#E2E8F0", "#1A4A7A")


class SettingsPage(ctk.CTkFrame):

    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color=BG_PAGE, corner_radius=0)
        self.user = user
        self.app  = app

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=BG_HEADER, corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        ctk.CTkLabel(
            header, text="Settings",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=32, pady=20, sticky="w")

    # ── Body ──────────────────────────────────────────────────────────────────

    def _build_body(self):
        scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_PAGE, corner_radius=0
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=32, pady=16)
        scroll.grid_columnconfigure(0, weight=1)

        self._section_profile(scroll, 0)
        self._section_appearance(scroll, 1)
        self._section_categories(scroll, 2)
        self._section_data(scroll, 3)

    # ── Profile section ───────────────────────────────────────────────────────

    def _section_profile(self, parent, row):
        card = self._card(parent, row, "👤  Profile")

        self._label(card, "Your name", 1)
        self.name_entry = ctk.CTkEntry(
            card, font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.name_entry.insert(0, self.user.name)
        self.name_entry.grid(row=2, column=0, padx=24, pady=(0, 12), sticky="ew")

        self._label(card, "Currency", 3)
        self.currency_var = ctk.StringVar(value=self.user.currency)
        ctk.CTkOptionMenu(
            card,
            values=["USD", "EUR", "GBP", "RUB", "ILS"],
            variable=self.currency_var,
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        ).grid(row=4, column=0, padx=24, pady=(0, 12), sticky="ew")

        self._label(card, "Budget month starts on day", 5)
        self.month_start_var = ctk.StringVar(value=str(self.user.month_start))
        ctk.CTkOptionMenu(
            card,
            values=[str(d) for d in range(1, 29)],
            variable=self.month_start_var,
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        ).grid(row=6, column=0, padx=24, pady=(0, 20), sticky="ew")

        ctk.CTkButton(
            card, text="Save Profile",
            height=40, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._save_profile,
        ).grid(row=7, column=0, padx=24, pady=(0, 24), sticky="ew")

    def _save_profile(self):
        with db:
            self.user.name        = self.name_entry.get().strip() or self.user.name
            self.user.currency    = self.currency_var.get()
            self.user.month_start = int(self.month_start_var.get())
            self.user.save()
        set_currency(self.user.currency)
        messagebox.showinfo("Saved", "Profile updated successfully.")

    # ── Appearance section ────────────────────────────────────────────────────

    def _section_appearance(self, parent, row):
        card = self._card(parent, row, "🎨  Appearance")

        self._label(card, "Theme", 1)
        self.theme_var = ctk.StringVar(value=ctk.get_appearance_mode())
        ctk.CTkSegmentedButton(
            card,
            values=["Light", "Dark", "System"],
            variable=self.theme_var,
            font=ctk.CTkFont(size=13),
            command=self._change_theme,
        ).grid(row=2, column=0, padx=24, pady=(0, 24), sticky="ew")

    def _change_theme(self, value):
        ctk.set_appearance_mode(value)

    # ── Categories section ────────────────────────────────────────────────────

    def _section_categories(self, parent, row):
        card = self._card(parent, row, "🏷️  Custom Categories")

        user_cats = list(Category.select().where(
            Category.user == self.user,
            Category.is_archived == False,
        ).order_by(Category.name))

        if not user_cats:
            ctk.CTkLabel(
                card, text="No custom categories yet.",
                font=ctk.CTkFont(size=13), text_color=TEXT_MUTED,
            ).grid(row=1, column=0, padx=24, pady=(0, 12), sticky="w")
        else:
            for i, cat in enumerate(user_cats):
                row_f = ctk.CTkFrame(card, fg_color=BG_ROW, corner_radius=8)
                row_f.grid(row=i + 1, column=0, padx=24, pady=(0, 8), sticky="ew")
                row_f.grid_columnconfigure(0, weight=1)

                ctk.CTkLabel(
                    row_f,
                    text=f"{cat.icon}  {cat.name}  ({cat.type})",
                    font=ctk.CTkFont(size=13), text_color=TEXT_PRIMARY,
                ).grid(row=0, column=0, padx=12, pady=10, sticky="w")

                ctk.CTkButton(
                    row_f, text="Archive", width=80, height=28,
                    corner_radius=6, fg_color="transparent",
                    hover_color=HOVER_RED, text_color="#DC2626",
                    font=ctk.CTkFont(size=12),
                    command=lambda c=cat: self._archive_category(c, card),
                ).grid(row=0, column=1, padx=8)

        add_row = ctk.CTkFrame(card, fg_color="transparent")
        add_row.grid(row=99, column=0, padx=24, pady=(8, 24), sticky="ew")
        add_row.grid_columnconfigure(0, weight=1)

        self.new_cat_entry = ctk.CTkEntry(
            add_row, placeholder_text="Category name",
            font=ctk.CTkFont(size=13), height=36, corner_radius=8,
        )
        self.new_cat_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        self.new_cat_type = ctk.StringVar(value="expense")
        ctk.CTkOptionMenu(
            add_row, values=["expense", "income"],
            variable=self.new_cat_type,
            width=100, height=36, corner_radius=8,
            font=ctk.CTkFont(size=13),
        ).grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            add_row, text="+ Add",
            width=80, height=36, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._add_category,
        ).grid(row=0, column=2)

    def _add_category(self):
        name = self.new_cat_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter a category name")
            return
        with db:
            Category.create(
                user=self.user, name=name,
                type=self.new_cat_type.get(),
                icon="📦",
            )
        self.app.show_page("settings")

    def _archive_category(self, cat, card):
        ok = messagebox.askyesno("Archive", f"Archive category '{cat.name}'?")
        if ok:
            with db:
                cat.is_archived = True
                cat.save()
            self.app.show_page("settings")

    # ── Data section ──────────────────────────────────────────────────────────

    def _section_data(self, parent, row):
        card = self._card(parent, row, "💾  Data & Backup")

        ctk.CTkLabel(
            card,
            text=f"Database: {DB_PATH}",
            font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
        ).grid(row=1, column=0, padx=24, pady=(0, 16), sticky="w")

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=2, column=0, padx=24, pady=(0, 24), sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_row, text="📦 Backup Database",
            height=40, corner_radius=8,
            fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
            command=self._backup,
        ).grid(row=0, column=0, padx=(0, 8), sticky="ew")

        ctk.CTkButton(
            btn_row, text="📂 Open Backup Folder",
            height=40, corner_radius=8,
            fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
            command=self._open_backup_folder,
        ).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        ctk.CTkButton(
            card, text="🔔 Test Notifications",
            height=40, corner_radius=8,
            fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
            command=self._test_notifications,
        ).grid(row=3, column=0, padx=24, pady=(0, 24), sticky="ew")

    def _backup(self):
        backup_dir  = os.path.join(os.path.dirname(DB_PATH), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"budget_backup_{timestamp}.db")
        shutil.copy2(DB_PATH, backup_path)
        messagebox.showinfo("Backup", f"Saved to:\n{backup_path}")

    def _open_backup_folder(self):
        backup_dir = os.path.join(os.path.dirname(DB_PATH), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        os.system(f"open '{backup_dir}'")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _card(self, parent, row, title) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=12)
        card.grid(row=row, column=0, sticky="ew", pady=(0, 16))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text=title,
            font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=24, pady=(20, 12), sticky="w")

        return card

    def _label(self, parent, text, row):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=13), text_color=TEXT_SECONDARY,
        ).grid(row=row, column=0, padx=24, pady=(0, 4), sticky="w")

    def _test_notifications(self):
        from utils.notifications import check_now
        sent = check_now(self.user)
        if sent == 0:
            messagebox.showinfo(
                "Notifications",
                "No budget limits exceeded or in warning zone.\n"
                "Add budget limits and transactions to test."
            )
        else:
            messagebox.showinfo(
                "Notifications",
                f"Sent {sent} notification(s).\nCheck your macOS notification center."
            )
