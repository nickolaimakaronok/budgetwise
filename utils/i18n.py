"""
utils/i18n.py
Internationalization — all UI strings in English, Russian, and German.
Usage: from utils.i18n import t
       t("add_transaction")  →  "+ Add Transaction" / "+ Добавить" / "+ Hinzufügen"
"""

TRANSLATIONS = {
    "en": {
        # ── Navigation ────────────────────────────────────────────────────────
        "dashboard":    "Dashboard",
        "transactions": "Transactions",
        "budget":       "Budget",
        "analytics":    "Analytics",
        "goals":        "Goals",
        "settings":     "Settings",

        # ── Dashboard ─────────────────────────────────────────────────────────
        "monthly_balance":      "Monthly Balance",
        "days_left":            "days left this month",
        "daily_avg":            "Daily avg",
        "income":               "Income",
        "expenses":             "Expenses",
        "saved":                "Saved",
        "recent_transactions":  "Recent Transactions",
        "see_all":              "See all →",
        "no_transactions_yet":  "No transactions yet.\nAdd your first one!",

        # ── Transactions ──────────────────────────────────────────────────────
        "add_transaction":      "+ Add Transaction",
        "export_csv":           "⬇ Export CSV",
        "export_pdf":           "📄 Export PDF",
        "search_placeholder":   "🔍 Search by category or note...",
        "search":               "Search",
        "all":                  "All",
        "expense":              "Expense",
        "all_categories":       "All categories",
        "date_from":            "From:",
        "date_to":              "To:",
        "apply":                "Apply",
        "reset":                "Reset",
        "category":             "Category",
        "date":                 "Date",
        "note":                 "Note",
        "amount":               "Amount",
        "no_transactions_found":"No transactions found.",
        "delete_transaction":   "Delete transaction",
        "delete_confirm":       "Delete this transaction?",
        "export_complete":      "Export complete",
        "saved_to":             "Saved {} transactions to:\n{}",
        "uncategorized":        "Uncategorized",

        # ── Add / Edit Transaction Dialog ─────────────────────────────────────
        "add_transaction_title":  "Add Transaction",
        "edit_transaction_title": "Edit Transaction",
        "amount_label":           "Amount",
        "category_label":         "Category",
        "date_label":             "Date",
        "note_label":             "Note (optional)",
        "note_placeholder":       "e.g. Weekly groceries",
        "recurring":              "🔄 Repeat monthly — auto-create every month",
        "save_transaction":       "Save Transaction",
        "save_changes":           "Save Changes",
        "invalid_amount":         "Invalid amount. Enter a number like 150.50",
        "invalid_date":           "Invalid date. Use DD.MM.YYYY format",

        # ── Budget ────────────────────────────────────────────────────────────
        "copy_last_month":      "Copy last month",
        "set_limit":            "+ Set Limit",
        "no_budget_limits":     "No budget limits set.\nClick '+ Set Limit' to add one.",
        "left":                 "Left:",
        "delete_limit":         "Delete limit",
        "remove_limit_confirm": "Remove this budget limit?",
        "no_prev_month":        "No budget limits found in previous month.",
        "copy_last_month_title":"Copy last month",
        "set_budget_title":     "Set Budget Limit",
        "monthly_limit":        "Monthly Limit",
        "save_limit":           "Save Limit",
        "invalid_limit":        "Invalid amount. Enter a number like 500.00",

        # ── Analytics ─────────────────────────────────────────────────────────
        "spending_by_category": "Spending by Category",
        "no_expense_data":      "No expense data for this month.",
        "daily_expenses":       "Daily Expenses",
        "breakdown":            "Breakdown",
        "year_overview":        "Year Overview — {}",

        # ── Goals ─────────────────────────────────────────────────────────────
        "new_goal":             "+ New Goal",
        "no_goals":             "No goals yet.\nClick '+ New Goal' to create one.",
        "contribute":           "+ Contribute",
        "goal_reached":         "✅ Goal reached!",
        "overdue_by":           "⚠️ Overdue by {} days",
        "days_left_save":       "📅 {} days left  ·  Save {}/month",
        "archive_goal":         "Archive goal",
        "archive_confirm":      "Archive '{}'?",
        "new_goal_title":       "New Goal",
        "goal_name":            "Goal name",
        "goal_name_placeholder":"e.g. Japan trip",
        "target_amount":        "Target amount",
        "deadline_optional":    "Deadline (optional)",
        "create_goal":          "Create Goal",
        "goal_name_required":   "Please enter a goal name",
        "invalid_amount_goal":  "Invalid amount",
        "invalid_deadline":     "Invalid deadline. Use DD.MM.YYYY format",
        "contribute_title":     "Contribute to {}",
        "amount_to_add":        "Amount to add",
        "contribute_btn":       "Contribute",

        # ── Settings ──────────────────────────────────────────────────────────
        "profile":              "👤  Profile",
        "your_name":            "Your name",
        "currency":             "Currency",
        "month_starts":         "Budget month starts on day",
        "save_profile":         "Save Profile",
        "profile_saved":        "Profile updated successfully.",
        "appearance":           "🎨  Appearance",
        "theme":                "Theme",
        "light":                "Light",
        "dark":                 "Dark",
        "system":               "System",
        "language":             "Language",
        "custom_categories":    "🏷️  Custom Categories",
        "no_custom_categories": "No custom categories yet.",
        "archive":              "Archive",
        "archive_category":     "Archive",
        "archive_cat_confirm":  "Archive category '{}'?",
        "cat_name_placeholder": "Category name",
        "add":                  "+ Add",
        "cat_name_required":    "Please enter a category name",
        "data_backup":          "💾  Data & Backup",
        "database":             "Database:",
        "backup_db":            "📦 Backup Database",
        "open_backup_folder":   "📂 Open Backup Folder",
        "test_notifications":   "🔔 Test Notifications",
        "backup_saved":         "Saved to:\n{}",
        "notifications_none":   "No budget limits exceeded or in warning zone.\nAdd budget limits and transactions to test.",
        "notifications_sent":   "Sent {} notification(s).\nCheck your macOS notification center.",
        "saved":                "Saved",

        # ── PDF Report ────────────────────────────────────────────────────────
        "pdf_title":            "BudgetWise — Monthly Report",
        "pdf_summary":          "Summary",
        "pdf_categories":       "Spending by Category",
        "pdf_transactions":     "All Transactions",
        "pdf_footer":           "Generated by BudgetWise  ·  {}",
        "pdf_income":           "Income",
        "pdf_expenses":         "Expenses",
        "pdf_balance":          "Balance",
        "pdf_category":         "Category",
        "pdf_spent":            "Spent",
        "pdf_percent":          "% of Total",
        "pdf_date":             "Date",
        "pdf_note":             "Note",
        "pdf_amount":           "Amount",

        # ── General ───────────────────────────────────────────────────────────
        "error":                "Error",
        "ok":                   "OK",
        "cancel":               "Cancel",
        "yes":                  "Yes",
        "no":                   "No",
        "saved_title":          "Saved",
        "january":   "January",   "february":  "February",
        "march":     "March",     "april":     "April",
        "may":       "May",       "june":      "June",
        "july":      "July",      "august":    "August",
        "september": "September", "october":   "October",
        "november":  "November",  "december":  "December",
    },

    "ru": {
        # ── Navigation ────────────────────────────────────────────────────────
        "dashboard":    "Главная",
        "transactions": "Транзакции",
        "budget":       "Бюджет",
        "analytics":    "Аналитика",
        "goals":        "Цели",
        "settings":     "Настройки",

        # ── Dashboard ─────────────────────────────────────────────────────────
        "monthly_balance":      "Баланс за месяц",
        "days_left":            "дней осталось",
        "daily_avg":            "В среднем в день",
        "income":               "Доходы",
        "expenses":             "Расходы",
        "saved":                "Накоплено",
        "recent_transactions":  "Последние транзакции",
        "see_all":              "Все →",
        "no_transactions_yet":  "Транзакций пока нет.\nДобавьте первую!",

        # ── Transactions ──────────────────────────────────────────────────────
        "add_transaction":      "+ Добавить",
        "export_csv":           "⬇ Экспорт CSV",
        "export_pdf":           "📄 Экспорт PDF",
        "search_placeholder":   "🔍 Поиск по категории или заметке...",
        "search":               "Найти",
        "all":                  "Все",
        "expense":              "Расход",
        "all_categories":       "Все категории",
        "date_from":            "С:",
        "date_to":              "По:",
        "apply":                "Применить",
        "reset":                "Сбросить",
        "category":             "Категория",
        "date":                 "Дата",
        "note":                 "Заметка",
        "amount":               "Сумма",
        "no_transactions_found":"Транзакции не найдены.",
        "delete_transaction":   "Удалить транзакцию",
        "delete_confirm":       "Удалить эту транзакцию?",
        "export_complete":      "Экспорт завершён",
        "saved_to":             "Сохранено {} транзакций:\n{}",
        "uncategorized":        "Без категории",

        # ── Add / Edit Transaction Dialog ─────────────────────────────────────
        "add_transaction_title":  "Добавить транзакцию",
        "edit_transaction_title": "Редактировать транзакцию",
        "amount_label":           "Сумма",
        "category_label":         "Категория",
        "date_label":             "Дата",
        "note_label":             "Заметка (необязательно)",
        "note_placeholder":       "например, Продукты на неделю",
        "recurring":              "🔄 Повторять — создавать каждый месяц",
        "save_transaction":       "Сохранить",
        "save_changes":           "Сохранить изменения",
        "invalid_amount":         "Неверная сумма. Введите число, например 150.50",
        "invalid_date":           "Неверная дата. Используйте формат ДД.ММ.ГГГГ",

        # ── Budget ────────────────────────────────────────────────────────────
        "copy_last_month":      "Копировать прошлый месяц",
        "set_limit":            "+ Установить лимит",
        "no_budget_limits":     "Лимиты не установлены.\nНажмите '+ Установить лимит'.",
        "left":                 "Остаток:",
        "delete_limit":         "Удалить лимит",
        "remove_limit_confirm": "Удалить этот лимит бюджета?",
        "no_prev_month":        "Лимиты за прошлый месяц не найдены.",
        "copy_last_month_title":"Копировать прошлый месяц",
        "set_budget_title":     "Установить лимит бюджета",
        "monthly_limit":        "Лимит на месяц",
        "save_limit":           "Сохранить",
        "invalid_limit":        "Неверная сумма. Введите число, например 500.00",

        # ── Analytics ─────────────────────────────────────────────────────────
        "spending_by_category": "Расходы по категориям",
        "no_expense_data":      "Нет данных о расходах за этот месяц.",
        "daily_expenses":       "Расходы по дням",
        "breakdown":            "Разбивка",
        "year_overview":        "Обзор года — {}",

        # ── Goals ─────────────────────────────────────────────────────────────
        "new_goal":             "+ Новая цель",
        "no_goals":             "Целей пока нет.\nНажмите '+ Новая цель'.",
        "contribute":           "+ Пополнить",
        "goal_reached":         "✅ Цель достигнута!",
        "overdue_by":           "⚠️ Просрочено на {} дней",
        "days_left_save":       "📅 Осталось {} дней  ·  Откладывать {}/мес",
        "archive_goal":         "Архивировать цель",
        "archive_confirm":      "Архивировать '{}'?",
        "new_goal_title":       "Новая цель",
        "goal_name":            "Название цели",
        "goal_name_placeholder":"например, Поездка в Японию",
        "target_amount":        "Целевая сумма",
        "deadline_optional":    "Срок (необязательно)",
        "create_goal":          "Создать цель",
        "goal_name_required":   "Введите название цели",
        "invalid_amount_goal":  "Неверная сумма",
        "invalid_deadline":     "Неверная дата. Используйте формат ДД.ММ.ГГГГ",
        "contribute_title":     "Пополнить: {}",
        "amount_to_add":        "Сумма пополнения",
        "contribute_btn":       "Пополнить",

        # ── Settings ──────────────────────────────────────────────────────────
        "profile":              "👤  Профиль",
        "your_name":            "Ваше имя",
        "currency":             "Валюта",
        "month_starts":         "Бюджетный месяц начинается с",
        "save_profile":         "Сохранить профиль",
        "profile_saved":        "Профиль успешно обновлён.",
        "appearance":           "🎨  Внешний вид",
        "theme":                "Тема",
        "light":                "Светлая",
        "dark":                 "Тёмная",
        "system":               "Системная",
        "language":             "Язык",
        "custom_categories":    "🏷️  Пользовательские категории",
        "no_custom_categories": "Пользовательских категорий пока нет.",
        "archive":              "Архив",
        "archive_category":     "Архивировать",
        "archive_cat_confirm":  "Архивировать категорию '{}'?",
        "cat_name_placeholder": "Название категории",
        "add":                  "+ Добавить",
        "cat_name_required":    "Введите название категории",
        "data_backup":          "💾  Данные и резервные копии",
        "database":             "База данных:",
        "backup_db":            "📦 Создать резервную копию",
        "open_backup_folder":   "📂 Открыть папку с копиями",
        "test_notifications":   "🔔 Проверить уведомления",
        "backup_saved":         "Сохранено:\n{}",
        "notifications_none":   "Лимиты бюджета не превышены.\nДобавьте лимиты и транзакции для проверки.",
        "notifications_sent":   "Отправлено {} уведомлений.\nПроверьте центр уведомлений macOS.",
        "saved":                "Сохранено",

        # ── PDF Report ────────────────────────────────────────────────────────
        "pdf_title":            "BudgetWise — Отчёт за месяц",
        "pdf_summary":          "Сводка",
        "pdf_categories":       "Расходы по категориям",
        "pdf_transactions":     "Все транзакции",
        "pdf_footer":           "Создано BudgetWise  ·  {}",
        "pdf_income":           "Доходы",
        "pdf_expenses":         "Расходы",
        "pdf_balance":          "Баланс",
        "pdf_category":         "Категория",
        "pdf_spent":            "Потрачено",
        "pdf_percent":          "% от общего",
        "pdf_date":             "Дата",
        "pdf_note":             "Заметка",
        "pdf_amount":           "Сумма",

        # ── General ───────────────────────────────────────────────────────────
        "error":                "Ошибка",
        "ok":                   "ОК",
        "cancel":               "Отмена",
        "yes":                  "Да",
        "no":                   "Нет",
        "saved_title":          "Сохранено",
        "january":   "Январь",    "february":  "Февраль",
        "march":     "Март",      "april":     "Апрель",
        "may":       "Май",       "june":      "Июнь",
        "july":      "Июль",      "august":    "Август",
        "september": "Сентябрь",  "october":   "Октябрь",
        "november":  "Ноябрь",    "december":  "Декабрь",
    },

    "de": {
        # ── Navigation ────────────────────────────────────────────────────────
        "dashboard":    "Übersicht",
        "transactions": "Transaktionen",
        "budget":       "Budget",
        "analytics":    "Analyse",
        "goals":        "Ziele",
        "settings":     "Einstellungen",

        # ── Dashboard ─────────────────────────────────────────────────────────
        "monthly_balance":      "Monatliches Guthaben",
        "days_left":            "Tage verbleibend",
        "daily_avg":            "Tagesdurchschnitt",
        "income":               "Einnahmen",
        "expenses":             "Ausgaben",
        "saved":                "Gespart",
        "recent_transactions":  "Letzte Transaktionen",
        "see_all":              "Alle →",
        "no_transactions_yet":  "Noch keine Transaktionen.\nFügen Sie die erste hinzu!",

        # ── Transactions ──────────────────────────────────────────────────────
        "add_transaction":      "+ Hinzufügen",
        "export_csv":           "⬇ CSV exportieren",
        "export_pdf":           "📄 PDF exportieren",
        "search_placeholder":   "🔍 Nach Kategorie oder Notiz suchen...",
        "search":               "Suchen",
        "all":                  "Alle",
        "expense":              "Ausgabe",
        "all_categories":       "Alle Kategorien",
        "date_from":            "Von:",
        "date_to":              "Bis:",
        "apply":                "Anwenden",
        "reset":                "Zurücksetzen",
        "category":             "Kategorie",
        "date":                 "Datum",
        "note":                 "Notiz",
        "amount":               "Betrag",
        "no_transactions_found":"Keine Transaktionen gefunden.",
        "delete_transaction":   "Transaktion löschen",
        "delete_confirm":       "Diese Transaktion löschen?",
        "export_complete":      "Export abgeschlossen",
        "saved_to":             "{} Transaktionen gespeichert:\n{}",
        "uncategorized":        "Ohne Kategorie",

        # ── Add / Edit Transaction Dialog ─────────────────────────────────────
        "add_transaction_title":  "Transaktion hinzufügen",
        "edit_transaction_title": "Transaktion bearbeiten",
        "amount_label":           "Betrag",
        "category_label":         "Kategorie",
        "date_label":             "Datum",
        "note_label":             "Notiz (optional)",
        "note_placeholder":       "z.B. Wocheneinkauf",
        "recurring":              "🔄 Monatlich wiederholen",
        "save_transaction":       "Speichern",
        "save_changes":           "Änderungen speichern",
        "invalid_amount":         "Ungültiger Betrag. Geben Sie eine Zahl ein, z.B. 150.50",
        "invalid_date":           "Ungültiges Datum. Verwenden Sie TT.MM.JJJJ",

        # ── Budget ────────────────────────────────────────────────────────────
        "copy_last_month":      "Letzten Monat kopieren",
        "set_limit":            "+ Limit festlegen",
        "no_budget_limits":     "Keine Budgetlimits gesetzt.\nKlicken Sie auf '+ Limit festlegen'.",
        "left":                 "Verbleibend:",
        "delete_limit":         "Limit löschen",
        "remove_limit_confirm": "Dieses Budgetlimit entfernen?",
        "no_prev_month":        "Keine Budgetlimits im Vormonat gefunden.",
        "copy_last_month_title":"Letzten Monat kopieren",
        "set_budget_title":     "Budgetlimit festlegen",
        "monthly_limit":        "Monatliches Limit",
        "save_limit":           "Speichern",
        "invalid_limit":        "Ungültiger Betrag. Geben Sie eine Zahl ein, z.B. 500.00",

        # ── Analytics ─────────────────────────────────────────────────────────
        "spending_by_category": "Ausgaben nach Kategorie",
        "no_expense_data":      "Keine Ausgabendaten für diesen Monat.",
        "daily_expenses":       "Tägliche Ausgaben",
        "breakdown":            "Aufschlüsselung",
        "year_overview":        "Jahresübersicht — {}",

        # ── Goals ─────────────────────────────────────────────────────────────
        "new_goal":             "+ Neues Ziel",
        "no_goals":             "Noch keine Ziele.\nKlicken Sie auf '+ Neues Ziel'.",
        "contribute":           "+ Einzahlen",
        "goal_reached":         "✅ Ziel erreicht!",
        "overdue_by":           "⚠️ {} Tage überfällig",
        "days_left_save":       "📅 Noch {} Tage  ·  {}/Monat sparen",
        "archive_goal":         "Ziel archivieren",
        "archive_confirm":      "'{}' archivieren?",
        "new_goal_title":       "Neues Ziel",
        "goal_name":            "Zielname",
        "goal_name_placeholder":"z.B. Japan-Reise",
        "target_amount":        "Zielbetrag",
        "deadline_optional":    "Frist (optional)",
        "create_goal":          "Ziel erstellen",
        "goal_name_required":   "Bitte geben Sie einen Zielnamen ein",
        "invalid_amount_goal":  "Ungültiger Betrag",
        "invalid_deadline":     "Ungültiges Datum. Verwenden Sie TT.MM.JJJJ",
        "contribute_title":     "Einzahlen: {}",
        "amount_to_add":        "Einzuzahlender Betrag",
        "contribute_btn":       "Einzahlen",

        # ── Settings ──────────────────────────────────────────────────────────
        "profile":              "👤  Profil",
        "your_name":            "Ihr Name",
        "currency":             "Währung",
        "month_starts":         "Budgetmonat beginnt am Tag",
        "save_profile":         "Profil speichern",
        "profile_saved":        "Profil erfolgreich aktualisiert.",
        "appearance":           "🎨  Erscheinungsbild",
        "theme":                "Thema",
        "light":                "Hell",
        "dark":                 "Dunkel",
        "system":               "System",
        "language":             "Sprache",
        "custom_categories":    "🏷️  Eigene Kategorien",
        "no_custom_categories": "Noch keine eigenen Kategorien.",
        "archive":              "Archiv",
        "archive_category":     "Archivieren",
        "archive_cat_confirm":  "Kategorie '{}' archivieren?",
        "cat_name_placeholder": "Kategoriename",
        "add":                  "+ Hinzufügen",
        "cat_name_required":    "Bitte geben Sie einen Kategorienamen ein",
        "data_backup":          "💾  Daten & Sicherung",
        "database":             "Datenbank:",
        "backup_db":            "📦 Datenbank sichern",
        "open_backup_folder":   "📂 Sicherungsordner öffnen",
        "test_notifications":   "🔔 Benachrichtigungen testen",
        "backup_saved":         "Gespeichert:\n{}",
        "notifications_none":   "Keine Budgetlimits überschritten.\nFügen Sie Limits und Transaktionen hinzu.",
        "notifications_sent":   "{} Benachrichtigung(en) gesendet.\nÜberprüfen Sie das macOS-Benachrichtigungscenter.",
        "saved":                "Gespeichert",

        # ── PDF Report ────────────────────────────────────────────────────────
        "pdf_title":            "BudgetWise — Monatsbericht",
        "pdf_summary":          "Zusammenfassung",
        "pdf_categories":       "Ausgaben nach Kategorie",
        "pdf_transactions":     "Alle Transaktionen",
        "pdf_footer":           "Erstellt von BudgetWise  ·  {}",
        "pdf_income":           "Einnahmen",
        "pdf_expenses":         "Ausgaben",
        "pdf_balance":          "Guthaben",
        "pdf_category":         "Kategorie",
        "pdf_spent":            "Ausgegeben",
        "pdf_percent":          "% des Gesamten",
        "pdf_date":             "Datum",
        "pdf_note":             "Notiz",
        "pdf_amount":           "Betrag",

        # ── General ───────────────────────────────────────────────────────────
        "error":                "Fehler",
        "ok":                   "OK",
        "cancel":               "Abbrechen",
        "yes":                  "Ja",
        "no":                   "Nein",
        "saved_title":          "Gespeichert",
        "january":   "Januar",    "february":  "Februar",
        "march":     "März",      "april":     "April",
        "may":       "Mai",       "june":      "Juni",
        "july":      "Juli",      "august":    "August",
        "september": "September", "october":   "Oktober",
        "november":  "November",  "december":  "Dezember",
    },
}

# Current language — changed via Settings
_current_language = "en"


def set_language(lang: str):
    """Sets the current language. Call this when user changes language in Settings."""
    global _current_language
    if lang in TRANSLATIONS:
        _current_language = lang


def get_language() -> str:
    """Returns the current language code."""
    return _current_language


def t(key: str, *args) -> str:
    """
    Returns translated string for the current language.
    Supports format arguments: t("saved_to", 5, "/path/file.csv")
    Falls back to English if key not found in current language.
    Falls back to key itself if not found anywhere.
    """
    lang   = _current_language
    result = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key)
    if result is None:
        result = TRANSLATIONS["en"].get(key, key)
    if args:
        result = result.format(*args)
    return result


def months_list() -> list[str]:
    """Returns list of 12 month names in the current language."""
    keys = [
        "january", "february", "march", "april",
        "may", "june", "july", "august",
        "september", "october", "november", "december"
    ]
    return [t(k) for k in keys]
