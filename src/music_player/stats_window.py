# Listening statistics window: three cards with the total numbers and two small
# charts, the most played songs and the listening time of the last two weeks,
# drawn on plain tk canvases instead of a plotting library. The numbers are
# prepared by the pure functions below and read from the active history backend.

from __future__ import annotations

import math
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from datetime import date
from tkinter import ttk

from . import theme
from .history import HistoryBackend, HistoryEntry, HistoryError
from .history.stats import listening_by_day, top_songs, total_listening_seconds

# Size of the window when it opens and the smallest size the user may drag it to.
WINDOW_SIZE = "860x560"
MIN_WIDTH = 700
MIN_HEIGHT = 480

# Spacing of the layout, in pixels: window padding, gap between widgets and the
# padding of the three cards at the top.
PAD = 16
GAP = 12
CARD_PAD = 16

# How many songs the left chart shows and how many days the right chart covers.
TOP_LIMIT = 8
CHART_DAYS = 14

# Weekday initials under the daily bars, Monday first, so the labels stay short.
WEEKDAY_INITIALS = ("M", "T", "W", "T", "F", "S", "S")


@dataclass(frozen=True)
class StatsSummary:
    """The numbers of the window, ready to draw without touching the backend."""

    plays: int
    total_seconds: float
    distinct: int
    top: list[tuple[str, int]]
    daily: list[tuple[date, float]]


def summarize(
    entries: list[HistoryEntry],
    today: date | None = None,
    limit: int = TOP_LIMIT,
    days: int = CHART_DAYS,
) -> StatsSummary:
    """Turn a list of plays into the numbers of the cards and of both charts."""
    return StatsSummary(
        plays=len(entries),
        total_seconds=total_listening_seconds(entries),
        distinct=len({entry.title for entry in entries}),
        top=top_songs(entries, limit=limit),
        daily=listening_by_day(entries, days=days, today=today),
    )


