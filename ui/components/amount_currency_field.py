"""
ui/components/amount_currency_field.py
The amount field of the Add / Edit transaction windows, with a currency next to it:

    [ 20.00                ] [EUR ▾]
    1 EUR = [3.95] ₪   ≈ 79.00 ₪        ← only for another currency
    Rate from 03.10.2026 — check it…    ← only if the saved rate is older than a month

The currencies offered: the main one + those with a saved rate (Settings).
With no saved rates it looks exactly like the plain amount field.
"""

from datetime import date

import customtkinter as ctk

from services.currency_service import get_rates, preview_conversion
from utils.currencies import currency_symbol
from utils.formatters import format_date, format_money
from utils.i18n import t

TEXT_SECONDARY = ("#64748B", "#94A3B8")
TEXT_WARNING   = ("#B45309", "#F59E0B")
STALE_AFTER_DAYS = 30


class AmountCurrencyField(ctk.CTkFrame):

    def __init__(self, parent, user, amount_text: str = "",
                 currency: str | None = None, rate: str | None = None):
        """
        currency / rate: the transaction's own ones (Edit window); None = main currency.
        Editing keeps the purchase's own rate unless the user changes it.
        """
        super().__init__(parent, fg_color="transparent")
        self.main = user.currency
        self.saved = {r.currency: r for r in get_rates(user)}
        self.own_currency, self.own_rate = currency, rate

        codes = [self.main] + list(self.saved)
        if currency and currency not in codes:
            codes.append(currency)               # its saved rate was deleted since
        self.grid_columnconfigure(0, weight=1)

        self.amount_entry = ctk.CTkEntry(
            self, placeholder_text="0.00",
            font=ctk.CTkFont(size=22, weight="bold"), height=52, corner_radius=8,
        )
        if amount_text:
            self.amount_entry.insert(0, amount_text)
        self.amount_entry.grid(row=0, column=0, sticky="ew")
        self.amount_entry.bind("<KeyRelease>", lambda _e: self._refresh_hint())

        self.currency_var = ctk.StringVar(value=currency or self.main)
        if len(codes) > 1:
            ctk.CTkOptionMenu(
                self, values=codes, variable=self.currency_var,
                width=90, height=52, corner_radius=8,
                font=ctk.CTkFont(size=14, weight="bold"),
                command=lambda _code: self._on_currency(),
            ).grid(row=0, column=1, padx=(8, 0))

        # 1 EUR = [3.95] ₪   ≈ 79.00 ₪  (hidden for the main currency)
        self.rate_row = ctk.CTkFrame(self, fg_color="transparent")
        self.rate_label = ctk.CTkLabel(self.rate_row, text="", font=ctk.CTkFont(size=13))
        self.rate_label.grid(row=0, column=0, padx=(0, 6))
        self.rate_entry = ctk.CTkEntry(self.rate_row, width=90, height=30, corner_radius=6,
                                       font=ctk.CTkFont(size=13))
        self.rate_entry.grid(row=0, column=1)
        self.rate_entry.bind("<KeyRelease>", lambda _e: self._refresh_hint())
        ctk.CTkLabel(self.rate_row, text=currency_symbol(self.main),
                     font=ctk.CTkFont(size=13)).grid(row=0, column=2, padx=(6, 12))
        self.hint = ctk.CTkLabel(self.rate_row, text="", font=ctk.CTkFont(size=13, weight="bold"),
                                 text_color=TEXT_SECONDARY)
        self.hint.grid(row=0, column=3, sticky="w")
        self.stale = ctk.CTkLabel(self.rate_row, text="", font=ctk.CTkFont(size=11),
                                  text_color=TEXT_WARNING)

        self._on_currency()

    def _on_currency(self):
        code = self.currency_var.get()
        if code == self.main:
            self.rate_row.grid_remove()
            return
        self.rate_row.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.rate_label.configure(text=f"1 {code} =")

        own = code == self.own_currency and self.own_rate
        rate_text = self.own_rate if own else (self.saved[code].rate if code in self.saved else "")
        self.rate_entry.delete(0, "end")
        self.rate_entry.insert(0, rate_text)

        # a saved rate older than a month: remind to check it (not for an edited purchase's own rate)
        saved = self.saved.get(code)
        if not own and saved and (date.today() - saved.updated_at.date()).days > STALE_AFTER_DAYS:
            self.stale.configure(text=t("rate_stale").format(format_date(saved.updated_at.date())))
            self.stale.grid(row=1, column=0, columnspan=4, sticky="w", pady=(2, 0))
        else:
            self.stale.grid_remove()
        self._refresh_hint()

    def _refresh_hint(self):
        """≈ 79.00 ₪ — updated on every key press in the amount or the rate."""
        if self.currency_var.get() == self.main:
            return
        cents = preview_conversion(self.amount_entry.get(), self.rate_entry.get())
        self.hint.configure(text=f"≈ {format_money(cents)}" if cents is not None else "")

    def currency_and_rate(self) -> tuple[str | None, str | None]:
        """(None, None) for the main currency, otherwise (code, the rate as typed)."""
        code = self.currency_var.get()
        if code == self.main:
            return None, None
        return code, self.rate_entry.get()