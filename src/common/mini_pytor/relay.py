"""Relay server class file"""
import pickle
import os
import select
import sys
import socket
import struct
import requests
import time

import cryptography.hazmat.primitives.asymmetric.padding
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from util import padder128, RELAY_DEBUG
from cell import Cell, CellType


class Client:
    """Client class"""
    def __init__(self, sock, key, generated_key):
        self.sock = sock
        self.key = key  # the derived key
        # the generated elliptic curve diffie hellman key.
        self.generated_key = generated_key
        self.bounce_ip = None
        self.bounce_port = None
        self.bounce_socket = None


class Relay():
    """Relay class"""
    CLIENTS = []
    CLIENT_SOCKS = []

    def __init__(self, port_number, identity=None):
        pem_file = os.path.join(
            os.path.dirname(__file__),
            "privates/privatetest" + str(identity) + ".pem"
        )
        temp_open = open(pem_file, "rb")
        self.true_private_key = serialization.load_pem_private_key(
            temp_open.read(), password=None, backend=default_backend())  # used for signing, etc.
        self.sendingpublickey = self.true_private_key.public_key()

        serialised_public_key = self.sendingpublickey.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo)
        # obtain the serialised public key for directory
        base_bytearray = os.urandom(128)
        # generate random bytearray with 128 bytes.
        signedbytearray = self.sign(base_bytearray)

        directorycell = Cell(serialised_public_key, signature=signedbytearray,
                             salt=base_bytearray, IV=port_number, ctype=CellType.GIVE_DIRECT)
        # store the byte array, signed version, serialised public key,
        # and actual port number for sending.

        self.directory_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.directory_socket.connect((socket.gethostbyname(socket.gethostname()), 50000))
        # connect to the directory server.
        self.directory_socket.send(pickle.dumps(directorycell))

        # begin listening for clientele.
        self.relay_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.relay_socket.bind(("", port_number))
        self.relay_socket.listen(100)

    @staticmethod
    def aes_decryptor(secret_key, provided_cell):
        """Decrypt provided_cell's payload with an AES key"""
        cipher = Cipher(
            algorithms.AES(secret_key),
            modes.CBC(provided_cell.init_vector),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(provided_cell.payload)
        decrypted += decryptor.finalize()  # finalise decryption
        return decrypted

    def sign(self, given_bytes):
        """Signs stuff."""
        signed_bytes = self.true_private_key.sign(  # sign byte array to prove you own the key
            given_bytes, cryptography.hazmat.primitives.asymmetric.padding.PSS(
                mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                    algorithm=hashes.SHA256()),
                salt_length=cryptography.hazmat.primitives.asymmetric.padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signed_bytes

    def rsa_decrypt(self, thing):
        """thing that is in RSA encryption must be decrypted before continuing."""
        return self.true_private_key.decrypt(
            thing,
            cryptography.hazmat.primitives.asymmetric.padding.OAEP(
                mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                    algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def exchange_keys(self, client_sock, obtained_cell):
        """Exchange Key with someone, obtaining a shared secret.
        Also, generate salt and pass it back to them with your private key."""

        private_key = ec.generate_private_key(
            ec.SECP384R1(), default_backend())  # elliptic curve
        public_key = private_key.public_key()  # duh same.
        serialised_public_key = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        # serialise the public key that I'm going to send them
        their_key = serialization.load_pem_public_key(
            obtained_cell.payload, backend=default_backend())
        shared_key = private_key.exchange(ec.ECDH(), their_key)
        salty = os.urandom(8)
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salty,
            info=None,
            backend=default_backend()
        ).derive(shared_key)
        reply_cell = Cell(serialised_public_key,
                          salt=salty, ctype=CellType.CONNECT_RESP)
        signature = self.sign(salty)  # sign the random bytes
        reply_cell.signature = signature  # assign the signature.
        if RELAY_DEBUG:
            print("reply cell")
            print(pickle.dumps(reply_cell))
        # send them the serialised version.
        client_sock.send(pickle.dumps(reply_cell))
        return private_key, derived_key

    def handle_client(self, client_sock):
        """A method to handle client connections."""
        obtained_cell = client_sock.recv(4096)
        try:
            if RELAY_DEBUG:
                print("raw data obtained. (Cell)")
                print(obtained_cell)
            # decrypt the item.
            obtained_cell = self.rsa_decrypt(obtained_cell)

        except ValueError:  # decryption failure
            print("Rejected one connection")
            return None

        if RELAY_DEBUG:
            print("Decrypted cell with actual keys.")
            print(obtained_cell)

        obtained_cell = pickle.loads(obtained_cell)
        if RELAY_DEBUG:
            print("after pickle load")
            print(obtained_cell)
        if obtained_cell.type != CellType.ADD_CON:  # wrongly generated cell!
            return None

        generated_privkey, derived_key = self.exchange_keys(client_sock, obtained_cell)
        client_class = Client(client_sock, derived_key, generated_privkey)
        client_name = client_class.sock.getpeername()
        self.CLIENTS.append(client_class)
        self.CLIENT_SOCKS.append(client_sock)
        print(f"Connected to client:{client_name}\n\n\n")
        return client_class

    @staticmethod
    def extend_circuit(cell_to_next, decrypted, client_reference, socket_to_client):
        """Extend the circuit"""
        try:
            sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((cell_to_next.ip_addr, cell_to_next.port))
            if RELAY_DEBUG:
                print((cell_to_next.ip_addr, cell_to_next.port))
                print("cell to next")
                print(decrypted)
                print("payload")
                print(cell_to_next.payload)
            # send over the cell payload
            sock.send(cell_to_next.payload)
            their_cell = sock.recv(4096)  # await answer
            if RELAY_DEBUG:
                print("got values")
                print(their_cell)
            if their_cell == b"":
                encrypted, init_vector = Relay.aes_encryptor(
                    client_reference.key,
                    padder128(pickle.dumps(Cell("", ctype=CellType.FAILED)))
                )

                if RELAY_DEBUG:
                    print("sent failed")
                socket_to_client.send(pickle.dumps(Cell(
                    encrypted,
                    IV=init_vector,
                    ctype=CellType.FAILED)))
            else:
                encrypted, init_vector = Relay.aes_encryptor(
                    client_reference.key,
                    padder128(pickle.dumps(Cell(their_cell, ctype=CellType.CONNECT_RESP)))
                )
                if RELAY_DEBUG:
                    print("sent valid response")
                socket_to_client.send(pickle.dumps(Cell(
                    encrypted,
                    IV=init_vector,
                    ctype=CellType.FINISHED
                )))
                client_reference.bounce_ip = cell_to_next.ip_addr
                client_reference.bounce_port = cell_to_next.port  # Save Next target addresses
                client_reference.bounce_socket = sock

                print("Connection success.\n\n\n\n\n")

        except (ConnectionRefusedError, ConnectionResetError,
                ConnectionAbortedError, struct.error,
                socket.timeout):
            print("failed to connect to other relay. "
                  + "sending back failure message, or timed out.")

            innercell = pickle.dumps(Cell("CONNECTIONREFUSED", ctype=CellType.FAILED))
            outercell = padder128(pickle.dumps(Cell(innercell, ctype=CellType.FAILED)))
            encrypted, init_vector = Relay.aes_encryptor(client_reference.key, outercell)
            socket_to_client.send(pickle.dumps(Cell(
                encrypted,
                IV=init_vector,
                ctype=CellType.FAILED
            )))
            print("sent back failure message.")

    @staticmethod
    def aes_encryptor(secret_key, provided_cell, ):
        """Encrypt something given a secret key. and data."""
        init_vector = os.urandom(16)
        cipher = Cipher(
            algorithms.AES(secret_key),
            modes.CBC(init_vector),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(provided_cell)
        encrypted += encryptor.finalize()  # finalise decryption
        return encrypted, init_vector

    @staticmethod
    def request_processing(cell_to_next, client_reference):
        """method to process a request."""
        print(cell_to_next.payload)
        if isinstance(cell_to_next.payload, str):
            request = cell_to_next.payload
            try:
                header = {
                    "User-Agent": "Mozilla/5.0 "
                                  + "(Windows NT 10.0; Win64; x64) "
                                  + "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  + "Chrome/70.0.3538.77 Safari/537.36"}

                req = requests.get(request, headers=header)
                print("length of answer" + str(len(req.content)))
            except requests.exceptions.ConnectionError:
                req = "ERROR"
                print("Failed to receive response from website")

            payloadbytes = pickle.dumps(req)
            if len(payloadbytes) > 4096:
                # print("was larger")
                payloadbytes = bytearray(payloadbytes)
                while len(payloadbytes) > 4096:
                    encrypted, init_vector = Relay.aes_encryptor(
                        client_reference.key,
                        padder128(pickle.dumps(Cell(
                            payloadbytes[:4096],
                            ctype=CellType.CONTINUE)))
                    )

                    client_reference.sock.send(pickle.dumps(
                        Cell(encrypted, IV=init_vector, ctype=CellType.ADD_CON)))
                    if RELAY_DEBUG:
                        print("sent one packet")
                    del payloadbytes[:4096]
                    # remove the bytes from the total bytes that have to be sent
                    time.sleep(10 / 1000000)
                    # slight delay for buffer issues

                # encrypt and send what is left.

                encrypted, init_vector = Relay.aes_encryptor(
                    client_reference.key,
                    padder128(pickle.dumps(Cell(
                        bytes(payloadbytes),
                        ctype=CellType.CONNECT_RESP)))
                )
                client_reference.sock.send(pickle.dumps(
                    Cell(encrypted, IV=init_vector, ctype=CellType.FINISHED)))
                print("finished sending valid replies.")
            else:
                encrypted, init_vector = Relay.aes_encryptor(
                    client_reference.key,
                    padder128(pickle.dumps(Cell(
                        payloadbytes,
                        ctype=CellType.CONNECT_RESP
                    )))
                )
                client_reference.sock.send(pickle.dumps(
                    Cell(encrypted, IV=init_vector, ctype=CellType.ADD_CON)))
                print("finished sending valid reply.")

        else:
            encrypted, init_vector = Relay.aes_encryptor(
                client_reference.key,
                padder128(pickle.dumps(Cell(
                    "INVALID REQUEST DUMDUM",
                    ctype=CellType.CONNECT_RESP
                )))
            )

            client_reference.sock.send(
                pickle.dumps(
                    Cell(encrypted, IV=init_vector, ctype=CellType.ADD_CON)
                ))
            print("INVALID REQUEST REPLIED")

    @staticmethod
    def relay(client_reference, decrypted, cell_to_next):
        """Method to Relay information to another relay, and stream information back."""
        if client_reference.bounce_socket is None:
            # There is no next hop registered to this client.
            return
        sock = client_reference.bounce_socket
        if RELAY_DEBUG:
            print("bouncing cell's decrypted..")
            print(decrypted)
            print("payload")
            print(cell_to_next.payload)
            print(cell_to_next.type)

        sock.send(cell_to_next.payload)  # send over the cell
        while True:
            try:
                their_cell = sock.recv(32768)  # await answer
            except socket.timeout:
                their_cell = "request timed out!"
            their_cell = pickle.loads(their_cell)
            if RELAY_DEBUG:
                print("relay reply received type")
                print(their_cell.type)
            if their_cell.type != CellType.FINISHED:
                print("got answer back.. as a relay.")
                encrypted, init_vector = Relay.aes_encryptor(
                    client_reference.key,
                    padder128(pickle.dumps(Cell(their_cell, ctype=CellType.CONNECT_RESP)))
                )
                client_reference.sock.send(pickle.dumps(Cell(
                    encrypted,
                    IV=init_vector,
                    ctype=CellType.CONTINUE
                )))
                print("relayed a packet.")
            else:
                print("received the last packet.")
                encrypted, init_vector = Relay.aes_encryptor(
                    client_reference.key,
                    padder128(
                        pickle.dumps(Cell(their_cell, ctype=CellType.FINISHED))
                    )
                )

                client_reference.sock.send(pickle.dumps(Cell(
                    encrypted,
                    IV=init_vector,
                    ctype=CellType.FINISHED
                )))
                print("relayed the last packet for this communication")
                break

        print("Relay success.\n\n\n\n\n")

    def run(self):
        """main method"""
        client_class = None  # initialise as none.
        read_ready, _, _ = select.select(
            [self.relay_socket] + self.CLIENT_SOCKS, [], [])
        for i in read_ready:
            if i == self.relay_socket:  # i've gotten a new connection
                print("Client connecting...")
                client_sock, _ = self.relay_socket.accept()
                client_sock.settimeout(0.3)
                try:
                    client_class = self.handle_client(client_sock)
                    if not client_class:  # client class is None
                        continue

                except (struct.error, ConnectionResetError,
                        socket.timeout, pickle.UnpicklingError,
                        pickle.PickleError):
                    print("ERROR! might have timed out, or inappropriate data was provided!")
                    if client_class is not None:
                        self.CLIENTS.remove(client_class)
                    continue

            else:  # came from an existing client.
                sending_client = None
                try:
                    for k in self.CLIENTS:
                        if k.sock == i:
                            sending_client = k  # identify the sending client.
                    received = i.recv(4096)
                    print("got a packet from an existing client")
                    if not received:  # received.. None. shouldn't be possible but in case.
                        raise ConnectionResetError

                except (struct.error, ConnectionResetError,
                        ConnectionAbortedError, socket.timeout):
                    print("Client was closed or timed out.")
                    # clean up the client and delete.
                    sending_client.sock.close()
                    if sending_client.bounce_socket is not None:
                        sending_client.bounce_socket.close()
                    self.CLIENT_SOCKS.remove(i)
                    self.CLIENTS.remove(sending_client)
                    continue

                gotten_cell = pickle.loads(received)
                decrypted = self.aes_decryptor(sending_client.key, gotten_cell)
                # decrypt the obtained cell
                cell_to_next = pickle.loads(decrypted)

                if RELAY_DEBUG:
                    print(f"Cell type: {cell_to_next.type}")

                if cell_to_next.type == CellType.RELAY_CONNECT:
                    # is a request for a relay connect
                    self.extend_circuit(cell_to_next, decrypted, sending_client, i)

                elif cell_to_next.type == CellType.RELAY:
                    # is a cell that is to be relayed.
                    self.relay(sending_client, decrypted, cell_to_next)

                elif cell_to_next.type == CellType.REQ:
                    self.request_processing(cell_to_next, sending_client)


def main():
    """Main function"""
    sys.argv = input("you know the drill. \n")  # added for my debug
    if len(sys.argv) == 1:  # was 2 -> 1
        identity = 3
        port = sys.argv[0]  # was 1 ->0
        if port == "a":
            port = 45000
            identity = 0
        elif port == "b":
            port = 45001
            identity = 1
        elif port == "c":
            port = 45002
            identity = 2
    else:
        print("Usage: python relay.py [port]")
        return

    relay = Relay(int(port), identity)
    print("Started relay on %d with identity %d" % (port, identity))

    while True:
        relay.run()


if __name__ == "__main__":
    main()
