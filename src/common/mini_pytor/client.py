"""Client class file"""

import pickle
import sys
import json
import struct
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer

import urllib
import requests
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

import util
from cell import Cell, CellType


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
    def get_directory_items():
        """Method to obtain items from directory"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # connect to directory
        sock.connect((socket.gethostbyname(socket.gethostname()), 50000))
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
        if util.CLIENT_DEBUG:
            print("first connect Actual cell (encrypted bytes) ")
            print(readied_cell)
        encrypted_cell = rsa_public_key.encrypt(
            readied_cell,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        # return my generated ecdhe key and the encrypted cell
        return encrypted_cell, ec_privkey

    @staticmethod
    def check_signature_and_derive(provided_cell, rsa_key, private_ecdhe):
        """given a cell, attempt to verify payload. Afterwards, derive shared key."""
        signature = provided_cell.signature
        try:
            # verify that the cell was signed using their key.
            util.rsa_verify(rsa_key, signature, provided_cell.salt)
            # load up their half of the ecdhe key
            their_ecdhe_key = serialization.load_pem_public_key(
                provided_cell.payload, backend=default_backend())
            shared_key = private_ecdhe.exchange(ec.ECDH(), their_ecdhe_key)
            derived_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=provided_cell.salt,
                info=None,
                backend=default_backend()
            ).derive(shared_key)

            # derived key is returned
            return derived_key

        except InvalidSignature:
            if util.CLIENT_DEBUG:
                print("Something went wrong.. Signature was invalid.",
                      file=sys.stderr)
            return None

    def first_connect(self, gonnect, gonnectport, rsa_key):
        """Connect to the first relay of the trio"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((gonnect, gonnectport))
            encrypted_cell, ec_privkey = Client.make_first_connect_cell(
                rsa_key)
            if util.CLIENT_DEBUG:
                print("First connect actual cell (decrypted bytes)")
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
                if util.CLIENT_DEBUG:
                    print("connected successfully to relay @ " + gonnect
                          + "   Port: " + str(gonnectport))
                self.relay_list.append(
                    RelayData(gonnect, sock, derived_key, ec_privkey, rsa_key, gonnectport))
            else:  # Verification error or Unpacking Error occurred
                print("verification of signature failed/Invalid cell was received.")
        except (struct.error, ConnectionResetError, ConnectionRefusedError):
            print("disconnected or relay is not online/ connection was "
                  + "refused.", file=sys.stderr)

    def more_connect_1(self, gonnect, gonnectport, rsa_key):
        """Connect to the next relay through the first one."""
        encrypted_cell, ec_privkey = Client.make_first_connect_cell(rsa_key)
        if util.CLIENT_DEBUG:
            print("Innermost cell with keys (Encrypted)")
            print(encrypted_cell)

        intermediate_relays = self.relay_list
        sending_cell = Cell(encrypted_cell, ctype=CellType.RELAY_CONNECT)
        sending_cell.ip_addr = gonnect
        sending_cell.port = gonnectport
        # inform of next port of call.
        encrypted_cell, init_vector = util.aes_encryptor(
            intermediate_relays[0].key,
            sending_cell
        )
        sending_cell = Cell(encrypted_cell, IV=init_vector,
                            ctype=CellType.RELAY_CONNECT)
        # wrap in another cell to save init_vector

        try:
            sock = intermediate_relays[0].sock
            sock.send(pickle.dumps(sending_cell))  # send over the cell
            if util.CLIENT_DEBUG:
                print("cell sent: ")
                print(pickle.dumps(sending_cell))
            their_cell = sock.recv(4096)  # await answer
            # you now receive a cell with encrypted payload.
            their_cell = pickle.loads(their_cell)
            decrypted = util.aes_decryptor(
                intermediate_relays[0].key, their_cell)
            if util.CLIENT_DEBUG:
                print(decrypted)
            their_cell = pickle.loads(decrypted)
            if util.CLIENT_DEBUG:
                print(their_cell.payload)
            their_cell = pickle.loads(their_cell.payload)

            if their_cell.type == CellType.FAILED:
                if util.CLIENT_DEBUG:
                    print("FAILED AT CONNECTION!", file=sys.stderr)
                if their_cell.payload == "CONNECTIONREFUSED":
                    print("Connection was refused. Is the relay online yet?")
                return

            derived_key = self.check_signature_and_derive(
                their_cell, rsa_key, ec_privkey)

            self.relay_list.append(
                RelayData(gonnect, sock, derived_key, ec_privkey, rsa_key, gonnectport))

            if util.CLIENT_DEBUG:
                print("connected successfully to relay @ " + gonnect
                      + "   Port: " + str(gonnectport), file=sys.stderr)

        except (ConnectionResetError, ConnectionRefusedError, struct.error):
            if util.CLIENT_DEBUG:
                print("Socket Error, removing from the list.", file=sys.stderr)
            del self.relay_list[0]  # remove it from the lsit
            if util.CLIENT_DEBUG:
                print("REMOVED relay 0 DUE TO FAILED CONNECTION")

    def more_connect_2(self, gonnect, gonnectport, rsa_key):
        """Connect to the next relay through my 2 connected relays."""
        encrypted_cell, ec_privkey = Client.make_first_connect_cell(rsa_key)
        if util.CLIENT_DEBUG:
            print("Innermost cell with keys (encrypted)", file=sys.stderr)
            print(encrypted_cell)

        intermediate_relays = self.relay_list
        # connection type. exit node always knows
        sending_cell = Cell(encrypted_cell, ctype=CellType.RELAY_CONNECT)
        # Deepest layer, encrypted with RSA
        sending_cell.ip_addr = gonnect
        sending_cell.port = gonnectport
        # inform of next port of call.
        encrypted_cell, init_vector = util.aes_encryptor(
            intermediate_relays[1].key,
            sending_cell
        )
        # encrypt using said keys.
        sending_cell = Cell(encrypted_cell, IV=init_vector,
                            ctype=CellType.RELAY_CONNECT)
        # 2nd Layer from top

        sending_cell.ip_addr = intermediate_relays[1].ip_addr
        sending_cell.port = intermediate_relays[1].port
        # inform of next port of call again.
        sending_cell = Cell(pickle.dumps(sending_cell), ctype=CellType.RELAY)

        encrypted_cell, init_vector = util.aes_encryptor(
            intermediate_relays[0].key,
            sending_cell
        )
        sending_cell = Cell(encrypted_cell, IV=init_vector,
                            ctype=CellType.RELAY)  # Outermost layer
        sending_cell.ip_addr = intermediate_relays[0].ip_addr
        sending_cell.port = intermediate_relays[0].port
        # inform of next port of call one more time

        try:
            sock = intermediate_relays[0].sock
            sock.send(pickle.dumps(sending_cell))  # send over the cell
            their_cell = sock.recv(4096)  # await answer
            # you now receive a cell with encrypted payload.
            if util.CLIENT_DEBUG:
                print(their_cell)
            their_cell = pickle.loads(their_cell)
            if util.CLIENT_DEBUG:
                print(their_cell.payload)
            counter = 0
            while counter < len(intermediate_relays):
                # print(their_cell.payload)
                decrypted = util.aes_decryptor(
                    intermediate_relays[counter].key, their_cell)
                if util.CLIENT_DEBUG:
                    print(decrypted)
                their_cell = pickle.loads(decrypted)
                # print(their_cell.payload)
                counter += 1
                if counter < len(intermediate_relays):
                    their_cell = their_cell.payload

            if their_cell.type == CellType.FAILED:
                if util.CLIENT_DEBUG:
                    print("FAILED AT CONNECTION!", file=sys.stderr)
                return

            their_cell = pickle.loads(their_cell.payload)
            derived_key = self.check_signature_and_derive(
                their_cell, rsa_key, ec_privkey)

            self.relay_list.append(
                RelayData(gonnect, sock, derived_key, ec_privkey, rsa_key, gonnectport))

            if util.CLIENT_DEBUG:
                print("connected successfully to relay @ " + gonnect
                      + "   Port: " + str(gonnectport), file=sys.stderr)
        except struct.error:
            print("socket error occurred", file=sys.stderr)

    @staticmethod
    def req_wrapper(request, relay_list):
        """Generate a encrypted cell for sending that contains the request"""
        sending_cell = Cell(request, ctype=CellType.REQ)
        # generate True payload
        encrypted_cell, init_vector = util.aes_encryptor(
            relay_list[2].key, sending_cell)
        sending_cell = Cell(encrypted_cell, IV=init_vector,
                            ctype=CellType.RELAY)
        sending_cell.ip_addr = relay_list[2].ip_addr
        sending_cell.port = relay_list[2].port
        sending_cell = Cell(pickle.dumps(sending_cell), ctype=CellType.RELAY)

        encrypted_cell, init_vector = util.aes_encryptor(
            relay_list[1].key, sending_cell)
        sending_cell = Cell(encrypted_cell, IV=init_vector,
                            ctype=CellType.RELAY)
        sending_cell.ip_addr = relay_list[1].ip_addr
        sending_cell.port = relay_list[1].port
        sending_cell = Cell(pickle.dumps(sending_cell), ctype=CellType.RELAY)

        encrypted_cell, init_vector = util.aes_encryptor(
            relay_list[0].key, sending_cell)
        sending_cell = Cell(encrypted_cell, IV=init_vector,
                            ctype=CellType.RELAY)
        sending_cell.ip_addr = relay_list[0].ip_addr
        sending_cell.port = relay_list[0].port
        return sending_cell

    @staticmethod
    def chain_decryptor(list_of_intermediate_relays, provided_cell):
        """decrypt something given a list the intermediate relay list
        and the cell"""
        counter = 0
        while counter < len(list_of_intermediate_relays):
            decrypted = util.aes_decryptor(
                list_of_intermediate_relays[counter].key,
                provided_cell
            )
            provided_cell = pickle.loads(decrypted)
            counter += 1
            if counter < len(list_of_intermediate_relays):
                provided_cell = provided_cell.payload

        return provided_cell

    def req(self, request):
        """send out stuff in router."""
        if util.CLIENT_DEBUG:
            print("REQUEST SENDING TEST")
        # must send IV and a cell that is encrypted with the next public key
        # public key list will have to be accessed in order with list of relays
        # connection type. exit node always knows
        intermediate_relays = self.relay_list
        sending_cell = Client.req_wrapper(request, intermediate_relays)
        try:
            sock = intermediate_relays[0].sock
            sock.send(pickle.dumps(sending_cell))
            recv_cell = sock.recv(8192)
            their_cell = pickle.loads(recv_cell)
            if util.CLIENT_DEBUG:
                print("received cell")
                print(len(recv_cell))
                print(recv_cell)
                print("received cell payload")
                print(their_cell.payload)
            their_cell = Client.chain_decryptor(
                intermediate_relays, their_cell)
            if their_cell.type == CellType.FAILED:
                print("FAILED AT CONNECTION!", file=sys.stderr)
                return Client.failure()  # return failure

            if their_cell.type == CellType.CONTINUE:
                if util.CLIENT_DEBUG:
                    print("Information is being Streamed. ", file=sys.stderr)
                summation = their_cell.payload
                while their_cell.type == CellType.CONTINUE:
                    recv_cell = sock.recv(8192)  # await answer
                    # you now receive a cell with encrypted payload.
                    their_cell = pickle.loads(recv_cell)
                    if util.CLIENT_DEBUG:
                        print("received PART", file=sys.stderr)
                        print(len(recv_cell), file=sys.stderr)
                        print(recv_cell, file=sys.stderr)
                        print("received cell payload", file=sys.stderr)
                        print(their_cell.payload, file=sys.stderr)
                    their_cell = Client.chain_decryptor(
                        intermediate_relays, their_cell)
                    summation += their_cell.payload
                resp = bytes(summation)  # take the sum of all your bytes
                resp = pickle.loads(resp)  # load the FINAL item.
                return Client._check_response(resp)

            resp = pickle.loads(their_cell.payload)
            return Client._check_response(resp)
        except struct.error:
            print("socketerror", file=sys.stderr)

    @staticmethod
    def _check_response(response):
        if isinstance(response, requests.models.Response):
            # check if it's a response type item.
            # This check is unnecessary based off code though...
            # Left in in case of attack
            if util.CLIENT_DEBUG:
                print(response.content, file=sys.stderr)
                print(response.status_code, file=sys.stderr)
            return_dict = {
                "content": response.content.decode(response.encoding),
                "status code": response.status_code
            }
            print(json.dumps(return_dict))
            return response
        # Reaching this branch implies data corruption of some form
        return Client.failure()

    def close(self):  # to close things.
        """Run at the end of a client call to CLOSE all sockets"""
        for i in self.relay_list:
            i.sock.close()

    @staticmethod
    def failure():
        """Default Error message."""
        print("Some form of data corruption occurred, "
              + "or no reply was obtained.", file=sys.stderr)
        return json.dumps({"content": "", "status": 404})


