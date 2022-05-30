# Music Player

This is our project for the Advanced Programming (Programação Avançada) course. It is a desktop music player written in Python with tkinter for the window and pygame for the audio. It comes in two versions: a local one that keeps the play history in a text file, and a database one that keeps it in a SQL Server table.

## Features

- Playlist with the file names of the songs; MP3 files can come from any folder.
- Add one or many songs, remove the selected song or the whole playlist.
- Play, pause, stop, next and previous buttons.
- Progress slider that shows the position and lets you jump inside the song, plus the elapsed time in the status bar.
- Volume slider.
- Play history: every song that starts is recorded with its time and date; the history can be viewed in a read-only window and cleared.
- The next song starts automatically when one ends.

## Requirements

- Python 3.8 or newer with tkinter (included in the standard Windows installer).
- The libraries in `requirements.txt`: `pygame`, `mutagen` and `pyodbc` (only the database version needs `pyodbc`).
- For the database version: a SQL Server database and an ODBC driver installed on the computer.

## Setup

```
pip install -r requirements.txt
```

Put some MP3 files in the `music/` folder (optional, the file dialog can open any folder).

### Database version

1. Run `sql/create_music_history.sql` on your database to create the `music_history` table.
2. Copy `db_config.example.ini` to `db_config.ini` and fill in the driver, server, database, user and password. `db_config.ini` is ignored by git, so the credentials stay on your computer.

## Run

```
python src/local_player.py
python src/db_player.py
```

The database version opens even if the database cannot be reached: the music plays and a message explains why the history is not saved.

## Project structure

```
tkinter-music-player/
|-- src/
|   |-- local_player.py          local version (history in recent_songs.txt)
|   `-- db_player.py             database version (history in SQL Server)
|-- assets/images/               window icon and button images
|-- music/                       put your own MP3 files here (ignored by git)
|-- sql/create_music_history.sql table used by the database version
|-- docs/
|   |-- Relatório de Projeto (81744 - 81809).docx   project report
|   `-- REPORT.md                                   English report
|-- db_config.example.ini        template for the database settings
`-- requirements.txt
```

## How it works

- `pygame.mixer.music` loads and plays the selected MP3 file; `mutagen` reads the length of the song.
- The listbox shows the song names, while the full file paths are kept in a separate list in the same order.
- `play_time()` runs once per second (through `after`) to move the slider and update the status bar; only one timer runs at a time.
- When a song starts, `rec_music()` writes one line to `recent_songs.txt` (local version) or inserts a row in `music_history` (database version).
- The database connection is created the first time it is needed, from the settings in `db_config.ini`.

## Team

- Tiago Cabaça (81744)
- Francisco Diniz (81809)

## Course

Programação Avançada (Advanced Programming), 2nd semester of the CTeSP (Curso Técnico Superior Profissional) in Informatics at AESM, Academia de Ensino Superior de Mafra, academic year 2021/2022.

## Documentation

The project report is in the `docs` folder: the Portuguese Word document and an English version in [docs/REPORT.md](docs/REPORT.md).
