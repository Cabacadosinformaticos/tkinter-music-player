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

# Play The Next Song in the playlist
def next_song():

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

    # Grab song title from playlist
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

# Play Previous Song In Playlist
def previous_song():

    # Get the current song tuple number
    previous_one = song_box.curselection()
    # Subtract one to the current song number
    previous_one = previous_one[0] - 1

    # condition to prevent the function form an error
    if previous_one < 0:

        previous_one = previous_one + 1

    # Grab song title from playlist
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

# Create Volume Function
def volume(X):

    # Sets the volume according to volume_slider position
    pygame.mixer.music.set_volume(volume_slider.get())

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

# Create Volume Label Frame
volume_frame = LabelFrame(master_frame, text = 'Volume')
volume_frame.grid(row = 0, column = 1, padx = 15)

volume_slider.pack(pady = 10)

root.mainloop()
