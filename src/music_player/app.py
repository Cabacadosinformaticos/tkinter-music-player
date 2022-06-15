# Main window of the music player: the "now playing" panel on the left (cover,
# song text, seek bar, transport buttons and volume) and the playlist on the
# right, built on config, playlist, metadata, player, theme and widgets.

from __future__ import annotations

import os
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

from . import config, metadata, theme
from .playlist import Playlist, Track, format_duration
from .player import AudioPlayer, PlayerError
from .widgets import CoverArt, IconButton, Slider

# Audio files accepted by the open dialog and when adding a whole folder.
AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".flac", ".m4a")

# Filter of the open dialog: the audio files first, then every file.
AUDIO_FILETYPES = (
    ("Audio files", "*.mp3 *.wav *.ogg *.flac *.m4a"),
    ("All files", "*.*"),
)

# Spacing of the layout, in pixels: window padding and gap between widgets.
PAD = 16
GAP = 8


def _clamp(value: float, low: float, high: float) -> float:
    """Keep a number inside the low..high range."""
    return max(low, min(high, value))


def _shorten(text: str, font: tkfont.Font, max_width: int) -> str:
    """Cut text so that it fits in max_width pixels, adding "..." at the end."""
    if max_width <= 0 or font.measure(text) <= max_width:
        return text
    cut = text
    while cut and font.measure(cut + "...") > max_width:
        cut = cut[:-1]
    return cut + "..."


def _font_object(root: tk.Tk, size: int, weight: str = "normal") -> tkfont.Font:
    """Tk font object matching theme.font(), used to measure how much text fits."""
    family, size, weight = theme.font(size, weight)
    return tkfont.Font(root=root, family=family, size=size, weight=weight)


