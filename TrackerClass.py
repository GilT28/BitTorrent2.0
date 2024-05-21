import TorrentClass
import binascii
import random
import socket
import struct


class TrackerClass:
    def __init__(self, tracker_ip: tuple, sock: socket, torrent_instance: TorrentClass, peer_id: bytes):
        self.sock = sock  # Socket for communication
        self.sock.settimeout(5) # Timeout for the socket
        self.tracker_ip = tracker_ip  # The tracker IP
        self.torrent_instance = torrent_instance  # An instance of the Torrent class object
        self.connection_id = 0  # Connection id, will not be a 0 after a successful connection.
        self.peer_id = peer_id  # Random 20 bytes for the id
        self.peer_list = []

    def start_communicating(self):
        print(f'{self.tracker_ip} Connecting...')
        print(self.tracker_ip)
        self.sock.connect(self.tracker_ip)
        print(f'{self.tracker_ip} Connected! Sending connection message')
        con_msg, transaction_id = self.create_connection_msg()
        self.sock.send(con_msg)
        print(f'{self.tracker_ip} Connection message sent!')
        tracker_con_msg = self.decode_connection_msg(self.sock.recv(4096))  # Trackers own connection message
        if tracker_con_msg['action'] == 3 or tracker_con_msg['transaction_id'] != transaction_id:
            print(f'{self.tracker_ip} ERROR: invalid connection. breaking socket')
            return
        print(f'{self.tracker_ip} Received valid connection message: {tracker_con_msg}')
        print(f'{self.tracker_ip} Sending announce message')
        ann_msg, transaction_id = self.create_announce_msg(tracker_con_msg['connection_id'],
                                                           self.torrent_instance.info_hash, self.peer_id,
                                                           self.torrent_instance.size)
        self.sock.send(ann_msg)
        print(f'{self.tracker_ip} Announce message sent!')
        tracker_ann_msg = self.decode_announce_msg(self.sock.recv(4096))
        if tracker_ann_msg['action'] == 3 or tracker_ann_msg['transaction_id'] != transaction_id:
            print(f'{self.tracker_ip} ERROR: invalid connection. breaking socket')
            return
        print(f'{self.tracker_ip} Received valid announce message: {tracker_ann_msg}')
        self.peer_list = tracker_ann_msg['peer_list']
        return self.peer_list

    def create_connection_msg(self):  # Creates the connection message to be sent
        action = 0  # 0 For connecting
        transaction_id = random.randint(0, 0xffffffff)
        con_msg = struct.pack('!QII', 0x41727101980, action, transaction_id)
        return con_msg, transaction_id

    def create_announce_msg(self, connection_id, info_hash, peer_id, size):  # Creates the announce message to be sent
        action = 1  # Announcing
        transaction_id = random.randint(0, 0xffffffff)
        info_hash = binascii.a2b_hex(info_hash)
        downloaded = 0  # haven't downloaded a thing yet...
        left = size  # How many bytes are left to download
        ip = 0  # The ip the tracker will send messages to, 0 means that use the ip that is sending the messages
        key = random.randint(0, 0xffffffff)  # Random key
        num_want = -1  # The tracker will send the amount of peer based on this variable, -1 for normal amount
        port = 6881
        uploaded = 0  # Haven't uploaded a thing yet...
        event = 2  # 2 for starting to download 0 for none
        msg = struct.pack('!QII20s20sQQQIIIiH', connection_id, action, transaction_id, info_hash, peer_id, downloaded,
                          left,
                          uploaded, event, ip, key, num_want, port)
        return msg, transaction_id

    def decode_connection_msg(self, msg):
        action, transaction_id, connection_id = struct.unpack('!IIQ', msg)
        decoded_msg = {'action': action, 'transaction_id': transaction_id, 'connection_id': connection_id}
        return decoded_msg

    def decode_announce_msg(self, msg):
        action, transaction_id, interval, leechers, seeders = struct.unpack('!IIIII',
                                                                            msg[:20])  # 20 bytes are the fixed amount
        ip_and_port_list = []
        i = 20
        while i in range(len(msg)):  # Receiving unfixed amount of bytes
            ip = socket.inet_ntoa(msg[i:i + 4])  # Bytes to string ip
            port = struct.unpack('!H', msg[i + 4:i + 6])[
                0]  # Unpacking port, H for unsigned short. ([0] because struct.unpack returns tuple).
            peer = (ip, port)
            ip_and_port_list.append(peer)
            i += 6

        response_dict = {'action': action, 'transaction_id': transaction_id, 'interval': interval, 'leechers': leechers,
                         'seeders': seeders, 'peer_list': ip_and_port_list}

        return response_dict
