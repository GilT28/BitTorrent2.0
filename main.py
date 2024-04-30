import socket
import os
import time
import TorrentClass
import TrackerClass
import PeerClass
import threading
import queue
import traceback

def conncet_to_peer(peer_address,peer_id,torrent_instance,download_queue,piece_availability):
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
        r'C:\Users\gilth\PycharmProjects\BitTorrent 2.0\Dune Part 2 (1.6GB).torrent')
    piece_availability = [set() for _ in range(torrent_instance.number_of_pieces)]
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    peer_id = os.urandom(20)
    download_queue = queue.Queue()
    for i in range(0, torrent_instance.number_of_pieces):
        download_queue.put(i)
    try:
        tracker_instance = TrackerClass.TrackerClass(torrent_instance.announce_list[0], udp_sock, torrent_instance, peer_id)  # Temp only for testing (will change to check every tracker)
        tracker_instance.start_communicating()
        peer_list = tracker_instance.peer_list
        udp_sock.close()
        time.sleep(2)
        for peer_address in peer_list:
            try:
                t1 = threading.Thread(target=conncet_to_peer, args=(
                peer_address, peer_id, torrent_instance, download_queue, piece_availability))
                t1.start()
            except Exception as e:
                print("Exception: ", e)
                print("Traceback: ", traceback.format_exc())


    except Exception as e:
        print("Exception: ", e)
        print("Traceback: ", traceback.format_exc())
        udp_sock.close()