class PlayerApp:
    """Main window: now playing panel, playlist, transport controls and theme."""

    def __init__(
        self, root: tk.Tk, settings: config.Settings, player: AudioPlayer | None = None
    ) -> None:
        """Build the window; `player` is injectable and defaults to a real AudioPlayer."""
        self.root = root
        self.settings = settings
        self.playlist = Playlist()
        # Start with the shuffle and repeat choices saved the last time.
        self.playlist.shuffle = bool(settings["shuffle"])
        self.playlist.repeat = str(settings["repeat"])
        self.player = player
        if self.player is None:
            try:
                self.player = AudioPlayer()
            except PlayerError as error:
                # Without an audio device the window still opens, the transport
                # buttons simply do nothing.
                messagebox.showerror("Music Player", str(error))
                self.player = None
        self._timer: str | None = None
        self._closing = False
        self._cover_size = 320
        self._title_text = ""
        self._title_shown = ""
        self._artist_text = ""
        self._artist_shown = ""
        self._album_text = ""
        self._album_shown = ""

        self._build_window()
        self._build_menu()
        self._build_left_panel()
        self._build_right_panel()
        self._apply_palette()
        self._refresh_playlist()
        self._update_song_labels(None)
        self._set_initial_volume()
        self._tick()

    # ------------------------------------------------------------------
    # Build the interface
    # ------------------------------------------------------------------

    def _build_window(self) -> None:
        """Title, icon, size and background of the root window, plus the two columns."""
        palette = theme.current_palette()
        self.root.title("Music Player")
        self.root.geometry("1040x680")
        self.root.minsize(900, 600)
        self.root.configure(bg=palette["bg"])
        try:
            self.root.iconbitmap(str(config.IMAGES_DIR / "icon.ico"))
        except (tk.TclError, OSError):
            # No icon available: the window opens with the default one.
            pass
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # The two columns of the window: now playing and playlist.
        self.container = ttk.Frame(self.root)
        self.container.grid(row=0, column=0, sticky="nsew", padx=PAD, pady=PAD)
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1, minsize=380)
        self.container.columnconfigure(1, weight=2)

    def _build_menu(self) -> None:
        """File, Playlist and View menus, kept in the native menu bar colours."""
        self.menu = tk.Menu(self.root)

        file_menu = tk.Menu(self.menu, tearoff=False)
        file_menu.add_command(label="Add songs...", command=self._add_songs)
        file_menu.add_command(label="Add folder...", command=self._add_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self._on_close)
        self.menu.add_cascade(label="File", menu=file_menu)

        playlist_menu = tk.Menu(self.menu, tearoff=False)
        playlist_menu.add_command(label="Remove selected song", command=self._remove_selected)
        playlist_menu.add_command(label="Clear playlist", command=self._clear_playlist)
        self.menu.add_cascade(label="Playlist", menu=playlist_menu)

        self.view_menu = tk.Menu(self.menu, tearoff=False)
        self.theme_entry = 0
        self.view_menu.add_command(label=self._theme_menu_label(), command=self._toggle_theme)
        self.menu.add_cascade(label="View", menu=self.view_menu)

        self.root.configure(menu=self.menu)

    def _build_left_panel(self) -> None:
        """Cover, song text, seek bar, transport buttons and volume, all centred."""
        self.left = ttk.Frame(self.container)
        self.left.grid(row=0, column=0, sticky="nsew", padx=(0, PAD))
        self.left.columnconfigure(0, weight=1)
        self.left.bind("<Configure>", self._on_left_resize)

        self._title_font = _font_object(self.root, 20, "bold")
        self._artist_font = _font_object(self.root, 12)
        self._album_font = _font_object(self.root, 10)

        # Cover art at the top, resized with the column.
        self.cover = CoverArt(self.left, size=self._cover_size)
        self.cover.grid(row=0, column=0, pady=(0, PAD))

        # Title, artist and album, one line each with an ellipsis when they are too long.
        self.title_label = ttk.Label(self.left, style="Title.TLabel", anchor="center")
        self.title_label.grid(row=1, column=0, sticky="ew")
        self.title_label.bind("<Configure>", self._on_title_resize)
        self.artist_label = ttk.Label(self.left, style="Artist.TLabel", anchor="center")
        self.artist_label.grid(row=2, column=0, sticky="ew", pady=(GAP // 2, 0))
        self.artist_label.bind("<Configure>", self._on_artist_resize)
        # An empty label keeps the height of one line, so the layout never jumps.
        self.album_label = ttk.Label(self.left, style="Muted.TLabel", anchor="center")
        self.album_label.grid(row=3, column=0, sticky="ew", pady=(0, PAD))
        self.album_label.bind("<Configure>", self._on_album_resize)

        # Seek bar: elapsed time, slider, total time.
        seek_row = ttk.Frame(self.left)
        seek_row.grid(row=4, column=0, sticky="ew")
        seek_row.columnconfigure(1, weight=1)
        self.elapsed_label = ttk.Label(seek_row, style="Time.TLabel", width=6, anchor="e")
        self.elapsed_label.grid(row=0, column=0, padx=(0, GAP))
        self.seek_slider = Slider(seek_row, on_commit=self._on_seek)
        self.seek_slider.grid(row=0, column=1, sticky="ew")
        self.total_label = ttk.Label(seek_row, style="Time.TLabel", width=6, anchor="w")
        self.total_label.grid(row=0, column=2, padx=(GAP, 0))

        # Transport buttons: shuffle, previous, play or pause, next, repeat and,
        # after a larger gap, stop. The five main ones share the same spacing.
        controls = ttk.Frame(self.left)
        controls.grid(row=5, column=0, pady=PAD)
        self.shuffle_button = IconButton(controls, "shuffle", command=self._on_shuffle)
        self.shuffle_button.pack(side="left", padx=GAP // 2)
        self.previous_button = IconButton(controls, "previous", command=self._on_previous)
        self.previous_button.pack(side="left", padx=GAP // 2)
        self.play_button = IconButton(
            controls, "play", command=self._on_play_pause, size=56, circle=True
        )
        self.play_button.pack(side="left", padx=GAP // 2)
        self.next_button = IconButton(controls, "next", command=self._on_next)
        self.next_button.pack(side="left", padx=GAP // 2)
        self.repeat_button = IconButton(controls, "repeat", command=self._on_repeat)
        self.repeat_button.pack(side="left", padx=GAP // 2)
        self.stop_button = IconButton(controls, "stop", command=self._on_stop)
        self.stop_button.pack(side="left", padx=(PAD, 0))

        # Volume: icon (no command yet) and a short slider.
        volume_row = ttk.Frame(self.left)
        volume_row.grid(row=6, column=0)
        self.volume_button = IconButton(volume_row, "volume", size=32)
        self.volume_button.pack(side="left", padx=(0, GAP))
        self.volume_slider = Slider(volume_row, on_change=self._on_volume)
        self.volume_slider.configure(width=140)
        self.volume_slider.pack(side="left")

        # Empty space at the bottom keeps the content at the top of the column.
        self.left.rowconfigure(7, weight=1)

    def _build_right_panel(self) -> None:
        """Playlist header with its buttons, the song table and the footer."""
        self.right = ttk.Frame(self.container)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.columnconfigure(0, weight=1)
        self.right.rowconfigure(1, weight=1)

        # Header: section name on the left, add and remove buttons on the right.
        header = ttk.Frame(self.right)
        header.grid(row=0, column=0, sticky="ew", pady=(0, GAP))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="PLAYLIST", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        buttons = ttk.Frame(header)
        buttons.grid(row=0, column=1, sticky="e")
        self.add_button = IconButton(buttons, "add", command=self._add_songs, size=32)
        self.add_button.pack(side="left", padx=(0, GAP))
        self.folder_button = IconButton(buttons, "folder", command=self._add_folder, size=32)
        self.folder_button.pack(side="left", padx=(0, GAP))
        self.remove_button = IconButton(buttons, "close", command=self._remove_selected, size=32)
        self.remove_button.pack(side="left")

        # Song table with its scrollbar.
        table = ttk.Frame(self.right)
        table.grid(row=1, column=0, sticky="nsew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            table,
            style="Playlist.Treeview",
            columns=("#", "Title", "Artist", "Time"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("#", text="#")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Artist", text="Artist")
        self.tree.heading("Time", text="Time")
        self.tree.column("#", width=48, anchor="e", stretch=False)
        self.tree.column("Title", width=240, anchor="w", stretch=True)
        self.tree.column("Artist", width=160, anchor="w", stretch=True)
        self.tree.column("Time", width=72, anchor="e", stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<Double-1>", self._on_row_double_click)
        self.tree.bind("<Return>", self._on_row_enter)

        # Footer with the number of songs and their total time.
        self.footer = ttk.Label(self.right, style="Muted.TLabel")
        self.footer.grid(row=2, column=0, sticky="w", pady=(GAP, 0))

    # ------------------------------------------------------------------
    # Playlist actions
    # ------------------------------------------------------------------

    def _refresh_playlist(self) -> None:
        """Rebuild the table from playlist.tracks, so rows and indices stay in the same order."""
        self.tree.delete(*self.tree.get_children())
        for index, track in enumerate(self.playlist.tracks):
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(index + 1, track.title, track.artist, format_duration(track.duration)),
            )
        self._update_footer()
        self._highlight_playing()

    def _update_footer(self) -> None:
        """Number of songs and their total time, or a hint when the playlist is empty."""
        count = len(self.playlist)
        if count == 0:
            self.footer.configure(text="No songs yet - use the + button or File > Add songs")
            return
        word = "song" if count == 1 else "songs"
        total = format_duration(self.playlist.total_duration())
        self.footer.configure(text=f"{count} {word}, {total}")

    def _highlight_playing(self) -> None:
        """Mark the row of the song that is playing with the accent colour."""
        for iid in self.tree.get_children():
            self.tree.item(iid, tags=())
        if self.player is None or self.player.state == "stopped":
            return
        index = self.playlist.current
        if 0 <= index < len(self.playlist) and self.tree.exists(str(index)):
            iid = str(index)
            self.tree.item(iid, tags=("playing",))
            self.tree.see(iid)

    def _selected_index(self) -> int | None:
        """Index of the selected row, or None when no row is selected."""
        selection = self.tree.selection()
        if not selection:
            return None
        try:
            index = int(selection[0])
        except ValueError:
            return None
        if 0 <= index < len(self.playlist):
            return index
        return None

    def _add_songs(self) -> None:
        """Ask for audio files, remember the folder and add the new ones."""
        paths = filedialog.askopenfilenames(
            parent=self.root,
            title="Add songs",
            initialdir=self._initial_dir(),
            filetypes=AUDIO_FILETYPES,
        )
        paths = tuple(paths)
        if not paths:
            return
        self._remember_folder(os.path.dirname(os.path.abspath(paths[0])))
        self._add_paths(paths)

    def _add_folder(self) -> None:
        """Ask for a folder and add its audio files, sorted by name and not recursive."""
        folder = filedialog.askdirectory(
            parent=self.root, title="Add folder", initialdir=self._initial_dir()
        )
        if not folder:
            return
        self._remember_folder(folder)
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            return
        paths = [
            os.path.join(folder, name)
            for name in names
            if name.lower().endswith(AUDIO_EXTENSIONS)
        ]
        self._add_paths(paths)

    def _add_paths(self, paths) -> int:
        """Add the files that are not in the playlist yet and return how many were added."""
        known = {os.path.normcase(os.path.abspath(track.path)) for track in self.playlist.tracks}
        added = 0
        for path in paths:
            path = os.path.abspath(path)
            key = os.path.normcase(path)
            if key in known:
                continue
            known.add(key)
            self.playlist.add(metadata.read_track(path))
            added += 1
        if added:
            self._refresh_playlist()
        return added

    def _remember_folder(self, folder: str) -> None:
        """Remember the folder used by the dialogs and save the settings."""
        self.settings["music_dir"] = folder
        self.settings.save()

    def _initial_dir(self) -> str:
        """Folder the dialogs open in: the last one used, then music/, then the home folder."""
        remembered = str(self.settings["music_dir"])
        if remembered and os.path.isdir(remembered):
            return remembered
        if config.MUSIC_DIR.is_dir():
            return str(config.MUSIC_DIR)
        return os.path.expanduser("~")

    def _remove_selected(self) -> None:
        """Delete the selected song, stopping it first when it is the one playing."""
        index = self._selected_index()
        if index is None:
            return
        if index == self.playlist.current and self.player is not None:
            if self.player.state != "stopped":
                self._stop_playback()
        self.playlist.remove(index)
        self._refresh_playlist()
        self._update_song_labels(self.playlist.current_track())

    def _clear_playlist(self) -> None:
        """Stop the music and empty the playlist."""
        self._stop_playback()
        self.playlist.clear()
        self._refresh_playlist()
        self._update_song_labels(None)

    # ------------------------------------------------------------------
    # Playback actions
    # ------------------------------------------------------------------

    def _play_index(self, index: int) -> None:
        """Make one song current, start it and update the whole interface."""
        if self.player is None:
            return
        if self.playlist.current == index:
            # advance() already moved the current position here: selecting the
            # same song again would drop the shuffled order, so it is kept.
            track = self.playlist.current_track()
        else:
            track = self.playlist.select(index)
        if track is None:
            return
        try:
            self.player.play(track.path)
        except PlayerError as error:
            messagebox.showerror("Music Player", str(error))
            self._stop_playback()
            return
        self._update_song_labels(track)
        self.cover.set_cover(metadata.read_cover(track.path))
        self.play_button.set_kind("pause")
        self.seek_slider.set_fraction(0.0)
        self.elapsed_label.configure(text="0:00")
        self.total_label.configure(
            text=format_duration(track.duration) if track.duration > 0 else "--:--"
        )
        self._highlight_playing()

    def _stop_playback(self) -> None:
        """Stop the audio and put the progress display back to the start."""
        if self.player is not None:
            self.player.stop()
        self.play_button.set_kind("play")
        self.seek_slider.set_fraction(0.0)
        track = self.playlist.current_track()
        if track is not None and track.duration > 0:
            self.elapsed_label.configure(text="0:00")
            self.total_label.configure(text=format_duration(track.duration))
        else:
            self.elapsed_label.configure(text="--:--")
            self.total_label.configure(text="--:--")
        self._highlight_playing()

    def _on_play_pause(self) -> None:
        """Play, pause or resume, following the state of the player."""
        if self.player is None:
            return
        if self.player.state == "playing":
            self.player.pause()
            self.play_button.set_kind("play")
            self._highlight_playing()
            return
        if self.player.state == "paused":
            self.player.resume()
            self.play_button.set_kind("pause")
            self._highlight_playing()
            return
        # Stopped: play the selected row, or the first song.
        index = self._selected_index()
        if index is None:
            if len(self.playlist) == 0:
                self._update_footer()
                return
            index = 0
        self._play_index(index)

    def _on_next(self) -> None:
        """Move to the next song and play it, or stop when the playlist ends."""
        if self.player is None:
            return
        index = self.playlist.advance(auto=False)
        if index is None:
            self._stop_playback()
            return
        self._play_index(index)

    def _on_previous(self) -> None:
        """Move to the previous song and play it."""
        if self.player is None:
            return
        index = self.playlist.previous()
        if index is None:
            self._stop_playback()
            return
        self._play_index(index)

    def _on_stop(self) -> None:
        """Stop the current song and reset its position."""
        self._stop_playback()

    def _on_track_end(self) -> None:
        """A song ended by itself: play the next one, or stop at the end of the playlist."""
        index = self.playlist.advance(auto=True)
        if index is None:
            self._stop_playback()
            return
        # A file that cannot be played stops the player inside _play_index, so
        # an unreadable song does not start the next one over and over.
        self._play_index(index)

    def _on_shuffle(self) -> None:
        """Switch shuffle on or off and remember the choice."""
        self.playlist.shuffle = not self.playlist.shuffle
        self.settings["shuffle"] = self.playlist.shuffle
        self.settings.save()
        self._update_mode_buttons()

    def _on_repeat(self) -> None:
        """Cycle the repeat mode off, all, one and remember the choice."""
        modes = ("off", "all", "one")
        position = modes.index(self.playlist.repeat)
        self.playlist.repeat = modes[(position + 1) % len(modes)]
        self.settings["repeat"] = self.playlist.repeat
        self.settings.save()
        self._update_mode_buttons()

    def _update_mode_buttons(self) -> None:
        """Show the shuffle and repeat state on their buttons."""
        self.shuffle_button.set_active(self.playlist.shuffle)
        repeat = self.playlist.repeat
        self.repeat_button.set_kind("repeat_one" if repeat == "one" else "repeat")
        self.repeat_button.set_active(repeat != "off")

    def _on_row_double_click(self, event) -> None:
        """Play the row under the mouse pointer."""
        row = self.tree.identify_row(event.y)
        if not row:
            return
        try:
            index = int(row)
        except ValueError:
            return
        self._play_index(index)

    def _on_row_enter(self, event) -> None:
        """Play the selected row when Enter is pressed."""
        index = self._selected_index()
        if index is not None:
            self._play_index(index)

    # ------------------------------------------------------------------
    # Progress and volume
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        """Refresh the seek bar and the time labels about five times per second."""
        if self._closing:
            return
        if self.player is not None and self.player.finished():
            self._on_track_end()
        self._update_progress()
        self._timer = self.root.after(200, self._tick)

    def _update_progress(self) -> None:
        """Show the position of the current song; a song without duration stays at "--:--"."""
        track = self.playlist.current_track()
        duration = track.duration if track is not None else 0.0
        if duration <= 0:
            self.elapsed_label.configure(text="--:--")
            self.total_label.configure(text="--:--")
            self.seek_slider.set_fraction(0.0)
            return
        position = self.player.position() if self.player is not None else 0.0
        position = min(position, duration)
        self.elapsed_label.configure(text=format_duration(position))
        self.total_label.configure(text=format_duration(duration))
        self.seek_slider.set_fraction(position / duration)

    def _on_seek(self, fraction: float) -> None:
        """Jump to the place where the user released the seek bar."""
        if self.player is None or self.player.state == "stopped":
            return
        track = self.playlist.current_track()
        if track is None or track.duration <= 0:
            return
        try:
            self.player.seek(fraction * track.duration)
        except PlayerError as error:
            messagebox.showerror("Music Player", str(error))
            self._stop_playback()

    def _set_initial_volume(self) -> None:
        """Start with the volume saved in the settings."""
        volume = float(self.settings["volume"])
        self.volume_slider.set_fraction(volume)
        if self.player is not None:
            self.player.set_volume(volume)

    def _on_volume(self, fraction: float) -> None:
        """Set the volume while the user moves the volume slider."""
        if self.player is not None:
            self.player.set_volume(fraction)
        self.settings["volume"] = fraction

    # ------------------------------------------------------------------
    # Now playing text, theme and closing
    # ------------------------------------------------------------------

    def _update_song_labels(self, track: Track | None) -> None:
        """Show the title, artist and album of one track, or the empty state when there is none."""
        if track is None:
            self._title_text = "Nothing playing"
            self._artist_text = "Add songs to start"
            self._album_text = ""
            self.cover.set_cover(None)
        else:
            self._title_text = track.title
            self._artist_text = track.artist
            self._album_text = track.album
        self._update_window_title(track)
        self._show_title(self.title_label.winfo_width())
        self._show_artist(self.artist_label.winfo_width())
        self._show_album(self.album_label.winfo_width())

    def _update_window_title(self, track: Track | None) -> None:
        """Window title with the song and its artist, or the plain name when nothing is loaded."""
        if track is None:
            self.root.title("Music Player")
        elif track.artist:
            self.root.title(f"{track.title} - {track.artist} - Music Player")
        else:
            self.root.title(f"{track.title} - Music Player")

    def _show_title(self, width: int) -> None:
        """Title on a single centred line, cut with an ellipsis when the label is narrow."""
        shown = _shorten(self._title_text, self._title_font, width - GAP)
        if shown != self._title_shown:
            self._title_shown = shown
            self.title_label.configure(text=shown)

    def _show_artist(self, width: int) -> None:
        """Artist on a single centred line, cut with an ellipsis when the label is narrow."""
        shown = _shorten(self._artist_text, self._artist_font, width - GAP)
        if shown != self._artist_shown:
            self._artist_shown = shown
            self.artist_label.configure(text=shown)

    def _show_album(self, width: int) -> None:
        """Album on a single centred line, cut with an ellipsis when the label is narrow."""
        shown = _shorten(self._album_text, self._album_font, width - GAP)
        if shown != self._album_shown:
            self._album_shown = shown
            self.album_label.configure(text=shown)

    def _on_title_resize(self, event) -> None:
        """The title label changed width: fit the text again."""
        self._show_title(event.width)

    def _on_artist_resize(self, event) -> None:
        """The artist label changed width: fit the text again."""
        self._show_artist(event.width)

    def _on_album_resize(self, event) -> None:
        """The album label changed width: fit the text again."""
        self._show_album(event.width)

    def _on_left_resize(self, event) -> None:
        """Resize the cover with the left column, between 200 and 420 pixels."""
        if event.width <= 1:
            return
        size = int(_clamp(event.width - 32, 200, 420))
        if abs(size - self._cover_size) >= 8:
            self._cover_size = size
            self.cover.set_size(size)

    def _theme_menu_label(self) -> str:
        """Text of the View entry for the theme that is not in use."""
        if theme.current_theme() == "dark":
            return "Switch to light theme"
        return "Switch to dark theme"

    def _toggle_theme(self) -> None:
        """Swap dark and light, repaint the widgets and remember the choice."""
        other = "light" if theme.current_theme() == "dark" else "dark"
        theme.apply_theme(self.root, other)
        self._apply_palette()
        self.view_menu.entryconfigure(self.theme_entry, label=self._theme_menu_label())
        self.settings["theme"] = other
        self.settings.save()

    def _apply_palette(self) -> None:
        """Repaint the root window, the canvas widgets and the playing row tag."""
        palette = theme.current_palette()
        self.root.configure(bg=palette["bg"])
        for widget in (
            self.cover,
            self.seek_slider,
            self.volume_slider,
            self.play_button,
            self.shuffle_button,
            self.previous_button,
            self.next_button,
            self.repeat_button,
            self.stop_button,
            self.volume_button,
            self.add_button,
            self.folder_button,
            self.remove_button,
        ):
            widget.apply_palette()
        # apply_palette() keeps the toggled flag, this redraws the active colour
        # and the repeat icon with the new palette.
        self._update_mode_buttons()
        self.tree.tag_configure("playing", foreground=palette["accent"])

    def _on_close(self) -> None:
        """Cancel the timer, stop the music, save the settings and close the window."""
        if self._closing:
            return
        self._closing = True
        if self._timer is not None:
            self.root.after_cancel(self._timer)
            self._timer = None
        if self.player is not None:
            self.player.stop()
        self.settings.save()
        self.root.destroy()


def main() -> None:
    """Start the player: DPI awareness, theme, main window and main loop."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            # Older Windows versions do not have this call: the window still opens.
            pass
    root = tk.Tk()
    settings = config.Settings.load()
    theme.apply_theme(root, str(settings["theme"]))
    PlayerApp(root, settings)
    root.mainloop()
