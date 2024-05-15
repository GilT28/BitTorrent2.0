import glob
import socket
import os
import time
import TorrentClass
import TrackerClass
import PeerClass
import threading
import traceback

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
    print("Assembly complete!")


def conncet_to_peer(peer_address, peer_id, torrent_instance, download_queue, piece_availability):
    try:
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_instance = PeerClass.PeerClass(peer_address, tcp_sock, peer_id, torrent_instance)
        if peer_instance.connect():
            peer_instance.peer_handler(download_queue, piece_availability)
    except Exception as e:
        print("Exception: ", e)
        print("Traceback: ", traceback.format_exc())
        tcp_sock.close()
    finally:
        tcp_sock.close()


if __name__ == '__main__':
    torrent_instance = TorrentClass.TorrentClass(
        r'C:\Users\gilth\PycharmProjects\BitTorrent 2.0\Selena Gomez & Marshmello - Wolves (Single) (2017) (Mp3 320kbps).torrent')
    print(torrent_instance.number_of_pieces)
    piece_availability = {piece: 0 for piece in torrent_instance.piece_list}  # 0 means that no peer has the piece
    download_queue = [1 for piece in range(0, torrent_instance.number_of_pieces)]  # Queue of pieces to download
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    peer_id = os.urandom(20)
    try:
        peer_list = []
        for tracker in torrent_instance.announce_list:
            tracker_instance = TrackerClass.TrackerClass(tracker, udp_sock, torrent_instance, peer_id)
            try:
                tracker_instance.start_communicating()
                if tracker_instance.peer_list:
                    peer_list = tracker_instance.peer_list
                    break
            except socket.timeout:
                print(f"Timeout when connecting to tracker {tracker}. Moving on to next tracker.")
        udp_sock.close()
        time.sleep(2)
        threads = []  # List to hold all threads

        for peer_address in peer_list:
            try:
                t1 = threading.Thread(target=conncet_to_peer, args=(
                    peer_address, peer_id, torrent_instance, download_queue, piece_availability))
                t1.start()
                threads.append(t1)  # Add the thread to the list
            except Exception as e:
                print("Exception: ", e)
                print("Traceback: ", traceback.format_exc())

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        number_pieces = len(os.listdir('pieces'))
        if number_pieces == torrent_instance.number_of_pieces:
            assemble_torrent(torrent_instance)
        else:
            print(f"Download got fucked try again lmaooooo")
            files = glob.glob('pieces')
            for f in files:
                os.remove(f)

    except Exception as e:
        print("Exception: ", e)
        print("Traceback: ", traceback.format_exc())
        udp_sock.close()