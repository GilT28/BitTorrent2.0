import os
import Torrent
import settings
import logging
import time
import tkinter as tk
from tkinter import filedialog
import webbrowser

DOWNLOAD_FOLDER = settings.DOWNLOAD_FOLDER
PIECE_FOLDER = settings.PIECE_FOLDER

logging.basicConfig(filename='torrent.log', level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filemode='w')

logger = logging.getLogger(__name__)

def create_folders(download_path, piece_path):
    os.makedirs(download_path, exist_ok=True)
    os.makedirs(piece_path, exist_ok=True)
    return

def welcome_sequence():
    print("Welcome to my...")
    print_list = [" ____  _ _   _                            _          _ _            _   ",
                  "|  _ \(_) | | |                          | |        | (_)          | |  ",
                  "| |_) |_| |_| |_ ___  _ __ _ __ ___ _ __ | |_    ___| |_  ___ _ __ | |_ ",
                  "|  _ <| | __| __/ _ \| '__| '__/ _ \ '_ \| __|  / __| | |/ _ \ '_ \| __|",
                  "| |_) | | |_| || (_) | |  | | |  __/ | | | |_  | (__| | |  __/ | | | |_ ",
                  "|____/|_|\__|\__\___/|_|  |_|  \___|_| |_|\__|  \___|_|_|\___|_| |_|\__|"]
    time.sleep(0.5)
    for line in print_list:
        time.sleep(0.1)
        print(line)
    time.sleep(1)
    print("Created by: Gil Turgeman :)\n")
    time.sleep(1)

def start_torrent():
    root = tk.Tk()
    root.withdraw()
    print("[1]. Select Torrent File")
    print("[2]. Cancel")
    command = input("Enter your choice: ")
    match command:
        case "1":
            # Open file explorer to select torrent file
            print("Select Torrent File")
            file_path = filedialog.askopenfilename(title="Select Torrent File", filetypes=[("Torrent Files", "*.torrent")])
            if file_path:
                print(f"Selected torrent file: {file_path}")
                x = input("Start the download? (y/n): ")
                if x.lower() != 'y':
                    return
                os.system('cls' if os.name == 'nt' else 'clear')
                torrent = Torrent.Torrent(file_path, logger)
                print(f"Downloading {torrent.name}...")
                torrent.start()
            else:
                print("No torrent file selected.")
        case "2":
            return

def edit_settings():
    print("Which settings would you like to edit?")
    print("[1]. Downloads Folder location")
    print("[2]. Piece Folder location")
    print("[3]. Both")
    print("[4]. Cancel")
    command = input("Enter your choice: ")
    match command:
        case "1":
            edit_downloads_folder()
        case "2":
            edit_piece_folder()
        case "3":
            edit_downloads_folder()
            edit_piece_folder()
        case "4":
            return
        case _:
            print("Invalid input")
    create_folders(DOWNLOAD_FOLDER, PIECE_FOLDER)

def secret():
    x = input("Are you sure you want to do this? (y/n): ")
    if x.lower() != 'y':
        return
    print("ok...")
    time.sleep(1)
    print("You asked for this...")
    time.sleep(1.5)
    webbrowser.open('https://youtu.be/ySuMsyta6O8?si=ivYnGY0Gc4Hv3JJS')

def edit_downloads_folder():
    root = tk.Tk()
    root.withdraw()
    # Open file explorer to select downloads folder
    print("Select Downloads Folder")
    download_folder = filedialog.askdirectory(title="Select Downloads Folder")
    if download_folder:
        print(f"Selected downloads folder: {download_folder}")
        settings.DOWNLOAD_FOLDER = download_folder
    else:
        print("No downloads folder selected.")

def edit_piece_folder():
    # Open file explorer to select piece folder
    print("Select Piece Folder")
    piece_folder = filedialog.askdirectory(title="Select Piece Folder")
    if piece_folder:
        print(f"Selected piece folder: {piece_folder}")
        settings.PIECE_FOLDER = piece_folder
    else:
        print("No piece folder selected.")

