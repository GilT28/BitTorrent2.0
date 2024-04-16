import TorrentClass

torrent_instance = TorrentClass.TorrentClass(
        r'C:\Users\gilth\PycharmProjects\BitTorrent 2.0\torrent example.torrent')

sum = 0
for i in torrent_instance.piece_list:
    sum += i.size
print(sum)
print(torrent_instance.size)
