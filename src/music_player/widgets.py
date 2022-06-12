# Custom widgets drawn on tk.Canvas: the icon buttons of the transport bar, the
# thin slider used for the seek bar and the volume, and the cover art with
# rounded corners or a generated cover when a song has no picture. All of them
# read their colours from theme.current_palette(), so they follow a theme switch.

from __future__ import annotations

import io
import math
import tkinter as tk

from PIL import Image, ImageDraw, ImageTk

from . import theme

# ---------------------------------------------------------------------------
# Small helpers shared by the icons.
# ---------------------------------------------------------------------------


def _flatten(points: list[tuple[float, float]]) -> list[float]:
    """Turn a list of (x, y) points into the flat list the canvas items expect."""
    return [value for point in points for value in point]


def _rgb(color: str) -> tuple[int, int, int]:
    """Turn a "#rrggbb" colour into its three numbers."""
    return tuple(int(color[index : index + 2], 16) for index in (1, 3, 5))


def _polyline(canvas: tk.Canvas, points, color: str, width: float, tags: str) -> None:
    """Draw a thick line with rounded ends and corners."""
    canvas.create_line(
        *_flatten(points),
        fill=color,
        width=width,
        capstyle="round",
        joinstyle="round",
        tags=tags,
    )


def _polygon(canvas: tk.Canvas, points, color: str, tags: str) -> None:
    """Draw a filled shape with the given colour."""
    canvas.create_polygon(_flatten(points), fill=color, outline=color, tags=tags)


def _arrow_head(canvas: tk.Canvas, tip, direction, size: float, color: str, tags: str) -> None:
    """Draw a small filled triangle with its point at `tip`, facing `direction`."""
    length = math.hypot(direction[0], direction[1]) or 1.0
    dx, dy = direction[0] / length, direction[1] / length
    px, py = -dy, dx
    base = (tip[0] - dx * size, tip[1] - dy * size)
    _polygon(
        canvas,
        [
            tip,
            (base[0] + px * size * 0.55, base[1] + py * size * 0.55),
            (base[0] - px * size * 0.55, base[1] - py * size * 0.55),
        ],
        color,
        tags,
    )


def _rounded_points(x0: float, y0: float, x1: float, y1: float, radius: float, steps: int = 8):
    """Points of a rectangle with rounded corners, used for the loop and stop icons."""
    radius = max(0.0, min(radius, (x1 - x0) / 2.0, (y1 - y0) / 2.0))
    corners = [
        (x1 - radius, y0 + radius, -90.0, 0.0),
        (x1 - radius, y1 - radius, 0.0, 90.0),
        (x0 + radius, y1 - radius, 90.0, 180.0),
        (x0 + radius, y0 + radius, 180.0, 270.0),
    ]
    points = []
    for cx, cy, start, end in corners:
        for step in range(steps + 1):
            angle = math.radians(start + (end - start) * step / steps)
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


# ---------------------------------------------------------------------------
# One drawing function per icon kind. Every one draws inside the square of
# radius `r` around (cx, cy) and tags its items with `tags`.
# ---------------------------------------------------------------------------


def _draw_play(canvas, cx, cy, r, color, width, tags):
    """Triangle pointing right."""
    _polygon(canvas, [(cx - r * 0.5, cy - r), (cx + r * 0.9, cy), (cx - r * 0.5, cy + r)], color, tags)


def _draw_pause(canvas, cx, cy, r, color, width, tags):
    """Two rounded bars."""
    for offset in (-r * 0.42, r * 0.42):
        _polyline(canvas, [(cx + offset, cy - r * 0.9), (cx + offset, cy + r * 0.9)], color, r * 0.46, tags)


def _draw_previous(canvas, cx, cy, r, color, width, tags):
    """Triangle pointing left with a bar on its left side."""
    _polyline(canvas, [(cx - r * 0.72, cy - r * 0.85), (cx - r * 0.72, cy + r * 0.85)], color, r * 0.4, tags)
    _polygon(canvas, [(cx + r * 0.9, cy - r), (cx + r * 0.9, cy + r), (cx - r * 0.35, cy)], color, tags)


