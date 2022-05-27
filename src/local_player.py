from tkinter import *
import pygame
from tkinter import filedialog
from tkinter import messagebox
import time
from mutagen.mp3 import MP3
import tkinter.ttk as ttk
from datetime import date, datetime
import os

# Repository root folder is the parent folder of this script's folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Folders and files used by the program
IMAGES_DIR = os.path.join(BASE_DIR, 'assets', 'images')
# Default folder shown when the file dialog opens
MUSIC_DIR = os.path.join(BASE_DIR, 'music').replace('\\', '/')
HISTORY_FILE = os.path.join(BASE_DIR, 'recent_songs.txt')

# Create the program's Window
root = Tk()
root.title('Music Player')
root.iconbitmap(os.path.join(IMAGES_DIR, 'icon.ico'))
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
active_song = ''

# Create Global active_path Variable
global active_path
active_path = ''

# Full file path of each listbox item, same order as the listbox
global playlist
playlist = []

# Create Global Stopped Variable
global stopped
stopped = False

# Create Global Pause Variable
global paused
paused = False

# Id of the pending play_time timer, None when no timer is waiting
global time_job
time_job = None

# Add a full path to the playlist list and to the listbox
def add_to_playlist(file_path):

    # Do nothing when the dialog was cancelled
    if file_path == '':
        return

    # Save the full path so the song can be loaded later
    playlist.append(file_path)

    # Show only the file name without extension in the listbox
    song_name = os.path.splitext(os.path.basename(file_path))[0]
    song_box.insert(END, song_name)

# Add Song Function
def add_song():

    song = filedialog.askopenfilename(initialdir = MUSIC_DIR, title = "Select a song", filetypes = (("MP3 files", "*.mp3"), ))

    # Add the song to the playlist
    add_to_playlist(song)

# Add many songs to playlist
def add_many_songs():

    songs = filedialog.askopenfilenames(initialdir = MUSIC_DIR, title = "Select songs", filetypes = (("MP3 files", "*.mp3"), ))

    # Loop through the song list and add each one
    for song in songs:
        add_to_playlist(song)

# Delete A Song
def delete_song():

    # Get the selected song index, do nothing if nothing is selected
    selected = song_box.curselection()

    if selected == ():
        return

    # Calls function stop to stop the music
    stop()

    # Delete Currently Selected Song from the listbox and the playlist
    song_box.delete(selected[0])
    del playlist[selected[0]]

    # Stop Music if it's playing
    pygame.mixer.music.stop()

# Delete All Songs from Playlist
def delete_all_songs():

    # Calls function stop to stop the music
    stop()

    # Delete All Songs
    song_box.delete(0, END)

    # Clear the playlist list
    playlist.clear()

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

    # Gets the music full path
    global active_path

    # Do nothing when there is nothing to play
    if song_box.size() == 0:
        messagebox.showinfo("Music Player", "The playlist is empty")
        return

    # Use the selected song, or the first one when nothing is selected
    selected = song_box.curselection()

    if selected == ():
        index = 0
        song_box.selection_set(index)
    else:
        index = selected[0]

    if playing == True:

        # Reset Slider and Status Bar
        status_bar.config(text=' ')
        my_slider.config(value=0)

        # Stop Song From Playing
        pygame.mixer.music.stop()

        # Grab song title from playlist
        active_song = song_box.get(index)
        # Grab the full path of the selected song
        active_path = playlist[index]

        # Load and play song
        pygame.mixer.music.load(active_path)
        pygame.mixer.music.play(loops=0)

        # Start a single timer loop for the new song
        start_play_time()

        # Calls the Recent Music function
        rec_music()

    else:
        # Reset Slider and Status Bar
        status_bar.config(text=' ')
        my_slider.config(value=0)

        # Grab song title from playlist
        active_song = song_box.get(index)
        # Grab the full path of the selected song
        active_path = playlist[index]

        # Load and play song
        pygame.mixer.music.load(active_path)
        pygame.mixer.music.play(loops = 0)

        # Start a single timer loop for the new song
        start_play_time()

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

    # Clear The Status Bar
    status_bar.config(text = '')

    # Cancel the pending timer so no old loop keeps running
    global time_job

    if time_job is not None:
        status_bar.after_cancel(time_job)
        time_job = None

    # Set Stop Variable To True
    global stopped
    stopped = True

    # Set Playing Variable To False
    global playing
    playing = False

