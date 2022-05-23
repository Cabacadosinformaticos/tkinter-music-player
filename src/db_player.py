from tkinter import *
import pygame
from tkinter import filedialog
from tkinter import messagebox
import time
from mutagen.mp3 import MP3
import tkinter.ttk as ttk
from datetime import date, datetime
import mysql.connector
import pyodbc
import os
import configparser

# Create the program's Window
root = Tk()
root.title('Music Player')
root.iconbitmap('assets/images/icon.ico')
root.geometry("455x345")

# set minimum window size value
root.minsize(455, 345)
# set maximum window size value
root.maxsize(455, 345)

# Initialize Pygame Mixer
pygame.mixer.init()

# Creation of Global variables
# Create Global Playing Variable
global playing
playing = False

# Create Global active_song Variable
global active_song

# Create Global path Variable
global path
path = 'C:/Users/tiago/Downloads/Escola/P&A/PyCharm/Trabalhos no Python/Music Player (trabalho final de disciplina) (81744 - 81809)/Musicas/'

# Create Global Stopped Variable
global stopped
stopped = False

# Create Global Pause Variable
global paused
paused = False

# Absolute path to the config file, in the repo root (parent folder of src)
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'db_config.ini')

# Create Global Conn for the server connection, created on first use
global conn
conn = None

# Flag to avoid repeating the database warning while a song keeps playing
global db_warning_shown
db_warning_shown = False

# Create the connection to the database on first use
def get_connection():

    global conn

    # Reuse the connection if it was already created
    if conn is not None:
        return conn

    # Check that the config file exists
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError("Ficheiro db_config.ini não encontrado. Copie db_config.example.ini para db_config.ini e preencha os dados da base de dados.")

    # Read the database settings from the config file
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding = 'utf-8')
    db_config = config['database']

    # Read the required settings, a missing key is reported to the user
    try:
        driver = db_config['driver']
        server = db_config['server']
        database = db_config['database']
        user = db_config['user']
        password = db_config['password']
    except KeyError as error:
        raise KeyError("Chave em falta no ficheiro db_config.ini: %s" % error)

    # Build the connection string from the settings
    conn_str = 'DRIVER={%s};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s' % (driver, server, database, user, password)

    # Connect with a short timeout so the window does not lock up for long
    try:
        conn = pyodbc.connect(conn_str, timeout = 5)
    except pyodbc.Error as error:
        raise RuntimeError("Não foi possível ligar à base de dados: %s" % error)

    return conn

# Add Song Function
def add_song():

    song = filedialog.askopenfilename(initialdir = 'C:\\Users\tiago\Downloads\Escola\P&A\PyCharm\Trabalhos no Python\Music Player (trabalho final de disciplina) (81744 - 81809)\Musicas', title = "Selecione a música", filetypes = (("mp3 Files", "*.mp3"), ))

    # strip out the directory info and mp3 extension from the song name
    global path
    song = song.replace(path, "")
    song = song.replace(".mp3", "")

    # Add the song to listbox
    song_box.insert(END, song)

# Add many songs to playlist
def add_many_songs():

    songs = filedialog.askopenfilenames(initialdir = 'C:\\Users\tiago\Downloads\Escola\P&A\PyCharm\Trabalhos no Python\Music Player (trabalho final de disciplina) (81744 - 81809)\Musicas', title = "Selecione as musicas", filetypes = (("mp3 Files", "*.mp3"), ))

    # Loop through song list and replace directory info and mp3
    for song in songs:
        global path
        song = song.replace(path, "")
        song = song.replace(".mp3", "")

        # Add the songs to the listbox
        song_box.insert(END, song)

# Delete A Song
def delete_song():

    # Calls function stop to stop the music
    stop()

    # Delete Currently Selected Song
    song_box.delete(ANCHOR)

    # Stop Music if it's playing
    pygame.mixer.music.stop()

# Delete All Songs from Playlist
def delete_all_songs():

    # Calls function stop to stop the music
    stop()

    # Delete All Songs
    song_box.delete(0, END)

    # Stop Music if it's playing
    pygame.mixer.music.stop()