def _draw_next(canvas, cx, cy, r, color, width, tags):
    """Triangle pointing right with a bar on its right side."""
    _polyline(canvas, [(cx + r * 0.72, cy - r * 0.85), (cx + r * 0.72, cy + r * 0.85)], color, r * 0.4, tags)
    _polygon(canvas, [(cx - r * 0.9, cy - r), (cx - r * 0.9, cy + r), (cx + r * 0.35, cy)], color, tags)


def _draw_stop(canvas, cx, cy, r, color, width, tags):
    """Rounded square."""
    _polygon(canvas, _rounded_points(cx - r * 0.72, cy - r * 0.72, cx + r * 0.72, cy + r * 0.72, r * 0.28), color, tags)


def _draw_shuffle(canvas, cx, cy, r, color, width, tags):
    """Two arrows crossing from the left side to the right side."""
    for sign in (1, -1):
        start = (cx - r, cy + sign * r * 0.5)
        end = (cx + r * 0.85, cy - sign * r * 0.5)
        _polyline(canvas, [start, end], color, width, tags)
        _arrow_head(canvas, end, (end[0] - start[0], end[1] - start[1]), r * 0.5, color, tags)


def _repeat_loop(canvas, cx, cy, r, color, width, tags):
    """Rounded loop with one arrow on the top edge and one on the bottom edge."""
    loop = _rounded_points(cx - r, cy - r * 0.58, cx + r, cy + r * 0.58, r * 0.58)
    canvas.create_polygon(_flatten(loop), fill="", outline=color, width=width, tags=tags)
    size = r * 0.5
    _arrow_head(canvas, (cx + r * 0.42 + size * 0.6, cy - r * 0.58), (1, 0), size, color, tags)
    _arrow_head(canvas, (cx - r * 0.42 - size * 0.6, cy + r * 0.58), (-1, 0), size, color, tags)


def _draw_repeat(canvas, cx, cy, r, color, width, tags):
    """Loop of two arrows."""
    _repeat_loop(canvas, cx, cy, r, color, width, tags)


def _draw_repeat_one(canvas, cx, cy, r, color, width, tags):
    """Loop of two arrows with a small "1" in the middle."""
    _repeat_loop(canvas, cx, cy, r, color, width, tags)
    thin = max(1.5, width * 0.9)
    _polyline(canvas, [(cx - r * 0.18, cy - r * 0.12), (cx, cy - r * 0.32)], color, thin, tags)
    _polyline(canvas, [(cx, cy - r * 0.32), (cx, cy + r * 0.3)], color, thin, tags)
    _polyline(canvas, [(cx - r * 0.22, cy + r * 0.3), (cx + r * 0.22, cy + r * 0.3)], color, thin, tags)


def _speaker(canvas, cx, cy, r, color, tags):
    """Small speaker: a box with a cone, drawn filled."""
    _polygon(
        canvas,
        [
            (cx - r * 0.85, cy - r * 0.3),
            (cx - r * 0.35, cy - r * 0.3),
            (cx + r * 0.1, cy - r * 0.8),
            (cx + r * 0.1, cy + r * 0.8),
            (cx - r * 0.35, cy + r * 0.3),
            (cx - r * 0.85, cy + r * 0.3),
        ],
        color,
        tags,
    )


def _sound_arc(canvas, cx, cy, radius, color, width, tags):
    """Arc on the right side of the speaker, the classic sound wave."""
    canvas.create_arc(
        cx - radius,
        cy - radius,
        cx + radius,
        cy + radius,
        start=-42,
        extent=84,
        style="arc",
        outline=color,
        width=width,
        tags=tags,
    )


