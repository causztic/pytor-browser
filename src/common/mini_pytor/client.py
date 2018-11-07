"""Client class file"""

import pickle
import os
import json
import sys
import struct
import requests
import socket

import cryptography.hazmat.primitives.asymmetric.padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from http.server import BaseHTTPRequestHandler, HTTPServer
from util import padder128, CLIENT_DEBUG
from cell import Cell, CellType


class Relay():
    """relay class"""

    def __init__(self, ip, sock, derived_key, ec_key, rsa_key, port):
        self.ip_addr = ip
        self.sock = sock
        self.key = derived_key
        self.ec_key = ec_key
        self.rsa_key = rsa_key
        self.port = port


class Client():
    """Client class"""

    def __init__(self):
        print("re_init")
        self.relay_LIST = []
        # generate RSA public private key pair
        self.private_key = rsa.generate_private_key(
            backend=default_backend(), public_exponent=65537, key_size=3072)
        self.public_key = self.private_key.public_key()
        # serialised RSA public key.
        self.serialised_public_key = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    @staticmethod
    def make_first_connect_cell():
        """add method def"""
        ec_privkey = ec.generate_private_key(
            ec.SECP384R1(), default_backend())  # elliptic curve
        dh_pubkey_bytes = ec_privkey.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        # send the initialising cell, by sending the DHpublicKeyBytes
        sending_cell = Cell(dh_pubkey_bytes, ctype=CellType.ADD_CON)
        return sending_cell, ec_privkey

    def first_connect(self, gonnect, gonnectport, rsa_key_public):
        """you should already HAVE their public key."""
        try:
            # TCP connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((gonnect, gonnectport))
            sending_cell, ec_privkey = Client.make_first_connect_cell()
            # key encryption for RSA HERE USING SOME PUBLIC KEY
            readied_cell = pickle.dumps(sending_cell)
            if CLIENT_DEBUG:
                print("first connect Actual cell (encrypted bytes) ")
                print(readied_cell)
            encrypted_cell = rsa_key_public.encrypt(
                readied_cell,
                cryptography.hazmat.primitives.asymmetric.padding.OAEP(
                    mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                        algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            if CLIENT_DEBUG:
                print("first connect Actual cell(decrypted bytes)")
                print(encrypted_cell)
            sock.send(encrypted_cell)  # send my public key... tcp style
            their_cell = sock.recv(4096)
            their_cell = pickle.loads(their_cell)  # load up their cell
            if CLIENT_DEBUG:
                print(their_cell.type)

            # this cell isn't encrypted. Extract the signature to verify
            signature = their_cell.signature
            try:
                rsa_key_public.verify(
                    signature,
                    their_cell.salt,
                    cryptography.hazmat.primitives.asymmetric.padding.PSS(
                        mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                            algorithm=hashes.SHA256()),
                        salt_length=cryptography.hazmat.primitives
                        .asymmetric.padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                # verify that the cell was signed using their key.
                # load up their key.
                their_key = serialization.load_pem_public_key(
                    their_cell.payload, backend=default_backend())

                shared_key = ec_privkey.exchange(ec.ECDH(), their_key)
                derived_key = HKDF(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=their_cell.salt,
                    info=None,
                    backend=default_backend()
                ).derive(shared_key)
                # cipher = Cipher(algorithms.AES(derived_key), modes.CBC(IV),
                # backend=default_backend()) #256 bit length cipher lel
                # encryptor = cipher.encryptor()
                # ct = encryptor.update() + encryptor.finalize()
                # decryptor = cipher.decryptor()
                # decryptor.update(ct) + decryptor.finalize()

                # Connection is established at this point.
                if CLIENT_DEBUG:
                    print("connected successfully to relay @ " + gonnect
                          + "   Port: " + str(gonnectport))
                self.relay_LIST.append(
                    Relay(gonnect, sock, derived_key, ec_privkey, rsa_key_public, gonnectport))
                return   # a relay item is created.
            except InvalidSignature:
                if CLIENT_DEBUG:
                    print("Something went wrong.. Signature was invalid.")
                return
        except (struct.error, ConnectionResetError, ConnectionRefusedError):
            print("disconnected or relay is not online/ connection was refused.")

    def more_connect_1(self, gonnect, gonnectport, intermediate_relays, rsa_key):
        """must send IV and a cell that is encrypted with the next public key
        public key list will have to be accessed in order with list of relays.
        number between is to know when to stop i guess."""

        sending_cell, ec_privkey = Client.make_first_connect_cell()
        sending_cell = pickle.dumps(sending_cell)
        if CLIENT_DEBUG:
            print("Innermost cell with keys")
            print(sending_cell)
        sending_cell = rsa_key.encrypt(
            sending_cell,
            cryptography.hazmat.primitives.asymmetric.padding.OAEP(
                mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                    algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        if CLIENT_DEBUG:
            print("Innermost cell with keys (Encrypted)")
            print(sending_cell)
        # connection type. exit node always knows
        sending_cell = Cell(sending_cell, ctype=CellType.RELAY_CONNECT)
        sending_cell.ip_addr = gonnect
        # save the stuff i should be sending over.
        sending_cell.port = gonnectport
        init_vector = os.urandom(16)

        cipher = Cipher(
            algorithms.AES(intermediate_relays[0].key),
            modes.CBC(init_vector),
            backend=default_backend()
        )  # 256 bit length cipher lel
        encryptor = cipher.encryptor()  # encrypt the entire cell
        encrypted = encryptor.update(padder128(pickle.dumps(sending_cell)))
        encrypted += encryptor.finalize()  # finalise encryption.
        sending_cell = Cell(encrypted, IV=init_vector,
                            ctype=CellType.RELAY_CONNECT)

        try:
            sock = intermediate_relays[0].sock
            sock.send(pickle.dumps(sending_cell))  # send over the cell
            if CLIENT_DEBUG:
                print("cell sent: ")
                print(pickle.dumps(sending_cell))
            their_cell = sock.recv(4096)  # await answer
            # you now receive a cell with encrypted payload.
            counter = len(intermediate_relays) - 1
            their_cell = pickle.loads(their_cell)
            while counter >= 0:
                cipher = Cipher(
                    algorithms.AES(intermediate_relays[counter].key),
                    modes.CBC(their_cell.init_vector),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                decrypted = decryptor.update(their_cell.payload)
                decrypted += decryptor.finalize()  # finalise decryption
                if CLIENT_DEBUG:
                    print(decrypted)
                print(decrypted)
                their_cell = pickle.loads(decrypted)
                counter -= 1
                if CLIENT_DEBUG:
                    print(their_cell.payload)
                their_cell = pickle.loads(their_cell.payload)
            if their_cell.type == CellType.FAILED:
                if CLIENT_DEBUG:
                    print("FAILED AT CONNECTION!")
                if their_cell.payload == "CONNECTIONREFUSED":
                    print("Connection was refused. Is the relay online yet?")
                return
            # their_cell = pickle.loads(their_cell.payload)

            # this cell isn't encrypted. Extract the signature to verify
            signature = their_cell.signature
            their_cell.signature = None
            rsa_key.verify(
                signature,
                their_cell.salt,
                cryptography.hazmat.primitives.asymmetric.padding.PSS(
                    mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                        algorithm=hashes.SHA256()),
                    salt_length=cryptography.hazmat.primitives
                    .asymmetric.padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            # Verify that the cell was signed using their key.
            # At this point, you have the cell that is the public key of your target relay.
            # Additionally, salt too..

            # Load up their key.
            their_key = serialization.load_pem_public_key(
                their_cell.payload, backend=default_backend())
            shared_key = ec_privkey.exchange(ec.ECDH(), their_key)
            derived_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=their_cell.salt,
                info=None,
                backend=default_backend()
            ).derive(shared_key)
            self.relay_LIST.append(
                Relay(gonnect, sock, derived_key, ec_privkey, rsa_key, gonnectport))
            if CLIENT_DEBUG:
                print("connected successfully to relay @ " + gonnect
                      + "   Port: " + str(gonnectport))
        except (ConnectionResetError, ConnectionRefusedError, struct.error):
            if CLIENT_DEBUG:
                print("Socket Error, removing from the list.")
            del self.relay_LIST[0]  # remove it from the lsit
            if CLIENT_DEBUG:
                print("REMOVED relay 0 DUE TO FAILED CONNECTION")

    def more_connect_2(self, gonnect, gonnectport, intermediate_relays, rsa_key):
        """must send IV and a cell that is encrypted with the next public key
        public key list will have to be accessed in order with list of relays.
        number between is to know when to stop i guess."""

        sending_cell, ec_privkey = Client.make_first_connect_cell()
        sending_cell = pickle.dumps(sending_cell)
        if CLIENT_DEBUG:
            print("Innermost cell with keys")
            print(sending_cell)
        sending_cell = rsa_key.encrypt(
            sending_cell,
            cryptography.hazmat.primitives.asymmetric.padding.OAEP(
                mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                    algorithm=hashes.SHA256()
                ),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        if CLIENT_DEBUG:
            print("Innermost cell with keys (Encrypted)")
            print(sending_cell)
        # connection type. exit node always knows
        sending_cell = Cell(sending_cell, ctype=CellType.RELAY_CONNECT)
        sending_cell.ip_addr = gonnect
        # save the stuff i should be sending over.
        sending_cell.port = gonnectport
        init_vector = os.urandom(16)
        cipher = Cipher(
            algorithms.AES(intermediate_relays[1].key),
            modes.CBC(init_vector),
            backend=default_backend()
        )  # 256 bit length cipher lel
        encryptor = cipher.encryptor()  # encrypt the entire cell
        encrypted = encryptor.update(padder128(pickle.dumps(sending_cell)))
        encrypted += encryptor.finalize()  # finalise encryption.
        sending_cell = Cell(encrypted, IV=init_vector,
                            ctype=CellType.RELAY_CONNECT)
        sending_cell.ip_addr = intermediate_relays[1].ip_addr
        sending_cell.port = intermediate_relays[1].port
        sending_cell = Cell(pickle.dumps(sending_cell), ctype=CellType.RELAY)
        init_vector = os.urandom(16)

        cipher = Cipher(
            algorithms.AES(intermediate_relays[0].key),
            modes.CBC(init_vector),
            backend=default_backend()
        )  # 256 bit length cipher lel
        encryptor = cipher.encryptor()  # encrypt the entire cell
        encrypted = encryptor.update(padder128(pickle.dumps(sending_cell)))
        encrypted += encryptor.finalize()  # finalise encryption.
        sending_cell = Cell(encrypted, IV=init_vector, ctype=CellType.RELAY)
        sending_cell.ip_addr = intermediate_relays[0].ip_addr
        sending_cell.port = intermediate_relays[0].port
        try:
            sock = intermediate_relays[0].sock
            sock.send(pickle.dumps(sending_cell))  # send over the cell
            their_cell = sock.recv(4096)  # await answer
            # you now receive a cell with encrypted payload.
            if CLIENT_DEBUG:
                print(their_cell)
            their_cell = pickle.loads(their_cell)
            if CLIENT_DEBUG:
                print(their_cell.payload)
            counter = 0
            while counter < len(intermediate_relays):
                # print(their_cell.payload)
                cipher = Cipher(
                    algorithms.AES(intermediate_relays[counter].key),
                    modes.CBC(their_cell.init_vector),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                decrypted = decryptor.update(their_cell.payload)
                decrypted += decryptor.finalize()  # finalise decryption
                if CLIENT_DEBUG:
                    print(decrypted)
                their_cell = pickle.loads(decrypted)
                # print(their_cell.payload)
                counter += 1
                if counter < len(intermediate_relays):
                    their_cell = their_cell.payload

            if their_cell.type == CellType.FAILED:
                if CLIENT_DEBUG:
                    print("FAILED AT CONNECTION!")
                return
            # this cell isn't encrypted. Extract the signature to verify
            their_cell = pickle.loads(their_cell.payload)
            # print("new")
            # print(their_cell.signature)
            # print(their_cell.payload)

            signature = their_cell.signature
            their_cell.signature = None
            rsa_key.verify(
                signature,
                their_cell.salt,
                cryptography.hazmat.primitives.asymmetric.padding.PSS(
                    mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                        algorithm=hashes.SHA256()),
                    salt_length=cryptography.hazmat.primitives.asymmetric.padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            # Verify that the cell was signed using their key.
            # At this point, you have the cell that is the public key of your target relay.
            # Additionally, salt too...
            # Load up their key
            their_key = serialization.load_pem_public_key(
                their_cell.payload, backend=default_backend())
            shared_key = ec_privkey.exchange(ec.ECDH(), their_key)
            derived_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=their_cell.salt,
                info=None,
                backend=default_backend()
            ).derive(shared_key)
            self.relay_LIST.append(
                Relay(gonnect, sock, derived_key, ec_privkey, rsa_key, gonnectport))
            if CLIENT_DEBUG:
                print("connected successfully to relay @ " + gonnect
                      + "   Port: " + str(gonnectport))
        except struct.error:
            print("socket error occurred")

    def req(self, request, intermediate_relays):
        """send out stuff in router."""
        if CLIENT_DEBUG:
            print("REQUEST SENDING TEST")
        # must send IV and a cell that is encrypted with the next public key
        # public key list will have to be accessed in order with list of relays
        # number between is to know when to stop i guess.
        # connection type. exit node always knows
        sending_cell = Cell(request, ctype=CellType.REQ)
        init_vector = os.urandom(16)
        cipher = Cipher(
            algorithms.AES(intermediate_relays[2].key),
            modes.CBC(init_vector),
            backend=default_backend()
        )  # 256 bit length cipher lel
        encryptor = cipher.encryptor()  # encrypt the entire cell
        encrypted = encryptor.update(padder128(pickle.dumps(sending_cell)))
        encrypted += encryptor.finalize()  # finalise encryption.
        sending_cell = Cell(encrypted, IV=init_vector, ctype=CellType.RELAY)
        sending_cell.ip_addr = intermediate_relays[2].ip_addr
        sending_cell.port = intermediate_relays[2].port
        sending_cell = Cell(pickle.dumps(sending_cell), ctype=CellType.RELAY)

        init_vector = os.urandom(16)
        cipher = Cipher(algorithms.AES(intermediate_relays[1].key), modes.CBC(init_vector),
                        backend=default_backend())  # 256 bit length cipher lel
        encryptor = cipher.encryptor()  # encrypt the entire cell
        encrypted = encryptor.update(padder128(pickle.dumps(sending_cell)))
        encrypted += encryptor.finalize()  # finalise encryption.
        sending_cell = Cell(encrypted, IV=init_vector, ctype=CellType.RELAY)
        sending_cell.ip_addr = intermediate_relays[1].ip_addr
        sending_cell.port = intermediate_relays[1].port
        sending_cell = Cell(pickle.dumps(sending_cell), ctype=CellType.RELAY)
        init_vector = os.urandom(16)

        cipher = Cipher(algorithms.AES(intermediate_relays[0].key), modes.CBC(init_vector),
                        backend=default_backend())  # 256 bit length cipher lel
        encryptor = cipher.encryptor()  # encrypt the entire cell
        encrypted = encryptor.update(padder128(pickle.dumps(sending_cell)))
        encrypted += encryptor.finalize()  # finalise encryption
        sending_cell = Cell(encrypted, IV=init_vector, ctype=CellType.RELAY)
        sending_cell.ip_addr = intermediate_relays[0].ip_addr
        sending_cell.port = intermediate_relays[0].port
        try:
            sock = intermediate_relays[0].sock
            sock.send(pickle.dumps(sending_cell))  # send over the cell
            their_cell = sock.recv(8192)  # await answer
            # you now receive a cell with encrypted payload.
            if CLIENT_DEBUG:
                print("received cell")
                print(len(their_cell))
                print(their_cell)
            their_cell = pickle.loads(their_cell)
            if CLIENT_DEBUG:
                print("received cell payload")
                print(their_cell.payload)
            counter = 0
            while counter < len(intermediate_relays):
                cipher = Cipher(
                    algorithms.AES(intermediate_relays[counter].key),
                    modes.CBC(their_cell.init_vector),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                decrypted = decryptor.update(their_cell.payload)
                decrypted += decryptor.finalize()  # finalise decryption
                their_cell = pickle.loads(decrypted)
                counter += 1
                if counter < len(intermediate_relays):
                    their_cell = their_cell.payload

            if their_cell.type == CellType.FAILED:
                if CLIENT_DEBUG:
                    print("FAILED AT CONNECTION!")
                return
            elif their_cell.type == CellType.CONTINUE:
                if CLIENT_DEBUG:
                    print("Information is being Streamed. ")
                summation = their_cell.payload
                while their_cell.type == CellType.CONTINUE:
                    their_cell = sock.recv(8192)  # await answer
                    # you now receive a cell with encrypted payload.
                    if CLIENT_DEBUG:
                        print("received PART")
                        print(len(their_cell))
                        print(their_cell)
                    their_cell = pickle.loads(their_cell)
                    if CLIENT_DEBUG:
                        print("received cell payload")
                        print(their_cell.payload)
                    counter = 0
                    while counter < len(intermediate_relays):
                        cipher = Cipher(
                            algorithms.AES(intermediate_relays[counter].key),
                            modes.CBC(their_cell.init_vector),
                            backend=default_backend()
                        )
                        decryptor = cipher.decryptor()
                        decrypted = decryptor.update(their_cell.payload)
                        decrypted += decryptor.finalize()  # finalise decryption
                        their_cell = pickle.loads(decrypted)
                        counter += 1
                        if counter < len(intermediate_relays):
                            their_cell = their_cell.payload
                    summation += their_cell.payload
                response = bytes(summation)
                response = pickle.loads(response)
                if isinstance(response, requests.models.Response):
                    if CLIENT_DEBUG:
                        print(response.content)
                        print(response.status_code)
                    return_dict = {"content": response.content.decode(
                        response.encoding), "status code": response.status_code}
                    print(json.dumps(return_dict))
                    # print(response.json())
                    return response

                else:
                    # TODO - the error code should be specific to our implementation, not generic ones
                    # e.g. node offline, decryption failure etc etc
                    print(json.dumps({"content": "", "status": 404}))

            else:
                response = pickle.loads(their_cell.payload)
                if isinstance(response, requests.models.Response):
                    if CLIENT_DEBUG:
                        print(response.content)
                        print(response.status_code)
                    return_dict = {"content": response.content.decode(
                        response.encoding), "status code": response.status_code}
                    print(json.dumps(return_dict))
                    return response
                else:
                    # TODO - the error code should be specific to our implementation, not generic ones
                    # e.g. node offline, decryption failure etc etc
                    print(json.dumps({"content": "", "status": 404}))

        except struct.error:
            print("socketerror")

    def close(self):
        for i in self.relay_LIST:
            i.sock.close()
        pass


class Responder(BaseHTTPRequestHandler):
    def do_GET(self):
        my_client = Client()
        print("get")
        print(self.path)
        # given_args = sys.argv
        given_args = ["client.py", "localhost", "45000", "0", "localhost", "45001", "1", "localhost", "45002", "2",
                      ]
        # TODO - refactor and use argument parsers.
        # See https://docs.python.org/3/library/argparse.html
        for i, _ in enumerate(given_args):
            if given_args[i] == "localhost":
                given_args[i] = socket.gethostbyname(socket.gethostname())

        given_args[2] = int(given_args[2])
        given_args[5] = int(given_args[5])
        given_args[8] = int(given_args[8])
        # pem_prefix = "./mini_pytor/publics/publictest"
        pem_prefix = "publics/publictest"  # #### ADDDDDED

        # set up static chain.
        # TODO - get the client to query a directory for the relay keys instead of manually getting
        temp_open = open(pem_prefix + given_args[3] + ".pem", "rb")
        public_key = serialization.load_pem_public_key(
            temp_open.read(), backend=default_backend())
        temp_open.close()
        my_client.first_connect(given_args[1], given_args[2], public_key)

        temp_open = open(pem_prefix + given_args[6] + ".pem", "rb")
        public_key = serialization.load_pem_public_key(
            temp_open.read(), backend=default_backend())
        temp_open.close()
        my_client.more_connect_1(given_args[4], given_args[5],
                                 my_client.relay_LIST, public_key)

        temp_open = open(pem_prefix + given_args[9] + ".pem", "rb")
        public_key = serialization.load_pem_public_key(
            temp_open.read(), backend=default_backend())
        temp_open.close()
        my_client.more_connect_2(given_args[7], given_args[8],
                                 my_client.relay_LIST, public_key)

        obtained_response = my_client.req(self.path[2:], my_client.relay_LIST)
        self.send_response(obtained_response.status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes(obtained_response.content))
        my_client.close()


def main():
    """Main function"""
    server_address = ('', 27182)
    httpd = HTTPServer(server_address, Responder)
    httpd.serve_forever()
    """else:
        print("insufficient arguments\n"
              + "<relay 1 IP> <relay 1 Port> <key 1 number> "
              + "<relay 2 IP> <relay 2 Port> <key 2 number> "
              + "<relay 3 IP> <relay 3 Port> <key 3 number> <Website>\n"
              + "if localhost is IP, just leave it as localhost")
    """


if __name__ == "__main__":
    main()