# Play selected song
def play():

    # Set Stopped Variable To False So Song Can Play
    global stopped
    stopped = False

    # Set Paused Variable To False So Song Can Play
    global paused
    paused = False

    # Get Playing Variable
    global playing

    # Saves the song title
    global active_song

    # Gets the music path
    global path

    if playing == True:

        # Reset Slider and Status Bar
        status_bar.config(text=' ')
        my_slider.config(value=0)

        # Get the current song tuple number
        active = song_box.curselection()

        # Stop Song From Playing
        pygame.mixer.music.stop()

        # Grab song title from playlist
        active_song = song_box.get(active)
        # Add directory structure and mp3 to song title
        song = f'{path}{active_song}.mp3'

        # Load and play song
        pygame.mixer.music.load(song)
        pygame.mixer.music.play(loops=0)

        # Calls the Recent Music function
        rec_music()

    else:
        # Reset Slider and Status Bar
        status_bar.config(text=' ')
        my_slider.config(value=0)

        # Grab song title from playlist
        active_song = song_box.get(ACTIVE)
        # Add directory structure and mp3 to song title
        song = f'{path}{active_song}.mp3'

        # Load and play song
        pygame.mixer.music.load(song)
        pygame.mixer.music.play(loops = 0)

        # Call the play_time function to get song lenght
        play_time()

        # Set Playing Variable To True
        playing = True

        # Calls the Recent Music function
        rec_music()

# Stop playing current song
def stop():

    # Reset Slider and Status Bar
    status_bar.config(text=' ')
    my_slider.config(value=0)

    # Stop Song From Playing
    pygame.mixer.music.stop()
    song_box.selection_clear(ACTIVE)

    # Clear The Status Bar
    status_bar.config(text = '')

    # Set Stop Variable To True
    global stopped
    stopped = True

    # Set Playing Variable To False
    global playing
    playing = False

# Play The Next Song in the playlist
def next_song():

    # Reset Slider and Status Bar
    status_bar.config(text=' ')
    my_slider.config(value=0)

    # Get the current song tuple number
    next_one = song_box.curselection()
    # Add one to the current song number
    next_one = next_one[0] + 1

    # Creation of variable max_lenght
    max_lenght = song_box.size() - 1

    # condition to prevent the function form an error
    if next_one > max_lenght:

        stop()

        return

    # Gets song title from global variable
    global active_song
    active_song = song_box.get(next_one)
    # Add directory structure and mp3 to song title
    song = f'{path}{active_song}.mp3'

    # Load and play song
    pygame.mixer.music.load(song)
    pygame.mixer.music.play(loops=0)

    # Move active bar in playlist listbox
    song_box.selection_clear(0, END)

    # Activate new song bar
    song_box.activate(next_one)

    # Set Active Bar to Next Song
    song_box.selection_set(next_one, last = None)

    # Calls the Recent Music function
    rec_music()

# Play Previous Song In Playlist
def previous_song():

    # Reset Slider and Status Bar
    status_bar.config(text=' ')
    my_slider.config(value=0)

    # Get the current song tuple number
    previous_one = song_box.curselection()
    # Subtract one to the current song number
    previous_one = previous_one[0] - 1

    # condition to prevent the function form an error
    if previous_one < 0:

        previous_one = previous_one + 1

    # Gets song title from global variable
    global active_song
    active_song = song_box.get(previous_one)
    # Add directory structure and mp3 to song title
    song = f'{path}{active_song}.mp3'

    # Load and play song
    pygame.mixer.music.load(song)
    pygame.mixer.music.play(loops=0)

    # Move active bar in playlist listbox
    song_box.selection_clear(0, END)

    # Activate new song bar
    song_box.activate(previous_one)

    # Set Active Bar to Previous Song
    song_box.selection_set(previous_one, last=None)

    # Calls the Recent Music function
    rec_music()

# Pause and Unpause The Current Song
def pause(is_paused):

    global paused
    paused = is_paused

    if paused:
        # Unpause
        pygame.mixer.music.unpause()
        paused = False
    else:
        # Pause
        pygame.mixer.music.pause()
        paused = True

# Create slider function
def slide(X):

    # Gets song title from variable
    global active_song
    # Add directory structure and mp3 to song title
    song = f'{path}{active_song}.mp3'

    # Loads the info to the slider
    pygame.mixer.music.load(song)
    pygame.mixer.music.play(loops=0, start = int(my_slider.get()))

