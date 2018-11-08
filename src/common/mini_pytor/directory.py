"""Directory Server Class file"""
import socket
import select
import pickle
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import cryptography.hazmat.primitives.asymmetric.padding
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import rsa
from util import RegisteredRelay
from cell import Cell, CellType


class Relay:
    """Relay data class"""
    def __init__(self, ip_addr, provided_socket, portnum, given_key):
        self.ip_addr = ip_addr
        self.socket = provided_socket
        self.port = portnum
        self.key = given_key


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
        # tcp type chosen for first.
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # now you have a signature of your own damned public key.
        # better be "" or it'll listen only on localhost
        self.socket.bind(("", 50000))
        self.socket.listen(100)

    def handleconnection(self):
        """Handle an incoming connection to the server."""
        print("got a connection request.")
        relaysocket, _ = self.socket.accept()
        # obtain the data sent over.
        obtained = relaysocket.recv(4096)
        try:
            receivedcell = pickle.loads(obtained)
        except (pickle.PickleError, pickle.PicklingError, pickle.UnpicklingError) as _:
            relaysocket.close()
            return

        # ensure it is indeed a cell.
        if not isinstance(receivedcell, Cell):
            relaysocket.close()
            return

        if receivedcell.type == CellType.GIVE_DIRECT:
            base_bytearray = receivedcell.salt
            signature = receivedcell.signature
            publickey = receivedcell.payload
            publickey_bytes = receivedcell.payload
            portnum = receivedcell.init_vector
            theirpublickey = serialization.load_pem_public_key(
                publickey, backend=default_backend())

            try:
                theirpublickey.verify(signature, base_bytearray,
                                      cryptography.hazmat.primitives.asymmetric.padding.PSS(
                                          mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1
                                          (hashes.SHA256()),
                                          salt_length=cryptography.hazmat.primitives.asymmetric.padding.PSS.MAX_LENGTH),
                                      hashes.SHA256())
            except InvalidSignature:
                # reject. signature validation failed.
                relaysocket.close()
                return

            ipaddress, _ = relaysocket.getpeername()  # obtain the ip and port of that server.
            print("Added-> PORT: " + str(portnum) + " IP: " + str(ipaddress))
            self.connected_relays.append(
                Relay(ipaddress, relaysocket, portnum, theirpublickey))

            self.registered_relays.append(
                RegisteredRelay(ipaddress, portnum, publickey_bytes))

            self.relay_sockets.append(relaysocket)
            return

        elif receivedcell.type == CellType.GET_DIRECT:
            print("got a directory request")
            relaysocket.settimeout(0.03)  # ensure we don't block forever
            relaysocket.send(pickle.dumps(
                Cell(self.registered_relays, ctype=CellType.GET_DIRECT)))
            relaysocket.recv(4096)
            relaysocket.close()
            return
        else:
            relaysocket.close()
            # reject connection as it does not contain a valid cell.

    def handleclosed(self, provided_socket):
        """Handle a closed connection"""
        reference = None
        reference2 = None
        try:
            provided_socket.recv(4096)
        except (ConnectionResetError, ConnectionError) as _:
            # search for the socket, as it must be part of both lists.
            for k in self.connected_relays:
                if k.socket == provided_socket:
                    reference = k

            for k in self.registered_relays:
                if k.ip == reference.ip_addr and k.port == reference.port:
                    reference2 = k

            print("relay WAS closed! or timed out.")
            print("Removed relay with IP: " + str(reference.ip_addr)
                  + " Port: " + str(reference.port))

            provided_socket.close()
            print("closed connection to relay.")
            self.connected_relays.remove(reference)
            self.registered_relays.remove(reference2)
            self.relay_sockets.remove(provided_socket)

    def mainloop(self):
        """Main Loop """
        while True:
            readready, _, _ = select.select(
                [self.socket]+self.relay_sockets, [], [])
            for i in readready:
                if i == self.socket:  # is receiving a new connection request.
                    self.handleconnection()
                else:
                    self.handleclosed(i)


DIRECTORY = DirectoryServer()
DIRECTORY.mainloop()
