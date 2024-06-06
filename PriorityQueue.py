import heapq
import threading
from TorrentClass import Piece


class PriorityQueue:
    def __init__(self):
        self.heap = []
        self.lock = threading.Lock()
        self.index_map = {}

    def initialize_queue(self, piece_list):
        with self.lock:
            self.heap = piece_list[:]
            heapq.heapify(self.heap)
            self.index_map = {piece.index: piece for piece in piece_list}

    def push(self, piece_index):
        with self.lock:
            piece = self.index_map.get(piece_index)
            heapq.heappush(self.heap, piece)
            self.index_map[piece.index] = piece

    def pop(self):
        with self.lock:
            if self.heap:
                piece = heapq.heappop(self.heap)
                self.index_map.pop(piece.index, None)
                return piece
            else:
                return None

    def update_piece_rarity(self, piece_index):
        with self.lock:
            piece = self.index_map.get(piece_index)
            if piece:
                piece.rarity += 1
                # To maintain the heap property after updating the rarity,
                # We remove the piece and reinsert it
                self.heap.remove(piece)
                heapq.heappush(self.heap, piece)

    def update_download_status(self, piece_index, download_status):
        with self.lock:
            piece = self.index_map.get(piece_index)
            piece.download_status = download_status

    def get_download_status(self, piece_index):
        with self.lock:
            return self.index_map.get(piece_index).download_status

    def get_piece(self, piece_index):
        with self.lock:
            return self.index_map.get(piece_index)
