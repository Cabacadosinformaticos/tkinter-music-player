# Main window of the music player: the "now playing" panel on the left (cover,
# song text, seek bar, transport buttons and volume) and the playlist on the
# right, built on config, playlist, metadata, player, theme and widgets.

from __future__ import annotations

import os
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

from . import config, metadata, theme
from .history import HistoryBackend, HistoryError, make_backend
from .history_window import HistoryWindow
from .m3u import load_m3u, save_m3u
from .playlist import Playlist, Track, format_duration
from .player import AudioPlayer, PlayerError
from .settings_dialog import SettingsDialog
from .stats_window import StatsWindow
from .widgets import CoverArt, IconButton, Slider

# Audio files accepted by the open dialog and when adding a whole folder.
AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".flac", ".m4a")

# Filter of the open dialog: the audio files first, then every file.
AUDIO_FILETYPES = (
    ("Audio files", "*.mp3 *.wav *.ogg *.flac *.m4a"),
    ("All files", "*.*"),
)

# Filter of the playlist dialogs: the usual M3U files, with the UTF-8 variant.
PLAYLIST_FILETYPES = (
    ("M3U playlists", "*.m3u *.m3u8"),
    ("All files", "*.*"),
)

# Window size used when there is no saved geometry to restore.
DEFAULT_GEOMETRY = "1040x680"

# Spacing of the layout, in pixels: window padding and gap between widgets.
PAD = 16
GAP = 8

# Grey text shown in the search box while it is empty and not focused.
SEARCH_PLACEHOLDER = "Search title, artist or album"

# Volume change of one arrow key press, as a fraction of the slider.
VOLUME_STEP = 0.05

# Below this volume the icon shows only one sound wave.
VOLUME_LOW_LIMIT = 0.4

# Widget classes that receive typed text: shortcuts stay out of their way.
TEXT_CLASSES = ("Entry", "TEntry", "Text")

