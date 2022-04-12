from tkinter import *
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

# Create Global path Variable
global path
path = 'C:/Users/tiago/Downloads/Escola/P&A/PyCharm/Trabalhos no Python/Music Player (trabalho final de disciplina) (81744 - 81809)/Musicas/'

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

# Create Master Frame
master_frame = Frame(root)
master_frame.pack(pady = 20, padx = 10)

# Create Playlist Box
song_box = Listbox(master_frame, bg = "black", fg = "green", width = 60, selectbackground = "gray", selectforeground = "black")
song_box.grid(row = 0, column = 0)

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
