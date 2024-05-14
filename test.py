import TorrentClass
import random
torrent_instance = TorrentClass.TorrentClass(
        r'C:\Users\gilth\PycharmProjects\BitTorrent 2.0\Selena Gomez & Marshmello - Wolves (Single) (2017) (Mp3 320kbps).torrent')
piece_availability = {piece: 0 for piece in torrent_instance.piece_list}  # 0 means that no peer has the piece
download_queue = [1 for piece in range(0, torrent_instance.number_of_pieces)]  # Queue of pieces to download



for i in range(20):
    r_int = random.randint(0, torrent_instance.number_of_pieces-1)
    piece_availability[torrent_instance.get_piece(r_int)] += 1

piece_availability = sorted(piece_availability.items(), key=lambda x: x[1], reverse=True)
piece_availability = dict(piece_availability)
print(piece_availability)