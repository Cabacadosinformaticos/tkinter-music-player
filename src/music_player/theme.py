# Theme for the music player: the dark and light colour palettes, the setup of
# the sv-ttk theme (with a plain ttk fallback when it is not installed) and the
# extra ttk styles used by the interface, such as the labels, the panels and the
# playlist treeview.

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

try:
    import sv_ttk
except ImportError:
    # sv-ttk is optional: without it the program falls back to the built-in
    # "clam" theme, coloured from the palette below.
    sv_ttk = None

# Colour palettes, dark first because the app starts in dark mode.
PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#1c1c1c",
        "surface": "#202020",
        "surface_alt": "#2b2b2b",
        "border": "#2e2e2e",
        "text": "#f2f2f2",
        "text_muted": "#a0a0a0",
        "accent": "#1ed760",
        "accent_hover": "#3be477",
        "accent_text": "#0b0b0b",
        "danger": "#e5484d",
    },
    "light": {
        "bg": "#fafafa",
        "surface": "#ffffff",
        "surface_alt": "#ececee",
        "border": "#dcdce0",
        "text": "#18181b",
        "text_muted": "#6b6b76",
        "accent": "#1db954",
        "accent_hover": "#17a349",
        "accent_text": "#ffffff",
        "danger": "#d93036",
    },
}

# Remembered theme, read by the widgets through current_palette().
_theme_name = "dark"
_palette = PALETTES["dark"]


def current_theme() -> str:
    """Name of the theme applied last ("dark" or "light")."""
    return _theme_name


def current_palette() -> dict:
    """Colour palette of the current theme; treat the returned dict as read-only."""
    return _palette


def mix(color_a: str, color_b: str, amount: float) -> str:
    """Blend two "#rrggbb" colours: amount 0 keeps the first one, amount 1 gives the second."""
    amount = min(1.0, max(0.0, float(amount)))
    parts = []
    for index in (1, 3, 5):
        first = int(color_a[index : index + 2], 16)
        second = int(color_b[index : index + 2], 16)
        parts.append(round(first + (second - first) * amount))
    return "#%02x%02x%02x" % tuple(parts)


def font(size: int = 10, weight: str = "normal") -> tuple:
    """Font tuple for the interface: Segoe UI on Windows, the Tk default family elsewhere."""
    if sys.platform == "win32":
        return ("Segoe UI", size, weight)
    try:
        import tkinter.font as tkfont

        family = tkfont.nametofont("TkDefaultFont").actual("family")
    except Exception:
        # No Tk root yet: this works everywhere, even if it is not the best match.
        family = "Helvetica"
    return (family, size, weight)


