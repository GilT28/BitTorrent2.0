import TorrentClass
import os


import os

import os

def assemble_torrent(torrent_instance, pieces_dir='pieces'):
    file_index = 0  # The index of the current file
    bytes_written = 0  # The number of bytes written to the current file
    file_paths = list(torrent_instance.files.keys())
    file_sizes = list(torrent_instance.files.values())

    # Create a directory named after the torrent
    torrent_dir = torrent_instance.name
    os.makedirs(torrent_dir, exist_ok=True)

    # Modify the file paths to include the torrent directory
    file_paths = [os.path.join(torrent_dir, file_path) for file_path in file_paths]

    # Create the directories for the files
    for file_path in file_paths:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

    f = open(file_paths[file_index], 'wb')  # Open the first file

    # Write each piece to the file
    for piece_index in range(torrent_instance.number_of_pieces):
        piece_path = os.path.join(pieces_dir, f'downloaded_piece_{piece_index}.bin')
        piece_file = open(piece_path, 'rb')
        piece_data = piece_file.read()
        piece_file.close()  # Close the file manually

        # If the current piece will exceed the size of the current file
        if bytes_written + len(piece_data) > file_sizes[file_index]:
            # Calculate how much of the piece can be written to the current file
            remaining = file_sizes[file_index] - bytes_written

            # Write the remaining part of the piece to the current file
            f.write(piece_data[:remaining])
            f.close()  # Close the current file

            # Move to the next file
            file_index += 1
            bytes_written = 0

            # Open the next file and write the rest of the piece
            f = open(file_paths[file_index], 'wb')  # Open the next file
            f.write(piece_data[remaining:])
            bytes_written += len(piece_data) - remaining
        else:
            # Write the entire piece to the current file
            f.write(piece_data)
            bytes_written += len(piece_data)

        # If the end of the current file has been reached, move to the next file
        if bytes_written == file_sizes[file_index]:
            f.close()  # Close the current file
            file_index += 1
            bytes_written = 0
            if file_index < len(file_paths):  # If there are more files
                f = open(file_paths[file_index], 'wb')  # Open the next file

        # Delete the piece file after it has been written
        os.remove(piece_path)

    f.close()  # Close the last file

if __name__ == '__main__':
    torrent_instance = TorrentClass.TorrentClass(
        r'C:\Users\gilth\PycharmProjects\BitTorrent 2.0\Selena Gomez & Marshmello - Wolves (Single) (2017) (Mp3 320kbps).torrent')
    assemble_torrent(torrent_instance)
