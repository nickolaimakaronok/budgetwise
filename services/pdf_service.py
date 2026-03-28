"""
services/pdf_service.py
Generates a monthly PDF report using ReportLab.
Includes: summary, spending by category, pie chart, all transactions.
"""

import io
import os
from datetime import date
from calendar import monthrange

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for file rendering
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, Image,
)

from services.analytics_service import get_spending_by_category, get_month_summary
from services.transaction_service import get_transactions
from utils.formatters import format_money_short, format_date, set_currency


# ── Color palette ─────────────────────────────────────────────────────────────
C_DARK   = colors.HexColor("#1E293B")
C_MUTED  = colors.HexColor("#64748B")
C_LIGHT  = colors.HexColor("#F8FAFC")
C_BORDER = colors.HexColor("#E2E8F0")
C_GREEN  = colors.HexColor("#16A34A")
C_RED    = colors.HexColor("#DC2626")
C_WHITE  = colors.white

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def _pie_chart_image(categories) -> Image | None:
    """Renders a pie chart and returns it as a ReportLab Image (in-memory PNG)."""
    if not categories:
        return None

    labels = [c["category"].name for c in categories]
    sizes  = [c["spent_cents"] for c in categories]
    clrs   = [c["color"] for c in categories]

    fig, ax = plt.subplots(figsize=(5, 3), facecolor="white")
    wedges, _, autotexts = ax.pie(
        sizes, labels=None, colors=clrs,
        autopct="%1.0f%%", startangle=90,
        pctdistance=0.75,
        wedgeprops={"width": 0.6, "edgecolor": "white", "linewidth": 2},
    )
    for t in autotexts:
        t.set_fontsize(8)
        t.set_color("white")
        t.set_fontweight("bold")

    ax.legend(
        wedges, labels,
        loc="center left", bbox_to_anchor=(1.05, 0.5),
        fontsize=8, frameon=False,
    )

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    img = Image(buf, width=12*cm, height=7*cm)
    return img


def generate_monthly_report(user, year: int, month: int, filepath: str):
    """
    Generates a monthly PDF report and saves it to filepath.
    """
    set_currency(user.currency)

    month_name = MONTH_NAMES[month - 1]
    last_day   = monthrange(year, month)[1]
    date_from  = date(year, month, 1)
    date_to    = date(year, month, last_day)

    summary    = get_month_summary(user, year, month)
    categories = get_spending_by_category(user, date_from, date_to)
    txs        = get_transactions(user, date_from=date_from, date_to=date_to)

    # ── Document ──────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    story  = []

    # ── Styles ────────────────────────────────────────────────────────────────
    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    title_s = S("T", fontSize=22, fontName="Helvetica-Bold",
                textColor=C_DARK, spaceAfter=12)
    sub_s = S("S", fontSize=12, fontName="Helvetica",
              textColor=C_MUTED, spaceAfter=24)
    section_s = S("Se", fontSize=13, fontName="Helvetica-Bold",   textColor=C_DARK,  spaceBefore=16, spaceAfter=8)
    label_s   = S("L",  fontSize=10, fontName="Helvetica",        textColor=C_MUTED)
    footer_s  = S("F",  fontSize=9,  fontName="Helvetica",        textColor=C_MUTED, alignment=TA_CENTER)
    normal_s  = styles["Normal"]

    def hr():
        return HRFlowable(width="100%", thickness=1, color=C_BORDER)

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("BudgetWise — Monthly Report", title_s))
    story.append(Paragraph(f"{month_name} {year}  ·  {user.name}", sub_s))
    story.append(hr())
    story.append(Spacer(1, 16))

    # ── Summary ───────────────────────────────────────────────────────────────
    story.append(Paragraph("Summary", section_s))

    income  = format_money_short(summary["income_cents"])
    expense = format_money_short(summary["expense_cents"])
    balance = format_money_short(summary["balance_cents"])
    bal_hex = "#16A34A" if summary["balance_cents"] >= 0 else "#DC2626"

    sum_data = [
        [Paragraph("Income", label_s),   Paragraph("Expenses", label_s),  Paragraph("Balance", label_s)],
        [
            Paragraph(f'<font color="#16A34A"><b>{income}</b></font>',  normal_s),
            Paragraph(f'<font color="#DC2626"><b>{expense}</b></font>', normal_s),
            Paragraph(f'<font color="{bal_hex}"><b>{balance}</b></font>', normal_s),
        ],
    ]
    sum_table = Table(sum_data, colWidths=["33%", "33%", "34%"])
    sum_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_LIGHT),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("FONTSIZE",      (0, 1), (-1, 1), 14),
    ]))
    story.append(sum_table)
    story.append(Spacer(1, 20))

    # ── Pie chart ─────────────────────────────────────────────────────────────
    if categories:
        story.append(hr())
        story.append(Paragraph("Spending by Category", section_s))

        pie = _pie_chart_image(categories)
        if pie:
            story.append(pie)
            story.append(Spacer(1, 8))

        # Category table
        cat_data = [["Category", "Spent", "% of Total"]]
        for c in categories:
            cat_data.append([
                f"{c['icon']}  {c['category'].name}",
                format_money_short(c["spent_cents"]),
                f"{c['percent']}%",
            ])

        cat_table = Table(cat_data, colWidths=["55%", "25%", "20%"])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), C_DARK),
            ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_LIGHT]),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("ALIGN",         (1, 0), (-1, -1), "RIGHT"),
        ]))
        story.append(cat_table)
        story.append(Spacer(1, 20))

    # ── Transactions ──────────────────────────────────────────────────────────
    if txs:
        story.append(hr())
        story.append(Paragraph("All Transactions", section_s))

        tx_data = [["Date", "Category", "Note", "Amount"]]
        for tx in txs:
            cat_name = tx.category.name if tx.category else "Uncategorized"
            sign     = "+" if tx.type == "income" else "\u2212"
            amount   = f"{sign}{format_money_short(tx.amount_cents)}"
            note     = (tx.note[:32] + "…") if len(tx.note) > 32 else tx.note
            tx_data.append([format_date(tx.date), cat_name, note, amount])

        tx_table = Table(tx_data, colWidths=["15%", "25%", "40%", "20%"])
        tx_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), C_DARK),
            ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_LIGHT]),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("ALIGN",         (3, 0), (3, -1), "RIGHT"),
        ]))
        story.append(tx_table)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 24))
    story.append(hr())
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Generated by BudgetWise  ·  {date.today().strftime('%d.%m.%Y')}",
        footer_s,
    ))

    doc.build(story)
