"""
ui/pages/goals.py
Goals page — savings goals with progress bars.
"""

import logging
import customtkinter as ctk
from tkinter import messagebox
from services.goal_service import (
    get_goals, add_goal, contribute_to_goal,
    archive_goal, get_goal_progress
)
from utils.formatters import format_money_short, set_currency

logger = logging.getLogger(__name__)

# ── Theme colors — (light, dark) tuples ──────────────────────────────────────
BG_PAGE        = ("#F8FAFC", "#1A1A2E")
BG_CARD        = ("#FFFFFF", "#16213E")
BG_HEADER      = ("#FFFFFF", "#0F0F23")
BG_BAR         = ("#F1F5F9", "#0F3460")
TEXT_PRIMARY   = ("#1E293B", "#E2E8F0")
TEXT_SECONDARY = ("#64748B", "#94A3B8")
TEXT_MUTED     = ("#94A3B8", "#64748B")
HOVER_RED      = ("#FEE2E2", "#3D1A1A")
HOVER_BLUE     = ("#EFF6FF", "#1E3A5F")
BTN_CONTRIBUTE = ("#EFF6FF", "#1E3A5F")
BTN_CONTRIBUTE_HOVER = ("#DBEAFE", "#1A4A7A")


class GoalsPage(ctk.CTkFrame):

    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color=BG_PAGE, corner_radius=0)
        self.user = user
        self.app  = app
        set_currency(user.currency)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=BG_HEADER, corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        ctk.CTkLabel(
            header, text="Goals",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=32, pady=20, sticky="w")

        ctk.CTkButton(
            header, text="+ New Goal",
            width=130, height=36, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._open_add_dialog,
        ).grid(row=0, column=1, padx=32, pady=16, sticky="e")

    def _build_body(self):
        self.body = ctk.CTkScrollableFrame(
            self, fg_color=BG_PAGE, corner_radius=0
        )
        self.body.grid(row=1, column=0, sticky="nsew", padx=32, pady=16)
        self.body.grid_columnconfigure((0, 1), weight=1)
        self._load_goals()

    def _load_goals(self):
        for w in self.body.winfo_children():
            w.destroy()

        goals = get_goals(self.user)

        if not goals:
            ctk.CTkLabel(
                self.body,
                text="No goals yet.\nClick '+ New Goal' to create one.",
                font=ctk.CTkFont(size=14),
                text_color=TEXT_MUTED,
                justify="center",
            ).grid(row=0, column=0, columnspan=2, pady=60)
            return

        for i, goal in enumerate(goals):
            col = i % 2
            row = i // 2
            self._goal_card(row, col, goal)

    def _goal_card(self, row, col, goal):
        progress = get_goal_progress(goal)
        pct  = progress["percent"] / 100
        done = progress["is_completed"]

        from services.goal_service import get_goal_deadline_info
        deadline_info = get_goal_deadline_info(goal)

        card = ctk.CTkFrame(self.body, fg_color=BG_CARD, corner_radius=12)
        card.grid(row=row, column=col,
                  padx=(0 if col == 0 else 12, 0),
                  pady=(0, 16), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        # Icon + name + archive button
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, padx=20, pady=(20, 8), sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top, text=f"{goal.icon}  {goal.name}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            top, text="✕", width=28, height=28, corner_radius=6,
            fg_color="transparent", hover_color=HOVER_RED,
            text_color=TEXT_MUTED,
            command=lambda g=goal: self._archive(g),
        ).grid(row=0, column=1)

        # Progress bar
        bar_bg = ctk.CTkFrame(card, fg_color=BG_BAR, corner_radius=4, height=10)
        bar_bg.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="ew")
        bar_bg.grid_propagate(False)

        if pct > 0:
            bar_color = "#16A34A" if done else "#2563EB"
            ctk.CTkFrame(
                bar_bg, fg_color=bar_color, corner_radius=4, height=10
            ).place(relx=0, rely=0, relwidth=min(pct, 1.0), relheight=1)

        # Amount + percent
        ctk.CTkLabel(
            card,
            text=f"{format_money_short(goal.current_cents)} / "
                 f"{format_money_short(goal.target_cents)}  ·  {progress['percent']}%",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
        ).grid(row=2, column=0, padx=20, pady=(0, 4), sticky="w")

        # Deadline info
        if deadline_info["has_deadline"] and not done:
            if deadline_info["is_overdue"]:
                deadline_text  = f"⚠️ Overdue by {abs(deadline_info['days_left'])} days"
                deadline_color = "#DC2626"
            else:
                deadline_text = (
                    f"📅 {deadline_info['days_left']} days left  ·  "
                    f"Save {format_money_short(deadline_info['needed_per_month'])}/month"
                )
                deadline_color = TEXT_SECONDARY

            ctk.CTkLabel(
                card,
                text=deadline_text,
                font=ctk.CTkFont(size=12),
                text_color=deadline_color,
            ).grid(row=3, column=0, padx=20, pady=(0, 8), sticky="w")

        action_row = 4 if deadline_info["has_deadline"] and not done else 3

        if done:
            ctk.CTkLabel(
                card, text="✅ Goal reached!",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#16A34A",
            ).grid(row=action_row, column=0, padx=20, pady=(0, 20), sticky="w")
        else:
            ctk.CTkButton(
                card, text="+ Contribute",
                height=34, corner_radius=8,
                fg_color=BTN_CONTRIBUTE, hover_color=BTN_CONTRIBUTE_HOVER,
                text_color=("#2563EB", "#3B82F6"),
                font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda g=goal: self._contribute(g),
            ).grid(row=action_row, column=0, padx=20, pady=(0, 20), sticky="ew")

    def _open_add_dialog(self):
        AddGoalDialog(self, self.user, on_save=self._load_goals)

    def _contribute(self, goal):
        ContributeDialog(self, goal, on_save=self._load_goals)

    def _archive(self, goal):
        ok = messagebox.askyesno("Archive goal", f"Archive '{goal.name}'?")
        if ok:
            archive_goal(goal)
            logger.info(f"User archived goal: {goal.name}")
            self._load_goals()