def _use_clam(root: tk.Tk) -> None:
    """Colour the built-in clam theme from the palette, used when sv-ttk is missing."""
    palette = _palette
    style = ttk.Style(master=root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        return
    style.configure(
        ".",
        background=palette["bg"],
        foreground=palette["text"],
        fieldbackground=palette["surface_alt"],
        bordercolor=palette["border"],
        lightcolor=palette["surface_alt"],
        darkcolor=palette["surface"],
        troughcolor=palette["surface_alt"],
        selectbackground=palette["accent"],
        selectforeground=palette["accent_text"],
        focuscolor=palette["accent"],
        font=font(10),
    )
    style.configure(
        "TButton",
        background=palette["surface_alt"],
        foreground=palette["text"],
        borderwidth=0,
        focusthickness=0,
        padding=(12, 6),
    )
    style.map(
        "TButton",
        background=[("pressed", palette["accent_hover"]), ("active", palette["accent"])],
        foreground=[("pressed", palette["accent_text"]), ("active", palette["accent_text"])],
    )
    style.configure(
        "TEntry",
        fieldbackground=palette["surface_alt"],
        foreground=palette["text"],
        insertcolor=palette["text"],
        bordercolor=palette["border"],
        lightcolor=palette["border"],
        darkcolor=palette["border"],
        padding=6,
    )
    style.map("TEntry", bordercolor=[("focus", palette["accent"])])
    for name in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        style.configure(
            name,
            background=palette["surface_alt"],
            troughcolor=palette["bg"],
            bordercolor=palette["bg"],
            arrowcolor=palette["text_muted"],
            gripcount=0,
        )
    style.configure(
        "TCombobox",
        fieldbackground=palette["surface_alt"],
        background=palette["surface_alt"],
        foreground=palette["text"],
        arrowcolor=palette["text_muted"],
        bordercolor=palette["border"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", palette["surface_alt"])],
        foreground=[("readonly", palette["text"])],
        selectbackground=[("readonly", palette["surface_alt"])],
    )
    for name in ("TCheckbutton", "TRadiobutton"):
        style.configure(name, background=palette["bg"], foreground=palette["text"])
        style.map(name, background=[("active", palette["bg"])])
    style.configure(
        "TSpinbox",
        fieldbackground=palette["surface_alt"],
        foreground=palette["text"],
        arrowcolor=palette["text_muted"],
        bordercolor=palette["border"],
    )
    style.configure("TNotebook", background=palette["bg"], borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure(
        "TNotebook.Tab",
        background=palette["surface_alt"],
        foreground=palette["text_muted"],
        padding=(14, 7),
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", palette["surface"])],
        foreground=[("selected", palette["text"])],
    )
    style.configure("TLabelframe", background=palette["bg"], bordercolor=palette["border"])
    style.configure(
        "TLabelframe.Label", background=palette["bg"], foreground=palette["text_muted"]
    )
    style.configure("TSeparator", background=palette["border"])
    style.configure("TScale", background=palette["bg"], troughcolor=palette["surface_alt"])


def _configure_styles(root: tk.Tk) -> None:
    """Custom ttk styles of the interface, applied on top of the current ttk theme."""
    palette = _palette
    style = ttk.Style(master=root)

    # Frames: the window background, the panels and the cards.
    style.configure("TFrame", background=palette["bg"])
    style.configure("Panel.TFrame", background=palette["surface"])
    style.configure("Card.TFrame", background=palette["surface_alt"])

    # Labels: sizes and colours of the text of the player.
    style.configure("TLabel", background=palette["bg"], foreground=palette["text"])
    style.configure(
        "Title.TLabel", background=palette["bg"], foreground=palette["text"], font=font(20, "bold")
    )
    style.configure(
        "Artist.TLabel",
        background=palette["bg"],
        foreground=palette["text_muted"],
        font=font(12),
    )
    style.configure(
        "Muted.TLabel",
        background=palette["bg"],
        foreground=palette["text_muted"],
        font=font(10),
    )
    style.configure(
        "Time.TLabel", background=palette["bg"], foreground=palette["text_muted"], font=font(9)
    )
    style.configure(
        "Section.TLabel",
        background=palette["bg"],
        foreground=palette["text_muted"],
        font=font(9, "bold"),
    )

    # Playlist: tall rows, flat borders and a soft accent tint on the selected row.
    selected = mix(palette["accent"], palette["surface"], 0.72)
    for name in ("Treeview", "Playlist.Treeview"):
        style.configure(
            name,
            background=palette["surface"],
            fieldbackground=palette["surface"],
            foreground=palette["text"],
            borderwidth=0,
            relief="flat",
            font=font(10),
            rowheight=34,
        )
        style.map(
            name,
            background=[("selected", selected)],
            foreground=[("selected", palette["text"])],
        )
    style.configure(
        "Playlist.Treeview.Heading",
        background=palette["surface"],
        foreground=palette["text_muted"],
        relief="flat",
        borderwidth=0,
        font=font(9, "bold"),
    )
    style.map(
        "Playlist.Treeview.Heading",
        background=[("active", palette["surface_alt"])],
        foreground=[("active", palette["text"])],
    )


def apply_theme(root: tk.Tk, name: str) -> dict:
    """Apply "dark" or "light" to the whole window, restyle everything and return the palette."""
    global _theme_name, _palette
    name = str(name).lower()
    if name not in PALETTES:
        name = "dark"
    _theme_name = name
    _palette = PALETTES[name]

    # The window and the canvas widgets share the same background colour.
    root.configure(bg=_palette["bg"])

    if sv_ttk is not None:
        sv_ttk.set_theme(name, root)
    else:
        _use_clam(root)

    _configure_styles(root)
    return _palette
