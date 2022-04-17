from tkinter import *
import pygame
from tkinter import filedialog

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

    # Loop thru song list and replace directory info and mp3
    for song in songs:
        global path
        song = song.replace(path, "")
        song = song.replace(".mp3", "")

        # Add the songs to the listbox
        song_box.insert(END, song)

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

    else:

        # Grab song title from playlist
        active_song = song_box.get(ACTIVE)
        # Add directory structure and mp3 to song title
        song = f'{path}{active_song}.mp3'

        # Load and play song
        pygame.mixer.music.load(song)
        pygame.mixer.music.play(loops = 0)

        # Set Playing Variable To True
        playing = True

# Stop playing current song
def stop():

    # Stop Song From Playing
    pygame.mixer.music.stop()
    song_box.selection_clear(ACTIVE)

    # Set Stop Variable To True
    global stopped
    stopped = True

    # Set Playing Variable To False
    global playing
    playing = False

# Create Master Frame
master_frame = Frame(root)
master_frame.pack(pady = 20, padx = 10)

# Create Playlist Box
song_box = Listbox(master_frame, bg = "black", fg = "green", width = 60, selectbackground = "gray", selectforeground = "black")
song_box.grid(row = 0, column = 0)

play_btn_img = PhotoImage(file = 'assets/images/play.png')
stop_btn_img = PhotoImage(file = 'assets/images/stop.png')

# Create Player Control Frame
controls_frame = Frame(master_frame)
controls_frame.grid(row = 2, column = 0)

play_button = Button(controls_frame, image = play_btn_img, borderwidth = 0, command = play)
stop_button = Button(controls_frame, image = stop_btn_img, borderwidth = 0, command = stop)

play_button.grid(row = 0, column = 2, padx = 7)
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

root.mainloop()
