import os
import Torrent
import settings
import logging
import time
import tkinter as tk
from tkinter import filedialog
import webbrowser
import math
import shutil

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


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def print_torrent_info(torrent_instance):
    print(f"Selected Torrent: {torrent_instance.name}")
    print(f"Torrent size: {convert_size(torrent_instance.size)}")
    print(f"Torrent files:")
    for file, file_size in torrent_instance.files.items():
        print(f"File: {file} Size: {convert_size(file_size)}")
    return


def start_torrent(messages):
    root = tk.Tk()
    root.withdraw()
    print("[1]. Select Torrent File")
    print("[2]. Cancel")
    command = input("Enter your choice: ")
    match command:
        case "1":
            # Open file explorer to select torrent file
            print("Select Torrent File")
            file_path = filedialog.askopenfilename(title="Select Torrent File",
                                                   filetypes=[("Torrent Files", "*.torrent")])
            if file_path:
                os.system('cls' if os.name == 'nt' else 'clear')
                torrent = Torrent.Torrent(file_path, logger, messages)
                if not enough_available_space(settings.DOWNLOAD_FOLDER,torrent.torrent_instance.size):
                    messages.append("ERROR: Not enough disk space to download torrent")
                    return
                print_torrent_info(torrent.torrent_instance)
                x = input("Start the download? (y/n): ")
                if x.lower() != 'y':
                    return
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"Downloading {torrent.name}...")
                if torrent.start():
                    os.startfile(torrent.download_path)
            else:
                print("No torrent file selected.")
        case "2":
            return


def enough_available_space(download_path,torrent_size):
    return shutil.disk_usage(download_path)[2] > torrent_size


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
        print(line)
        time.sleep(0.1)


def print_messages(messages):
    while len(messages) > 0:
        print(f"{messages.pop(0)}\n")
    return


def main():
    create_folders(DOWNLOAD_FOLDER, PIECE_FOLDER)
    messages = []
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        welcome_sequence()
        print_messages(messages)
        print("[1]. Start a new torrent download")
        print("[2]. Edit settings")
        print("[3]. Exit")
        command = input("Enter your choice: ")
        os.system('cls' if os.name == 'nt' else 'clear')
        match command:
            case "1":
                start_torrent(messages)
            case "2":
                edit_settings()
            case "3":
                print_spunchbob()
                time.sleep(1)
                print("Bye bye!")
                break
            case "4":
                secret()
            case _:
                messages.append("Invalid input")


if __name__ == '__main__':
    main()
