import socket
import time
import select
import pickle
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import cryptography.hazmat.primitives.asymmetric.padding
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cell import Cell, CellType


class Serverreg():
    """Server data class"""
    def __init__(self, ipaddr, port, socketinput, publickey):
        self.ip = ipaddr
        self.port = port
        self.socket = socketinput
        self.key = publickey

class Relay():
    """Relay data class"""
    def __init__(self,ipaddr,portnum,publickey):
        self.ip = ipaddr
        self.port = portnum
        self.key = publickey


class DirectoryServer():
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

        self.lasttime = time.time()
        self.registered_relays = []
        self.identities = []
        for i in range(100):
            self.identities.append(i)  # add 1 to 100 for the identities.

        # tcp type chosen for first.
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # now you have a signature of your own damned public key.
        # better be "" or it'll listen only on localhost
        self.socket.bind(("", 50000))
        self.socket.listen(100)
        self.giving_server = []

    def mainloop(self):
        while True:
            readready, _, _ = select.select(
                [self.socket], [], [])
            print("obtained a connection.")
            for i in readready:
                if i == self.socket:  # is receiving a new connection request.
                    (serversocket, myport) = readready[0].accept
                    # obtain the data sent over.
                    obtained = serversocket.recv(4096)
                    try:
                        receivedcell = pickle.loads(obtained)
                    except (pickle.PickleError, pickle.PicklingError, pickle.UnpicklingError) as error:
                        continue

                    # ensure it is indeed a cell.
                    if isinstance(receivedcell, Cell):
                        if receivedcell.type == CellType.GIVE_DIRECT:
                            signedbytearray = receivedcell.salt
                            signature = receivedcell.signature
                            publickey = receivedcell.payload
                            portnum = receivedcell.IV
                            theirpublickey = serialization.load_pem_public_key(
                                publickey, backend=default_backend())

                            try:
                                theirpublickey.verify(signature, signedbytearray,
                                                      cryptography.hazmat.primitives.asymmetric.padding.PSS(
                                                          mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                                                              hashes.SHA256()),
                                                          salt_length=cryptography.hazmat.primitives.asymmetric.padding.PSS.MAX_LENGTH),
                                                      hashes.SHA256())
                            except InvalidSignature:
                                # reject. signature validation failed.
                                serversocket.close()
                                continue

                            ipaddress, portcon = serversocket.getpeername()  # obtain the ip and port of that server.
                            self.registered_relays.append(
                                Serverreg(ipaddress, portnum, serversocket, theirpublickey))
                            # reply or no reply?
                        elif receivedcell.type == CellType.GET_DIRECT:
                            serversocket.setSocketTimeout(0.00003)
                            serversocket.send(pickle.dumps(Cell(self.giving_server, ctype=CellType.GET_DIRECT)))
                            # slow timeout for receive. Else, force close. Basically ensure they have obtained list.
                            serversocket.recv()
                            serversocket.close()
                            continue
                        else:
                            serversocket.close()
                            # reject connection as it does not contain a valid cell.
                else:
                    reference = None
                    print("got from existing.")
                    received = i.recv(4096)
                    for k in self.registered_relays:
                        if k.socket == i:
                            # i.e it is part of the thing.
                            reference = k
                    if len(received) == 0:  # disconnect catch
                        print("CLIENT WAS CLOSED! or timed out.")
                        i.socket.close()
                        self.registered_relays.remove(reference)
                        continue
