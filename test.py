import TorrentClass

if __name__ == '__main__':
    torrent = TorrentClass.TorrentClass(r"C:\Users\gilth\PycharmProjects\BitTorrent2.0\Dune Part 2 (1.6GB).torrent")
    print(torrent.number_of_pieces)