def format_listening_time(seconds: float) -> str:
    """Listening time as "3 h 12 min", "42 min" or "0 min"."""
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        seconds = 0.0
    if seconds < 0:
        seconds = 0.0
    minutes = int(seconds // 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours} h {minutes} min"
    return f"{minutes} min"


def _shorten(text: str, font: tkfont.Font, max_width: int) -> str:
    """Cut text so that it fits in max_width pixels, adding "..." at the end."""
    if max_width <= 0 or font.measure(text) <= max_width:
        return text
    cut = text
    while cut and font.measure(cut + "...") > max_width:
        cut = cut[:-1]
    return cut + "..."


def _axis_top(minutes: float) -> float:
    """Top of the daily chart: the tallest value rounded up to a friendly number of minutes."""
    if minutes <= 0:
        return 1.0
    if minutes <= 10:
        step = 1
    elif minutes <= 60:
        step = 5
    else:
        step = 10
    return float(math.ceil(minutes / step) * step)


def _font_object(master, size: int, weight: str = "normal") -> tkfont.Font:
    """Tk font object matching theme.font(), used to measure how much text fits."""
    family, size, weight = theme.font(size, weight)
    return tkfont.Font(root=master, family=family, size=size, weight=weight)


class StatsWindow(tk.Toplevel):
    """Window with the totals of the play history and two charts drawn by hand."""

    def __init__(self, master, history: HistoryBackend) -> None:
        """Build the window around `history` and load its plays right away."""
        super().__init__(master)
        self.history = history
        self._summary: StatsSummary | None = None
        self._font = _font_object(self, 10)
        self._big_font = _font_object(self, 22, "bold")
        self._section_font = _font_object(self, 9, "bold")
        # Labels painted by apply_palette(): the card values, the card captions
        # and the titles inside the two surface panels.
        self._card_values: list[tk.Label] = []
        self._card_captions: list[tk.Label] = []
        self._surface_labels: list[tk.Label] = []
        palette = theme.current_palette()
        self.title("Listening statistics")
        self.geometry(WINDOW_SIZE)
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.resizable(True, True)
        self.configure(bg=palette["bg"])
        self.transient(master)
        # Escape closes the window, like the play history one.
        self.bind("<Escape>", lambda _event: self.destroy())
        self._build()
        self.apply_palette()
        self.refresh()

    # ------------------------------------------------------------------
    # Build the interface
    # ------------------------------------------------------------------

    def _build(self) -> None:
        """Cards at the top, the two charts in the middle and the footer below."""
        frame = ttk.Frame(self, padding=PAD)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        self._build_cards(frame)
        # The two charts share the middle row; the error label takes their place
        # when the backend cannot be read.
        self.charts = ttk.Frame(frame)
        self.charts.grid(row=2, column=0, sticky="nsew")
        self.charts.columnconfigure(0, weight=1)
        self.charts.columnconfigure(1, weight=1)
        self.charts.rowconfigure(0, weight=1)
        self._build_top_chart(self.charts)
        self._build_daily_chart(self.charts)
        self.error_label = tk.Label(
            frame,
            font=self._font,
            anchor="center",
            justify="center",
            bg=theme.current_palette()["bg"],
            fg=theme.current_palette()["danger"],
        )
        self.error_label.grid(row=2, column=0, sticky="nsew")
        self.error_label.grid_remove()
        self._build_footer(frame)

    def _build_cards(self, parent) -> None:
        """Three cards side by side: plays, listening time and different songs."""
        cards = ttk.Frame(parent)
        cards.grid(row=0, column=0, sticky="ew", pady=(0, PAD))
        for column in range(3):
            cards.columnconfigure(column, weight=1, uniform="cards")
        self._build_card(cards, 0, "Plays")
        self._build_card(cards, 1, "Listening time")
        self._build_card(cards, 2, "Different songs")

    def _build_card(self, parent, column: int, caption: str) -> None:
        """One card with a big number on top and its small muted caption below."""
        card = ttk.Frame(parent, style="Card.TFrame", padding=CARD_PAD)
        card.grid(row=0, column=column, sticky="nsew", padx=(0, GAP if column < 2 else 0))
        value = tk.Label(card, font=self._big_font, anchor="w")
        value.pack(fill="x")
        caption_label = tk.Label(card, text=caption, font=self._font, anchor="w")
        caption_label.pack(fill="x", pady=(2, 0))
        self._card_values.append(value)
        self._card_captions.append(caption_label)

    def _build_top_chart(self, parent) -> None:
        """Left half: the title and the canvas of the most played songs."""
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=PAD)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, GAP // 2))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)
        title = tk.Label(panel, text="Most played", font=self._section_font, anchor="w")
        title.grid(row=0, column=0, sticky="w", pady=(0, GAP))
        self._surface_labels.append(title)
        self.top_canvas = tk.Canvas(panel, highlightthickness=0, borderwidth=0)
        self.top_canvas.grid(row=1, column=0, sticky="nsew")
        self.top_canvas.bind("<Configure>", lambda _event: self._draw_top())

    def _build_daily_chart(self, parent) -> None:
        """Right half: the title and the canvas of the listening time per day."""
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=PAD)
        panel.grid(row=0, column=1, sticky="nsew", padx=(GAP // 2, 0))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)
        title = tk.Label(
            panel,
            text=f"Listening time, last {CHART_DAYS} days",
            font=self._section_font,
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, GAP))
        self._surface_labels.append(title)
        self.daily_canvas = tk.Canvas(panel, highlightthickness=0, borderwidth=0)
        self.daily_canvas.grid(row=1, column=0, sticky="nsew")
        self.daily_canvas.bind("<Configure>", lambda _event: self._draw_daily())

    def _build_footer(self, parent) -> None:
        """Footer: where the history is stored and the refresh button."""
        footer = ttk.Frame(parent)
        footer.grid(row=3, column=0, sticky="ew", pady=(PAD, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, style="Muted.TLabel", text=self.history.describe()).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(footer, text="Refresh", command=self.refresh).grid(row=0, column=1)

    # ------------------------------------------------------------------
    # Data and refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Read the plays again and redraw the cards and both charts."""
        try:
            entries = self.history.entries()
        except HistoryError as error:
            # A backend that cannot be read shows the message in the danger
            # colour instead of the charts, never as a crash.
            self._summary = None
            self._show_error(str(error))
            return
        self._summary = summarize(entries)
        self._update_cards()
        self.error_label.grid_remove()
        self.charts.grid()
        self._draw_top()
        self._draw_daily()

    def _update_cards(self) -> None:
        """Fill the three cards with the numbers of the last read plays."""
        summary = self._summary
        if summary is None:
            return
        values = (
            str(summary.plays),
            format_listening_time(summary.total_seconds),
            str(summary.distinct),
        )
        for label, text in zip(self._card_values, values):
            label.configure(text=text)

    def _show_error(self, message: str) -> None:
        """Hide the charts and show the backend message, centred and in danger colour."""
        self.charts.grid_remove()
        for label in self._card_values:
            label.configure(text="-")
        palette = theme.current_palette()
        self.error_label.configure(text=message, background=palette["bg"], foreground=palette["danger"])
        self.error_label.grid()

    def apply_palette(self) -> None:
        """Repaint the window, the cards and both charts with the current theme."""
        palette = theme.current_palette()
        self.configure(bg=palette["bg"])
        for label in self._card_values:
            label.configure(background=palette["surface_alt"], foreground=palette["text"])
        for label in self._card_captions:
            label.configure(background=palette["surface_alt"], foreground=palette["text_muted"])
        for label in self._surface_labels:
            label.configure(background=palette["surface"], foreground=palette["text_muted"])
        for canvas in (self.top_canvas, self.daily_canvas):
            canvas.configure(bg=palette["surface"])
        self.error_label.configure(background=palette["bg"], foreground=palette["danger"])
        self._draw_top()
        self._draw_daily()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    @staticmethod
    def _canvas_size(canvas: tk.Canvas) -> tuple[int, int]:
        """Size of a canvas in pixels, using the requested one before it is mapped."""
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1:
            width = int(canvas["width"])
        if height <= 1:
            height = int(canvas["height"])
        return int(width), int(height)

    def _draw_top(self) -> None:
        """Horizontal bars of the most played songs, longest first."""
        canvas = self.top_canvas
        canvas.delete("all")
        if self._summary is None:
            return
        width, height = self._canvas_size(canvas)
        palette = theme.current_palette()
        top = self._summary.top
        if not top:
            # Empty state: one centred muted message instead of the bars.
            canvas.create_text(
                width / 2.0,
                height / 2.0,
                text="No plays yet. Play some songs and come back.",
                fill=palette["text_muted"],
                font=self._font,
                justify="center",
                width=max(40, width - 2 * GAP),
                tags="empty",
            )
            return
        row_height = height / len(top)
        bar_height = max(6.0, min(18.0, row_height * 0.5))
        label_width = max(70, int(width * 0.38))
        bar_left = label_width + GAP
        bar_max = max(10.0, width - 44 - bar_left)
        tallest = top[0][1] or 1
        for index, (title, plays) in enumerate(top):
            center_y = row_height * (index + 0.5)
            # Song title cut with an ellipsis so it always fits its column.
            canvas.create_text(
                label_width,
                center_y,
                text=_shorten(title, self._font, label_width - GAP),
                anchor="e",
                fill=palette["text"],
                font=self._font,
            )
            length = max(bar_height, bar_max * plays / tallest)
            canvas.create_line(
                bar_left,
                center_y,
                bar_left + length,
                center_y,
                fill=palette["accent"],
                width=bar_height,
                capstyle="round",
            )
            canvas.create_text(
                bar_left + length + GAP,
                center_y,
                text=str(plays),
                anchor="w",
                fill=palette["text_muted"],
                font=self._font,
            )

    def _draw_daily(self) -> None:
        """One vertical bar per day of the last two weeks, today highlighted."""
        canvas = self.daily_canvas
        canvas.delete("all")
        if self._summary is None:
            return
        width, height = self._canvas_size(canvas)
        palette = theme.current_palette()
        daily = self._summary.daily
        if not daily:
            return
        minutes = [seconds / 60.0 for _day, seconds in daily]
        top = _axis_top(max(minutes))

        # Plot area: minute labels on the left, day initials under the bars.
        plot_left = 56.0
        plot_right = max(plot_left + 10.0, width - 6.0)
        plot_top = 12.0
        plot_bottom = max(plot_top + 20.0, height - 22.0)
        plot_height = plot_bottom - plot_top
        plot_width = plot_right - plot_left

        # Light baseline and three faint grid lines with their minute labels.
        canvas.create_line(plot_left, plot_bottom, plot_right, plot_bottom, fill=palette["border"])
        for step in (1, 2, 3):
            y = plot_bottom - plot_height * step / 3.0
            canvas.create_line(plot_left, y, plot_right, y, fill=palette["border"])
            canvas.create_text(
                plot_left - GAP // 2,
                y,
                text=f"{int(round(top * step / 3.0))} min",
                anchor="e",
                fill=palette["text_muted"],
                font=self._font,
            )

        step = plot_width / len(daily)
        bar_width = max(4.0, min(22.0, step * 0.55))
        today = date.today()
        dim = theme.mix(palette["accent"], palette["surface"], 0.55)
        for index, (day, seconds) in enumerate(daily):
            center_x = plot_left + step * (index + 0.5)
            value = seconds / 60.0
            bar_height = plot_height * min(1.0, value / top)
            is_today = day == today
            color = palette["accent"] if is_today else dim
            y_top = plot_bottom - bar_height
            if bar_height >= 2.0:
                # Flat bottom on the baseline with a rounded top, drawn as a
                # rectangle plus a small oval.
                radius = min(bar_width / 2.0, bar_height / 2.0)
                canvas.create_rectangle(
                    center_x - radius,
                    y_top + radius,
                    center_x + radius,
                    plot_bottom,
                    fill=color,
                    outline=color,
                )
                canvas.create_oval(
                    center_x - radius,
                    y_top,
                    center_x + radius,
                    y_top + 2 * radius,
                    fill=color,
                    outline=color,
                )
            # The value in minutes above the bar, only when there is room for it.
            if bar_height >= 22.0 and value >= 1.0:
                canvas.create_text(
                    center_x,
                    y_top - 4,
                    text=str(int(round(value))),
                    anchor="s",
                    fill=palette["text_muted"],
                    font=self._font,
                )
            canvas.create_text(
                center_x,
                plot_bottom + 4,
                text=WEEKDAY_INITIALS[day.weekday()],
                anchor="n",
                fill=palette["text_muted"],
                font=self._font,
            )