# Pairs of key and action shown in the Keyboard shortcuts window.
SHORTCUTS = (
    ("Space", "Play or pause"),
    ("Right arrow", "Next song"),
    ("Left arrow", "Previous song"),
    ("Up arrow", "Volume up 5%"),
    ("Down arrow", "Volume down 5%"),
    ("M", "Mute or unmute"),
    ("S", "Shuffle on or off"),
    ("R", "Repeat mode"),
    ("Ctrl+O", "Add songs"),
    ("Ctrl+Shift+O", "Add folder"),
    ("Ctrl+F", "Focus the search box"),
    ("Ctrl+,", "Open the settings"),
    ("Delete", "Remove the selected song"),
    ("Ctrl+Left / Ctrl+Right", "Previous or next song, also in the table"),
    ("Ctrl+Up / Ctrl+Down", "Volume, also in the table"),
    ("Escape", "Close this window"),
)


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
        self,
        root: tk.Tk,
        settings: config.Settings,
        player: AudioPlayer | None = None,
        history: HistoryBackend | None = None,
    ) -> None:
        """Build the window; `player` and `history` are injectable and default to the real ones."""
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
        # Play history: built from the settings, or injected by the tests. A
        # backend that cannot be opened only warns: the player works without it.
        self.history = history
        if self.history is None:
            try:
                self.history = make_backend(str(settings["history_backend"]))
            except (HistoryError, ValueError) as error:
                messagebox.showwarning("Music Player", f"Could not open the play history: {error}")
                self.history = None
        # Warn about a failing history backend only once, like the old player did.
        self._history_warned = False
        self._history_window: HistoryWindow | None = None
        self._stats_window: StatsWindow | None = None
        self._timer: str | None = None
        self._closing = False
        self._cover_size = 320
        # Mute state and the small Keyboard shortcuts window, built on demand.
        self._muted = bool(settings["muted"])
        self._shortcuts_window: tk.Toplevel | None = None
        # Search box: _placeholder_on is True while the grey hint is shown and
        # _search_programmatic blocks the change callback during code writes.
        self._placeholder_on = True
        self._search_programmatic = False
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
        self._bind_shortcuts()
        self._apply_palette()
        self._restore_session()
        self._refresh_playlist()
        if self.playlist.current >= 0:
            self._select_row(self.playlist.current)
        self._set_initial_volume()
        self._tick()

    # ------------------------------------------------------------------
    # Build the interface
    # ------------------------------------------------------------------

    def _build_window(self) -> None:
        """Title, icon, size and background of the root window, plus the two columns."""
        palette = theme.current_palette()
        self.root.title("Music Player")
        self._restore_window_geometry()
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

    def _restore_window_geometry(self) -> None:
        """Use the size and position of the last session, moved back on screen when it is off."""
        geometry = str(self.settings["window_geometry"]).strip()
        match = re.fullmatch(r"(\d+)x(\d+)([+-]\d+)([+-]\d+)", geometry)
        if match is None:
            self.root.geometry(DEFAULT_GEOMETRY)
            return
        width, height, x, y = (int(value) for value in match.groups())
        on_screen = (
            0 <= x < self.root.winfo_screenwidth() and 0 <= y < self.root.winfo_screenheight()
        )
        if on_screen:
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        else:
            # The saved position would put the window off the screen: keep the size only.
            self.root.geometry(f"{width}x{height}")

    def _build_menu(self) -> None:
        """File, Playlist, View and Help menus, kept in the native menu bar colours."""
        self.menu = tk.Menu(self.root)

        file_menu = tk.Menu(self.menu, tearoff=False)
        file_menu.add_command(
            label="Add songs...", command=self._add_songs, accelerator="Ctrl+O"
        )
        file_menu.add_command(
            label="Add folder...", command=self._add_folder, accelerator="Ctrl+Shift+O"
        )
        file_menu.add_separator()
        file_menu.add_command(label="Open playlist...", command=self._open_playlist)
        file_menu.add_command(label="Save playlist as...", command=self._save_playlist_as)
        file_menu.add_separator()
        file_menu.add_command(
            label="Settings...", command=self._open_settings, accelerator="Ctrl+,"
        )
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self._on_close)
        self.menu.add_cascade(label="File", menu=file_menu)

        playlist_menu = tk.Menu(self.menu, tearoff=False)
        playlist_menu.add_command(
            label="Remove selected song", command=self._remove_selected, accelerator="Delete"
        )
        playlist_menu.add_command(label="Clear playlist", command=self._clear_playlist)
        self.menu.add_cascade(label="Playlist", menu=playlist_menu)

        self.view_menu = tk.Menu(self.menu, tearoff=False)
        self.theme_entry = 0
        self.view_menu.add_command(label=self._theme_menu_label(), command=self._toggle_theme)
        self.menu.add_cascade(label="View", menu=self.view_menu)

        history_menu = tk.Menu(self.menu, tearoff=False)
        history_menu.add_command(label="View play history...", command=self._show_history)
        history_menu.add_command(label="Statistics...", command=self._show_stats)
        history_menu.add_separator()
        history_menu.add_command(label="Clear play history...", command=self._clear_history)
        self.menu.add_cascade(label="History", menu=history_menu)

        help_menu = tk.Menu(self.menu, tearoff=False)
        help_menu.add_command(label="Keyboard shortcuts", command=self._show_shortcuts)
        self.menu.add_cascade(label="Help", menu=help_menu)

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

        # Volume: the mute button and a short slider.
        volume_row = ttk.Frame(self.left)
        volume_row.grid(row=6, column=0)
        self.volume_button = IconButton(
            volume_row, "volume", command=self._on_volume_button, size=32
        )
        self.volume_button.pack(side="left", padx=(0, GAP))
        self.volume_slider = Slider(volume_row, on_change=self._on_volume)
        self.volume_slider.configure(width=140)
        self.volume_slider.pack(side="left")

        # Empty space at the bottom keeps the content at the top of the column.
        self.left.rowconfigure(7, weight=1)

    def _build_right_panel(self) -> None:
        """Playlist header with its buttons, the search box, the song table and the footer."""
        self.right = ttk.Frame(self.container)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.columnconfigure(0, weight=1)
        self.right.rowconfigure(2, weight=1)

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

        # Search box: magnifier, the entry with its placeholder and the clear
        # button, which only appears once something is typed.
        search = ttk.Frame(self.right)
        search.grid(row=1, column=0, sticky="ew", pady=(0, GAP))
        search.columnconfigure(1, weight=1)
        self.search_icon = IconButton(search, "search", size=24)
        self.search_icon.grid(row=0, column=0, padx=(0, GAP))
        self.search_var = tk.StringVar(value=SEARCH_PLACEHOLDER)
        self.search_entry = ttk.Entry(search, textvariable=self.search_var, style="Search.TEntry")
        self.search_entry.grid(row=0, column=1, sticky="ew")
        self.clear_search_button = IconButton(search, "close", command=self._clear_search, size=24)
        self.clear_search_button.grid(row=0, column=2, padx=(GAP, 0))
        self.clear_search_button.grid_remove()
        self.search_var.trace_add("write", self._on_search_changed)
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)
        self.search_entry.bind("<Escape>", self._on_search_escape)

        # Song table with its scrollbar.
        table = ttk.Frame(self.right)
        table.grid(row=2, column=0, sticky="nsew")
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
        self.footer.grid(row=3, column=0, sticky="w", pady=(GAP, 0))

    # ------------------------------------------------------------------
    # Playlist actions
    # ------------------------------------------------------------------

    def _refresh_playlist(self) -> None:
        """Rebuild the rows that match the search; the iid is the real playlist index."""
        self.tree.delete(*self.tree.get_children())
        for index in self.playlist.filter(self._search_query()):
            track = self.playlist.tracks[index]
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(index + 1, track.title, track.artist, format_duration(track.duration)),
            )
        self._update_footer()
        self._highlight_playing()

    def _update_footer(self) -> None:
        """Footer text: the filtered count while searching, otherwise songs and total time."""
        count = len(self.playlist)
        if count == 0:
            self.footer.configure(text="No songs yet - use the + button or File > Add songs")
            return
        if self._search_query().strip():
            shown = len(self.tree.get_children())
            if shown == 0:
                self.footer.configure(text="No songs match")
                return
            self.footer.configure(text=f"{shown} of {count} songs")
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

    def _restore_session(self) -> None:
        """Rebuild the playlist and the selection of the last session, without playing anything."""
        paths = [path for path in self.settings["last_playlist"] if os.path.isfile(path)]
        if not paths:
            self._update_song_labels(None)
            return
        self.playlist.add_many([metadata.read_track(path) for path in paths])
        index = int(self.settings["last_index"])
        if 0 <= index < len(self.playlist):
            self.playlist.select(index)
        self._update_song_labels(self.playlist.current_track())

    def _select_row(self, index: int) -> None:
        """Select one row of the table, when the current search shows it."""
        iid = str(index)
        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.focus(iid)
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
            self._remember_playlist()
        return added

    def _remember_folder(self, folder: str) -> None:
        """Remember the folder used by the dialogs and save the settings."""
        self.settings["music_dir"] = folder
        self.settings.save()

    def _remember_playlist(self) -> None:
        """Store the songs and the selected one, then write the settings file."""
        self.settings["last_playlist"] = [track.path for track in self.playlist.tracks]
        index = self._selected_index()
        self.settings["last_index"] = index if index is not None else self.playlist.current
        self._save_settings()

    def _save_settings(self) -> None:
        """Write the settings file; a disk problem must never stop the player."""
        try:
            self.settings.save()
        except OSError:
            pass

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
        self._remember_playlist()

    def _clear_playlist(self) -> None:
        """Stop the music and empty the playlist."""
        self._stop_playback()
        self.playlist.clear()
        self._refresh_playlist()
        self._update_song_labels(None)
        self._remember_playlist()

    def _open_playlist(self) -> None:
        """Ask for an M3U file and replace the playlist with the songs it lists."""
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Open playlist",
            initialdir=self._initial_dir(),
            filetypes=PLAYLIST_FILETYPES,
        )
        if not path:
            return
        self._load_playlist(path)

    def _load_playlist(self, path: str) -> None:
        """Replace the playlist with the file entries, skipping the ones whose file is gone."""
        try:
            entries = load_m3u(path)
        except (OSError, ValueError) as error:
            messagebox.showerror("Music Player", f"Could not open the playlist:\n{error}")
            return
        self._stop_playback()
        self.playlist.clear()
        skipped = 0
        for entry in entries:
            if not os.path.isfile(entry.path):
                skipped += 1
                continue
            self.playlist.add(self._fresh_track(entry))
        self._refresh_playlist()
        self._update_song_labels(self.playlist.current_track())
        self._remember_playlist()
        if skipped:
            messagebox.showinfo(
                "Music Player",
                f"{skipped} song(s) in the playlist could not be found and were skipped.",
            )

    def _fresh_track(self, entry: Track) -> Track:
        """Read the file tags again; the playlist title is kept when the file has no tags."""
        track = metadata.read_track(entry.path)
        fallback = os.path.splitext(os.path.basename(entry.path))[0]
        if track.title == fallback and entry.title:
            track.title = entry.title
        return track

    def _save_playlist_as(self) -> None:
        """Ask for a file name and write the current songs as an M3U playlist."""
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save playlist as",
            initialdir=self._initial_dir(),
            defaultextension=".m3u",
            filetypes=PLAYLIST_FILETYPES,
        )
        if not path:
            return
        try:
            save_m3u(path, self.playlist.tracks)
        except OSError as error:
            messagebox.showerror("Music Player", f"Could not save the playlist:\n{error}")

    # ------------------------------------------------------------------
    # Play history
    # ------------------------------------------------------------------

    def _show_history(self) -> None:
        """Open the play history window, or bring the open one to the front and refresh it."""
        if self.history is None:
            messagebox.showinfo("Music Player", "The play history is not available")
            return
        if self._history_window is not None and self._history_window.winfo_exists():
            self._history_window.refresh()
            self._history_window.lift()
            self._history_window.focus_set()
            return
        self._history_window = HistoryWindow(self.root, self.history)

    def _show_stats(self) -> None:
        """Open the statistics window, or bring the open one to the front and refresh it."""
        if self.history is None:
            messagebox.showinfo("Music Player", "The play history is not available")
            return
        if self._stats_window is not None and self._stats_window.winfo_exists():
            self._stats_window.refresh()
            self._stats_window.lift()
            self._stats_window.focus_set()
            return
        self._stats_window = StatsWindow(self.root, self.history)

    def _clear_history(self) -> None:
        """Ask for confirmation and delete every saved play."""
        if self.history is None:
            messagebox.showinfo("Music Player", "The play history is not available")
            return
        if not messagebox.askyesno("Music Player", "Delete every saved play?"):
            return
        try:
            self.history.clear()
        except Exception as error:
            messagebox.showerror("Music Player", f"Could not clear the play history: {error}")
            return
        # The open window, if any, must show the empty list right away.
        if self._history_window is not None and self._history_window.winfo_exists():
            self._history_window.refresh()

    def _switch_history(self, kind: str) -> str | None:
        """Use the history backend named `kind`; None on success, the error text on failure."""
        try:
            backend = make_backend(str(kind))
        except (HistoryError, ValueError) as error:
            # The old backend is kept, so the player keeps recording where it did.
            return str(error)
        # The SQL Server backend connects lazily, so a wrong server or a missing
        # db_config.ini would only show up when a song is played: check it now
        # and keep the old backend when it cannot be reached.
        if str(kind) == "sqlserver":
            try:
                backend.entries()
            except Exception as error:
                backend.close()
                return str(error)
        if self.history is not None:
            try:
                self.history.close()
            except Exception:
                # A backend that fails to close must not stop the switch.
                pass
        self.history = backend
        self._history_warned = False
        # The open windows belong to the old backend: they are dropped, so the
        # next open builds fresh ones over the new backend.
        if self._history_window is not None and self._history_window.winfo_exists():
            self._history_window.destroy()
        self._history_window = None
        if self._stats_window is not None and self._stats_window.winfo_exists():
            self._stats_window.destroy()
        self._stats_window = None
        self.settings["history_backend"] = str(kind)
        self._save_settings()
        return None

    # ------------------------------------------------------------------
    # Search box
    # ------------------------------------------------------------------

    def _search_query(self) -> str:
        """Text typed in the search box; the grey placeholder is never used as a query."""
        if self._placeholder_on:
            return ""
        return self.search_var.get()

    def _set_search_text(self, text: str, placeholder: bool) -> None:
        """Write in the search box from the code without treating it as a user edit."""
        self._search_programmatic = True
        self._placeholder_on = placeholder
        self.search_var.set(text)
        self._search_programmatic = False
        self._style_search_entry()

    def _style_search_entry(self) -> None:
        """Muted text while the placeholder is shown, normal text for a real query."""
        palette = theme.current_palette()
        color = palette["text_muted"] if self._placeholder_on else palette["text"]
        try:
            ttk.Style(master=self.root).configure("Search.TEntry", foreground=color)
        except tk.TclError:
            # A ttk theme that refuses the option keeps its own text colour.
            pass

    def _on_search_changed(self, *_args) -> None:
        """The user typed: show or hide the clear button and filter the table again."""
        if self._search_programmatic:
            return
        if self.search_var.get():
            self.clear_search_button.grid()
        else:
            self.clear_search_button.grid_remove()
        self._refresh_playlist()

    def _on_search_focus_in(self, _event) -> None:
        """The search box got the focus: drop the placeholder."""
        if self._placeholder_on:
            self._set_search_text("", placeholder=False)

    def _on_search_focus_out(self, _event) -> None:
        """The search box lost the focus: show the placeholder again when it is empty."""
        if not self.search_var.get():
            self._set_search_text(SEARCH_PLACEHOLDER, placeholder=True)

    def _on_search_escape(self, _event) -> str:
        """Escape clears the search box and leaves the focus in it."""
        self._clear_search(focus_table=False)
        return "break"

    def _clear_search(self, focus_table: bool = True) -> None:
        """Empty the search box; the clear button also sends the focus back to the table."""
        self._set_search_text("", placeholder=False)
        self.clear_search_button.grid_remove()
        self._refresh_playlist()
        if focus_table:
            self.tree.focus_set()
            self._show_search_placeholder()

    def _show_search_placeholder(self) -> None:
        """Show the placeholder when the search box is empty and not focused."""
        if not self.search_var.get():
            self._set_search_text(SEARCH_PLACEHOLDER, placeholder=True)

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
        # The song really started, so this play is saved; pausing, resuming and
        # seeking never land here.
        self._record_play(track)

    def _record_play(self, track: Track) -> None:
        """Save one play in the history; a failure warns once and never stops the music."""
        if self.history is None:
            return
        try:
            self.history.record(track.display_name, duration=track.duration)
        except Exception as error:
            if not self._history_warned:
                messagebox.showwarning("Music Player", f"Could not save the play history: {error}")
                self._history_warned = True
            return
        # The write worked, allow another warning if the backend fails again.
        self._history_warned = False

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
        """Start with the volume and mute state saved in the settings."""
        volume = float(self.settings["volume"])
        self.volume_slider.set_fraction(volume)
        if self.player is not None:
            self.player.set_volume(0.0 if self._muted else volume)
        self._update_volume_icon()

    def _on_volume(self, fraction: float) -> None:
        """Set the volume while the user moves the volume slider."""
        self._apply_volume(fraction)

    def _apply_volume(self, fraction: float) -> None:
        """Move the slider, set the player volume and remember it; stays silent while muted."""
        fraction = _clamp(float(fraction), 0.0, 1.0)
        self.volume_slider.set_fraction(fraction)
        if self.player is not None:
            self.player.set_volume(0.0 if self._muted else fraction)
        self.settings["volume"] = fraction
        self._update_volume_icon()

    def _volume_step(self, delta: float) -> None:
        """Move the volume by one step, up or down (arrow keys)."""
        self._apply_volume(self.volume_slider.fraction + delta)

    def _on_volume_button(self) -> None:
        """Click on the volume icon: mute or unmute."""
        self._set_muted(not self._muted)

    def _set_muted(self, muted: bool) -> None:
        """Mute or unmute, keep the slider in place and remember the choice."""
        self._muted = bool(muted)
        self.settings["muted"] = self._muted
        self.settings.save()
        if self.player is not None:
            if self._muted:
                self.player.set_volume(0.0)
            else:
                # Unmuting goes back to the position of the slider.
                self.player.set_volume(self.volume_slider.fraction)
        self._update_volume_icon()

    def _update_volume_icon(self) -> None:
        """Icon of the volume button: a cross when muted or empty, fewer waves when low."""
        fraction = self.volume_slider.fraction
        if self._muted or fraction <= 0:
            kind = "mute"
        elif fraction < VOLUME_LOW_LIMIT:
            kind = "volume_low"
        else:
            kind = "volume"
        self.volume_button.set_kind(kind)

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _bind_shortcuts(self) -> None:
        """Bind the shortcuts of the window; the table also gets its own space key."""
        self.root.bind_all("<space>", self._on_space_key)
        self.root.bind_all("<Left>", self._on_left_key)
        self.root.bind_all("<Right>", self._on_right_key)
        self.root.bind_all("<Up>", self._on_up_key)
        self.root.bind_all("<Down>", self._on_down_key)
        self.root.bind_all("<Control-Left>", self._on_ctrl_left_key)
        self.root.bind_all("<Control-Right>", self._on_ctrl_right_key)
        self.root.bind_all("<Control-Up>", self._on_ctrl_up_key)
        self.root.bind_all("<Control-Down>", self._on_ctrl_down_key)
        self.root.bind_all("<Control-o>", self._on_add_songs_key)
        self.root.bind_all("<Control-Shift-O>", self._on_add_folder_key)
        self.root.bind_all("<Control-f>", self._on_focus_search_key)
        self.root.bind_all("<Control-comma>", self._on_settings_key)
        self.root.bind_all("<Delete>", self._on_delete_key)
        self.root.bind_all("<m>", self._on_mute_key)
        self.root.bind_all("<s>", self._on_shuffle_key)
        self.root.bind_all("<r>", self._on_repeat_key)
        # Space on the table runs before the Treeview class binding, which would
        # otherwise toggle the selection of the row under the cursor.
        self.tree.bind("<space>", self._on_tree_space)

    def _focus_class(self) -> str:
        """Widget class of the focused widget, or an empty string when there is none."""
        try:
            widget = self.root.focus_get()
        except KeyError:
            return ""
        if widget is None:
            return ""
        try:
            return widget.winfo_class()
        except tk.TclError:
            return ""

    def _is_typing(self) -> bool:
        """True while the focus is in a text field, where the keys must only type text."""
        return self._focus_class() in TEXT_CLASSES

    def _tree_has_focus(self) -> bool:
        """True while the playlist table has the focus."""
        return self._focus_class() == "Treeview"

    def _on_space_key(self, _event=None) -> str | None:
        """Space: play or pause, everywhere except in a text field."""
        if self._is_typing():
            return None
        self._on_play_pause()
        return "break"

    def _on_tree_space(self, _event=None) -> str:
        """Space on the playlist table: play or pause without changing the selection."""
        self._on_play_pause()
        return "break"

    def _on_left_key(self, _event=None) -> str | None:
        """Left arrow: previous song, unless the table or a text field has the focus."""
        if self._is_typing() or self._tree_has_focus():
            return None
        self._on_previous()
        return "break"

    def _on_right_key(self, _event=None) -> str | None:
        """Right arrow: next song, unless the table or a text field has the focus."""
        if self._is_typing() or self._tree_has_focus():
            return None
        self._on_next()
        return "break"

    def _on_up_key(self, _event=None) -> str | None:
        """Up arrow: volume up, unless the table or a text field has the focus."""
        if self._is_typing() or self._tree_has_focus():
            return None
        self._volume_step(VOLUME_STEP)
        return "break"

    def _on_down_key(self, _event=None) -> str | None:
        """Down arrow: volume down, unless the table or a text field has the focus."""
        if self._is_typing() or self._tree_has_focus():
            return None
        self._volume_step(-VOLUME_STEP)
        return "break"

    def _on_ctrl_left_key(self, _event=None) -> str | None:
        """Ctrl+Left: previous song, also while the table has the focus."""
        if self._is_typing():
            return None
        self._on_previous()
        return "break"

    def _on_ctrl_right_key(self, _event=None) -> str | None:
        """Ctrl+Right: next song, also while the table has the focus."""
        if self._is_typing():
            return None
        self._on_next()
        return "break"

    def _on_ctrl_up_key(self, _event=None) -> str | None:
        """Ctrl+Up: volume up, also while the table has the focus."""
        if self._is_typing():
            return None
        self._volume_step(VOLUME_STEP)
        return "break"

    def _on_ctrl_down_key(self, _event=None) -> str | None:
        """Ctrl+Down: volume down, also while the table has the focus."""
        if self._is_typing():
            return None
        self._volume_step(-VOLUME_STEP)
        return "break"

    def _on_add_songs_key(self, _event=None) -> str:
        """Ctrl+O: open the add songs dialog."""
        self._add_songs()
        return "break"

    def _on_add_folder_key(self, _event=None) -> str:
        """Ctrl+Shift+O: open the add folder dialog."""
        self._add_folder()
        return "break"

    def _on_focus_search_key(self, _event=None) -> str:
        """Ctrl+F: put the focus in the search box."""
        self.search_entry.focus_set()
        return "break"

    def _on_settings_key(self, _event=None) -> str:
        """Ctrl+,: open the settings dialog."""
        self._open_settings()
        return "break"

    def _on_delete_key(self, _event=None) -> str | None:
        """Delete: remove the selected song when the table has the focus."""
        if not self._tree_has_focus():
            return None
        self._remove_selected()
        return "break"

    def _on_mute_key(self, _event=None) -> str | None:
        """M: mute or unmute, everywhere except in a text field."""
        if self._is_typing():
            return None
        self._on_volume_button()
        return "break"

    def _on_shuffle_key(self, _event=None) -> str | None:
        """S: turn shuffle on or off, everywhere except in a text field."""
        if self._is_typing():
            return None
        self._on_shuffle()
        return "break"

    def _on_repeat_key(self, _event=None) -> str | None:
        """R: cycle the repeat mode, everywhere except in a text field."""
        if self._is_typing():
            return None
        self._on_repeat()
        return "break"

    def _show_shortcuts(self) -> None:
        """Open the Keyboard shortcuts window, or bring it to the front when it is already open."""
        if self._shortcuts_window is not None and self._shortcuts_window.winfo_exists():
            self._shortcuts_window.lift()
            self._shortcuts_window.focus_set()
            return
        palette = theme.current_palette()
        window = tk.Toplevel(self.root)
        self._shortcuts_window = window
        window.title("Keyboard shortcuts")
        window.configure(bg=palette["bg"])
        window.resizable(False, False)
        window.transient(self.root)
        window.protocol("WM_DELETE_WINDOW", self._close_shortcuts)
        window.bind("<Escape>", lambda _event: self._close_shortcuts())

        # Two columns: the key on the left, the action on the right.
        frame = ttk.Frame(window, padding=PAD)
        frame.grid(row=0, column=0, sticky="nsew")
        ttk.Label(frame, text="KEYBOARD SHORTCUTS", style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, GAP)
        )
        for row, (key, action) in enumerate(SHORTCUTS, start=1):
            ttk.Label(frame, text=key, style="Section.TLabel").grid(
                row=row, column=0, sticky="w", padx=(0, PAD * 2), pady=2
            )
            ttk.Label(frame, text=action).grid(row=row, column=1, sticky="w", pady=2)

        # Place the window over the middle of the main one.
        window.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - window.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - window.winfo_height()) // 2
        window.geometry(f"+{max(0, x)}+{max(0, y)}")
        window.focus_set()

    def _close_shortcuts(self) -> None:
        """Close the Keyboard shortcuts window."""
        if self._shortcuts_window is not None and self._shortcuts_window.winfo_exists():
            self._shortcuts_window.destroy()
        self._shortcuts_window = None

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
        self._set_theme(other)

    def _open_settings(self) -> SettingsDialog:
        """Open the settings dialog over the main window and return it."""
        # The backend in use is the history one when it opened, otherwise the
        # choice saved in the settings.
        current = self.history.name if self.history is not None else str(
            self.settings["history_backend"]
        )
        return SettingsDialog(
            self.root,
            self.settings,
            current,
            on_apply_backend=self._switch_history,
            on_apply_theme=self._set_theme,
        )

    def _set_theme(self, name: str) -> None:
        """Apply a named theme, repaint the widgets and remember the choice."""
        theme.apply_theme(self.root, name)
        self._apply_palette()
        self.view_menu.entryconfigure(self.theme_entry, label=self._theme_menu_label())
        self.settings["theme"] = theme.current_theme()
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
            self.search_icon,
            self.clear_search_button,
        ):
            widget.apply_palette()
        # apply_palette() keeps the toggled flag, this redraws the active colour
        # and the repeat icon with the new palette.
        self._update_mode_buttons()
        # The search text follows the theme too, muted while the placeholder shows.
        self._style_search_entry()
        self.tree.tag_configure("playing", foreground=palette["accent"])
        # The shortcuts window, when open, follows the theme as well.
        if self._shortcuts_window is not None and self._shortcuts_window.winfo_exists():
            self._shortcuts_window.configure(bg=palette["bg"])
        # The statistics window, when open, follows the theme as well.
        if self._stats_window is not None and self._stats_window.winfo_exists():
            self._stats_window.apply_palette()

    def _on_close(self) -> None:
        """Cancel the timer, stop the music, save the whole session and close the window."""
        if self._closing:
            return
        self._closing = True
        if self._timer is not None:
            self.root.after_cancel(self._timer)
            self._timer = None
        if self.player is not None:
            self.player.stop()
        # Release the history backend; a failure here must not block the close.
        if self.history is not None:
            try:
                self.history.close()
            except Exception:
                pass
            self.history = None
        # The geometry is only worth keeping in the normal state, not minimised
        # or maximised.
        try:
            if self.root.state() == "normal":
                self.settings["window_geometry"] = self.root.geometry()
        except tk.TclError:
            pass
        self.settings["volume"] = self.volume_slider.fraction
        self.settings["muted"] = self._muted
        self.settings["shuffle"] = self.playlist.shuffle
        self.settings["repeat"] = self.playlist.repeat
        self.settings["theme"] = theme.current_theme()
        # Stores the songs and the selected one, then saves everything at once.
        self._remember_playlist()
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
