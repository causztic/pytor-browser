"""Client class file"""

import pickle
import os
import json
import struct
import socket
import requests
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
from util import padder128, CLIENT_DEBUG, RegisteredRelay
from cell import Cell, CellType


class Relay:
    """relay data class"""
    def __init__(self, given_ip, provided_socket, derived_key, ec_privkey,
                 given_rsa_key, given_port):

        self.ip_addr = given_ip
        self.sock = provided_socket
        self.key = derived_key
        self.ec_key_ = ec_privkey
        self.rsa_key = given_rsa_key
        self.port = given_port


class Client:
    """Client class"""

    def __init__(self):
        self.relay_list = []
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
    def getdirectoryitems():
        """Method to obtain items from directory"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((socket.gethostbyname(socket.gethostname()), 50000))  # connect to directory
        sock.send(pickle.dumps(Cell("", ctype=CellType.GET_DIRECT)))
        received_cell = sock.recv(32768)
        received_cell = pickle.loads(received_cell)
        if isinstance(received_cell.payload, list):
            print(received_cell.payload)
        return received_cell.payload

    @staticmethod
    def make_first_connect_cell(rsa_public_key):
        """Create the cell that is used to initiate a connection with any relay."""
        ec_privkey = ec.generate_private_key(
            ec.SECP384R1(), default_backend())  # elliptic curve
        dh_pubkey_bytes = ec_privkey.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        # send the initialising cell, by sending the DHpublicKeyBytes
        sending_cell = Cell(dh_pubkey_bytes, ctype=CellType.ADD_CON)
        readied_cell = pickle.dumps(sending_cell)
        if CLIENT_DEBUG:
            print("first connect Actual cell (encrypted bytes) ")
            print(readied_cell)
        encrypted_cell = rsa_public_key.encrypt(
            readied_cell,
            cryptography.hazmat.primitives.asymmetric.padding.OAEP(  # encrypt the readied cell.
                mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                    algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return encrypted_cell, ec_privkey  # return my generated ecdhe key and the encrypted cell

    @staticmethod
    def check_signature_and_derive(provided_cell, rsa_key, private_ecdhe):
        """given a cell, attempt to verify payload. Afterwards, derive shared key."""
        signature = provided_cell.signature
        try:
            rsa_key.verify(
                signature,
                provided_cell.salt,
                cryptography.hazmat.primitives.asymmetric.padding.PSS(
                    mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                        algorithm=hashes.SHA256()),
                    salt_length=cryptography.hazmat.primitives.asymmetric.padding.PSS.MAX_LENGTH
                ), hashes.SHA256()
            )

            # verify that the cell was signed using their key.
            # load up their half of the ecdhe key
            their_ecdhe_key = serialization.load_pem_public_key(
                provided_cell.payload, backend=default_backend())
            shared_key = private_ecdhe.exchange(ec.ECDH(), their_ecdhe_key)
            derived_key = HKDF(
                algorithm=hashes.SHA256(), length=32,
                salt=provided_cell.salt, info=None, backend=default_backend()
            ).derive(shared_key)

            # derived key is returned
            return derived_key

        except InvalidSignature:
            if CLIENT_DEBUG:
                print("Something went wrong.. Signature was invalid.")
            return None

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

    @staticmethod
    def aes_encryptor(secret_key, prepared_cell):
        """a method to encrypt with AES. returns the initial vector and the encrypted cell."""
        init_vector = os.urandom(16)
        cipher = Cipher(
            algorithms.AES(secret_key),
            modes.CBC(init_vector),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()  # encrypt the entire cell
        encrypted = encryptor.update(padder128(pickle.dumps(prepared_cell)))
        encrypted += encryptor.finalize()  # finalise encryption.
        return init_vector, encrypted

    def first_connect(self, gonnect, gonnectport, rsa_key):
        """Connect to the first Relay of the trio"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((gonnect, gonnectport))
            encrypted_cell, ec_privkey = Client.make_first_connect_cell(rsa_key)
            if CLIENT_DEBUG:
                print("first connect Actual cell(decrypted bytes)")
                print(encrypted_cell)
            sock.send(encrypted_cell)  # Send them my generated ecdhe key.
            their_cell = sock.recv(4096)  # await a response.
            their_cell = pickle.loads(their_cell)
            derived_key = self.check_signature_and_derive(
                their_cell,
                rsa_key,
                ec_privkey)
            # attempt to check the signature and derive their key.

            if derived_key:  # ie did not return None.
                if CLIENT_DEBUG:
                    print("connected successfully to relay @ " + gonnect
                          + "   Port: " + str(gonnectport))
                self.relay_list.append(
                    Relay(gonnect, sock, derived_key, ec_privkey, rsa_key, gonnectport))
                return

            else:  # Verification error or Unpacking Error occurred
                print("verification of signature failed/Invalid cell was received.")
                return
        except (struct.error, ConnectionResetError, ConnectionRefusedError):
            print("disconnected or relay is not online/ connection was refused.")

    def more_connect_1(self, gonnect, gonnectport, intermediate_relays, rsa_key):
        """Connect to the next relay through the first one."""
        encrypted_cell, ec_privkey = Client.make_first_connect_cell(rsa_key)
        if CLIENT_DEBUG:
            print("Innermost cell with keys (Encrypted)")
            print(encrypted_cell)

        sending_cell = Cell(encrypted_cell, ctype=CellType.RELAY_CONNECT)
        sending_cell.ip_addr = gonnect
        sending_cell.port = gonnectport
        # inform of next port of call.
        init_vector, encrypted_cell = Client.aes_encryptor(intermediate_relays[0].key, sending_cell)
        sending_cell = Cell(encrypted_cell, IV=init_vector,
                            ctype=CellType.RELAY_CONNECT)
        # wrap in another cell to save init_vector

        try:
            sock = intermediate_relays[0].sock
            sock.send(pickle.dumps(sending_cell))  # send over the cell
            if CLIENT_DEBUG:
                print("cell sent: ")
                print(pickle.dumps(sending_cell))
            their_cell = sock.recv(4096)  # await answer
            # you now receive a cell with encrypted payload.
            their_cell = pickle.loads(their_cell)
            decrypted = Client.aes_decryptor(intermediate_relays[0].key, their_cell)
            if CLIENT_DEBUG:
                print(decrypted)
            their_cell = pickle.loads(decrypted)
            if CLIENT_DEBUG:
                print(their_cell.payload)
            their_cell = pickle.loads(their_cell.payload)
            if their_cell.type == CellType.FAILED:
                if CLIENT_DEBUG:
                    print("FAILED AT CONNECTION!")
                if their_cell.payload == "CONNECTIONREFUSED":
                    print("Connection was refused. Is the relay online yet?")
                return

            derived_key = self.check_signature_and_derive(their_cell, rsa_key, ec_privkey)

            self.relay_list.append(
                Relay(gonnect, sock, derived_key, ec_privkey, rsa_key, gonnectport))

            if CLIENT_DEBUG:
                print("connected successfully to relay @ " + gonnect
                      + "   Port: " + str(gonnectport))

        except (ConnectionResetError, ConnectionRefusedError, struct.error):
            if CLIENT_DEBUG:
                print("Socket Error, removing from the list.")
            del self.relay_list[0]  # remove it from the lsit
            if CLIENT_DEBUG:
                print("REMOVED relay 0 DUE TO FAILED CONNECTION")

    def more_connect_2(self, gonnect, gonnectport, intermediate_relays, rsa_key):
        """Connect to the next relay through my 2 connected relays."""

        encrypted_cell, ec_privkey = Client.make_first_connect_cell(rsa_key)
        if CLIENT_DEBUG:
            print("Innermost cell with keys (Encrypted)")
            print(encrypted_cell)
        # connection type. exit node always knows
        sending_cell = Cell(encrypted_cell, ctype=CellType.RELAY_CONNECT)
        # Deepest layer, encrypted with RSA
        sending_cell.ip_addr = gonnect
        sending_cell.port = gonnectport
        # inform of next port of call.
        init_vector, encrypted_cell = Client.aes_encryptor(intermediate_relays[1].key, sending_cell)
        # encrypt using said keys.
        sending_cell = Cell(encrypted_cell, IV=init_vector, ctype=CellType.RELAY_CONNECT)
        # 2nd Layer from top

        sending_cell.ip_addr = intermediate_relays[1].ip_addr
        sending_cell.port = intermediate_relays[1].port
        # inform of next port of call again.
        sending_cell = Cell(pickle.dumps(sending_cell), ctype=CellType.RELAY)

        init_vector, encrypted_cell = Client.aes_encryptor(intermediate_relays[0].key, sending_cell)
        sending_cell = Cell(encrypted_cell, IV=init_vector, ctype=CellType.RELAY)  # Outermost layer
        sending_cell.ip_addr = intermediate_relays[0].ip_addr
        sending_cell.port = intermediate_relays[0].port
        # inform of next port of call one more time

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
                decrypted = Client.aes_decryptor(intermediate_relays[counter].key, their_cell)
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

            their_cell = pickle.loads(their_cell.payload)
            derived_key = self.check_signature_and_derive(their_cell, rsa_key, ec_privkey)

            self.relay_list.append(
                Relay(gonnect, sock, derived_key, ec_privkey, rsa_key, gonnectport))

            if CLIENT_DEBUG:
                print("connected successfully to relay @ " + gonnect
                      + "   Port: " + str(gonnectport))
        except struct.error:
            print("socket error occurred")

    @staticmethod
    def req_wrapper(request,relay_list):
        sending_cell = Cell(request, ctype=CellType.REQ)
        # generate True payload

        init_vector, encrypted_cell = Client.aes_encryptor(relay_list[2].key, sending_cell)
        sending_cell = Cell(encrypted_cell, IV=init_vector, ctype=CellType.RELAY)
        sending_cell.ip_addr = relay_list[2].ip_addr
        sending_cell.port = relay_list[2].port
        sending_cell = Cell(pickle.dumps(sending_cell), ctype=CellType.RELAY)

        init_vector, encrypted_cell = Client.aes_encryptor(relay_list[1].key, sending_cell)
        sending_cell = Cell(encrypted_cell, IV=init_vector, ctype=CellType.RELAY)
        sending_cell.ip_addr = relay_list[1].ip_addr
        sending_cell.port = relay_list[1].port
        sending_cell = Cell(pickle.dumps(sending_cell), ctype=CellType.RELAY)

        init_vector, encrypted_cell = Client.aes_encryptor(relay_list[0].key, sending_cell)
        sending_cell = Cell(encrypted_cell, IV=init_vector, ctype=CellType.RELAY)
        sending_cell.ip_addr = relay_list[0].ip_addr
        sending_cell.port = relay_list[0].port
        return sending_cell

    @staticmethod
    def req(request, intermediate_relays):
        """send out stuff in router."""
        if CLIENT_DEBUG:
            print("REQUEST SENDING TEST")
        # must send IV and a cell that is encrypted with the next public key
        # public key list will have to be accessed in order with list of relays
        # connection type. exit node always knows
        sending_cell = Client.req_wrapper(request,intermediate_relays)
        try:
            sock = intermediate_relays[0].sock
            sock.send(pickle.dumps(sending_cell))
            their_cell = sock.recv(8192)

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
                decrypted = Client.aes_decryptor(intermediate_relays[counter].key, their_cell)
                their_cell = pickle.loads(decrypted)
                counter += 1
                if counter < len(intermediate_relays):
                    their_cell = their_cell.payload

            if their_cell.type == CellType.FAILED:
                if CLIENT_DEBUG:
                    print("FAILED AT CONNECTION!")
                    print(json.dumps({"content": "", "status": 404}))
                    return None

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
                        decrypted = Client.aes_decryptor(intermediate_relays[counter].key,
                                                         their_cell)
                        their_cell = pickle.loads(decrypted)
                        counter += 1
                        if counter < len(intermediate_relays):
                            their_cell = their_cell.payload

                    summation += their_cell.payload

                response = bytes(summation)  # take the sum of all your bytes
                response = pickle.loads(response)  # load the FINAL item.
                if isinstance(response, requests.models.Response):
                    # check if it's a response type item.
                    # This check is unnecessary based off code though... Left in in case of attack
                    if CLIENT_DEBUG:
                        print(response.content)
                        print(response.status_code)
                    return_dict = {"content": response.content.decode(
                        response.encoding), "status code": response.status_code}
                    print(json.dumps(return_dict))
                    # print(response.json())
                    return response

                else:
                    # Reaching this branch implies data corruption of some form
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
                    # Reaching this branch implies data corruption of some form
                    print(json.dumps({"content": "", "status": 404}))

        except struct.error:
            print("socketerror")

    def close(self):  # to close things.
        """Run at the end of a client call to CLOSE all sockets"""
        for i in self.relay_list:
            i.sock.close()


class Responder(BaseHTTPRequestHandler):
    """Mini HTTP server"""
    def do_GET(self):
        """Get request response method"""
        my_client = Client()
        print("get")  # DEBUGGER
        relay_list = my_client.getdirectoryitems()  # Get references from directories.
        public_key1 = serialization.load_pem_public_key(
            relay_list[0].key, backend=default_backend())
        my_client.first_connect(relay_list[0].ip, relay_list[0].port, public_key1)
        public_key2 = serialization.load_pem_public_key(
            relay_list[1].key, backend=default_backend())
        my_client.more_connect_1(relay_list[1].ip, relay_list[1].port, my_client.relay_list,
                                 public_key2)
        public_key3 = serialization.load_pem_public_key(
            relay_list[2].key, backend=default_backend())
        my_client.more_connect_2(relay_list[2].ip, relay_list[2].port, my_client.relay_list,
                                 public_key3)
        obtained_response = my_client.req(self.path[2:], my_client.relay_list)

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


if __name__ == "__main__":
    main()
