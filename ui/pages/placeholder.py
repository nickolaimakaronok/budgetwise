"""
ui/pages/placeholder.py
Temporary placeholder shown for pages not yet implemented.
"""

import customtkinter as ctk


class PlaceholderPage(ctk.CTkFrame):

    def __init__(self, parent, emoji: str, title: str, subtitle: str):
        super().__init__(parent, fg_color="#F8FAFC", corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Centered content
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=0, column=0)

        ctk.CTkLabel(
            center,
            text=emoji,
            font=ctk.CTkFont(size=64),
        ).pack(pady=(0, 16))

        ctk.CTkLabel(
            center,
            text=title,
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#1E293B",
        ).pack()

        ctk.CTkLabel(
            center,
            text=subtitle,
            font=ctk.CTkFont(size=16),
            text_color="#94A3B8",
        ).pack(pady=(8, 0))