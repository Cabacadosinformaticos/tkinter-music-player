# Music Player - Project Report

Programação Avançada (Advanced Programming), CTeSP in Informatics, AESM - Academia de Ensino Superior de Mafra, 2nd semester, academic year 2021/2022.

Authors: Tiago Cabaça (81744) and Francisco Diniz (81809).

The Portuguese report is in this folder as `Relatório de Projeto (81744 - 81809).docx`. This file is an English version that describes what the final code does.

## 1. Goals

The goal is a Python application for the Advanced Programming course. The assignment requires the program to use local files (images and music) and a connection to a database that stores data produced and used by the program. The project also has to show what we learned during the course.

We build a music player with a graphical interface that looks like the players people use every day. It plays the songs of a playlist, shows the tags and the cover art of the song that is playing and keeps a history of what was played. The history can be stored in a SQLite database, in a text file or in a SQL Server table, and a statistics window draws charts from it.

## 2. Requirements

| Requirement | Where it is met |
|---|---|
| Graphical interface | tkinter window with the Sun Valley ttk theme, canvas buttons, sliders and charts, dark and light themes |
| Local files | MP3, WAV, OGG, FLAC and M4A songs chosen by the user, cover pictures read from the tags, M3U playlists, the JSON settings file and the window icon |
| Database connection | `src/music_player/history/`: SQLite (default) and SQL Server with pyodbc, plus a text file |
| Play audio | pygame mixer |
| Read tags and the length of a song | mutagen |

Functional requirements: add and remove songs, play, pause, stop, next, previous, seek with a slider, control the volume and mute, play the next song automatically, shuffle and repeat, search the playlist, save and open playlists, remember the session, record and list the play history, clear it and show statistics about it.

## 3. Approach and tools

We split the work between the two members and researched the libraries and the SQL we needed. The first version of the program was one script per history type, built part by part, function by function, with a mix of research and trial and error. In the final version the two scripts are merged into one application, organised in modules, so that the player code exists only once and the history is a replaceable part.

Tools: Python with the PyCharm IDE, SQL Server Management Studio to manage the database, pytest for the automated tests and GitHub Actions to run them.

## 4. Architecture

The program is a package, `music_player`, in the `src` folder. `run.py` starts it.

