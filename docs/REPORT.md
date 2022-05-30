# Music Player - Project Report

Programação Avançada (Advanced Programming), CTeSP in Informatics, AESM - Academia de Ensino Superior de Mafra, 2nd semester, academic year 2021/2022.

Authors: Tiago Cabaça (81744) and Francisco Diniz (81809).

The Portuguese report is in this folder as `Relatório de Projeto (81744 - 81809).docx`. This file is an English version that also describes what the final code does.

## 1. Goals

The goal is a Python application for the Advanced Programming course. The assignment requires the program to use local files (images and music) and a connection to a database that stores data produced and used by the program. The project also has to show what we learned during the course.

We build a music player with a graphical interface. We deliver two versions of it:

- a local version, where the play history is kept in a text file;
- a database version, where the play history is kept in a SQL Server table.

## 2. Requirements

| Requirement | Where it is met |
|---|---|
| Graphical interface | tkinter window with a playlist, buttons, sliders and menus |
| Local files | PNG and ICO images in `assets/images`, MP3 files chosen by the user |
| Database connection | `src/db_player.py` with pyodbc and SQL Server |
| Play audio | pygame mixer |
| Read the length of a song | mutagen |

Functional requirements: add and remove songs, play, pause, stop, next, previous, seek with a slider, control the volume, record and list the play history, and clear it.

## 3. Approach and tools

We split the work between the two members and then researched the libraries and the SQL we needed. The program is built part by part, function by function, with a mix of research and trial and error. The methods we use are: building one part at a time, searching for information, trial and error and trying alternative approaches.

Tools: Python with the PyCharm IDE, SQL Server Management Studio to manage the database, and MySQL Workbench for some internal tests with the database.

## 4. Architecture

Each version is a single script. The interface is created at module level and the functions are connected to the widgets as commands.

```
tkinter window
|-- Listbox (playlist, shows names)      <-> playlist list (full paths)
|-- Buttons: previous, stop, play, pause, next
|-- ttk.Scale: song position             -> slide() on release
|-- ttk.Scale: volume                    -> volume()
|-- Status bar                           <- play_time() every second
`-- Menus: add songs, remove songs, play history
         |
         v
pygame.mixer.music (playback)     mutagen (song length)
         |
         v
rec_music() -> recent_songs.txt   or   music_history table (SQL Server)
```

### Libraries

| Library | Use |
|---|---|
| tkinter | graphical interface |
| pygame | audio playback |
| time | time conversions |
| mutagen | length of the song |
| datetime | current date and time |
| pyodbc | database connection (database version only) |
| os, configparser | paths relative to the project and reading `db_config.ini` |

### Project layout

The scripts live in `src`, the images in `assets/images`, the personal MP3 files in `music` (not part of the repository), the table definition in `sql` and the documents in `docs`. All paths are built from the location of the script, so the program runs from any folder.

## 5. Implementation

### Functions

| Function | What it does |
|---|---|
| `add_to_playlist()` | stores the full path of a song and shows its name in the listbox |
| `add_song()` | adds one song chosen in a file dialog |
| `add_many_songs()` | adds several songs chosen in a file dialog |
| `delete_song()` | removes the selected song |
| `delete_all_songs()` | removes all songs |
| `play()` | plays the selected song (or the first one) |
| `stop()` | stops the music and the timer |
| `next_song()` | plays the next song, or stops after the last one |
| `previous_song()` | plays the previous song |
| `pause()` | pauses and resumes the music |
| `slide()` | jumps to the position where the slider was released |
| `start_play_time()` and `play_time()` | cancel any old timer, then update the slider and the status bar every second and go to the next song when one ends |
| `volume()` | sets the volume from the volume slider |
| `rec_music()` | records the song that started playing in the history |
| `view_rec_songs()` | shows the history in a read-only window |
| `delete_rec_songs()` | clears the history |
| `get_connection()` (database version) | reads `db_config.ini` and connects the first time the database is needed |
| `format_value()` (database version) | formats dates and times read from the table |

### Playlist

The listbox shows only the file name without the extension. The full path of each song is kept in a list in the same order, so songs from any folder can be played.

### Progress and time

pygame does not report the position inside a song directly, so `play_time()` runs once per second, reads the elapsed time, moves the slider and writes "Song time: mm:ss of mm:ss" in the status bar. A single timer exists at any moment: its id is stored and cancelled before a new one starts. The slider seeks only when the user releases it, so the updates made by the program never restart the song.

### Play history

Local version: each line says which song was played, at what time and on what date, and is appended to `recent_songs.txt` (UTF-8).

Database version: one row is inserted in `music_history`. The date and time are stored as ISO values, so the table sorts correctly by date and time. The connection settings are read from `db_config.ini`, which is not part of the repository; `db_config.example.ini` shows the format. If the database cannot be reached, the program still starts and plays, and shows a message explaining that the history was not saved.

## 6. Data

The database version uses one table, created by `sql/create_music_history.sql`:

| Column | Type | Description |
|---|---|---|
| Id | INT IDENTITY, primary key | row number |
| Music_name | NVARCHAR(255) | name of the song |
| Music_date | DATE | day the song started |
| Music_time | TIME(0) | time of day the song started |

The history window lists the rows ordered by `Music_date` and `Music_time`.

## 7. Testing

We test the program by hand with a set of MP3 files:

- adding one and many songs, removing the selected song and all songs;
- play, pause, stop, next and previous, including the first and the last song of the playlist and an empty playlist;
- moving the slider while playing and while paused;
- changing the volume;
- letting a song end, which starts the next one;
- viewing and clearing the history;
- in the database version, running with a valid configuration and with a wrong one.

Both scripts are also compiled with `python -m py_compile` to catch syntax errors.

## 8. Difficulties

The difficulties come from pieces of code that do not work and from libraries that do not behave as expected. We overcome them by searching for solutions in programming forums and by following tutorials on the topics involved. Tracking the position of the song is the hardest part, because the mixer only reports the time since playback started. Keeping the timer, the slider and the next-song logic consistent also takes several attempts.

## 9. Conclusion

This project is not an isolated exercise: it is the result of the work done during the second semester of the Informatics course. It gives us knowledge that we take into our professional and personal lives, and we are very satisfied with what we built together.