def _draw_volume(canvas, cx, cy, r, color, width, tags):
    """Speaker with two arcs."""
    _speaker(canvas, cx, cy, r, color, tags)
    _sound_arc(canvas, cx + r * 0.1, cy, r * 0.5, color, width, tags)
    _sound_arc(canvas, cx + r * 0.1, cy, r * 0.95, color, width, tags)


def _draw_volume_low(canvas, cx, cy, r, color, width, tags):
    """Speaker with a single arc."""
    _speaker(canvas, cx, cy, r, color, tags)
    _sound_arc(canvas, cx + r * 0.1, cy, r * 0.5, color, width, tags)


def _draw_mute(canvas, cx, cy, r, color, width, tags):
    """Speaker with a cross where the sound waves would be."""
    _speaker(canvas, cx, cy, r, color, tags)
    _polyline(canvas, [(cx + r * 0.32, cy - r * 0.4), (cx + r * 0.98, cy + r * 0.4)], color, width, tags)
    _polyline(canvas, [(cx + r * 0.98, cy - r * 0.4), (cx + r * 0.32, cy + r * 0.4)], color, width, tags)


def _draw_add(canvas, cx, cy, r, color, width, tags):
    """Plus sign."""
    _polyline(canvas, [(cx - r * 0.8, cy), (cx + r * 0.8, cy)], color, width * 1.1, tags)
    _polyline(canvas, [(cx, cy - r * 0.8), (cx, cy + r * 0.8)], color, width * 1.1, tags)


def _draw_folder(canvas, cx, cy, r, color, width, tags):
    """Filled folder."""
    _polygon(
        canvas,
        [
            (cx - r * 0.9, cy + r * 0.62),
            (cx - r * 0.9, cy - r * 0.55),
            (cx - r * 0.38, cy - r * 0.55),
            (cx - r * 0.12, cy - r * 0.25),
            (cx + r * 0.9, cy - r * 0.25),
            (cx + r * 0.9, cy + r * 0.62),
        ],
        color,
        tags,
    )


def _draw_search(canvas, cx, cy, r, color, width, tags):
    """Magnifier: a circle with a slanted handle."""
    canvas.create_oval(
        cx - r * 0.82,
        cy - r * 0.82,
        cx + r * 0.42,
        cy + r * 0.42,
        outline=color,
        width=width,
        tags=tags,
    )
    _polyline(canvas, [(cx + r * 0.24, cy + r * 0.24), (cx + r * 0.85, cy + r * 0.85)], color, width, tags)


def _draw_close(canvas, cx, cy, r, color, width, tags):
    """Cross."""
    _polyline(canvas, [(cx - r * 0.7, cy - r * 0.7), (cx + r * 0.7, cy + r * 0.7)], color, width, tags)
    _polyline(canvas, [(cx + r * 0.7, cy - r * 0.7), (cx - r * 0.7, cy + r * 0.7)], color, width, tags)


# Icon kind -> drawing function, the names come from the interfaces document.
ICONS = {
    "play": _draw_play,
    "pause": _draw_pause,
    "previous": _draw_previous,
    "next": _draw_next,
    "stop": _draw_stop,
    "shuffle": _draw_shuffle,
    "repeat": _draw_repeat,
    "repeat_one": _draw_repeat_one,
    "volume": _draw_volume,
    "volume_low": _draw_volume_low,
    "mute": _draw_mute,
    "add": _draw_add,
    "folder": _draw_folder,
    "search": _draw_search,
    "close": _draw_close,
}

ICON_KINDS = tuple(ICONS)


