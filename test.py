import bencodepy

with open(r'C:\Users\gilth\PycharmProjects\BitTorrent 2.0\Michael Jordan_ Mom Got Game.mp4.torrent', 'rb') as f:
    data = f.read()
    data = bencodepy.decode(data)
    print(data)
    f.close()
