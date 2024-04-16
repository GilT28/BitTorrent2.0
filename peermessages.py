import struct
import binascii

def createhandshakemsg(peerid,infohash):
    infohash = binascii.a2b_hex(infohash)
    msg = struct.pack('!B19sQ20s20s',19,'BitTorrent protocol'.encode(),0,infohash,peerid)
    return msg

def decodehandshakeresponse(response):
    response = struct.unpack('!c19s8s20s20s',response)
    responsedict = {'PstrLen':int.from_bytes(response[0], "big"),'Pstr':response[1].decode(),'Reserved':response[2].hex(),'Info-hash':response[3].hex(),'Peer-ID':response[4].hex()}
    return responsedict

def createmsgforpeer(id):
    msg = struct.pack('!IB',1,id)
    return msg

def decodepeerresponse(msg,peer): #Must use python 3.10 or newer for this!
    if peer.isbusy == False:
        if len(msg) == 4:
            return 'nothing'
        if len(msg) == 5:
            id = msg[4]
            match id:
                case 0: # Choke
                    print('Choked')
                    return 'choked'
                case 1: # Unchoked
                    peer.peerchoked = False
                    print('UnChoked')
                    return 'unchoked'
                case 2 | 3: #Interested/Uninterested
                    print('Interested/Uninterested')
                    return 'nothing'
        if len(msg) > 5:
            id = msg[4]
            payload = msg[5:]
            if id == 4: # Have
                print('Have')
                piece_index = payload
                return piece_index
            if id == 5: # Bitfield
                print('Bitfield')
                temppiecelist = []
                piecelist = []
                piececounter = 0
                pack_format = '!'
                for byte in payload:
                    pack_format += 'B'
                bytes_tuple = struct.unpack(pack_format, payload)
                for i in range(len(bytes_tuple)):
                    bits = '{0:08b}'.format(bytes_tuple[i])
                    temppiecelist.append(bits)
                for i in temppiecelist:
                    for j in i:
                        if int(j) == 1:
                            piecelist.append(piececounter)
                            piececounter += 1
                        else:
                            piececounter += 1
                return piecelist
        return 'nothing'

def createrequestmessage(pieceindex,begin,blocksize): #Block size = 16384 bytes
    msg = struct.pack('!IBIII',13,6,pieceindex,begin,blocksize)
    return msg


def blockoffsetcalc(piecesize,blocksize):
    times = piecesize / blocksize
    l = []
    for i in range(int(times)):
        l.append(blocksize)
    if not times.is_integer():
        l.append(int(blocksize * (times - int(times))))
    return l
def decodepiecemsg(msg):
    block_length = len(msg) - 13
    piece = struct.unpack(">IBII{}s".format(block_length), msg[:13 + block_length])
    piecedict = {'Len': piece[0], 'ID': piece[1], 'Piece index': piece[2], 'Block offset': piece[3],
                 'Block': piece[4]}
    return piecedict