```
PlayerApp (app.py)  <- main window, owns everything below
|-- theme.py, widgets.py        theme, IconButton, Slider, CoverArt
|-- Playlist (playlist.py)      songs, current song, shuffle, repeat, filter
|-- AudioPlayer (player.py)     state and position over pygame.mixer.music
|-- metadata.py                 tags and cover art (mutagen)
|-- m3u.py                      playlist files
|-- Settings (config.py)        data/settings.json
|-- HistoryBackend (history/)   text file | SQLite | SQL Server
|-- history_window.py           list of plays
|-- stats_window.py             charts (uses history/stats.py)
`-- settings_dialog.py          choose the storage and the theme
```

### Libraries

| Library | Use |
|---|---|
| tkinter | graphical interface |
| sv-ttk | Sun Valley ttk theme, dark and light |
| pygame | audio playback |
| mutagen | tags, cover art and the length of the song |
| Pillow | cover pictures: crop, resize and rounded corners |
| sqlite3 | default history (standard library) |
| pyodbc | SQL Server history (loaded only when it is used) |
| configparser, json, pathlib | `db_config.ini`, the settings file and the paths |
| pytest | automated tests |

### Project layout

The package is in `src/music_player`, the tests in `tests`, the window icon in `assets/images`, the personal MP3 files in `music` (not part of the repository), the table definition in `sql`, the screenshots and the reports in `docs`. The settings, the SQLite database and the text history are written to the `data` folder, which git ignores. The paths are built from the location of the code, so the program runs from any folder.

## 5. Implementation

### Window

The window has two columns that grow with it. The left one shows the now playing panel: the cover (it scales between 200 and 420 pixels with the column), the title, the artist, the album, the seek bar with the elapsed and total time, the buttons and the volume. The right one shows the playlist table, a search box and the buttons to add and remove songs. The buttons, the sliders and the cover are drawn on canvases, so they have the same look in both themes and react to the mouse (hover and pressed states). A palette per theme gives every widget its colours, and changing the theme redraws them without restarting.

### Playback

`AudioPlayer` hides `pygame.mixer.music` behind a small interface (`play`, `pause`, `resume`, `stop`, `seek`, `position`, `finished`). pygame reports only the time since the last `play()` call and does not count the time spent paused, so the player stores the start offset of the last seek and the position at the moment of the pause. A timer started with `after` runs five times per second, moves the seek bar, updates the times and asks the player whether the song ended; a single timer exists at any moment and it is cancelled when the window closes. The seek bar seeks only when the user releases it.

### Playlist

`Playlist` keeps the songs, the current song, the repeat mode (off, all, one) and the shuffle flag. `advance(auto)` gives the next song: when a song ends by itself, repeat one plays it again; when the user presses next, repeat one behaves like repeat all. With shuffle on, the playlist walks a shuffled order that contains every song once, and it builds a new one at the end when repeat is on. `previous()` walks back through the songs that were played. `filter(query)` returns the songs where every word of the query is in the title, the artist or the album; the window shows only those rows but keeps the real position of each song. Playlists are saved and opened as extended M3U files (`m3u.py`), with paths relative to the file when possible.

### Tags and cover art

`read_track` reads the title, artist, album and length with mutagen and falls back to the file name for files without tags. `read_cover` returns the embedded picture (ID3 APIC, FLAC pictures or MP4 covr). `CoverArt` crops it to a square, resizes it and rounds the corners with Pillow; without a picture it draws a generated cover in the accent colour.

### Settings and session

`Settings` reads and writes `data/settings.json`. A missing or damaged file gives the defaults and values of the wrong type are replaced one by one. The file stores the theme, the history storage, the volume, mute, shuffle, repeat, the last playlist and selected song, the folder of the file dialog and the window geometry, and it is written atomically.

### Play history

All backends implement `HistoryBackend`: `record`, `entries` (newest first), `clear`, `close` and `describe`. When a song starts, `PlayerApp` records its name and length; if the storage fails, the program warns once and keeps playing.

- Text file: one line per play with the date and time in ISO format, the length and the title, separated by tabs, in UTF-8.
- SQLite (default): the `plays` table in `data/history.db`.
- SQL Server: the `music_history` table. The connection settings are read from `db_config.ini`, which is not part of the repository; `db_config.example.ini` shows the format. The connection is opened the first time it is needed with a short timeout, the table is created when it is missing and `pyodbc` is imported only at that moment.

The settings dialog switches the storage while the program runs. If the new storage cannot be opened, the old one stays and the error is shown.

### Statistics

`history/stats.py` has three plain functions over the list of plays: `top_songs`, `listening_by_day` (a continuous range of days, with zero for the days without music) and `total_listening_seconds`. The statistics window shows the number of plays, the total listening time and the number of different songs in three cards, a bar chart with the most played songs and a bar chart with the listening time of the last 14 days. The charts are drawn on canvases and follow the size of the window.

### Keyboard

Space, the arrows, M, S, R, Ctrl+O, Ctrl+Shift+O, Ctrl+F, Delete and Ctrl+comma are shortcuts for the common actions. They do not fire while the user types in the search box, and Help, Keyboard shortcuts lists them.

## 6. Data

The SQL Server history uses one table, created by the program or by `sql/create_music_history.sql`:

| Column | Type | Description |
|---|---|---|
| Id | INT IDENTITY, primary key | row number |
| Music_name | NVARCHAR(255) | name of the song (artist and title) |
| Music_date | DATE | day the song started |
| Music_time | TIME(0) | time of day the song started |
| Duration_seconds | INT, null allowed | length of the song, used by the statistics |

The SQLite table `plays` has the same information: `id`, `title`, `played_at` (ISO date and time, so it sorts correctly) and `duration`.

## 7. Testing

The tests are written with pytest and need no display, no sound card and no database server. They cover:

- the playlist: next, previous, shuffle (every song once per round), repeat, filter and removal while a song is current;
- M3U files: round trip, relative paths, byte order mark, plain files without `EXTINF` lines, dashes inside titles;
- the tag reader, with WAV files generated in the test;
- the settings file: defaults, damaged files, invalid values and atomic saving;
- the audio player, with a fake mixer and a fake clock: states, position, seek, end of song, errors;
- the three history backends (the SQL Server one through a fake connection), the factory and the statistics;
- the numbers shown by the statistics window.

The workflow in `.github/workflows/ci.yml` compiles every Python file and runs the tests on every push.

The graphical part is tested by hand with a set of MP3 files: adding songs and folders, play, pause, stop, next and previous (including the first and the last song and an empty playlist), seeking while playing and while paused, volume and mute, songs that end by themselves with every repeat and shuffle combination, the search box, M3U playlists, closing and reopening the program, both themes and resizing the window, and the history storages including a wrong SQL Server configuration.

## 8. Difficulties

The difficulties come from libraries that do not behave as expected, and we overcome them by searching for solutions in programming forums and by following tutorials on the topics involved. Tracking the position of the song is the hardest part, because the mixer only reports the time since playback started, not the position in the file, and it starts counting from zero after a seek. Keeping the timer, the seek bar and the next-song logic consistent also takes several attempts. Other difficulties are the filtered playlist (the rows keep the real position of each song so that play, remove and next still work), switching the theme while the window is open and drawing sharp icons and charts with canvases.

## 9. Conclusion

This project is not an isolated exercise: it is the result of the work done during the second semester of the Informatics course. We go from two simple scripts to one application with a modern look, a replaceable history storage, statistics and automated tests. It gives us knowledge that we take into our professional and personal lives, and we are very satisfied with what we built together.