# Play The Next Song in the playlist
def next_song():

    # Do nothing when the playlist is empty
    if song_box.size() == 0:
        return

    # Reset Slider and Status Bar
    status_bar.config(text=' ')
    my_slider.config(value=0)

    # Get the current song number, start at the first song when nothing is selected
    selected = song_box.curselection()

    if selected == ():
        next_one = 0
    else:
        # Add one to the current song number
        next_one = selected[0] + 1

    # Creation of variable max_length
    max_length = song_box.size() - 1

    # condition to prevent the function from an error
    if next_one > max_length:

        stop()

        return

    # Grab song title from playlist
    global active_song
    active_song = song_box.get(next_one)
    # Grab the full path of the next song
    global active_path
    active_path = playlist[next_one]

    # Load and play song
    pygame.mixer.music.load(active_path)
    pygame.mixer.music.play(loops=0)

    # Start a single timer loop for the new song
    start_play_time()

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
    # Do nothing when the playlist is empty
    if song_box.size() == 0:
        return

    # Reset Slider and Status Bar
    status_bar.config(text=' ')
    my_slider.config(value=0)

    # Get the current song number, use the first song when nothing is selected
    selected = song_box.curselection()

    if selected == ():
        previous_one = 0
    else:
        # Subtract one to the current song number
        previous_one = selected[0] - 1

    # condition to prevent the function from an error
    if previous_one < 0:

        previous_one = 0

    # Grab song title from playlist
    global active_song
    active_song = song_box.get(previous_one)
    # Grab the full path of the previous song
    global active_path
    active_path = playlist[previous_one]

    # Load and play song
    pygame.mixer.music.load(active_path)
    pygame.mixer.music.play(loops=0)

    # Start a single timer loop for the new song
    start_play_time()

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

    # Do nothing when no song is playing
    if playing == False:
        return

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
def slide(event):

    # Do nothing when no song was ever loaded
    if playing == False:
        return

    # Gets the song full path from the global variable
    global active_path

    # Do nothing when there is no active song path
    if active_path == '':
        return

    # Loads the info to the slider
    pygame.mixer.music.load(active_path)
    pygame.mixer.music.play(loops=0, start = int(my_slider.get()))

    # Keep the song paused when it was paused before the seek
    if paused:
        pygame.mixer.music.pause()

# Cancel any pending timer and start a fresh play_time loop
def start_play_time():

    global time_job

    if time_job is not None:
        status_bar.after_cancel(time_job)
        time_job = None

    play_time()

# Grab Song Length Time Info
def play_time():

    # Check for double timing
    if stopped:
        return

    # Grab Current Song Elapsed Time
    current_time = pygame.mixer.music.get_pos() / 1000

    # Gets the song full path from the global variable
    global active_path

    # Get Song Length with Mutagen
    try:
        song_mut = MP3(active_path)
    except Exception:
        # The file could not be read, warn once and stop
        messagebox.showerror("Music Player", "Could not read the music file")
        stop()
        return

    # Get song Length
    global song_length
    song_length = song_mut.info.length

    # Convert to Time Format
    converted_song_length = time.strftime('%M:%S', time.gmtime(song_length))

    # Increase current time by 1 second
    current_time += 1

    # Function that rules the music time
    if int(my_slider.get()) == int(song_length):

        # Output time to status bar
        status_bar.config(text=f'Song time: {converted_song_length} of {converted_song_length}    ')

        # Play the next song if the actual song was ended
        next_song()

        # next_song already started its own timer, so this loop must end here
        return

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
        status_bar.config(text=f'Song time: {converted_current_time} of {converted_song_length}    ')

        # Move the slider along by one second
        next_time = int(my_slider.get()) + 1
        my_slider.config(value = next_time)

    # update time, keep the job id so it can be cancelled later
    global time_job
    time_job = status_bar.after(1000, play_time)

# Create Volume Function
def volume(X):

    # Sets the volume according to volume_slider position
    pygame.mixer.music.set_volume(volume_slider.get())

