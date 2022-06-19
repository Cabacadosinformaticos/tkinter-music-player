# Play history window: lists the songs that were played, newest first, in a
# table with their date, time and length, and offers buttons to refresh the
# list or to clear the whole history.

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from . import theme
from .history import HistoryBackend, HistoryError
from .playlist import format_duration

# Size of the window when it opens and the smallest size the user may drag it to.
WINDOW_SIZE = "760x520"
MIN_WIDTH = 560
MIN_HEIGHT = 360

# Spacing of the layout, in pixels: window padding and gap between widgets.
PAD = 16
GAP = 8


class HistoryWindow(tk.Toplevel):
    """Window that shows the plays of one history backend, newest first."""

    def __init__(self, master, history: HistoryBackend) -> None:
        """Build the window around `history` and load its plays right away."""
        super().__init__(master)
        self.history = history
        palette = theme.current_palette()
        self.title("Play history")
        self.geometry(WINDOW_SIZE)
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.resizable(True, True)
        self.configure(bg=palette["bg"])
        self.transient(master)
        # Escape closes the window, like the Keyboard shortcuts one.
        self.bind("<Escape>", lambda _event: self.destroy())
        self._build()
        self.refresh()

    def _build(self) -> None:
        """Header, table with its scrollbar and the footer with the buttons."""
        frame = ttk.Frame(self, padding=PAD)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        # Header: the window name and where the history is stored.
        ttk.Label(frame, text="Play history", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.where_label = ttk.Label(frame, style="Muted.TLabel")
        self.where_label.grid(row=1, column=0, sticky="w", pady=(0, GAP))
        self.where_label.configure(text=self.history.describe())

        # Table of plays, one row each, with its scrollbar on the right.
        table = ttk.Frame(frame)
        table.grid(row=2, column=0, sticky="nsew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            table,
            style="Playlist.Treeview",
            columns=("Date", "Time", "Song", "Length"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("Date", text="Date")
        self.tree.heading("Time", text="Time")
        self.tree.heading("Song", text="Song")
        self.tree.heading("Length", text="Length")
        self.tree.column("Date", width=110, anchor="w", stretch=False)
        self.tree.column("Time", width=70, anchor="w", stretch=False)
        self.tree.column("Song", width=420, anchor="w", stretch=True)
        self.tree.column("Length", width=90, anchor="e", stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Footer: the number of plays, then the refresh and clear buttons.
        footer = ttk.Frame(frame)
        footer.grid(row=3, column=0, sticky="ew", pady=(GAP, 0))
        footer.columnconfigure(0, weight=1)
        self.count_label = ttk.Label(footer, style="Muted.TLabel")
        self.count_label.grid(row=0, column=0, sticky="w")
        self.refresh_button = ttk.Button(footer, text="Refresh", command=self.refresh)
        self.refresh_button.grid(row=0, column=1, padx=(GAP, 0))
        self.clear_button = ttk.Button(footer, text="Clear history", command=self._on_clear)
        self.clear_button.grid(row=0, column=2, padx=(GAP, 0))

    def refresh(self) -> None:
        """Read the plays again and fill the table, newest first."""
        self.tree.delete(*self.tree.get_children())
        try:
            entries = self.history.entries()
        except HistoryError as error:
            # A backend that cannot be read shows the message in the footer
            # instead of breaking the window.
            self.count_label.configure(text=str(error), foreground=theme.current_palette()["danger"])
            return
        for entry in entries:
            self.tree.insert(
                "",
                "end",
                values=(
                    entry.played_at.strftime("%d/%m/%Y"),
                    entry.played_at.strftime("%H:%M"),
                    entry.title,
                    format_duration(entry.duration) if entry.duration > 0 else "-",
                ),
            )
        self.count_label.configure(
            text=self._count_text(len(entries)),
            foreground=theme.current_palette()["text_muted"],
        )

    @staticmethod
    def _count_text(count: int) -> str:
        """Footer text: "23 plays", or "1 play" for a single one."""
        word = "play" if count == 1 else "plays"
        return f"{count} {word}"

    def _on_clear(self) -> None:
        """Ask for confirmation and then delete every saved play."""
        confirmed = messagebox.askyesno(
            "Play history", "Delete every saved play?", parent=self
        )
        if not confirmed:
            return
        try:
            self.history.clear()
        except Exception as error:
            self.count_label.configure(
                text=str(error), foreground=theme.current_palette()["danger"]
            )
            return
        self.refresh()
