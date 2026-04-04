"""
ui/pages/onboarding.py
First-launch onboarding wizard — name, currency, language.
Shown when no User exists in the database.

Flow:
  Step 1 → Welcome + Language picker (so subsequent steps are localized)
  Step 2 → Name + Currency
  Step 3 → Done → launches main app

Usage in main.py:
    from ui.pages.onboarding import OnboardingWindow
    user = OnboardingWindow.run()   # blocks until user presses "Get Started"
"""

import customtkinter as ctk
from utils.i18n import t, set_language
from utils.category_translations import update_system_category_translations

# ── Theme colors ──────────────────────────────────────────────────────────────
BG_MAIN     = ("#F8FAFC", "#1A1A2E")
BG_CARD     = ("#FFFFFF", "#16213E")
BG_ACCENT   = ("#1E293B", "#0F0F23")
TEXT_PRIMARY = ("#1E293B", "#E2E8F0")
TEXT_SECOND  = ("#64748B", "#94A3B8")
TEXT_MUTED   = ("#94A3B8", "#64748B")
BTN_PRIMARY  = "#2563EB"
BTN_HOVER    = "#1D4ED8"
BTN_BACK     = ("#F1F5F9", "#0F3460")
BTN_BACK_H   = ("#E2E8F0", "#1A4A7A")
DIVIDER      = ("#E2E8F0", "#2D2D44")

LANGUAGES = {
    "English":  "en",
    "Русский":  "ru",
    "Deutsch":  "de",
}

CURRENCIES = ["USD", "EUR", "GBP", "RUB", "ILS"]

CURRENCY_LABELS = {
    "USD": "$ — US Dollar",
    "EUR": "€ — Euro",
    "GBP": "£ — British Pound",
    "RUB": "₽ — Российский рубль",
    "ILS": "₪ — Israeli Shekel",
}


