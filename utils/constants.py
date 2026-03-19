"""
utils/constants.py
Application-wide constants — colors, sizes, UI settings.
"""

APP_NAME    = "BudgetWise"
APP_VERSION = "0.1.0"

# ── Window size ───────────────────────────────────────────────────────────────
WINDOW_WIDTH  = 1100
WINDOW_HEIGHT = 700
SIDEBAR_WIDTH = 200

# ── Color palette (light theme) ───────────────────────────────────────────────
COLOR = {
    "income":  "#16A34A",   # Green — income
    "expense": "#DC2626",   # Red — expense (warnings only)
    "neutral": "#64748B",   # Grey
    "primary": "#2563EB",   # Blue — accent
    "warning": "#D97706",   # Orange — ~80% of budget limit
    "danger":  "#DC2626",   # Red — over 100% of limit
    "success": "#16A34A",   # Green — within limit
    "bg":      "#F8FAFC",   # App background
    "sidebar": "#1E293B",   # Sidebar background
    "card":    "#FFFFFF",   # Card background
}

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONT = {
    "title":    ("SF Pro Display", 28, "bold"),   # macOS
    "heading":  ("SF Pro Display", 18, "bold"),
    "body":     ("SF Pro Text",    14),
    "small":    ("SF Pro Text",    12),
    "mono":     ("SF Mono",        13),
    # Fallback for Windows / Linux
    "title_w":  ("Segoe UI",       28, "bold"),
    "heading_w":("Segoe UI",       18, "bold"),
    "body_w":   ("Segoe UI",       14),
}

# ── Navigation items: (id, emoji, label) ─────────────────────────────────────
NAV_ITEMS = [
    ("dashboard",    "🏠", "Dashboard"),
    ("transactions", "📋", "Transactions"),
    ("budget",       "📊", "Budget"),
    ("analytics",    "📈", "Analytics"),
    ("goals",        "🎯", "Goals"),
    ("settings",     "⚙️",  "Settings"),
]
