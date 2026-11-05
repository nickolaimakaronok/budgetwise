"""
ui/components/change_currency_dialog.py
The window that opens when the main currency is changed in Settings.

Two choices (services/currency_service.change_main_currency does the work):
  - only change the symbol — the amounts were already in the new currency
  - convert everything with one rate — moving to another currency
"""

import customtkinter as ctk
from tkinter import messagebox

from services.currency_service import (
    MODE_CONVERT, MODE_RELABEL, change_main_currency, format_rate, get_rate, parse_rate,
)
from utils.currencies import currency_label, currency_symbol
from utils.formatters import set_currency
from utils.i18n import t

TEXT_PRIMARY   = ("#1E293B", "#E2E8F0")
TEXT_SECONDARY = ("#64748B", "#94A3B8")
TEXT_ERROR     = "#DC2626"


class ChangeCurrencyDialog(ctk.CTkToplevel):

    def __init__(self, parent, user, new_currency, on_done, on_cancel):
        super().__init__(parent)
        self.user      = user
        self.old_code  = user.currency
        self.new_code  = new_currency
        self.on_done   = on_done
        self.on_cancel = on_cancel

        self.title(t("change_currency_title"))
        self.geometry("480x500")
        self.resizable(False, False)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self._cancel)    # closing the window = Cancel
        self._build()

    def _build(self):
        old_label = currency_label(self.old_code)
        new_label = currency_label(self.new_code)

        ctk.CTkLabel(
            self, text=t("change_currency_from_to").format(old_label, new_label),
            font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_PRIMARY,
            wraplength=420, justify="left",
        ).grid(row=0, column=0, padx=28, pady=(24, 16), sticky="w")

        self.mode_var = ctk.StringVar(value=MODE_RELABEL)

        # ── Only the symbol ──
        ctk.CTkRadioButton(
            self, text=t("mode_relabel"), variable=self.mode_var, value=MODE_RELABEL,
            font=ctk.CTkFont(size=14, weight="bold"), command=self._on_mode,
        ).grid(row=1, column=0, padx=28, sticky="w")
        ctk.CTkLabel(
            self, text=t("mode_relabel_hint").format(new_label),
            font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
            wraplength=400, justify="left",
        ).grid(row=2, column=0, padx=(56, 28), pady=(2, 16), sticky="w")

        # ── Convert everything ──
        ctk.CTkRadioButton(
            self, text=t("mode_convert"), variable=self.mode_var, value=MODE_CONVERT,
            font=ctk.CTkFont(size=14, weight="bold"), command=self._on_mode,
        ).grid(row=3, column=0, padx=28, sticky="w")
        ctk.CTkLabel(
            self, text=t("mode_convert_hint").format(new_label),
            font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
            wraplength=400, justify="left",
        ).grid(row=4, column=0, padx=(56, 28), pady=(2, 8), sticky="w")

        # 1 EUR = [3.95] ₪ — prefilled with the saved rate of the new currency, if there is one
        rate_row = ctk.CTkFrame(self, fg_color="transparent")
        rate_row.grid(row=5, column=0, padx=(56, 28), sticky="w")
        ctk.CTkLabel(rate_row, text=f"1 {self.new_code} =",
                     font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=(0, 8))
        self.rate_entry = ctk.CTkEntry(rate_row, width=110, height=36, corner_radius=8,
                                       placeholder_text="3.95", font=ctk.CTkFont(size=14))
        self.rate_entry.grid(row=0, column=1)
        saved = get_rate(self.user, self.new_code)
        if saved is not None:
            self.rate_entry.insert(0, format_rate(saved))
        ctk.CTkLabel(rate_row, text=currency_symbol(self.old_code),
                     font=ctk.CTkFont(size=14)).grid(row=0, column=2, padx=(8, 0))

        ctk.CTkLabel(
            self, text=t("backup_note"),
            font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
        ).grid(row=6, column=0, padx=(56, 28), pady=(8, 0), sticky="w")

        self.error_label = ctk.CTkLabel(self, text="", text_color=TEXT_ERROR,
                                        font=ctk.CTkFont(size=12))
        self.error_label.grid(row=7, column=0, padx=28, pady=(8, 0), sticky="w")

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=8, column=0, padx=28, pady=(12, 24), sticky="ew")
        buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(buttons, text=t("cancel"), height=40, corner_radius=8,
                      fg_color="transparent", border_width=1, text_color=TEXT_PRIMARY,
                      command=self._cancel).grid(row=0, column=0, padx=(0, 8), sticky="ew")
        ctk.CTkButton(buttons, text=t("apply"), height=40, corner_radius=8,
                      fg_color="#2563EB", hover_color="#1D4ED8",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._apply).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        self._on_mode()

    def _on_mode(self):
        """The rate is only needed for "convert everything"."""
        converting = self.mode_var.get() == MODE_CONVERT
        self.rate_entry.configure(state="normal" if converting else "disabled")
        self.error_label.configure(text="")

    def _apply(self):
        mode = self.mode_var.get()
        rate = None
        if mode == MODE_CONVERT:
            try:
                rate = parse_rate(self.rate_entry.get())
            except ValueError:
                self.error_label.configure(text=t("rate_invalid"))
                return

        try:
            counts = change_main_currency(self.user, self.new_code, mode, rate)
        except Exception as e:
            messagebox.showerror(t("error"), str(e), parent=self)
            return

        set_currency(self.new_code)
        if mode == MODE_CONVERT:
            text = t("currency_converted").format(
                currency_label(self.new_code),
                counts["transactions"], counts["budgets"], counts["goals"])
        else:
            text = t("currency_relabelled").format(currency_label(self.new_code))
        self.grab_release()
        self.destroy()
        messagebox.showinfo(t("saved_title"), text)
        self.on_done()

    def _cancel(self):
        self.grab_release()
        self.destroy()
        self.on_cancel()