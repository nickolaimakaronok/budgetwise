"""
utils/constants.py
Application-wide constants — colors, sizes, UI settings.
"""

APP_NAME    = "BudgetWise"
APP_VERSION = "1.7.0"

# ── Window size ───────────────────────────────────────────────────────────────
WINDOW_WIDTH  = 1100
WINDOW_HEIGHT = 700
SIDEBAR_WIDTH = 200

# ── Color palette (light theme) ───────────────────────────────────────────────
COLOR = {
    "income":  "#16A34A",
    "expense": "#DC2626",
    "neutral": "#64748B",
    "primary": "#2563EB",
    "warning": "#D97706",
    "danger":  "#DC2626",
    "success": "#16A34A",
    "bg":      "#F8FAFC",
    "sidebar": "#1E293B",
    "card":    "#FFFFFF",
}

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONT = {
    "title":    ("SF Pro Display", 28, "bold"),
    "heading":  ("SF Pro Display", 18, "bold"),
    "body":     ("SF Pro Text",    14),
    "small":    ("SF Pro Text",    12),
    "mono":     ("SF Mono",        13),
    "title_w":  ("Segoe UI",       28, "bold"),
    "heading_w":("Segoe UI",       18, "bold"),
    "body_w":   ("Segoe UI",       14),
}

# ── Navigation items: (page_id, emoji, i18n_key) ─────────────────────────────
# Label is looked up via t(i18n_key) at runtime so it updates with language
NAV_ITEMS = [
    ("dashboard",    "🏠", "dashboard"),
    ("transactions", "📋", "transactions"),
    ("budget",       "📊", "budget"),
    ("analytics",    "📈", "analytics"),
    ("goals",        "🎯", "goals"),
    ("settings",     "⚙️",  "settings"),
]
