import binascii
import hashlib
import os
import socket
import struct
import time
import TorrentClass
from sys import exit

class PeerClass:
    def __init__(self, address: tuple, sock: socket, peer_id: bytes, torrent_instance: TorrentClass, piece_folder: str,logger):
        self.address = address
        self.sock = sock
        self.peer_id = peer_id
        self.torrent_instance = torrent_instance
        self.available_pieces = {piece: False for piece in range(0,
                                                                 torrent_instance.number_of_pieces)}  # false if peer doesn't have piece, true if peer does have piece
        self.peer_choked = True
        self.piece_folder = piece_folder
        self.logger = logger

    def connect(self):
        try:
            self.sock.connect(self.address)
        except ConnectionRefusedError:
            return False
        except Exception as e:
            return False
        handshake = self.create_handshake(self.torrent_instance.info_hash, self.peer_id)
        self.sock.send(handshake)
        handshake_data = self.recv_handshake()
        if isinstance(handshake_data, bytes) and len(handshake_data) == 68 and handshake_data[
                                                                               1:20:] == b'BitTorrent protocol':
            self.logger.info(f'{self.torrent_instance.name} ({self.address}) Connected!')
            return True
        return False

    def peer_handler(self, download_queue, piece_availability,pbar,pbar_lock):
        start_time = time.time()
        interested_msg = self.create_msg(2)
        self.sock.send(interested_msg)
        self.sock.settimeout(3.0)
        while True:
            # Check if all pieces have been downloaded
            if all(piece == 0 for piece in download_queue):
                break

            current_time = time.time()
            if not self.peer_choked:
                no_pieces, rarest_piece = self.get_rarest_piece(piece_availability, download_queue)
                if not no_pieces:
                    download_queue[rarest_piece.index] = 2  # Set the count of this piece to 2 as it's being downloaded
                    self.logger.info(f"{self.torrent_instance.name} Downloading piece {rarest_piece.index} from peer {self.address}")
                    flag = self.download_piece(rarest_piece.index,pbar,pbar_lock)
                    if flag:
                        self.logger.info(f"{self.torrent_instance.name} Finished downloading piece {rarest_piece.index} from peer {self.address}")
                        download_queue[rarest_piece.index] = 0
                    else:
                        download_queue[rarest_piece.index] = 1
            if current_time - start_time >= 120:
                keep_alive = struct.pack('!I', 0)
                self.sock.send(keep_alive)
                start_time = current_time
            try:
                msg = self.sock.recv(4096)
                self.response_handler(msg, piece_availability)
            except socket.timeout:
                self.logger.info(f"{self.torrent_instance.name} ({self.address}) Timed out.")

    def response_handler(self, msg, piece_availability):
        if len(msg) == 5:
            id = msg[4]
            match id:
                case 0:  # Choke
                    self.choked()
                case 1:  # Unchoked
                    self.unchoked()
                case 2 | 3:  # Interested/Uninterested
                    return 'nothing'
        if len(msg) > 5:  # BitField or Have
            id = msg[4]
            payload = msg[5:]
            if id == 4:  # Have
                piece_index = payload
                self.have(piece_index, piece_availability)
            if id == 5:  # Bitfield
                self.bitfield(payload, piece_availability)

    def download_piece(self, piece_num,pbar,pbar_lock):
        self.logger.info(f"{self.torrent_instance.name} Downloading piece {piece_num} from peer {self.address}")
        try:
            download_piece = self.torrent_instance.get_piece(piece_num)
            block_size = min(16384, self.torrent_instance.piece_length)
            block_size_list = self.block_offset(download_piece.size, block_size)
            if self.torrent_instance.piece_length % block_size != 0:
                block_size_list[-1] = self.torrent_instance.piece_length % block_size

            begin = 0
            piece = b''
            for block_size in block_size_list:
                reqmsg = self.request_message(download_piece.index, begin, block_size)
                begin += block_size
                self.sock.send(reqmsg)
                block = b''
                while len(block) < block_size + 13:
                    part = self.sock.recv(block_size + 13 - len(block))
                    if part == b'':
                        break
                    block += part
                if len(block) < block_size + 13:
                    exit()
                if self.get_message_id(block) == 7:
                    piece += block[13:]
            piece_hash = hashlib.sha1(piece).digest()  # Calculate hash once
            if piece_hash == download_piece.hash_value:
                while pbar_lock:
                    pass
                pbar_lock = True
                pbar.update(round((download_piece.size) / (1024 * 1024),2))
                pbar_lock = False
                piece_name = f'downloaded_piece_{download_piece.index}_{self.torrent_instance.name}.bin'
                path = os.path.join(self.piece_folder, piece_name)
                with open(path, 'wb') as f:
                    f.write(piece)
                    f.close()
                return True
            return False
        except Exception as e:
            self.logger.error(f"{self.torrent_instance.name} Error downloading piece {piece_num} from peer {self.address}: {e}")
            return False
        
    def create_handshake(self, info_hash, peer_id):
        info_hash = binascii.a2b_hex(info_hash)
        msg = struct.pack('!B19sQ20s20s', 19, 'BitTorrent protocol'.encode(), 0, info_hash, peer_id)
        return msg

    def create_msg(self, id):
        msg = struct.pack('!IB', 1, id)
        return msg

    def recv_handshake(self):
        data = b''
        self.sock.settimeout(5)
        while True:
            try:
                part = self.sock.recv(1)
                data += part
                if part == b'':
                    return False
                if len(data) >= 68:
                    break
            except Exception as e:
                return False
        self.sock.settimeout(2)
        return data

    def choked(self):
        self.peer_choked = True
        return

    def unchoked(self):
        self.peer_choked = False
        msg = self.create_msg(2)
        self.sock.send(msg)
        return

    def have(self, index, piece_availability):
        self.available_pieces[index] = True
        piece_availability[self.torrent_instance.get_piece(index)] += 1
        piece_availability = dict(sorted(piece_availability.items(), key=lambda x: x[1], reverse=True))
        return

    def bitfield(self, payload, piece_availability):
        bitfield_list = []
        piece_counter = 0
        pack_format = '!' + 'B' * len(payload)
        bytes_tuple = struct.unpack(pack_format, payload)
        for byte in bytes_tuple:
            bits = '{0:08b}'.format(byte)
            for bit in bits:
                if bit == '1':
                    bitfield_list.append(piece_counter)
                piece_counter += 1
        if len(bitfield_list) > self.torrent_instance.number_of_pieces:
            self.sock.close()
        for i in bitfield_list:
            self.available_pieces[i] = True
            piece_availability[self.torrent_instance.get_piece(i)] += 1
        piece_availability = dict(sorted(piece_availability.items(), key=lambda x: x[1], reverse=True))
        return

    def block_offset(self, piecesize, block_size):
        times = piecesize / block_size
        l = []
        for i in range(int(times)):
            l.append(block_size)
        if not times.is_integer():
            l.append(int(block_size * (times - int(times))))
        return l

    def request_message(self, pieceindex, begin, block_size):  # Block size = 16384 bytes
        msg = struct.pack('!IBIII', 13, 6, pieceindex, begin, block_size)
        return msg
    
    def get_message_id(self,msg):
        length, id = struct.unpack(">IB", msg[:5])
        return id

    def get_rarest_piece(self, piece_availability, download_queue):
        no_pieces = True
        rarest_piece = None
        for piece in piece_availability:
            if download_queue[piece.index] != 0 and download_queue[piece.index] != 2:
                if self.available_pieces[piece.index]:
                    no_pieces = False
                    rarest_piece = piece
                    break
        return no_pieces, rarest_piece