class IconButton(tk.Canvas):
    """Square button that draws its icon with canvas items, with hover and pressed states."""

    def __init__(
        self,
        master,
        kind: str,
        command=None,
        size: int = 44,
        bg_key: str = "bg",
        circle: bool = False,
    ) -> None:
        """Create the button for one icon `kind`; `circle` fills it with the accent colour."""
        if kind not in ICONS:
            raise ValueError(f"unknown icon kind: {kind!r}")
        self._size = int(size)
        super().__init__(
            master,
            width=self._size,
            height=self._size,
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2",
        )
        self.command = command
        self._kind = kind
        self._bg_key = bg_key
        self._circle = bool(circle)
        self._active = False
        self._hover = False
        self._pressed = False
        self._apply_bg()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._redraw()

    def _background(self) -> str:
        """Background colour of the button, taken from the palette."""
        palette = theme.current_palette()
        return palette.get(self._bg_key, palette["bg"])

    def _apply_bg(self) -> None:
        """Paint the canvas background."""
        self.configure(bg=self._background())

    def _redraw(self) -> None:
        """Draw the optional circle and the icon for the current state."""
        self.delete("all")
        palette = theme.current_palette()
        center = self._size / 2.0
        offset = 1.0 if self._pressed else 0.0
        if self._circle:
            # Filled accent circle that grows a little while hovered or pressed.
            margin = 1.0 if (self._hover or self._pressed) else 2.0
            if self._pressed:
                fill = theme.mix(palette["accent"], palette["bg"], 0.2)
            elif self._hover:
                fill = palette["accent_hover"]
            else:
                fill = palette["accent"]
            self.create_oval(margin, margin, self._size - margin, self._size - margin, fill=fill, outline="", tags="icon")
            color = palette["accent_text"]
            radius = center * 0.46
        else:
            if self._active:
                color = palette["accent_hover"] if self._hover else palette["accent"]
            elif self._hover:
                color = palette["accent"]
            else:
                color = palette["text"]
            if self._pressed:
                # Pressed icons look a bit darker, as if they went into the surface.
                color = theme.mix(color, self._background(), 0.35)
            radius = center * 0.56
        ICONS[self._kind](self, center + offset, center + offset, radius, color, max(2.0, radius * 0.22), "icon")

    def _inside(self, event) -> bool:
        """True when the mouse event happened inside the square of the button."""
        return 0 <= event.x <= self._size and 0 <= event.y <= self._size

    def _on_enter(self, event) -> None:
        """Mouse over the button: highlight the icon."""
        self._hover = True
        self._redraw()

    def _on_leave(self, event) -> None:
        """Mouse left the button: drop hover and press so nothing is triggered."""
        self._hover = False
        self._pressed = False
        self._redraw()

    def _on_press(self, event) -> None:
        """Mouse button down: show the pressed state."""
        self._pressed = True
        self._redraw()

    def _on_release(self, event) -> None:
        """Mouse button released inside: run the command."""
        was_pressed = self._pressed
        self._pressed = False
        self._redraw()
        if was_pressed and self._inside(event) and self.command is not None:
            self.command()

    def set_kind(self, kind: str) -> None:
        """Switch the drawn icon, for example from "play" to "pause"."""
        if kind not in ICONS:
            raise ValueError(f"unknown icon kind: {kind!r}")
        self._kind = kind
        self._redraw()

    def set_active(self, on: bool) -> None:
        """Mark the button as toggled on (accent colour) or off."""
        self._active = bool(on)
        self._redraw()

    def apply_palette(self) -> None:
        """Repaint the button after a theme switch."""
        self._apply_bg()
        self._redraw()