class OnboardingWindow(ctk.CTk):
    """
    Standalone onboarding window.
    Call OnboardingWindow.run() — returns a dict with user settings
    or None if the window was closed.
    """

    _result: dict | None = None

    def __init__(self):
        super().__init__()

        self.title("BudgetWise")
        self.geometry("520x620")
        self.resizable(False, False)

        # Center on screen
        self.update_idletasks()
        w = 520
        h = 620
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # State
        self.step = 1
        self.selected_lang = "en"
        self.selected_currency = "USD"
        self.user_name = ""

        # Container
        self.container = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(1, weight=1)

        self._render_step()

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def _render_step(self):
        self._clear()

        if self.step == 1:
            self._step_welcome()
        elif self.step == 2:
            self._step_profile()
        elif self.step == 3:
            self._step_ready()

    # ── Step 1: Welcome + Language ────────────────────────────────────────────

    def _step_welcome(self):
        # Top spacer
        ctk.CTkLabel(
            self.container, text="",
        ).grid(row=0, column=0, pady=(40, 0))

        # Logo + title
        ctk.CTkLabel(
            self.container, text="💰",
            font=ctk.CTkFont(size=56),
        ).grid(row=1, column=0, pady=(0, 8))

        ctk.CTkLabel(
            self.container, text="BudgetWise",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=2, column=0, pady=(0, 8))

        ctk.CTkLabel(
            self.container,
            text=t("onboarding_subtitle"),
            font=ctk.CTkFont(size=14),
            text_color=TEXT_SECOND,
        ).grid(row=3, column=0, pady=(0, 32))

        # Step indicator
        self._step_indicator(4)

        # Language card
        card = ctk.CTkFrame(self.container, fg_color=BG_CARD, corner_radius=12)
        card.grid(row=5, column=0, padx=48, pady=(24, 0), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text=t("choose_language"),
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=24, pady=(20, 4), sticky="w")

        ctk.CTkLabel(
            card, text=t("change_later_settings"),
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, padx=24, pady=(0, 16), sticky="w")

        # Language buttons as radio-style buttons
        lang_frame = ctk.CTkFrame(card, fg_color="transparent")
        lang_frame.grid(row=2, column=0, padx=24, pady=(0, 24), sticky="ew")
        lang_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.lang_buttons: dict[str, ctk.CTkButton] = {}
        for i, (display, code) in enumerate(LANGUAGES.items()):
            is_selected = (code == self.selected_lang)
            btn = ctk.CTkButton(
                lang_frame,
                text=display,
                height=44,
                corner_radius=8,
                fg_color=BTN_PRIMARY if is_selected else BTN_BACK,
                hover_color=BTN_HOVER if is_selected else BTN_BACK_H,
                text_color="#FFFFFF" if is_selected else TEXT_PRIMARY,
                font=ctk.CTkFont(size=14, weight="bold" if is_selected else "normal"),
                command=lambda c=code: self._select_language(c),
            )
            btn.grid(row=0, column=i, padx=(0 if i == 0 else 8, 0), sticky="ew")
            self.lang_buttons[code] = btn

        # Next button
        ctk.CTkButton(
            self.container, text=t("next_step"),
            width=280, height=48, corner_radius=10,
            fg_color=BTN_PRIMARY, hover_color=BTN_HOVER,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._go_step_2,
        ).grid(row=6, column=0, pady=(32, 40))

    def _select_language(self, code: str):
        self.selected_lang = code
        set_language(code)
        self._render_step()  # re-render with new language

    # ── Step 2: Name + Currency ───────────────────────────────────────────────

    def _step_profile(self):
        ctk.CTkLabel(
            self.container, text="",
        ).grid(row=0, column=0, pady=(40, 0))

        ctk.CTkLabel(
            self.container, text="👤",
            font=ctk.CTkFont(size=48),
        ).grid(row=1, column=0, pady=(0, 8))

        ctk.CTkLabel(
            self.container, text=t("setup_profile"),
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=2, column=0, pady=(0, 4))

        ctk.CTkLabel(
            self.container, text=t("setup_profile_sub"),
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECOND,
        ).grid(row=3, column=0, pady=(0, 24))

        # Step indicator
        self._step_indicator(4)

        # Form card
        card = ctk.CTkFrame(self.container, fg_color=BG_CARD, corner_radius=12)
        card.grid(row=5, column=0, padx=48, pady=(24, 0), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        # Name
        ctk.CTkLabel(
            card, text=t("your_name"),
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECOND,
        ).grid(row=0, column=0, padx=24, pady=(20, 4), sticky="w")

        self.name_entry = ctk.CTkEntry(
            card,
            placeholder_text=t("name_placeholder"),
            font=ctk.CTkFont(size=16),
            height=46, corner_radius=8,
        )
        self.name_entry.grid(row=1, column=0, padx=24, pady=(0, 16), sticky="ew")
        if self.user_name:
            self.name_entry.insert(0, self.user_name)
        self.name_entry.focus()

        # Currency
        ctk.CTkLabel(
            card, text=t("currency"),
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECOND,
        ).grid(row=2, column=0, padx=24, pady=(0, 4), sticky="w")

        currency_display = [CURRENCY_LABELS.get(c, c) for c in CURRENCIES]
        self.currency_var = ctk.StringVar(
            value=CURRENCY_LABELS.get(self.selected_currency, self.selected_currency)
        )
        ctk.CTkOptionMenu(
            card,
            values=currency_display,
            variable=self.currency_var,
            font=ctk.CTkFont(size=14),
            height=46, corner_radius=8,
        ).grid(row=3, column=0, padx=24, pady=(0, 24), sticky="ew")

        # Error label (hidden by default)
        self.error_label = ctk.CTkLabel(
            self.container, text="",
            font=ctk.CTkFont(size=12),
            text_color="#DC2626",
        )
        self.error_label.grid(row=6, column=0, pady=(8, 0))

        # Buttons row
        btn_row = ctk.CTkFrame(self.container, fg_color="transparent")
        btn_row.grid(row=7, column=0, pady=(16, 40))

        ctk.CTkButton(
            btn_row, text=f"← {t('back')}",
            width=100, height=44, corner_radius=8,
            fg_color=BTN_BACK, hover_color=BTN_BACK_H,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=14),
            command=self._go_step_1,
        ).grid(row=0, column=0, padx=(0, 12))

        ctk.CTkButton(
            btn_row, text=t("next_step"),
            width=180, height=48, corner_radius=10,
            fg_color=BTN_PRIMARY, hover_color=BTN_HOVER,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._go_step_3,
        ).grid(row=0, column=1)

    # ── Step 3: Ready ─────────────────────────────────────────────────────────

    def _step_ready(self):
        ctk.CTkLabel(
            self.container, text="",
        ).grid(row=0, column=0, pady=(60, 0))

        ctk.CTkLabel(
            self.container, text="🎉",
            font=ctk.CTkFont(size=64),
        ).grid(row=1, column=0, pady=(0, 12))

        ctk.CTkLabel(
            self.container, text=t("all_set"),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=2, column=0, pady=(0, 8))

        ctk.CTkLabel(
            self.container, text=t("all_set_sub"),
            font=ctk.CTkFont(size=14),
            text_color=TEXT_SECOND,
        ).grid(row=3, column=0, pady=(0, 24))

        # Step indicator
        self._step_indicator(4)

        # Summary card
        card = ctk.CTkFrame(self.container, fg_color=BG_CARD, corner_radius=12)
        card.grid(row=5, column=0, padx=48, pady=(24, 0), sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        summary_items = [
            ("👤", t("your_name"),   self.user_name),
            ("💱", t("currency"),    self.selected_currency),
            ("🌐", t("language"),    dict(zip(LANGUAGES.values(), LANGUAGES.keys())).get(self.selected_lang, "English")),
        ]

        for i, (icon, label, value) in enumerate(summary_items):
            if i > 0:
                ctk.CTkFrame(card, fg_color=DIVIDER, height=1).grid(
                    row=i * 2 - 1, column=0, columnspan=2, padx=24, sticky="ew"
                )

            row_f = ctk.CTkFrame(card, fg_color="transparent")
            row_f.grid(row=i * 2, column=0, columnspan=2, padx=24, sticky="ew")
            row_f.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                row_f, text=f"{icon}  {label}",
                font=ctk.CTkFont(size=13),
                text_color=TEXT_SECOND,
            ).grid(row=0, column=0, pady=14, sticky="w")

            ctk.CTkLabel(
                row_f, text=value,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=TEXT_PRIMARY,
            ).grid(row=0, column=1, pady=14, sticky="e")

        # Buttons row
        btn_row = ctk.CTkFrame(self.container, fg_color="transparent")
        btn_row.grid(row=6, column=0, pady=(32, 40))

        ctk.CTkButton(
            btn_row, text=f"← {t('back')}",
            width=100, height=44, corner_radius=8,
            fg_color=BTN_BACK, hover_color=BTN_BACK_H,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=14),
            command=self._go_step_2_from_3,
        ).grid(row=0, column=0, padx=(0, 12))

        ctk.CTkButton(
            btn_row, text=t("get_started"),
            width=200, height=52, corner_radius=10,
            fg_color="#16A34A", hover_color="#15803D",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._finish,
        ).grid(row=0, column=1)

    # ── Step indicator (dots) ─────────────────────────────────────────────────

    def _step_indicator(self, grid_row: int):
        frame = ctk.CTkFrame(self.container, fg_color="transparent")
        frame.grid(row=grid_row, column=0, pady=(0, 0))

        for i in range(1, 4):
            is_current = (i == self.step)
            is_done = (i < self.step)

            if is_current:
                color = BTN_PRIMARY
                size = 10
            elif is_done:
                color = "#16A34A"
                size = 8
            else:
                color = ("#CBD5E1", "#334155")
                size = 8

            dot = ctk.CTkFrame(
                frame, fg_color=color,
                width=size, height=size,
                corner_radius=size // 2,
            )
            dot.grid(row=0, column=i, padx=4)
            dot.grid_propagate(False)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _go_step_1(self):
        # Save name state when going back
        if hasattr(self, "name_entry"):
            self.user_name = self.name_entry.get().strip()
        self.step = 1
        self._render_step()

    def _go_step_2(self):
        self.step = 2
        self._render_step()

    def _go_step_2_from_3(self):
        self.step = 2
        self._render_step()

    def _go_step_3(self):
        name = self.name_entry.get().strip()
        if not name:
            self.error_label.configure(text=t("name_required"))
            return

        self.user_name = name

        # Parse currency from display label
        selected_display = self.currency_var.get()
        for code, label in CURRENCY_LABELS.items():
            if label == selected_display:
                self.selected_currency = code
                break

        self.step = 3
        self._render_step()

    def _finish(self):
        OnboardingWindow._result = {
            "name":     self.user_name,
            "currency": self.selected_currency,
            "language": self.selected_lang,
        }

        # Update category translations to match selected language
        update_system_category_translations(self.selected_lang)

        self.destroy()

    # ── Public API ────────────────────────────────────────────────────────────

    @classmethod
    def run(cls) -> dict | None:
        """
        Shows the onboarding window and blocks until the user
        completes it or closes the window.

        Returns:
            {"name": "Alex", "currency": "USD", "language": "en"}
            or None if the user closed the window without finishing.
        """
        cls._result = None
        window = cls()
        window.mainloop()
        return cls._result
