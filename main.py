import os
import socket
import threading
import time
import traceback
import PeerClass
import TorrentClass
import TrackerClass
import settings

DOWNLOAD_FOLDER = settings.DOWNLOAD_FOLDER
PIECE_FOLDER = settings.PIECE_FOLDER
MAX_THREAD_PER_PEER = settings.MAX_THREAD_PER_PEER

def create_folders(download_path, piece_path):
    os.makedirs(download_path, exist_ok=True)
    os.makedirs(piece_path, exist_ok=True)
    return


def acquire_peer_list(torrent_instance, udp_sock, peer_id):
    peer_list = []
    for tracker in torrent_instance.announce_list:
        tracker_instance = TrackerClass.TrackerClass(tracker, udp_sock, torrent_instance, peer_id)
        try:
            peer_list = tracker_instance.start_communicating()
            if tracker_instance.peer_list:
                return peer_list
        except socket.timeout:
            print(f"Timeout when connecting to tracker {tracker}. Moving on to next tracker.")


def peer_communicating(peer_address, peer_id, torrent_instance, download_queue, piece_availability):
    try:
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_instance = PeerClass.PeerClass(peer_address, tcp_sock, peer_id, torrent_instance, PIECE_FOLDER, MAX_THREAD_PER_PEER)
        if peer_instance.connect():
            peer_instance.peer_handler(download_queue, piece_availability)
    except Exception as e:
        print("Exception: ", e)
        print("Traceback: ", traceback.format_exc())
        tcp_sock.close()
    finally:
        tcp_sock.close()


def peers_manager(peer_list, peer_id, torrent_instance, download_queue, piece_availability):
    threads = []
    for peer_address in peer_list:
        try:
            t1 = threading.Thread(target=peer_communicating, args=(
                peer_address, peer_id, torrent_instance, download_queue, piece_availability))
            t1.start()
            threads.append(t1)  # Add the thread to the list
        except Exception as e:
            print("Exception: ", e)
            print("Traceback: ", traceback.format_exc())
    for thread in threads:
        thread.join()
    return len(os.listdir(PIECE_FOLDER)) == torrent_instance.number_of_pieces


def assemble_torrent(torrent_instance, pieces_dir, download_folder):
    try:
        file_index = 0
        bytes_written = 0
        file_paths = list(torrent_instance.files.keys())
        file_sizes = list(torrent_instance.files.values())

        torrent_dir = torrent_instance.name
        #os.makedirs(torrent_dir, exist_ok=True)

        file_paths = [os.path.join(download_folder, torrent_dir, file_path) for file_path in file_paths]

        for file_path in file_paths:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

        f = open(file_paths[file_index], 'wb')

        for piece_index in range(torrent_instance.number_of_pieces):
            piece_path = os.path.join(pieces_dir, f'downloaded_piece_{piece_index}_{torrent_instance.name}.bin')
            piece_file = open(piece_path, 'rb')
            piece_data = piece_file.read()
            piece_file.close()

            if bytes_written + len(piece_data) > file_sizes[file_index]:
                remaining = file_sizes[file_index] - bytes_written
                f.write(piece_data[:remaining])
                f.close()
                file_index += 1
                bytes_written = 0
                f = open(file_paths[file_index], 'wb')
                f.write(piece_data[remaining:])
                bytes_written += len(piece_data) - remaining
            else:
                f.write(piece_data)
                bytes_written += len(piece_data)

            if bytes_written == file_sizes[file_index]:
                f.close()
                file_index += 1
                bytes_written = 0
                if file_index < len(file_paths):
                    f = open(file_paths[file_index], 'wb')

            os.remove(piece_path)

        f.close()
        print("Assembly complete!")
        return True
    except Exception as e:
        print(f"Assembly failed with error: {e}")
        return False


def main():
    create_folders(DOWNLOAD_FOLDER, PIECE_FOLDER)
    torrent_path = input("Enter the path to the torrent file: ")
    torrent_instance = TorrentClass.TorrentClass(torrent_path)
    piece_availability = {piece: 0 for piece in torrent_instance.piece_list}  # 0 means that no peer has the piece
    download_queue = [1 for piece in range(0, torrent_instance.number_of_pieces)]  # Queue of pieces to download
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    PEER_ID = os.urandom(20)
    print("Acquiring peer list...")
    peer_list = acquire_peer_list(torrent_instance, udp_sock, PEER_ID)
    if len(peer_list) == 0:
        print("No peers found. Exiting...")
        return
    udp_sock.close()
    time.sleep(1)

    print("Starting peer communication...")
    if peers_manager(peer_list, PEER_ID, torrent_instance, download_queue, piece_availability):
        assemble_torrent(torrent_instance, PIECE_FOLDER, DOWNLOAD_FOLDER)


if __name__ == '__main__':
    main()