class Slider(tk.Canvas):
    """Thin horizontal slider with a rounded track, an accent fill and a knob on hover or drag."""

    TRACK_HEIGHT = 4
    KNOB_RADIUS = 6
    PADDING = 8

    def __init__(self, master, on_change=None, on_commit=None, height: int = 18, bg_key: str = "bg") -> None:
        """Create the slider; `on_change` runs while moving, `on_commit` when the mouse is released."""
        self._height = int(height)
        super().__init__(
            master,
            width=240,
            height=self._height,
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2",
        )
        self.on_change = on_change
        self.on_commit = on_commit
        self._bg_key = bg_key
        self._fraction = 0.0
        self._hover = False
        self._dragging = False
        self._apply_bg()
        self.bind("<Configure>", self._on_configure)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._redraw()

    @property
    def fraction(self) -> float:
        """Position of the slider, from 0.0 to 1.0."""
        return self._fraction

    @fraction.setter
    def fraction(self, value: float) -> None:
        """Same as set_fraction()."""
        self.set_fraction(value)

    def _apply_bg(self) -> None:
        """Paint the canvas background."""
        palette = theme.current_palette()
        self.configure(bg=palette.get(self._bg_key, palette["bg"]))

    def _width(self) -> int:
        """Current width in pixels, using the requested one before the window is mapped."""
        width = self.winfo_width()
        if width <= 1:
            width = int(self["width"])
        return width

    def _fraction_from_x(self, x: float) -> float:
        """Turn a mouse x position into a fraction, clamped to 0..1."""
        usable = max(1.0, self._width() - 2 * self.PADDING)
        return min(1.0, max(0.0, (x - self.PADDING) / usable))

    def _redraw(self) -> None:
        """Draw the track, the filled part and the knob."""
        self.delete("all")
        palette = theme.current_palette()
        center = self._height / 2.0
        left = self.PADDING
        right = max(left + 1, self._width() - self.PADDING)
        self.create_line(
            left,
            center,
            right,
            center,
            fill=palette["surface_alt"],
            width=self.TRACK_HEIGHT,
            capstyle="round",
            tags="track",
        )
        position = left + (right - left) * self._fraction
        if self._fraction > 0:
            self.create_line(
                left,
                center,
                position,
                center,
                fill=palette["accent"],
                width=self.TRACK_HEIGHT,
                capstyle="round",
                tags="fill",
            )
        if self._hover or self._dragging:
            radius = self.KNOB_RADIUS
            self.create_oval(
                position - radius,
                center - radius,
                position + radius,
                center + radius,
                fill=palette["text"],
                outline=palette["bg"],
                tags="knob",
            )

    def _update_from_x(self, x: float) -> None:
        """Move the slider to the position under the mouse and report the change."""
        value = self._fraction_from_x(x)
        if value != self._fraction:
            self._fraction = value
            self._redraw()
            if self.on_change is not None:
                self.on_change(value)
        else:
            self._redraw()

    def set_fraction(self, value: float) -> None:
        """Move the slider from the code; ignored while the user is dragging it."""
        if self._dragging:
            return
        value = min(1.0, max(0.0, float(value)))
        if value != self._fraction:
            self._fraction = value
            self._redraw()

    def _on_configure(self, event) -> None:
        """The widget changed size: redraw to the new width."""
        self._redraw()

    def _on_enter(self, event) -> None:
        """Mouse over the slider: show the knob."""
        self._hover = True
        self._redraw()

    def _on_leave(self, event) -> None:
        """Mouse left the slider: hide the knob unless a drag is going on."""
        self._hover = False
        self._redraw()

    def _on_press(self, event) -> None:
        """Click anywhere on the track: jump to that position."""
        self._dragging = True
        self._update_from_x(event.x)

    def _on_drag(self, event) -> None:
        """Mouse moved with the button down: follow it."""
        self._update_from_x(event.x)

    def _on_release(self, event) -> None:
        """Mouse button released: keep the value and report it as committed."""
        if not self._dragging:
            return
        self._dragging = False
        self._redraw()
        if self.on_commit is not None:
            self.on_commit(self._fraction)

    def apply_palette(self) -> None:
        """Repaint the slider after a theme switch."""
        self._apply_bg()
        self._redraw()


def _gradient(size: int, start: str, end: str) -> Image.Image:
    """Diagonal gradient between two colours, built small and then enlarged."""
    steps = 32
    small = Image.new("RGB", (steps, steps))
    pixels = small.load()
    for y in range(steps):
        for x in range(steps):
            pixels[x, y] = _rgb(theme.mix(start, end, (x + y) / (2 * (steps - 1))))
    return small.resize((size, size), Image.LANCZOS)


