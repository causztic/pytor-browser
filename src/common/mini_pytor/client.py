"""Client class file"""

import pickle
import sys
import json
import struct
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from random import sample

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

DEFAULT_DIRECTORY_ADDRESS = ("127.0.0.1", 50000)
RANDOM_RELAY_ORDER = "random"


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
    def get_directory_items(directory_address=DEFAULT_DIRECTORY_ADDRESS):
        """Method to obtain items from directory"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # connect to directory
        sock.connect(directory_address)
        sock.send(pickle.dumps(Cell("", ctype=CellType.GET_DIRECT)))
        received_cell = sock.recv(32768)
        received_cell = pickle.loads(received_cell)
        # if isinstance(received_cell.payload, list) and util.CLIENT_DEBUG:
        #     print(received_cell.payload)
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
            print("First connect actual cell (encrypted bytes) ")
            print(readied_cell)
        encrypted_cell = rsa_public_key.encrypt(
            readied_cell,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        # return generated ECDHE key and the encrypted cell
        return encrypted_cell, ec_privkey

    @staticmethod
    def check_signature_and_derive(provided_cell, rsa_key, private_ecdhe):
        """given a cell, attempt to verify payload. Afterwards, derive shared key."""
        signature = provided_cell.signature
        try:
            # verify that the cell was signed using their key.
            util.rsa_verify(rsa_key, signature, provided_cell.salt)
            # load up their half of the ECDHE key
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

    def connect_relay(self, gonnect, gonnectport, rsa_key, connect_mode):
        """Wrapper function for easier use"""
        if connect_mode == 0:
            self.first_connect(gonnect, gonnectport, rsa_key)
        else:
            self.more_connect(gonnect, gonnectport, rsa_key, connect_mode)

    def first_connect(self, gonnect, gonnectport, rsa_key):
        """Connect to the first relay of the trio"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((gonnect, gonnectport))
            encrypted_cell, ec_privkey = Client.make_first_connect_cell(
                rsa_key)
            if util.CLIENT_DEBUG:
                print("First connect actual cell (encrypted)")
                print(encrypted_cell)
            # send out the generated ECDHE key
            sock.send(encrypted_cell)
            their_cell = sock.recv(4096)
            their_cell = pickle.loads(their_cell)
            # check the signature and derive their key.
            derived_key = self.check_signature_and_derive(
                their_cell, rsa_key, ec_privkey)

            if derived_key:
                if util.CLIENT_DEBUG:
                    print("Connected successfully to relay @ " + gonnect
                          + "   Port: " + str(gonnectport))
                self.relay_list.append(
                    RelayData(gonnect, sock, derived_key,
                              ec_privkey, rsa_key, gonnectport)
                )
            else:
                # Verification error or UnpackingError occurred
                print("Verification of signature failed"
                      + "/Invalid cell was received.")
        except (struct.error, ConnectionResetError, ConnectionRefusedError):
            print("Disconnected or relay is not online/ connection was "
                  + "refused.", file=sys.stderr)

    def more_connect(self, gonnect, gonnectport, rsa_key, connect_mode):
        """Connect to the next relay through my 2 connected relays."""
        encrypted_cell, ec_privkey = Client.make_first_connect_cell(rsa_key)
        if util.CLIENT_DEBUG:
            print("Innermost cell with keys (encrypted)")
            print(encrypted_cell)

        intermediate_relays = self.relay_list
        # connection type. exit node always knows
        sending_cell = Cell(encrypted_cell, ctype=CellType.RELAY_CONNECT)
        # deepest layer, encrypted with RSA
        sending_cell.ip_addr = gonnect
        sending_cell.port = gonnectport
        # inform of next port of call.
        encrypted_cell, init_vector = util.aes_encryptor(
            intermediate_relays[connect_mode - 1].key,
            sending_cell
        )
        # encrypt using said keys.
        sending_cell = Cell(encrypted_cell, IV=init_vector,
                            ctype=CellType.RELAY_CONNECT)

        if connect_mode >= 2:
            for i in range(connect_mode - 1, 0, -1):
                # 2nd layer from top
                sending_cell.ip_addr = intermediate_relays[i].ip_addr
                sending_cell.port = intermediate_relays[i].port
                # inform of next port of call again.
                sending_cell = Cell(pickle.dumps(sending_cell),
                                    ctype=CellType.RELAY)
                encrypted_cell, init_vector = util.aes_encryptor(
                    intermediate_relays[i - 1].key,
                    sending_cell
                )
                sending_cell = Cell(encrypted_cell, IV=init_vector,
                                    ctype=CellType.RELAY)  # Outermost layer
                sending_cell.ip_addr = intermediate_relays[i - 1].ip_addr
                sending_cell.port = intermediate_relays[i - 1].port

        try:
            sock = intermediate_relays[0].sock
            sock.send(pickle.dumps(sending_cell))  # send over the cell
            if util.CLIENT_DEBUG:
                print("Cell sent: ")
                print(pickle.dumps(sending_cell))
            their_cell = sock.recv(4096)  # await answer
            # you now receive a cell with encrypted payload.
            if util.CLIENT_DEBUG:
                print(their_cell)
            their_cell = pickle.loads(their_cell)
            if util.CLIENT_DEBUG:
                print(their_cell.payload)
            counter = 0
            while counter < len(intermediate_relays):
                decrypted = util.aes_decryptor(
                    intermediate_relays[counter].key, their_cell)
                if util.CLIENT_DEBUG:
                    print(decrypted)
                their_cell = pickle.loads(decrypted)
                if util.CLIENT_DEBUG:
                    print(their_cell.payload)
                counter += 1
                if counter < len(intermediate_relays):
                    their_cell = their_cell.payload
            their_cell = pickle.loads(their_cell.payload)

            if their_cell.type == CellType.FAILED:
                if util.CLIENT_DEBUG:
                    print("FAILED AT CONNECTION!", file=sys.stderr)
                if their_cell.payload == "CONNECTIONREFUSED":
                    print(
                        "Connection was refused. Is the relay online yet?", file=sys.stderr)
                return

            derived_key = self.check_signature_and_derive(
                their_cell, rsa_key, ec_privkey)
            self.relay_list.append(
                RelayData(gonnect, sock, derived_key, ec_privkey, rsa_key, gonnectport))

            if util.CLIENT_DEBUG:
                print("Connected successfully to relay @ " + gonnect
                      + "   Port: " + str(gonnectport))

        except (ConnectionResetError, ConnectionRefusedError, struct.error):
            print("Socket error.", file=sys.stderr)
            del self.relay_list[connect_mode - 1]  # remove it from the list
            if util.CLIENT_DEBUG:
                print("REMOVED relay 0 DUE TO FAILED CONNECTION", file=sys.stderr)

    @staticmethod
    def req_wrapper(request, relay_list):
        """Generate a encrypted cell for sending that contains the request"""
        sending_cell = Cell(request, ctype=CellType.REQ)
        for i in range(len(relay_list) - 1, -1, -1):
            encrypted_cell, init_vector = util.aes_encryptor(
                relay_list[i].key, sending_cell)
            sending_cell = Cell(encrypted_cell, IV=init_vector,
                                ctype=CellType.RELAY)
            sending_cell.ip_addr = relay_list[i].ip_addr
            sending_cell.port = relay_list[i].port
            if i != 0:
                sending_cell = Cell(pickle.dumps(
                    sending_cell), ctype=CellType.RELAY)

        return sending_cell

    @staticmethod
    def chain_decryptor(list_of_intermediate_relays, provided_cell):
        """Decrypt the provided cell given a list of intermediate relays"""
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
        # calculate packet size using number of relays
        pack_size = util.BASE_PACKET_SIZE \
            + util.WRAPPER_SIZE * (len(intermediate_relays) - 1)
        try:
            # get first packet
            sock = intermediate_relays[0].sock
            sock.send(pickle.dumps(sending_cell))
            recv_cell = sock.recv(pack_size)
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
                    print("Information is being streamed.")
                recv_bytes_arr = []
                cont_loop = True
                # get whole TCP stream and store it in array
                while cont_loop:
                    recv_bytes = sock.recv(pack_size * 5)  # await answer
                    print(len(recv_bytes))
                    if len(recv_bytes) < pack_size:
                        cont_loop = False
                    recv_bytes_arr.append(recv_bytes)
                total_payload = b"".join(recv_bytes_arr)
                if util.CLIENT_DEBUG:
                    print(f"Total length: {len(total_payload)}")
                # partition the entire payload to pack_size each
                # and process them accordingly
                decrypted_bytes = [their_cell.payload]
                for i in range(0, len(total_payload), pack_size):
                    recv_cell = total_payload[i:i + pack_size]
                    their_cell = pickle.loads(recv_cell)
                    if util.CLIENT_DEBUG:
                        print(f"Received packet, length {len(recv_cell)}")
                    their_cell = Client.chain_decryptor(
                        intermediate_relays, their_cell)
                    decrypted_bytes.append(their_cell.payload)
                # join all the bytes together
                resp = bytes(b"".join(decrypted_bytes))
                # unpickle the final concatenated bytes
                resp = pickle.loads(resp)
                return Client._check_response(resp)

            resp = pickle.loads(their_cell.payload)
            return Client._check_response(resp)
        except struct.error:
            print("socketerror", file=sys.stderr)

    @staticmethod
    def _check_response(response):
        if isinstance(response, requests.models.Response):
            # check if it's a response type item.
            # this check is unnecessary as of now...
            if util.CLIENT_DEBUG:
                return_dict = {
                    "content": response.content.decode(response.encoding),
                    "status code": response.status_code
                }
                print(json.dumps(return_dict))
            return response
        # reaching this branch implies data corruption of some form
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

    def __init__(self, directory_address, *args):
        self.directory_address = directory_address
        BaseHTTPRequestHandler.__init__(self, *args)

    def do_GET(self):
        """Get request response method"""
        my_client = Client()
        if self.path == "/favicon.ico":
            return

        url, order, num_of_relays = Responder._handle_url(self.path)

        if url is None or order is None:
            print("Producing invalid reply", file=sys.stderr)
            self.send_response(404)
            answer = ""
            my_client.close()
        else:
            # get references from directories.
            relay_list = Client.get_directory_items(self.directory_address)

            if num_of_relays < 3 or num_of_relays > len(relay_list):
                num_of_relays = 3

            if order == RANDOM_RELAY_ORDER:
                relay_list = sample(relay_list, num_of_relays)

            for i in range(num_of_relays):
                relay = relay_list[i]
                pubkey = serialization.load_pem_public_key(
                    relay["key"], backend=default_backend())
                my_client.connect_relay(
                    relay["ip_addr"], relay["port"], pubkey, i)

            print(f"Num of relays: {len(my_client.relay_list)}")
            print(f"URL: {url}")

            obtained_response = my_client.req(url)
            if isinstance(obtained_response, str):
                print("Producing invalid reply", file=sys.stderr)
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
        query = urllib.parse.parse_qs(url_path[2:])
        count = 3
        url = None
        order = RANDOM_RELAY_ORDER

        if "count" in query:
            count = int(query["count"][0])
        if "url" in query:
            url = query["url"][0]
        if "order" in query:
            order = query["order"][0]

        return url, order, count


class CustomHTTPServer:
    """Custom HTTP Server instance to inject directory IP"""

    def __init__(self, directory_address=DEFAULT_DIRECTORY_ADDRESS):
        def handler(*args):
            """Override the default handler to pass in the address"""
            Responder(directory_address, *args)
        server = HTTPServer(('', 27182), handler)
        server.serve_forever()


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
    if len(sys.argv) == 3:
        CustomHTTPServer((sys.argv[1], int(sys.argv[2])))
    elif len(sys.argv) == 2:
        CustomHTTPServer((sys.argv[1], 50000))
    else:
        CustomHTTPServer()


if __name__ == "__main__":
    main()
