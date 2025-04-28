import socket
import messages # our file
import json


def get_peer_list(tracker_host, tracker_port, info_hash):
    try:
        tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tracker_socket.connect((tracker_host, tracker_port))
        request = messages.make_request(info_hash) # function from a messages.py file
        tracker_socket.sendall(json.dumps(request).encode('utf-8'))
        response = tracker_socket.recv(1024)
        response_data = json.loads(response.decode('utf-8'))
        peer_list = response_data.get('peers', [])
        tracker_socket.close()
        return peer_list
    except Exception as e:
        print(f"Peer client: error occured while getting the peer list from the tracker: {e}")
        return []

def main():
    tracker_host = input("Peer client: enter the tracker host (for example, 'localhost' or '192.168.123.132'): ")
    tracker_port = int(input("Peer client: enter the tracker port (e.g., 4040): "))
    sha1_hash_input = input("Peer client: enter the SHA1 hash of the file you want to download (in hex format): ")

    try:
        info_hash = bytes.fromhex(sha1_hash_input)
    except ValueError:
        print("Peer client: invalid SHA1 hash format. Please try again")
        return
    
    print("Peer client: requesting the list of peers from the tracker...")
    peer_list = get_peer_list(tracker_host, tracker_port, info_hash)

    if not peer_list:
        print("Peer client: nobody has this file :((")
        return
    
    # here should be the logic to download a file 

import socket

HOST = '0.0.0.0'
PORT = 6889

def request(host, port, hash_value):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))


    # send the index as 4 bytes
    client_socket.sendall(piece_index.to_bytes(4, byteorder='big'))

    # get the piece length
    length = client_socket.recv(4)
    if not length:
        print("Peer client: there is no response from the server")
        return None

    piece_length = int.from_bytes(length, byteorder='big')
    if piece_length == 0:
        print("Peer client: there is no such piece on the server")
        return None

    print(f"Peer client: the piece is {piece_length} bytes")

    # read the piece 
    piece = b""
    while len(piece) < piece_length:
        chunk = client_socket.recv(piece_length - len(piece))
        if not chunk:
            break
        piece += chunk

    client_socket.close()
    return piece

if __name__ == "__main__":
    piece_index = 1

    piece = request(HOST, PORT, piece_index)
    if piece:
        print(f"[+] Downloaded piece {piece_index}: {piece}")
    else:
        print(f"[-] Failed to download piece {piece_index}")
