import hashlib
import math
import bencodepy
import re


class Piece:
    def __init__(self, index, size, hash_value):
        self.index = index
        self.size = size
        self.hash_value = hash_value


class TorrentClass:
    def __init__(self, file_path):
        with open(file_path, 'rb') as f:
            data = f.read()
            data = bencodepy.decode(data)
            f.close()

        self.name = data[b'info'][b'name'].decode('utf-8')
        self.info_hash = hashlib.sha1(bencodepy.encode(data[b"info"])).hexdigest()
        self.piece_length = data[b'info'][b'piece length']
        self.files = self.extract_files(data)
        self.size = self.calculate_total_size(data)
        self.announce_list = self.extract_announce_list(data)
        self.number_of_pieces = math.ceil(self.size / self.piece_length)
        self.piece_list = self.extract_piece_list(data)

    def extract_files(self, data):
        if b'files' in data[b'info']:
            return {file[b'path'][0].decode('utf-8'): file[b'length'] for file in data[b'info'][b'files']}
        else:
            return {self.name: data[b'info'][b'length']}

    def calculate_total_size(self, data):
        if b'files' in data[b'info']:
            return sum(file[b'length'] for file in data[b'info'][b'files'])
        else:
            return data[b'info'][b'length']

    def extract_announce_list(self, data):
        pattern = re.compile(r'(udp|http|https)://([\w.-]+)(?::(\d+))?')
        announce_list = []
        if b'announce-list' in data:
            for item in data[b'announce-list']:
                match = pattern.match(item[0].decode('utf-8'))
                if match:
                    protocol, host, port = match.groups()
                    if protocol == 'udp':
                        if port is None:
                            port = 6969
                        announce_list.append((host, int(port)))
        else:
            match = pattern.match(data[b'announce'].decode('utf-8'))
            if match:
                protocol, host, port = match.groups()
                if protocol == 'udp':
                    if port is None:
                        port = 6969
                    announce_list.append((host, int(port)))
        return announce_list

    def extract_piece_list(self, data):
        piece_size = self.piece_length
        pieces = data[b'info'][b'pieces']
        hash_list = [pieces[i:i + 20] for i in range(0, len(pieces), 20)]  # Split into 20-byte chunks
        piece_list = [Piece(index, piece_size, hash_value) for index, hash_value in enumerate(hash_list)]
        piece_list[len(piece_list) - 1].size = self.size - (self.number_of_pieces - 1) * self.piece_length
        return piece_list

    def get_piece(self,piece_index):
        for piece in self.piece_list:
            if piece.index == piece_index:
                return piece