# Insert the played song info in the txt file
def rec_music():

    # Gets song title from global variable
    global active_song

    # Grab Current Time
    now = datetime.now()
    current_time = now.strftime("%H:%M")

    # Grab Current Date
    today = date.today()
    # dd/mm/YY
    d1 = today.strftime("%d/%m/%Y")

    # Convert the variables to str()
    msg1 = str(active_song)
    msg2 = str(current_time)
    msg3 = str(d1)

    # Opens the file in append mode and writes the message in the file
    with open(HISTORY_FILE, 'a', encoding='utf-8') as file:
        file.write("The song %s was played at %s on %s\n" %(msg1, msg2, msg3))

# Gets the song info from txt file and displays it in the screen
def view_rec_songs():

    # Toplevel object which will be treated as a new window
    New_window = Toplevel(root)

    # sets the title of the Toplevel widget
    New_window.title("Play history")

    # sets the geometry of toplevel
    New_window.geometry("1050x450")

    # set minimum window size value
    New_window.minsize(1050, 450)
    # set maximum window size value
    New_window.maxsize(1050, 450)

    # A Label widget to show in toplevel
    Label(New_window, text="Play history", padx=5, pady=5).pack()

    # Creation of the text area
    txtarea = Text(New_window, width=125, height=25)
    txtarea.pack(side=LEFT, pady=0)

    # Vertical scrollbar for the text area
    scrollbar = Scrollbar(New_window, command=txtarea.yview)
    scrollbar.pack(side=RIGHT, fill=Y)

    # Link the text area to the scrollbar
    txtarea.config(yscrollcommand=scrollbar.set)

    # Show the history when the file exists, a message when nothing was played
    if os.path.exists(HISTORY_FILE):
        # Opens the file with reading permission and reads the content
        with open(HISTORY_FILE, 'r', encoding='utf-8') as reader:
            msg = reader.read()

        # Writes the content in the text area
        txtarea.insert(END, msg)
    else:
        txtarea.insert(END, "There are no songs in the history yet")

    # Make the text area read only
    txtarea.config(state=DISABLED)

# Delete the played song info from the txt file
def delete_rec_songs():

    # Opens the file with writing permission, this truncates it
    with open(HISTORY_FILE, 'w', encoding='utf-8'):
        pass

# Create Master Frame
master_frame = Frame(root)
master_frame.pack(pady = 20, padx = 10)

# Create Playlist Box
song_box = Listbox(master_frame, bg = "black", fg = "green", width = 60, selectbackground = "gray", selectforeground = "black", exportselection = False)
song_box.grid(row = 0, column = 0)

# Create Player Control Buttons
back_btn_img = PhotoImage(file = os.path.join(IMAGES_DIR, 'previous.png'))
forward_btn_img = PhotoImage(file = os.path.join(IMAGES_DIR, 'next.png'))
play_btn_img = PhotoImage(file = os.path.join(IMAGES_DIR, 'play.png'))
pause_btn_img = PhotoImage(file = os.path.join(IMAGES_DIR, 'pause.png'))
stop_btn_img = PhotoImage(file = os.path.join(IMAGES_DIR, 'stop.png'))

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
my_menu.add_cascade(label = "Add songs", menu = add_song_menu)
add_song_menu.add_command(label = "Add one song", command = add_song)
# Add Many Songs to playlist
add_song_menu.add_command(label = "Add many songs", command = add_many_songs)

# Create Delete Song Menu
remove_song_menu = Menu(my_menu, tearoff=0)
my_menu.add_cascade(label = "Remove songs", menu = remove_song_menu)
remove_song_menu.add_command(label = "Remove selected song", command = delete_song)
remove_song_menu.add_command(label = "Remove all songs", command = delete_all_songs)

# Create Historic Song Menu
historic_songs_menu = Menu(my_menu, tearoff=0)
my_menu.add_cascade(label = "Play history", menu = historic_songs_menu)
historic_songs_menu.add_command(label = "View play history", command = view_rec_songs)
historic_songs_menu.add_separator()
historic_songs_menu.add_command(label = "Clear play history", command = delete_rec_songs)

# Create Music Position Slider
my_slider = ttk.Scale(master_frame, from_ = 0, to = 100, orient = HORIZONTAL, value = 0, length = 360)
my_slider.grid(row = 1, column = 0, pady = 20)

# Seek only when the user releases the slider, not when the program updates it
my_slider.bind('<ButtonRelease-1>', slide)

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