class Responder(BaseHTTPRequestHandler):
    """Mini HTTP server"""

    def do_GET(self):
        """Get request response method"""
        my_client = Client()
        # Get references from directories.
        relay_list = Client.get_directory_items()
        NUM_RELAYS = 3
        options = {
            0: my_client.first_connect,
            1: my_client.more_connect_1,
            2: my_client.more_connect_2
        }

        for i in range(NUM_RELAYS):
            relay = relay_list[i]
            pubkey = serialization.load_pem_public_key(
                relay["key"], backend=default_backend())
            connect_func = options[i]
            connect_func(relay["ip_addr"], relay["port"], pubkey)
            print(my_client.relay_list)

        if self.path == "/favicon.ico":
            return
        path = Responder._handle_url(self.path)
        print(path)
        obtained_response = my_client.req(path)
        if isinstance(obtained_response, str):
            print("Producing invalid reply")
            self.send_response(404)
            answer = obtained_response.encode()
            my_client.close()
        else:
            print("Producing valid reply")
            self.send_response(obtained_response.status_code)
            my_client.close()
            answer = bytes(obtained_response.content)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(answer)

    @staticmethod
    def _handle_url(url_path):
        fallback = "http://www.motherfuckingwebsite.com"
        query = urllib.parse.parse_qs(url_path[2:])
        if not query:
            index1 = url_path.find("http://")
            index2 = url_path.find("https://")
            if index1 != -1:
                return url_path[index1:]
            if index2 != -1:
                return url_path[index2:]
            return fallback
        if "req" in query:
            return query["req"][0]
        return fallback

class RelayData:
    """Relay data class"""

    def __init__(self, given_ip, provided_socket, derived_key, ec_privkey,
                 given_rsa_key, given_port):

        self.ip_addr = given_ip
        self.sock = provided_socket
        self.key = derived_key
        self.ec_key_ = ec_privkey
        self.rsa_key = given_rsa_key
        self.port = given_port


def main():
    """Main function"""
    server_address = ('', 27182)
    httpd = HTTPServer(server_address, Responder)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
