import os
import Torrent
import settings
import logging

DOWNLOAD_FOLDER = settings.DOWNLOAD_FOLDER
PIECE_FOLDER = settings.PIECE_FOLDER

logging.basicConfig(filename='torrent.log', level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filemode='w')

logger = logging.getLogger(__name__)

def create_folders(download_path, piece_path):
    os.makedirs(download_path, exist_ok=True)
    os.makedirs(piece_path, exist_ok=True)
    return

def main():
    create_folders(DOWNLOAD_FOLDER, PIECE_FOLDER)
    path = input("Enter the path of the torrent file: ")
    torrent = Torrent.Torrent(path,logger)
    torrent.start()

if __name__ == '__main__':
    main()