# Grab Song Lenght and Time Info
def play_time():

    # Check for double timing
    if stopped:
        return

    # Grab Current Song Elapsed Time
    current_time = pygame.mixer.music.get_pos() / 1000

    # Gets song title from global variable
    global active_song
    # Add directory structure and mp3 to song title
    song = f'{path}{active_song}.mp3'

    # Get Song Length with Mutagen
    song_mut = MP3(song)

    # Get song Length
    global song_length
    song_length = song_mut.info.length

    # Convert to Time Format
    converted_song_length = time.strftime('%M:%S', time.gmtime(song_length))

    # Increase current time by 1 second
    current_time += 1

    # Funcion that rules the music time
    if int(my_slider.get()) == int(song_length):

        # Output time to status bar
        status_bar.config(text=f'Tempo de música: {converted_song_length} de {converted_song_length}    ')

        # Plays the next song if the actual song was ended
        next_song()

    elif paused:

        # If music pause, play-time pause ans slider pause too
        pass

    elif int(my_slider.get()) == int(current_time):

        # slider hasn't been moved

        # Update Slider To position
        slider_position = int(song_length)
        my_slider.config(to=slider_position, value=int(current_time))

    else:

        # slider HAS been moved!

        # Update Slider To position
        slider_position = int(song_length)
        my_slider.config(to=slider_position, value=int(my_slider.get()))

        # Convert to time format
        converted_current_time = time.strftime('%M:%S', time.gmtime(int(my_slider.get())))

        # Output time to status bar
        status_bar.config(text=f'Tempo de música: {converted_current_time} de {converted_song_length}    ')

        # Move this thing along by one second
        next_time = int(my_slider.get()) + 1
        my_slider.config(value = next_time)

    # update time
    status_bar.after(1000, play_time)

# Create Volume Function
def volume(X):

    # Sets the volume according to volume_slider position
    pygame.mixer.music.set_volume(volume_slider.get())

# Insert the played song info in the DB
def rec_music():

    # Gets song title from global variable
    global active_song

    # Grab the current date and time from a single reading
    now = datetime.now()
    # ISO formats, SQL Server converts them to DATE and TIME and they also sort as text
    current_time = now.strftime("%H:%M:%S")
    d1 = now.strftime("%Y-%m-%d")

    # Convert the variables to str()
    msg1 = str(active_song)
    msg2 = str(current_time)
    msg3 = str(d1)

    # Flag used to warn about the DB only once per failure
    global db_warning_shown

    # Inserts the data in the DB
    command = '''INSERT INTO music_history (Music_name, Music_time, Music_date) VALUES (?, ?, ?)'''
    val = (msg1, msg2, msg3)
    try:
        # Gets the connection with the DB
        global conn
        conn = get_connection()

        # Creates the cursor
        cursor = conn.cursor()
        cursor.execute(command, val)

        # Commit the transaction
        cursor.commit()
    except Exception as error:
        # The music must keep playing, warn only the first time
        if not db_warning_shown:
            messagebox.showwarning("Music Player", "Não foi possível guardar o histórico: %s" % error)
            db_warning_shown = True
        return

    # The write worked, allow a new warning if the DB fails again
    db_warning_shown = False

# Formats a DB value: date/time objects use the pattern, other types fall back to str()
def format_value(value, pattern):

    # pyodbc returns date and time objects, plain text columns return strings
    if hasattr(value, 'strftime'):
        return value.strftime(pattern)

    return str(value)

# Gets the song info from DB and displays it in the screen
def view_rec_songs():

    # Gets the connection with the DB before opening the window
    global conn
    try:
        conn = get_connection()
    except Exception as error:
        messagebox.showerror("Music Player", str(error))
        return

    # Toplevel object which will be treated as a new window
    New_window = Toplevel(root)

    # sets the title of the Toplevel widget
    New_window.title("Histórico de musicas")

    # sets the geometry of toplevel
    New_window.geometry("1050x450")

    # set minimum window size value
    New_window.minsize(1050, 450)
    # set maximum window size value
    New_window.maxsize(1050, 450)

    # A Label widget to show in toplevel
    Label(New_window, text="Histórico de musicas", padx=5, pady=5).pack()

    # Creation of the text area
    txtarea = Text(New_window, width=125, height=25)
    txtarea.pack(pady=0)

    # Gets the information from the DB
    command = '''SELECT Music_name, Music_time, Music_date FROM music_history ORDER BY Music_date, Music_time  ASC'''
    try:
        # Creates the cursor
        cursor = conn.cursor()
        cursor.execute(command)
        for row in cursor:

            # Creates the complete message, dates and times are formatted for display
            msg = "A musica %s foi ouvida ás %s, no dia %s\n" %(str(row.Music_name), format_value(row.Music_time, "%H:%M"), format_value(row.Music_date, "%d/%m/%Y"))

            # Writes the content in the text area
            txtarea.insert(END, msg)
    except pyodbc.Error as error:
        messagebox.showerror("Music Player", str(error))

    # Make the text area read-only
    txtarea.config(state = DISABLED)

