# Settings dialog: a small modal window where the user chooses where the play
# history is stored and which theme the player uses. The theme is previewed as
# soon as it is picked, the history backend changes only when Save is pressed
# and Cancel puts the theme that was in use when the window opened back.

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from . import config, theme

# Fixed width of the dialog and the spacing of its layout, in pixels.
WIDTH = 520
PAD = 16
GAP = 8

# The history choices: backend name, label and the line shown under it.
HISTORY_OPTIONS = (
    ("sqlite", "SQLite (default)", "Stored in data/history.db, works out of the box."),
    ("text", "Text file", "Stored in data/history.txt, one line per play."),
    (
        "sqlserver",
        "SQL Server",
        "Uses the connection settings in db_config.ini (copy db_config.example.ini first).",
    ),
)

# The theme choices shown in the appearance section.
THEME_OPTIONS = (("dark", "Dark"), ("light", "Light"))


class SettingsDialog(tk.Toplevel):
    """Modal window with the play history and theme settings."""

    def __init__(
        self,
        master,
        settings,
        current_backend_name,
        on_apply_backend,
        on_apply_theme,
    ) -> None:
        """Build the dialog over `master`; the callbacks apply the chosen values."""
        super().__init__(master)
        self.settings = settings
        self.on_apply_backend = on_apply_backend
        self.on_apply_theme = on_apply_theme
        # State at the moment the window opened: Save only switches the backend
        # when it really changed, Cancel puts the opening theme back.
        self._original_backend = str(current_backend_name)
        self._original_theme = theme.current_theme()
        self.backend_var = tk.StringVar(value=self._original_backend)
        self.theme_var = tk.StringVar(value=self._original_theme)

        self.title("Settings")
        self.resizable(False, False)
        self.configure(bg=theme.current_palette()["bg"])
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        # Escape closes the window like the Cancel button does.
        self.bind("<Escape>", lambda _event: self._on_cancel())

        self._build()
        self._center(master)
        self._make_modal()
        self.focus_set()

    # ------------------------------------------------------------------
    # Build the interface
    # ------------------------------------------------------------------

    def _build(self) -> None:
        """The two sections and the row with the Cancel and Save buttons."""
        frame = ttk.Frame(self, padding=PAD)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)

        # Play history: one radio button per backend, each with a muted line
        # under it explaining where the plays end up.
        row = 0
        ttk.Label(frame, text="PLAY HISTORY", style="Section.TLabel").grid(
            row=row, column=0, sticky="w", pady=(0, GAP)
        )
        row += 1
        self.backend_buttons = {}
        for kind, label, explanation in HISTORY_OPTIONS:
            button = ttk.Radiobutton(frame, text=label, value=kind, variable=self.backend_var)
            button.grid(row=row, column=0, sticky="w")
            self.backend_buttons[kind] = button
            row += 1
            ttk.Label(frame, text=explanation, style="Muted.TLabel").grid(
                row=row, column=0, sticky="w", padx=(PAD + GAP, 0), pady=(0, GAP)
            )
            row += 1
            # Under the SQL Server choice, say whether its settings file is there.
            if kind == "sqlserver":
                ttk.Label(frame, text=self._db_config_text(), style="Muted.TLabel").grid(
                    row=row, column=0, sticky="w", padx=(PAD + GAP, 0), pady=(0, GAP)
                )
                row += 1

        # Appearance: dark or light, applied right away as a preview.
        ttk.Label(frame, text="APPEARANCE", style="Section.TLabel").grid(
            row=row, column=0, sticky="w", pady=(PAD, GAP)
        )
        row += 1
        themes = ttk.Frame(frame)
        themes.grid(row=row, column=0, sticky="w")
        row += 1
        self.theme_buttons = {}
        for name, label in THEME_OPTIONS:
            button = ttk.Radiobutton(
                themes,
                text=label,
                value=name,
                variable=self.theme_var,
                command=self._on_theme_changed,
            )
            button.pack(side="left", padx=(0, PAD))
            self.theme_buttons[name] = button

        # Buttons: Cancel on the left, the accent Save on the right.
        buttons = ttk.Frame(frame)
        buttons.grid(row=row, column=0, sticky="e", pady=(PAD, 0))
        self.cancel_button = ttk.Button(buttons, text="Cancel", command=self._on_cancel)
        self.cancel_button.pack(side="left", padx=(0, GAP))
        self.save_button = ttk.Button(
            buttons, text="Save", style="Accent.TButton", command=self._on_save
        )
        self.save_button.pack(side="left")

    def _db_config_text(self) -> str:
        """Whether the SQL Server settings file exists, shown under its radio button."""
        if config.DB_CONFIG_FILE.exists():
            return "db_config.ini found"
        return "db_config.ini not found"

    def _center(self, master) -> None:
        """Give the window its fixed width and place it over the middle of `master`."""
        self.update_idletasks()
        height = self.winfo_reqheight()
        x = master.winfo_rootx() + (master.winfo_width() - WIDTH) // 2
        y = master.winfo_rooty() + (master.winfo_height() - height) // 2
        self.geometry(f"{WIDTH}x{height}+{max(0, x)}+{max(0, y)}")

    def _make_modal(self) -> None:
        """Hold the keyboard and mouse to this window, once it is on screen."""
        try:
            self.grab_set()
        except tk.TclError:
            # The window is not mapped yet: try again as soon as Tk is idle.
            self.after(100, self._make_modal)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_theme_changed(self) -> None:
        """Preview the chosen theme at once on the whole application."""
        self.on_apply_theme(self.theme_var.get())
        self.configure(bg=theme.current_palette()["bg"])

    def _on_save(self) -> None:
        """Apply the history choice and close; an error keeps the window open."""
        kind = self.backend_var.get()
        if kind != self._original_backend:
            error = self.on_apply_backend(kind)
            if error:
                messagebox.showerror("Settings", str(error), parent=self)
                return
        self.destroy()

    def _on_cancel(self) -> None:
        """Close without changing the history and put the opening theme back."""
        if theme.current_theme() != self._original_theme:
            self.on_apply_theme(self._original_theme)
        self.destroy()