def print_spunchbob():
    spunch_bob = """⡐⠉⠉⠉⣑⠂⠒⠊⠉⠶⡄⠈⠉⠓⠉⠉⠁⠁⢠⠖⠦⡉⠐⠒⠒⠊⠒⠐⢒⠢
⡄⢂⡁⠸⠱⠉⡀⣁⣰⣟⠁⠀⠐⡀⢈⠐⢈⠁⠈⠘⣆⠀⠐⠈⢀⠀⠻⠣⠀⢀
⠐⡄⣁⣐⣤⣲⣴⣿⣭⣈⡙⠲⣄⠀⠂⢈⠀⣠⡶⢛⣙⣿⣦⣥⣂⣌⣐⣀⡌⡎
⣾⠝⣩⣿⣿⣿⣿⣿⣿⣟⣿⣦⠈⢳⡀⢠⡾⣣⣶⣿⣿⣿⣿⣻⣿⣿⣍⠉⢦⡁
⡟⢰⣿⣯⣿⣿⣿⣿⠀⢨⣿⣿⣷⠀⢿⣟⣰⣿⣿⣿⣿⣿⣟⠉⢹⣯⣿⣧⠀⢻
⡇⢾⡿⣽⣿⣿⣿⣿⣿⣿⣿⣯⣿⡇⢸⡇⣿⡟⣾⣿⣿⣿⣿⣶⣿⣿⣞⣿⠀⢸
⡇⢻⣷⡻⣿⣿⣿⣿⣿⣿⣿⣹⡿⢀⣿⡆⢿⣿⢽⣿⣿⣿⣿⣿⣿⡿⣻⡿⠀⣼
⣿⣀⠻⣿⣍⣟⡿⢿⣟⣛⣾⠟⣡⣾⠏⣷⡘⠿⣷⣛⠿⡿⠿⢿⣻⣼⡿⠁⣴⠟
⠈⢻⣦⣥⣋⡛⢟⠻⢛⣋⣥⡼⡟⣼⡃⡿⣹⢦⣍⡛⠿⠿⠿⠿⢛⣡⣤⠟⣿⠈
⠀⢸⡯⣝⢻⢳⠾⠶⣾⢟⡏⢇⡱⣻⡇⣧⠉⠞⡻⠷⠶⣶⠶⢶⠞⡛⠩⣰⡟⠀
⠀⢸⠇⠈⢃⠊⠁⠃⠂⢈⠐⠠⣜⣿⡀⢿⡀⠐⢀⠉⠑⣸⢿⡌⠐⠈⠀⢿⡁⠀
⠀⢸⡇⠈⠈⠃⠐⠀⢂⠀⢤⡿⠽⣿⠀⡿⠹⣆⠀⠠⢱⠏⣞⢻⡄⣞⢀⠏⠀⠀
⠀⢀⣿⡄⠰⡶⣬⡐⠀⣠⡟⡠⢙⣿⠀⡽⠀⡸⢦⠄⣿⠘⣾⣤⠇⠈⡞⡀⠀⠀
⢀⡞⠈⢧⣤⣬⣥⣄⣀⣻⢾⣥⣎⣿⠀⢼⣀⣛⣏⣤⣭⣳⣞⣉⣀⣀⠇⢸⠀⠀
⠀⠛⢾⢿⣄⣀⣤⣀⣉⣉⠳⢤⣞⡗⠀⢾⠙⣭⠖⠋⠀⠁⠉⠉⠉⣿⣶⠂⠁⠀
⠀⢀⣾⢽⣿⣿⣿⣿⢿⣿⣿⣿⣿⡇⠀⣺⣿⣿⣿⣿⣿⣿⣿⣿⣿⡧⣿⠀⠀⠀
⠀⠀⣼⢫⣿⣞⣷⣯⣟⣾⣽⣾⣽⣿⣶⣿⣯⣟⣾⣳⣯⣿⣽⣳⣯⣟⣿⠀⠀⠀
⠀⠀⡝⣠⢛⡟⠯⡿⣟⣯⣟⣷⠏⠉⠉⠉⠉⢻⡿⣟⣯⣟⢿⢏⡟⢤⣻⠀⠀⠀"""
    for line in spunch_bob.splitlines():
        print (line)
        time.sleep(0.1)


def main():
    create_folders(DOWNLOAD_FOLDER, PIECE_FOLDER)
    while True:
        welcome_sequence()
        print("[1]. Start a new torrent download")
        print("[2]. Edit settings")
        print("[3]. Exit")
        command = input("Enter your choice: ")
        os.system('cls' if os.name == 'nt' else 'clear')
        match command:
            case "1":
                start_torrent()
                os.system('cls' if os.name == 'nt' else 'clear')
            case "2":
                edit_settings()
                os.system('cls' if os.name == 'nt' else 'clear')
            case "3":
                print_spunchbob()
                time.sleep(1)
                print("Bye bye!")
                break
            case "4":
                secret()
            case _:
                print("Invalid input")


if __name__ == '__main__':
    main()