# ── Add Goal Dialog ───────────────────────────────────────────────────────────

class AddGoalDialog(ctk.CTkToplevel):

    def __init__(self, parent, user, on_save):
        super().__init__(parent)
        self.user    = user
        self.on_save = on_save

        self.title("New Goal")
        self.geometry("380x400")
        self.resizable(False, False)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        pad = {"padx": 28, "sticky": "ew"}

        ctk.CTkLabel(self, text="Goal name", font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=0, column=0, padx=28, pady=(28, 4), sticky="w")
        self.name_entry = ctk.CTkEntry(
            self, placeholder_text="e.g. Japan trip",
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.name_entry.grid(row=1, column=0, **pad)
        self.name_entry.focus()

        ctk.CTkLabel(self, text="Target amount", font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=2, column=0, padx=28, pady=(16, 4), sticky="w")
        self.amount_entry = ctk.CTkEntry(
            self, placeholder_text="1000.00",
            font=ctk.CTkFont(size=22, weight="bold"),
            height=52, corner_radius=8,
        )
        self.amount_entry.grid(row=3, column=0, **pad)

        ctk.CTkLabel(self, text="Deadline (optional)", font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).grid(row=4, column=0, padx=28, pady=(16, 4), sticky="w")
        self.deadline_entry = ctk.CTkEntry(
            self, placeholder_text="DD.MM.YYYY",
            font=ctk.CTkFont(size=14), height=40, corner_radius=8,
        )
        self.deadline_entry.grid(row=5, column=0, padx=28, sticky="ew")

        ctk.CTkButton(
            self, text="Create Goal",
            height=48, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._save,
        ).grid(row=6, column=0, padx=28, pady=28, sticky="ew")

    def _save(self):
        from utils.formatters import parse_money, parse_date
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter a goal name")
            return
        try:
            target_cents = parse_money(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid amount")
            return

        deadline      = None
        deadline_text = self.deadline_entry.get().strip()
        if deadline_text:
            try:
                deadline = parse_date(deadline_text)
            except ValueError:
                messagebox.showerror("Error", "Invalid deadline. Use DD.MM.YYYY format")
                return

        try:
            add_goal(self.user, name, target_cents, deadline=deadline)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        self.on_save()
        self.destroy()


# ── Contribute Dialog ─────────────────────────────────────────────────────────

class ContributeDialog(ctk.CTkToplevel):

    def __init__(self, parent, goal, on_save):
        super().__init__(parent)
        self.goal    = goal
        self.on_save = on_save

        self.title(f"Contribute to {goal.name}")
        self.geometry("340x240")
        self.resizable(False, False)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self,
            text=f"{self.goal.icon} {self.goal.name}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=28, pady=(28, 4), sticky="w")

        ctk.CTkLabel(
            self,
            text=f"{format_money_short(self.goal.current_cents)} / "
                 f"{format_money_short(self.goal.target_cents)}",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
        ).grid(row=1, column=0, padx=28, pady=(0, 16), sticky="w")

        self.amount_entry = ctk.CTkEntry(
            self, placeholder_text="Amount to add",
            font=ctk.CTkFont(size=22, weight="bold"),
            height=52, corner_radius=8,
        )
        self.amount_entry.grid(row=2, column=0, padx=28, sticky="ew")
        self.amount_entry.focus()

        ctk.CTkButton(
            self, text="Contribute",
            height=44, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._save,
        ).grid(row=3, column=0, padx=28, pady=24, sticky="ew")

    def _save(self):
        from utils.formatters import parse_money
        try:
            amount_cents = parse_money(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid amount")
            return

        try:
            contribute_to_goal(self.goal, amount_cents)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        self.on_save()
        self.destroy()
