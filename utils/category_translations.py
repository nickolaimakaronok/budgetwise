"""
utils/category_translations.py
Translations for system category names.
Called when user changes language in Settings.
"""

# key = English name (as stored in DB on first run)
# value = translations per language
CATEGORY_TRANSLATIONS = {
    # ── Expenses ──────────────────────────────────────────────────────────────
    "Groceries": {
        "en": "Groceries",
        "ru": "Продукты",
        "de": "Lebensmittel",
    },
    "Cafes & Dining": {
        "en": "Cafes & Dining",
        "ru": "Кафе и рестораны",
        "de": "Cafés & Restaurants",
    },
    "Transport": {
        "en": "Transport",
        "ru": "Транспорт",
        "de": "Transport",
    },
    "Housing & Bills": {
        "en": "Housing & Bills",
        "ru": "Жильё и счета",
        "de": "Wohnen & Rechnungen",
    },
    "Health": {
        "en": "Health",
        "ru": "Здоровье",
        "de": "Gesundheit",
    },
    "Clothing": {
        "en": "Clothing",
        "ru": "Одежда",
        "de": "Kleidung",
    },
    "Entertainment": {
        "en": "Entertainment",
        "ru": "Развлечения",
        "de": "Unterhaltung",
    },
    "Sports": {
        "en": "Sports",
        "ru": "Спорт",
        "de": "Sport",
    },
    "Subscriptions": {
        "en": "Subscriptions",
        "ru": "Подписки",
        "de": "Abonnements",
    },
    "Education": {
        "en": "Education",
        "ru": "Образование",
        "de": "Bildung",
    },
    "Travel": {
        "en": "Travel",
        "ru": "Путешествия",
        "de": "Reisen",
    },
    "Gifts": {
        "en": "Gifts",
        "ru": "Подарки",
        "de": "Geschenke",
    },
    "Other": {
        "en": "Other",
        "ru": "Другое",
        "de": "Sonstiges",
    },
    # ── Income ────────────────────────────────────────────────────────────────
    "Salary": {
        "en": "Salary",
        "ru": "Зарплата",
        "de": "Gehalt",
    },
    "Freelance": {
        "en": "Freelance",
        "ru": "Фриланс",
        "de": "Freiberuflich",
    },
    "Side Job": {
        "en": "Side Job",
        "ru": "Подработка",
        "de": "Nebenjob",
    },
    "Investments": {
        "en": "Investments",
        "ru": "Инвестиции",
        "de": "Investitionen",
    },
    "Other Income": {
        "en": "Other Income",
        "ru": "Другой доход",
        "de": "Sonstiges Einkommen",
    },
}

# Reverse lookup — find English name by any translated name
def find_english_name(name: str) -> str | None:
    """Given any translated name, returns the English original."""
    for en_name, translations in CATEGORY_TRANSLATIONS.items():
        if name in translations.values():
            return en_name
    return None


def update_system_category_translations(lang: str):
    """
    Updates all system category names in DB to the given language.
    System categories have user=NULL.
    Safe to call multiple times.
    """
    from models.models import Category
    from db.database import db

    system_cats = list(Category.select().where(Category.user.is_null()))

    with db:
        for cat in system_cats:
            # Find the English key — try current name first, then reverse lookup
            en_name = CATEGORY_TRANSLATIONS.get(cat.name)
            if en_name is None:
                # Cat name might already be translated — find English original
                original = find_english_name(cat.name)
                if original:
                    translations = CATEGORY_TRANSLATIONS[original]
                else:
                    continue  # unknown category, skip
            else:
                translations = en_name

            new_name = translations.get(lang, translations.get("en", cat.name))
            if cat.name != new_name:
                cat.name = new_name
                cat.save()