def _draw_note(image: Image.Image, size: int) -> None:
    """Draw a simple white music note (two heads, two stems and a beam) over the cover."""
    draw = ImageDraw.Draw(image)
    head = size * 0.115
    left = (size * 0.36, size * 0.68)
    right = (size * 0.64, size * 0.61)
    left_top = size * 0.33
    right_top = size * 0.26
    stem = size * 0.045
    beam = stem * 1.8
    for cx, cy in (left, right):
        draw.ellipse((cx - head, cy - head, cx + head, cy + head), fill="#ffffff")
    draw.rectangle((left[0], left_top, left[0] + stem, left[1]), fill="#ffffff")
    draw.rectangle((right[0], right_top, right[0] + stem, right[1]), fill="#ffffff")
    draw.polygon(
        [
            (left[0], left_top),
            (left[0], left_top + beam),
            (right[0] + stem, right_top + beam),
            (right[0] + stem, right_top),
        ],
        fill="#ffffff",
    )


def _default_cover(size: int, palette: dict) -> Image.Image:
    """Generated cover: diagonal accent gradient with a white note, drawn at 3x and shrunk."""
    scale = 3
    big = size * scale
    dark = theme.mix(palette["accent"], "#000000", 0.55)
    image = _gradient(big, palette["accent"], dark)
    _draw_note(image, big)
    return image.resize((size, size), Image.LANCZOS)


def _rounded_image(image: Image.Image, radius: int) -> Image.Image:
    """Cut an image to a rounded square: mask drawn at 3x and downscaled, so the corners are smooth."""
    size = image.size[0]
    scale = 3
    mask = Image.new("L", (size * scale, size * scale), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size * scale - 1, size * scale - 1), radius=radius * scale, fill=255
    )
    mask = mask.resize((size, size), Image.LANCZOS)
    result = image.convert("RGBA")
    result.putalpha(mask)
    return result


class CoverArt(tk.Canvas):
    """Square cover: the song picture with rounded corners, or a generated cover when there is none."""

    def __init__(self, master, size: int = 320, bg_key: str = "bg") -> None:
        """Create the cover with a starting `size` in pixels."""
        self._size = max(32, int(size))
        super().__init__(
            master,
            width=self._size,
            height=self._size,
            highlightthickness=0,
            borderwidth=0,
        )
        self._bg_key = bg_key
        self._source: Image.Image | None = None
        self._photo: ImageTk.PhotoImage | None = None
        self._item = self.create_image(0, 0, anchor="nw")
        self._apply_bg()
        self._render()

    def _apply_bg(self) -> None:
        """Paint the canvas background."""
        palette = theme.current_palette()
        self.configure(bg=palette.get(self._bg_key, palette["bg"]))

    def _load_source(self, data: bytes | None) -> Image.Image | None:
        """Square RGB image from the picture bytes, or None when there is no usable picture."""
        if not data:
            return None
        try:
            image = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            # Broken or unsupported picture: the generated cover is used instead.
            return None
        width, height = image.size
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        return image.crop((left, top, left + side, top + side))

    def _render(self) -> None:
        """Rebuild the picture at the current size and show it on the canvas."""
        size = self._size
        if self._source is not None:
            base = self._source.resize((size, size), Image.LANCZOS)
        else:
            base = _default_cover(size, theme.current_palette())
        image = _rounded_image(base, max(4, size // 16))
        self._photo = ImageTk.PhotoImage(image)
        self.itemconfigure(self._item, image=self._photo)

    def set_cover(self, data: bytes | None) -> None:
        """Show a picture from its bytes; None or invalid data falls back to the generated cover."""
        self._source = self._load_source(data)
        self._render()

    def set_size(self, size: int) -> None:
        """Resize the widget and render the cached picture again."""
        size = max(32, int(size))
        if size == self._size:
            return
        self._size = size
        self.configure(width=size, height=size)
        self._render()

    def apply_palette(self) -> None:
        """Repaint the cover after a theme switch; the generated cover uses the accent colour."""
        self._apply_bg()
        self._render()
