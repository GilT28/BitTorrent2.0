import socket
import peermessages
import peerclass
import time
import threading
import struct
import hashlib

def connecttopeer(peerip,torrent,piecemanager,filesmanager):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, )
        sock.setblocking(True)
        sock.connect(peerip)
        print('Connected to peer!')
        sock.send(peermessages.createhandshakemsg(torrent.peerid, torrent.infohash))
        print('Sent Handshake!')
        handshakeresponse = sock.recv(68)
        print('Received handshake response')
        if len(handshakeresponse) > 68 or len(handshakeresponse) < 68:
            print('Received invalid handshake response...')
        else:
            handshakeresponse = peermessages.decodehandshakeresponse(handshakeresponse)
            print(handshakeresponse)
            if handshakeresponse['Pstr'] == 'BitTorrent protocol' and handshakeresponse[
                'Info-hash'] == torrent.infohash:
                print('Received valid handshake response!')
                peer = peerclass.peer(peerip, handshakeresponse['Peer-ID'], True)
                peer.active = True
                torrent.activepeers.append(peer)
                threading.Thread(target=keepalive, args=(peer, sock)).start()
                threading.Thread(target=peermessageexchange, args=(peer,sock,piecemanager,torrent)).start()
                threading.Thread(target=download, args=(peer, sock, piecemanager, torrent,filesmanager)).start()
            else:
                print('Received Invalid handshake response...')
                return
    except Exception as e:
        print(e)

def peermessageexchange(peer,sock,piecemanager,torrent):
    msg = peermessages.createmsgforpeer(2)
    sock.send(msg)
    while peer.needtocom:
        #ready = select.select([sock], [], [], 30)  # 0 for temp 30 for default
        #if ready[0]:
            msg = sock.recv(4096)
            job = peermessages.decodepeerresponse(msg,peer)
            if job == 'choked':
                choked(peer)
            if job == 'unchoke':
                unchoke(peer)
            if job == 'nothing':
                pass
            if type(job) == int:
                have(peer, piecemanager, job)
            if type(job) == list:
                bitfield(peer, piecemanager, job)
            if peer.peerchoked:
                sock.send(peermessages.createmsgforpeer(2))
    peer.active = False
    torrent.activepeers.remove(peer)
    sock.shutdown(socket.SHUT_RDWR)

def keepalive(peer,sock):
    try:
        while peer.peerchoked:
            msg = struct.pack('!I',0)
            sock.send(msg)
            time.sleep(30)
    except Exception:
        pass

def download(peer,sock,piecemanager,torrent,filesmanager):
    while peer.needtocom:
        if peer.startdownload:
            if peer.peerchoked == False:
                peer.isbusy = True
                blocksize = 16384
                if torrent.piece_length < 16384:
                    blocksize = torrent.piece_length
                blocksizelist = peermessages.blockoffsetcalc(peer.whatpiecetodownload.piece_size, blocksize)
                begin = 0
                counter = 0
                piece = b''
                downloaded = 0
                for blocksize in blocksizelist:
                    reqmsg = peermessages.createrequestmessage(peer.whatpiecetodownload.piece_index,begin,blocksize)
                    begin +=blocksize
                    sock.send(reqmsg)
                    block = sock.recv(18000)
                    downloaded += blocksize
                    torrent.downloadspeed += blocksize
                    decodedblock = peermessages.decodepiecemsg(block)
                    if type(decodedblock) == dict:
                        if decodedblock['ID'] == 7:
                            counter += 1
                            piece += decodedblock['Block']
                        else:
                            piece += block
                torrent.downloadspeed -= downloaded
                if hashlib.sha1(piece).hexdigest() == peer.whatpiecetodownload.piece_hash.hex():
                    print('Downloaded piece number: ',peer.whatpiecetodownload.piece_index,' writing to disk now...')
                    byteoffset = 0
                    for prevpiece in torrent.pieceslist:
                        if prevpiece.piece_index < peer.whatpiecetodownload.piece_index:
                            byteoffset += prevpiece.piece_size
                    filesmanager.writetofile(peer.whatpiecetodownload.piece_index,byteoffset,piece)
                    peer.isbusy = False
                    peer.startdownload = False
                    piecemanager.insertpiecestate(piecemanager.getpiecefromindex(peer.ownedpieces[0]),2)
                    torrent.downloaded += downloaded
                    peer.ownedpieces.remove(peer.whatpiecetodownload.piece_index)
                    del torrent.downloadmanager.queue[peer]

def choked(peer):
    peer.peerchoked = True
    peer.needtocom = False
    return

def unchoke(peer):
    peer.peerchoked = False
    return

def have(peer,piecemanager,job):
    peer.insertownedpieces(job)
    piecemanager.insertpiecestate(piecemanager.getpiecefromindex(job), 1)
    return

def bitfield(peer,piecemanager,job):
    for i in job:
        peer.insertownedpieces(i)
        piecemanager.insertpiecestate(piecemanager.getpiecefromindex(i), 1)
    return