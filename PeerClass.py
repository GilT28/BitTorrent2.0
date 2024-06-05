import hashlib
import os
import struct
import binascii
import time
from sys import exit


class PeerClass(Exception):
    def __init__(self, address, sock, peer_id, torrent_instance, piece_folder, logger):
        self.address = address
        self.sock = sock
        self.peer_id = peer_id
        self.torrent_instance = torrent_instance
        self.available_pieces = set()  # Piece index for each piece that the peer has
        self.peer_choked = True
        self.piece_folder = piece_folder
        self.logger = logger
        self.block_size = min(16384, self.torrent_instance.piece_length)

    def connect(self):
        try:
            self.logger.info(f"{self.torrent_instance.name} Attempting connection on peer {self.address}")
            self.sock.connect(self.address)
            handshake = self.create_handshake(self.torrent_instance.info_hash, self.peer_id)
            self.sock.send(handshake)
            handshake_data = self.receive_handshake()
            if isinstance(handshake_data, bytes) and len(handshake_data) == 68 and handshake_data[
                                                                                   1:20:] == b'BitTorrent protocol':
                self.logger.info(f'{self.torrent_instance.name} ({self.address}) Connected!')
                return True
            return False
        except Exception as e:
            return False
            # self.logger.error(f"{self.torrent_instance.name} ERROR with connecting to peer {self.address}, {e}")
            # print(f"{self.torrent_instance.name} ERROR with connecting to peer {self.address}, {e}")

    def peer_handler(self, priority_queue, pbar, pbar_lock, download_finished):
        start_time = time.time()
        interested_msg = self.create_msg(2)
        self.sock.send(interested_msg)
        self.sock.settimeout(5.0)
        while not download_finished:
            current_time = time.time()

            if not self.peer_choked:
                piece = self.get_rarest_available_piece(priority_queue)
                if piece is not None:
                    priority_queue.update_download_status(piece.index, 2)
                    if self.download_piece(piece, pbar, pbar_lock, priority_queue):
                        self.logger.info(
                            f"{self.torrent_instance.name} Finished downloading piece {piece.index} from peer {self.address}")
                        priority_queue.update_download_status(piece.index, 1)
                    else:
                        priority_queue.update_download_status(piece.index, 0)
                    continue
            if current_time - start_time >= 120:
                keep_alive = struct.pack('!I', 0)
                self.sock.send(keep_alive)
                start_time = current_time
            msg = self.sock.recv(4096)
            self.response_handler(msg, priority_queue)

    def response_handler(self, msg, priority_queue):
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
                self.have(piece_index, priority_queue)
            if id == 5:  # Bitfield
                self.bitfield(payload, priority_queue)

    def download_piece(self, download_piece, pbar, pbar_lock, priority_queue):
        self.logger.info(
            f"{self.torrent_instance.name} Downloading piece {download_piece.index} from peer {self.address}")
        try:
            block_size_list = self.block_offset(download_piece.size, self.block_size)
            if self.torrent_instance.piece_length % self.block_size != 0:
                block_size_list[-1] = self.torrent_instance.piece_length % self.block_size

            begin = 0
            piece = b''
            for block_size in block_size_list:
                reqmsg = self.request_message(download_piece.index, begin, block_size)
                begin += block_size
                self.sock.send(reqmsg)
                block = bytearray()
                part = self.sock.recv(18000)  # First BIG request to maybe receive the entire block at once
                block.extend(part)
                while len(block) < block_size + 13:
                    part = self.sock.recv(block_size + 13 - len(block))
                    if part == b'':
                        break
                    block.extend(part)
                if len(block) < block_size + 13:
                    exit()
                if self.get_message_id(block) == 7:
                    piece += block[13:]
            piece_hash = hashlib.sha1(piece).digest()
            if piece_hash == download_piece.hash_value:
                with pbar_lock:
                    pbar.update(round(download_piece.size / (1024 * 1024), 2))
                piece_name = f'downloaded_piece_{download_piece.index}_{self.torrent_instance.name}.bin'
                path = os.path.join(self.piece_folder, piece_name)
                with open(path, 'wb') as f:
                    f.write(piece)
                    f.close()
                return True
            return False
        except Exception as e:
            self.logger.error(
                f"{self.torrent_instance.name} Error downloading piece {download_piece.index} from peer {self.address}: {e}")
            priority_queue.update_download_status(download_piece.index, 0)
            exit()

    def create_handshake(self, info_hash, peer_id):
        return struct.pack('!B19sQ20s20s', 19, 'BitTorrent protocol'.encode(), 0, binascii.a2b_hex(info_hash), peer_id)

    def receive_handshake(self):
        data = bytearray()
        self.sock.settimeout(5)

        try:
            while len(data) < 68:
                part = self.sock.recv(68 - len(data))  # Receive the remaining bytes to reach 68 bytes
                if not part:
                    return False
                data.extend(part)
        except self.sock.timeout:
            return False
        except Exception as e:
            return False
        finally:
            self.sock.settimeout(2)

        return bytes(data)

    def get_rarest_available_piece(self, priority_queue):
        rarest_piece = None
        for piece in priority_queue.heap:
            if piece.index in self.available_pieces and piece.download_status == 0:
                rarest_piece = piece
                return rarest_piece
        return rarest_piece

    def create_msg(self, id):
        return struct.pack('!IB', 1, id)

    def choked(self):
        self.peer_choked = True
        return

    def unchoked(self):
        self.peer_choked = False
        return

    def have(self, index, priority_queue):
        self.available_pieces.add(index)
        priority_queue.update_piece_rarity(index)
        return

    def bitfield(self, payload, priority_queue):
        # Convert the payload bytes to a bitfield list
        bitfield_list = []
        piece_counter = 0
        for byte in payload:
            for i in range(7, -1, -1):  # Iterate over the bits of each byte
                if (byte >> i) & 1:  # Check if the bit is set
                    piece_index = piece_counter
                    if piece_index < self.torrent_instance.number_of_pieces:
                        bitfield_list.append(piece_index)
                        self.available_pieces.add(piece_index)
                        priority_queue.update_piece_rarity(piece_index)
                piece_counter += 1
        return bitfield_list

    def block_offset(self, piece_size, block_size):
        full_blocks = piece_size // block_size
        remainder = piece_size % block_size

        block_sizes = [block_size] * full_blocks
        if remainder:
            block_sizes.append(remainder)

        return block_sizes

    def request_message(self, piece_index, begin, block_size):  # Block size = 16384 bytes
        return struct.pack('!IBIII', 13, 6, piece_index, begin, block_size)

    def get_message_id(self, msg):
        return struct.unpack(">IB", msg[:5])[1]
