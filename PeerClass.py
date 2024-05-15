import binascii
import hashlib
import socket
import struct
import time
import TorrentClass
import threading

class PeerClass:
    def __init__(self, address: tuple, sock: socket, peer_id: bytes, torrent_instance: TorrentClass):
        self.address = address
        self.sock = sock
        self.peer_id = peer_id
        self.torrent_instance = torrent_instance
        self.available_pieces = {piece: False for piece in range(0,
                                                                 torrent_instance.number_of_pieces)}  # false if peer doesn't have piece, true if peer does have piece
        self.peer_choked = True

    def connect(self):
        print(f'{self.address} Connecting to peer...')
        try:
            self.sock.connect(self.address)
        except ConnectionRefusedError:
            print(f"Connection refused by {self.address}. Moving on to next peer.")
            return False
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return False
        print(f'{self.address} Connected to peer, sending handshake')
        handshake = self.create_handshake(self.torrent_instance.info_hash, self.peer_id)
        self.sock.send(handshake)
        print(f'{self.address} Handshake sent!')
        handshake_data = self.recv_handshake()
        if isinstance(handshake_data, bytes) and len(handshake_data) == 68 and handshake_data[
                                                                               1:20:] == b'BitTorrent protocol':
            print('Received valid connection')
            return True
        return False

    def peer_handler(self, download_queue, piece_availability,download_lock, available_pieces_lock):
        start_time = time.time()
        interested_msg = self.create_msg(2)
        self.sock.send(interested_msg)
        self.sock.settimeout(5.0)
        while True:
            # Check if all pieces have been downloaded
            if all(piece == 0 for piece in download_queue):
                print("Download complete!")
                break

            current_time = time.time()
            if not self.peer_choked:
                no_pieces, rarest_piece = self.get_rarest_piece(piece_availability, download_queue)
                if not no_pieces:
                    download_queue[rarest_piece.index] = 0  # Set the count of this piece to 0 as it's being downloaded
                    print(f'Downloading piece: {rarest_piece.index}')
                    flag = self.download_piece(rarest_piece.index)
                    if flag:
                        print(f'Downloaded piece {rarest_piece.index}!')
                    else:
                        while download_lock:
                            pass
                        download_lock = True
                        download_queue[rarest_piece.index] = 1
                        download_lock = False
                else:
                    print(f'Peer {self.address} does not have piece {rarest_piece.index}')
            if current_time - start_time >= 120:
                keep_alive = struct.pack('!I', 0)
                self.sock.send(keep_alive)
                start_time = current_time
            try:
                msg = self.sock.recv(4096)
                self.response_handler(msg, piece_availability, available_pieces_lock)
            except socket.timeout:
                print("No data received from peer within the timeout period.")

    def response_handler(self, msg, piece_availability, available_pieces_lock):
        if len(msg) == 5:
            id = msg[4]
            match id:
                case 0:  # Choke
                    print('Choked')
                    self.choked()
                case 1:  # Unchoked
                    print('UnChoked')
                    self.unchoked()
                case 2 | 3:  # Interested/Uninterested
                    print('Interested/Uninterested')
                    return 'nothing'
        if len(msg) > 5:  # BitField or Have
            id = msg[4]
            payload = msg[5:]
            if id == 4:  # Have
                print('Have')
                piece_index = payload
                self.have(piece_index, piece_availability, available_pieces_lock)
            if id == 5:  # Bitfield
                print('Bitfield')
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
                    print('Bitfield ERROR')
                    self.sock.close()
                    return
                self.bitfield(bitfield_list, piece_availability, available_pieces_lock)

    def download_piece(self, piece_num):
        print(f"Starting download of piece {piece_num} from peer {self.address}")
        download_piece = self.torrent_instance.get_piece(piece_num)
        block_size = 16384
        if self.torrent_instance.piece_length < 16384:
            block_size = self.torrent_instance.piece_length
        block_size_list = self.block_offset(download_piece.size, block_size)
        if self.torrent_instance.piece_length % 16384 != 0:
            block_size_list[-1] = self.torrent_instance.piece_length % 16384
        begin = 0
        counter = 0
        piece = b''
        downloaded = 0
        for block_size in block_size_list:
            print(f"Requesting block of size {block_size} from peer {self.address}")
            reqmsg = self.request_message(download_piece.index, begin, block_size)
            begin += block_size
            self.sock.send(reqmsg)
            block = b''
            while len(block) < block_size + 13:  # Keep receiving until the full amount of data is received
                part = self.sock.recv(block_size + 13 - len(block))
                if part == b'':
                    break
                block += part
            downloaded += block_size
            decodedblock = self.decode_block(block)
            if type(decodedblock) == dict:
                if decodedblock['ID'] == 7:
                    counter += 1
                    piece += decodedblock['Block']
                else:
                    piece += block[9:]
        print(f"Finished downloading blocks for piece {piece_num} from peer {self.address}")
        print(f'Len of this piece: {len(piece)} vs the actual len: {self.torrent_instance.piece_length}')
        print(f'This piece hash value: {hashlib.sha1(piece).hexdigest()} vs our: {download_piece.hash_value.hex()}')
        if hashlib.sha1(piece).digest() == download_piece.hash_value:
            print(f'Downloaded piece number: {download_piece.index} from peer {self.address}, writing to disk now...')
            with open(r'C:\Users\gilth\PycharmProjects\BitTorrent 2.0\pieces\downloaded_piece_{}.bin'.format(
                    download_piece.index), 'wb') as f:
                f.write(piece)
                f.close()
            return True
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
                print(e)
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

    def have(self, index, piece_availability,available_pieces_lock):
        while available_pieces_lock:
            pass
        available_pieces_lock = True
        self.available_pieces[index] = True
        piece_availability[self.torrent_instance.get_piece(index)] += 1
        piece_availability = dict(sorted(piece_availability.items(), key=lambda x: x[1], reverse=True))
        available_pieces_lock = False
        return

    def bitfield(self, bitfield_list, piece_availability,available_pieces_lock):
        while available_pieces_lock:
            pass
        available_pieces_lock = True
        print(bitfield_list)
        for i in bitfield_list:
            self.available_pieces[i] = True
            piece_availability[self.torrent_instance.get_piece(i)] += 1
        piece_availability = dict(sorted(piece_availability.items(), key=lambda x: x[1], reverse=True))
        available_pieces_lock = False
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

    def decode_block(self, msg):
        block_length = len(msg) - 13
        block = struct.unpack(f">IBII{block_length}s", msg[:13 + block_length])
        block_dict = {'Len': block[0], 'ID': block[1], 'Piece index': block[2], 'Block offset': block[3],
                      'Block': block[4]}
        return block_dict

    def get_rarest_piece(self, piece_availability, download_queue):  # Function to get the rarest piece that the peer has
        no_pieces = True  # Flag to check if there are no pieces for the peer to download
        i = 0
        while no_pieces:  # Choose the rarest piece
            piece_availability_list = list(piece_availability.keys())
            rarest_piece = piece_availability_list[i]
            if download_queue[rarest_piece.index] != 0:
                continue
            print(f'Peer {self.address} Checking to download piece: {rarest_piece.index}')
            if self.available_pieces[rarest_piece.index]:
                no_pieces = False
            elif i == len(piece_availability) - 1:
                no_pieces = True
                break
            i += 1
        return no_pieces, rarest_piece
