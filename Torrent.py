import TorrentClass
import settings
import TrackerClass
import socket
import PeerClass
import threading
import os
import time
import PriorityQueue
from tqdm import tqdm

class Torrent:
    def __init__(self, path, logger,messages):
        self.path = path
        self.logger = logger
        self.torrent_instance = None
        self.torrent_instance = TorrentClass.TorrentClass(self.path)
        self.priority_queue = PriorityQueue.PriorityQueue()
        self.name = self.torrent_instance.name
        self.messages = messages
        self.piece_path = str(os.path.join(settings.PIECE_FOLDER, self.name))
        self.download_path = ""
    def start(self):  # This is the function that will start and finish the download
        os.makedirs(self.piece_path, exist_ok=True)
        pbar_lock = threading.Lock()
        with tqdm(total=round(self.torrent_instance.size / (1024 * 1024), 2), desc="Downloading", unit="MB") as pbar:
            self.logger.info(f"{self.name} Starting download...")
            self.priority_queue.initialize_queue(self.torrent_instance.piece_list)
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            peer_id = os.urandom(20)

            self.logger.info(f"{self.name} Acquiring peer list...")
            peer_list = self.acquire_peer_list(self.torrent_instance, udp_sock, peer_id)
            if len(peer_list) == 0:
                self.logger.info(f"{self.name} No peers found. Exiting...")
                return

            udp_sock.close()
            time.sleep(1)

            self.logger.info(f"{self.name} Starting peer communication...")
            start_time = time.time()  # Start timing here
            download_finished = False
            if self.peers_manager(peer_list, peer_id, self.torrent_instance, pbar, pbar_lock,download_finished):
                self.logger.info(f"{self.name} All pieces downloaded. Assembling...")
                self.assemble_torrent(self.torrent_instance)
                end_time = time.time()  # End timing here
                duration = end_time - start_time
                hours = int(duration / 3600)
                minutes = int((duration % 3600) / 60)
                seconds = int(duration % 60)
                self.messages.append(f"{self.name} Download completed!")
                self.messages.append(f"{self.name} Download and assembly took {hours} hours, {minutes} minutes, and {seconds} seconds.")
                self.logger.info(
                    f"{self.name} Download and assembly for {self.name} took {hours} hours, {minutes} minutes, and {seconds} seconds.")
                return True
            return False

    def acquire_peer_list(self, torrent_instance, udp_sock,
                          peer_id):  # Connects to the tracker and gets the list of peers
        peer_list = []
        for tracker in torrent_instance.announce_list:
            tracker_instance = TrackerClass.TrackerClass(tracker, udp_sock, torrent_instance, peer_id, self.logger)
            try:
                peer_list = tracker_instance.start_communicating()
                if tracker_instance.peer_list:
                    return peer_list
            except socket.timeout:
                pass
        self.logger.info(f"{self.name} No peers found. Exiting...")
        return []

    def peer_communicating(self, peer_address, peer_id, torrent_instance, pbar,
                           pbar_lock,download_finished):
        try:
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_instance = PeerClass.PeerClass(peer_address, tcp_sock, peer_id, torrent_instance,
                                                self.piece_path, self.logger)
            if peer_instance.connect():
                peer_instance.peer_handler(self.priority_queue, pbar, pbar_lock,download_finished)
        except Exception as e:
            tcp_sock.close()
        finally:
            tcp_sock.close()

    def peers_manager(self, peer_list, peer_id, torrent_instance, pbar, pbar_lock,download_finished):
        threads = []
        for peer_address in peer_list:
            try:
                t1 = threading.Thread(target=self.peer_communicating, args=(
                    peer_address, peer_id, torrent_instance, pbar, pbar_lock,download_finished))
                t1.start()
                threads.append(t1)  # Add the thread to the list
            except Exception as e:
                pass
        while True:
            if len(os.listdir(self.piece_path)) == torrent_instance.number_of_pieces:
                download_finished = True
                break
        for thread in threads:
            thread.join()
        return len(os.listdir(self.piece_path)) == torrent_instance.number_of_pieces

    def assemble_torrent(self, torrent_instance):
        try:
            file_index = 0
            bytes_written = 0
            file_paths = list(torrent_instance.files.keys())
            file_sizes = list(torrent_instance.files.values())

            torrent_dir = torrent_instance.name

            file_paths = [os.path.join(settings.DOWNLOAD_FOLDER, torrent_dir, file_path) for file_path in file_paths]

            for file_path in file_paths:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

            f = open(file_paths[file_index], 'wb')

            for piece_index in range(torrent_instance.number_of_pieces):
                piece_path = os.path.join(self.piece_path,
                                          f'downloaded_piece_{piece_index}_{torrent_instance.name}.bin')
                with open(piece_path, 'rb') as piece_file:
                    piece_data = piece_file.read()

                piece_offset = 0

                while piece_offset < len(piece_data):
                    remaining_file_space = file_sizes[file_index] - bytes_written
                    remaining_piece_data = len(piece_data) - piece_offset

                    if remaining_piece_data <= remaining_file_space:
                        f.write(piece_data[piece_offset:])
                        bytes_written += remaining_piece_data
                        piece_offset += remaining_piece_data
                    else:
                        f.write(piece_data[piece_offset:piece_offset + remaining_file_space])
                        piece_offset += remaining_file_space
                        bytes_written += remaining_file_space

                    if bytes_written == file_sizes[file_index]:
                        f.close()
                        file_index += 1
                        bytes_written = 0
                        if file_index < len(file_paths):
                            f = open(file_paths[file_index], 'wb')

                os.remove(piece_path)

            f.close()
            self.logger.info(f"{self.name} Assembly complete.")
            os.rmdir(self.piece_path)
            self.download_path = os.path.join(settings.DOWNLOAD_FOLDER, torrent_dir)
            return True
        except Exception as e:
            self.logger.error(f"{self.name} Error assembling torrent: {e}")
            return False