# Delete the played song info from the DB
def delete_rec_songs():

    # Gets the connection with the DB
    global conn
    try:
        conn = get_connection()
    except Exception as error:
        messagebox.showerror("Music Player", str(error))
        return

    # Deletes the data from the table music_history
    command = '''DELETE FROM music_history'''
    try:
        # Creates the cursor
        cursor = conn.cursor()
        cursor.execute(command)

        # Commit the transaction
        cursor.commit()
    except pyodbc.Error as error:
        messagebox.showerror("Music Player", str(error))

# Create Master Frame
master_frame = Frame(root)
master_frame.pack(pady = 20, padx = 10)

# Create Playlist Box
song_box = Listbox(master_frame, bg = "black", fg = "green", width = 60, selectbackground = "gray", selectforeground = "black")
song_box.grid(row = 0, column = 0)

# Create Player Control Buttons
back_btn_img = PhotoImage(file = 'assets/images/previous.png')
forward_btn_img = PhotoImage(file = 'assets/images/next.png')
play_btn_img = PhotoImage(file = 'assets/images/play.png')
pause_btn_img = PhotoImage(file = 'assets/images/pause.png')
stop_btn_img = PhotoImage(file = 'assets/images/stop.png')

# Create Player Control Frame
controls_frame = Frame(master_frame)
controls_frame.grid(row = 2, column = 0)

# Create Player Control Buttons
back_button = Button(controls_frame, image = back_btn_img, borderwidth = 0, command = previous_song)
forward_button = Button(controls_frame, image = forward_btn_img, borderwidth = 0, command = next_song)
play_button = Button(controls_frame, image = play_btn_img, borderwidth = 0, command = play)
pause_button = Button(controls_frame, image = pause_btn_img, borderwidth = 0, command = lambda: pause(paused))
stop_button = Button(controls_frame, image = stop_btn_img, borderwidth = 0, command = stop)

back_button.grid(row = 0, column = 0, padx = 7)
forward_button.grid(row = 0, column = 4, padx = 7)
play_button.grid(row = 0, column = 2, padx = 7)
pause_button.grid(row = 0, column = 3, padx = 7)
stop_button.grid(row = 0, column = 1, padx = 7)

# Create Menu
my_menu = Menu(root)
root.config(menu = my_menu)

# Create Add Song Menu
add_song_menu = Menu(my_menu, tearoff=0)
my_menu.add_cascade(label = "Adicionar musicas", menu = add_song_menu)
add_song_menu.add_command(label = "Adicionar uma música", command = add_song)
# Add Many Songs to playlist
add_song_menu.add_command(label = "Adicionar várias musicas", command = add_many_songs)

# Create Delete Song Menu
remove_song_menu = Menu(my_menu, tearoff=0)
my_menu.add_cascade(label = "Eliminar musicas", menu = remove_song_menu)
remove_song_menu.add_command(label = "Eliminar uma música", command = delete_song)
remove_song_menu.add_command(label = "Eliminar todas as musicas", command = delete_all_songs)

# Create Historic Song Menu
historic_songs_menu = Menu(my_menu, tearoff=0)
my_menu.add_cascade(label = "Histórico de musicas", menu = historic_songs_menu)
historic_songs_menu.add_command(label = "Ver histórico de musicas", command = view_rec_songs)
historic_songs_menu.add_separator()
historic_songs_menu.add_command(label = "Eliminar histórico de musicas", command = delete_rec_songs)

# Create Music Position Slider
my_slider = ttk.Scale(master_frame, from_ = 0, to = 100, orient = HORIZONTAL, value = 0, command = slide, length = 360)
my_slider.grid(row = 1, column = 0, pady = 20)

# Create Volume Label Frame
volume_frame = LabelFrame(master_frame, text = 'Volume')
volume_frame.grid(row = 0, column = 1, padx = 15)

# Create Volume Slider
volume_slider = ttk.Scale(volume_frame, from_ = 1, to = 0, orient = VERTICAL, value = 1, command = volume, length = 125)
volume_slider.pack(pady = 10)

# Create Status Bar
status_bar = Label(root, text = '', bd = 1, relief = GROOVE, anchor = CENTER)
status_bar.pack(fill = X, side = BOTTOM, ipady = 2)

root.mainloop()