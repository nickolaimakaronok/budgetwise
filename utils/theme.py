"""
utils/theme.py
Centralized color constants for Light and Dark themes.
Use tuples (light, dark) for all CustomTkinter widgets.
"""

# ── Backgrounds ───────────────────────────────────────────────────────────────
BG_PAGE        = ("#F8FAFC", "#1A1A2E")   # page background
BG_CARD        = ("#FFFFFF", "#16213E")   # card / panel background
BG_HEADER      = ("#FFFFFF", "#0F0F23")   # header bar
BG_ROW_EVEN    = ("#FFFFFF", "#16213E")   # table row even
BG_ROW_ODD     = ("#F8FAFC", "#1A1A2E")  # table row odd
BG_INPUT       = ("#F1F5F9", "#0F3460")  # input / filter bar
BG_TOGGLE      = ("#F1F5F9", "#0F3460")  # segmented button bg

# ── Text ──────────────────────────────────────────────────────────────────────
TEXT_PRIMARY   = ("#1E293B", "#E2E8F0")  # main text
TEXT_SECONDARY = ("#64748B", "#94A3B8")  # muted text
TEXT_MUTED     = ("#94A3B8", "#64748B")  # very muted

# ── Accents ───────────────────────────────────────────────────────────────────
ACCENT_BLUE    = ("#2563EB", "#3B82F6")
ACCENT_GREEN   = ("#16A34A", "#22C55E")
ACCENT_RED     = ("#DC2626", "#EF4444")
ACCENT_YELLOW  = ("#D97706", "#F59E0B")

# ── Borders / Dividers ────────────────────────────────────────────────────────
BORDER         = ("#E2E8F0", "#2D2D44")
DIVIDER        = ("#F1F5F9", "#2D2D44")