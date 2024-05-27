import TorrentClass
import settings
import TrackerClass
import socket
import PeerClass
import traceback
import threading
import os
import time
from tqdm import tqdm

class Torrent:
    def __init__(self,path,logger) -> None:
        self.path = path
        self.logger = logger
        self.torrent_instance = None
        self.piece_availability = {}  # 0 means that no peer has the piece
        self.download_queue = []  # Queue of pieces to download
        self.name = ''
    
    def start(self): # This is the function that will start and finish the download
        self.torrent_instance = TorrentClass.TorrentClass(self.path)
        pbar_lock = False
        with tqdm(total=round((self.torrent_instance.size) / (1024 * 1024),2), desc="Downloading", unit="MB") as pbar:
            self.logger.info(f"{self.name} Starting download...")
            self.name = self.torrent_instance.name
            self.piece_availability = {piece: 0 for piece in self.torrent_instance.piece_list} 
            self.download_queue = [1 for piece in range(0, self.torrent_instance.number_of_pieces)]
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            PEER_ID = os.urandom(20)

            self.logger.info(f"{self.name} Acquiring peer list...")
            peer_list = self.acquire_peer_list(self.torrent_instance, udp_sock, PEER_ID)
            if len(peer_list) == 0:
                self.logger.info(f"{self.name} No peers found. Exiting...")
                return
            
            udp_sock.close()
            time.sleep(1)

            self.logger.info(f"{self.name} Starting peer communication...")
            start_time = time.time()  # Start timing here
            if self.peers_manager(peer_list, PEER_ID, self.torrent_instance, self.download_queue, self.piece_availability,pbar,pbar_lock):
                self.logger.info(f"{self.name} All pieces downloaded. Assembling...")
                self.assemble_torrent(self.torrent_instance)
                end_time = time.time()  # End timing here
                duration = end_time - start_time
                hours = int(duration / 3600)
                minutes = int((duration % 3600) / 60)
                seconds = int(duration % 60)
                self.logger.info(f"{self.name} Download and assembly for {self.name} took {hours} hours, {minutes} minutes, and {seconds} seconds.")
                return True
            return False

    def acquire_peer_list(self,torrent_instance, udp_sock, peer_id):  # Connects to the tracker and gets the list of peers
        peer_list = []
        for tracker in torrent_instance.announce_list:
            tracker_instance = TrackerClass.TrackerClass(tracker, udp_sock, torrent_instance, peer_id,self.logger)
            try:
                peer_list = tracker_instance.start_communicating()
                if tracker_instance.peer_list:
                    return peer_list
            except socket.timeout:
                pass
        self.logger.info(f"{self.name} No peers found. Exiting...")
        return []


    def peer_communicating(self,peer_address, peer_id, torrent_instance, download_queue, piece_availability,pbar,pbar_lock):
        try:
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_instance = PeerClass.PeerClass(peer_address, tcp_sock, peer_id, torrent_instance, settings.PIECE_FOLDER, self.logger)
            if peer_instance.connect():
                peer_instance.peer_handler(download_queue, piece_availability,pbar,pbar_lock)
        except Exception as e:
            tcp_sock.close()
            pass
        finally:
            tcp_sock.close()
    
    def peers_manager(self,peer_list, peer_id, torrent_instance, download_queue, piece_availability,pbar,pbar_lock):
        threads = []
        for peer_address in peer_list:
            try:
                t1 = threading.Thread(target=self.peer_communicating, args=(
                    peer_address, peer_id, torrent_instance, download_queue, piece_availability,pbar,pbar_lock))
                t1.start()
                threads.append(t1)  # Add the thread to the list
            except Exception as e:
                pass
        for thread in threads:
            thread.join()
        return len(os.listdir(settings.PIECE_FOLDER)) == torrent_instance.number_of_pieces

    def assemble_torrent(self,torrent_instance):
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
                piece_path = os.path.join(settings.PIECE_FOLDER, f'downloaded_piece_{piece_index}_{torrent_instance.name}.bin')
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
            self.logger.info(f"{self.name} Assembly complete.")
            return True
        except Exception as e:
            self.logger.error(f"{self.name} Error assembling torrent: {e}")
            return False

