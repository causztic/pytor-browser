"""Directory Server Class file"""

import socket
import select
import pickle

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import rsa

import util
from cell import Cell, CellType


class DirectoryServer:
    """Directory server class"""

    def __init__(self):
        self.key = rsa.generate_private_key(
            backend=default_backend(),
            public_exponent=65537,
            key_size=4096
        )  # used for signing, etc.

        self.public_bytes = self.key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.registered_relays = []
        self.relay_sockets = []
        self.connected_relays = []
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # now you have a signature of your own public key.
        # better be "" or it'll listen only on localhost
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("", 50000))
        self.socket.listen(100)

    def handle_conn(self):
        """Handle an incoming connection to the server."""
        print("Got a connection request.")
        relay_socket, _ = self.socket.accept()
        obtained = relay_socket.recv(4096)
        try:
            received_cell = pickle.loads(obtained)
        except (pickle.PickleError, pickle.PicklingError, pickle.UnpicklingError):
            relay_socket.close()
            return

        if not isinstance(received_cell, Cell):
            relay_socket.close()
            return

        if received_cell.type == CellType.GIVE_DIRECT:
            base_bytearray = received_cell.salt
            signature = received_cell.signature
            pubkey_bytes = received_cell.payload
            port_num = received_cell.init_vector
            their_pubkey = serialization.load_pem_public_key(
                pubkey_bytes, backend=default_backend())
            try:
                util.rsa_verify(their_pubkey, signature, base_bytearray)
            except InvalidSignature:
                # reject connection, signature validation failed
                relay_socket.close()
                return

            # obtain the ip and port of that server.
            ip_address, _ = relay_socket.getpeername()
            relay_data = {
                "ip_addr": ip_address,
                "port": port_num,
                "key": their_pubkey,
                "sock":  relay_socket
            }
            if relay_data not in self.connected_relays:
                self.connected_relays.append(relay_data)

            registered_relay_data = {
                "ip_addr": ip_address,
                "port": port_num,
                "key": pubkey_bytes
            }
            if registered_relay_data not in self.registered_relays:
                self.registered_relays.append(registered_relay_data)
            if relay_socket not in self.relay_sockets:
                self.relay_sockets.append(relay_socket)
            print(f"Added -> ({str(ip_address)}, {str(port_num)})")
            print(self.registered_relays, end="\n\n")
        elif received_cell.type == CellType.GET_DIRECT:
            print("Got a directory request")
            relay_socket.settimeout(0.03)  # ensure we don't block forever
            relay_socket.send(pickle.dumps(
                Cell(self.registered_relays, ctype=CellType.GET_DIRECT)))
            relay_socket.recv(4096)
            relay_socket.close()
        else:
            # reject connection as it does not contain a valid cell.
            relay_socket.close()

    def handle_closed_conn(self, provided_socket):
        """Handle a closed connection"""
        reference = None
        reference2 = None
        try:
            provided_socket.send(b"Hello")
        except (ConnectionResetError, ConnectionError):
            # search for the socket, as it must be part of both lists.
            for k in self.connected_relays:
                if k["sock"] == provided_socket:
                    reference = k

            for k in self.registered_relays:
                if k["ip_addr"] == reference["ip_addr"] \
                        and k["port"] == reference["port"]:
                    reference2 = k

            self.connected_relays.remove(reference)
            self.registered_relays.remove(reference2)
            self.relay_sockets.remove(provided_socket)
            print(f"Removed relay ({str(reference['ip_addr'])}, "
                  + f"{str(reference['port'])}): Socket closed or timed-out")
            print(self.registered_relays, end="\n\n")
            provided_socket.close()

    def run(self):
        """Start up directory"""
        while True:
            read_ready, _, _ = select.select(
                [self.socket] + self.relay_sockets, [], [])
            for i in read_ready:
                if i == self.socket:  # is receiving a new connection request.
                    self.handle_conn()
                else:
                    self.handle_closed_conn(i)


if __name__ == "__main__":
    DIRECTORY = DirectoryServer()
    DIRECTORY.run()
