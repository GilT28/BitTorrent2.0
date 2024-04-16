import binascii
import hashlib
import socket
import struct
import time

import TorrentClass


class PeerClass:
    def __init__(self, address: tuple, sock: socket,peer_id: bytes, torrent_instance: TorrentClass):
        self.address = address
        self.sock = sock
        self.peer_id = peer_id
        self.torrent_instance = torrent_instance
        self.available_pieces = {piece: False for piece in range(0,torrent_instance.number_of_pieces)} # false if peer doesn't have piece, true if peer does have piece
        self.peer_choked = True

    def connect(self):
        print(f'{self.address} Connecting to peer...')
        self.sock.connect(self.address)
        print(f'{self.address} Connected to peer, sending handshake')
        handshake = self.create_handshake(self.torrent_instance.info_hash, self.peer_id)
        self.sock.send(handshake)
        print(f'{self.address} Handshake sent!')
        handshake_data = self.recv_handshake()
        if isinstance(handshake_data, bytes) and len(handshake_data) == 68 and handshake_data[1:20:] == b'BitTorrent protocol':
            print('Received valid connection')
            return True
        return False


    def peer_handler(self,download_queue):
        start_time = time.time()
        while True:
            current_time = time.time()
            if not self.peer_choked and not download_queue.empty():
                p = download_queue.get()
                print(f'Checking to download piece: {p}')
                if self.available_pieces[p]:
                    print(f'Downloading piece: {p}')
                    flag = self.download_piece(p)
                    if flag == True:
                        print(f'Downloaded piece {p}!')
                        #download_queue.task_done()
                    else:
                        download_queue.put(p)
                else:
                    download_queue.put(p)
            if current_time - start_time >= 120:
                keep_alive = struct.pack('!I', 0)
                self.sock.send(keep_alive)
                start_time = current_time
            msg = self.sock.recv(4096)
            self.response_handler(msg)

    def response_handler(self,msg):
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
                self.have(piece_index)
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
                print(bitfield_list)
                self.bitfield(bitfield_list)


    def download_piece(self,piece_num):
        download_piece = self.torrent_instance.get_piece(piece_num)
        block_size = 16384
        if self.torrent_instance.piece_length < 16384:
            block_size = self.torrent_instance.piece_length
        block_size_list = self.block_offset(download_piece.size, block_size)
        begin = 0
        counter = 0
        piece = b''
        downloaded = 0
        for block_size in block_size_list:
            reqmsg = self.request_message(download_piece.index, begin, block_size)
            begin += block_size
            self.sock.send(reqmsg)
            block = self.sock.recv(18000)
            downloaded += block_size
            decodedblock = self.decode_block(block)
            if type(decodedblock) == dict:
                if decodedblock['ID'] == 7:
                    counter += 1
                    piece += decodedblock['Block']
                else:
                    piece += block
        print(f'Len of this piece: {len(piece)} vs the actual len: {self.torrent_instance.piece_length}')
        print(f'This piece hash value: {hashlib.sha1(piece).hexdigest()} vs our: {download_piece.hash_value.hex()}')
        if hashlib.sha1(piece).hexdigest() == download_piece.hash_value.hex():
            print('Downloaded piece number: ', download_piece.index, ' writing to disk now...')

            # Writing the piece to disk
            with open('downloaded_piece_{}.bin'.format(download_piece.index), 'wb') as f:
                f.write(piece)
            return True
        return False
    def create_handshake(self,info_hash,peer_id):
        info_hash = binascii.a2b_hex(info_hash)
        msg = struct.pack('!B19sQ20s20s', 19, 'BitTorrent protocol'.encode(), 0, info_hash, peer_id)
        return msg

    def create_msg(self,id):
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

    def have(self,index):
        self.available_pieces[index] = True
        return

    def bitfield(self,bitfield_list):
        for i in bitfield_list:
            self.available_pieces[i] = True
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
        block = struct.unpack(">IBII{}s".format(block_length), msg[:13 + block_length])
        block_dict = {'Len': block[0], 'ID': block[1], 'Piece index': block[2], 'Block offset': block[3],
                     'Block': block[4]}
        return block_dict