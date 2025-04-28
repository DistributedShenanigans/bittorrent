import socket
from threading import Thread
import messages # our file

HOST = '0.0.0.0'
PORT = 6889

# change to real files
pieces_by_hash = {
    bytes.fromhex('3d32f08b4374c1c1ff717a8ba4a8988e85b2e973'): b"This is piece 0",
    bytes.fromhex('97d6b5aaed1bc74f681b0411c04680f4f49963cf'): b"This is piece 1",
    bytes.fromhex('b7051c40b13515f65da3622ab1e5a2a077d5a3b1'): b"This is piece 2",
}

def handle_connection(client_socket, addr):
    print(f"Peer server: got connection from the peer {addr}")
    try:
        handshake = client_socket.recv(1024)
        handshake_valid = messages.validate_handshake(handshake)

        if not handshake_valid:
            print("Peer server: the handshake is invalid, closing the connection with the peer")
            return
        
        print("Peer server: the handshake is validated")
        
        # the SHA1 value of the requested piece
        hash_value = client_socket.recv(20)  # SHA-1 is 20 bytes long

        if not hash_value:
            return

        # find the content and send
        piece = pieces_by_hash.get(hash_value, None)

        if piece:
            length = len(piece)
            # send the size of the file
            client_socket.sendall(length.to_bytes(4, byteorder='big'))
            CHUNK_SIZE = 65536 # one chunk is 64 KB long
            sent = 0
            while sent < length:
                chunk_end = min(sent + CHUNK_SIZE, length) 
                chunk = piece[sent:chunk_end]
                client_socket.sendall(chunk)
                sent += len(chunk)
        else:
            print("Peer server: piece not found for given SHA1.")
            client_socket.sendall((0).to_bytes(4, byteorder='big'))
    finally:
        client_socket.close()


def server(host=HOST, port=PORT):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"Peer server: listening on {HOST}:{port}")

    while True:
        conn, addr = server.accept()
        Thread(target=handle_connection, args=(conn, addr)).start()

if __name__ == "__main__":
    server()