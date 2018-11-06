import socket
import time
import select
import pickle
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import cryptography.hazmat.primitives.asymmetric.padding
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

from cell import Cell


class Serverreg():
    """Server data class"""
    def __init__(self, ip, port, socketinput, publickey):
        self.ip = ip
        self.port = port
        self.socket = socketinput
        self.key = publickey


class DirectoryServer():
    """Directory server class"""
    def __init__(self):
        self.lasttime = time.time()
        self.registered_servers = []
        self.socketlist = []
        self.identities = []
        for i in range(100):
            self.identities.append(i)  # add 1 to 100 for the identities.

        # tcp type chosen for first.
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # now you have a signature of your own damned public key.
        # better be "" or it'll listen only on localhost
        self.socket.bind(("", 50000))
        self.socket.listen(100)

    def mainloop(self):
        while True:
            readready, _, _ = select.select(
                [self.socket]+self.socketlist, [], [])
            print("obtained a server connection.")
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
                    if isinstance(receivedcell, type(Cell(""))):
                        if receivedcell.type == "giveDirect":
                            signedbytearray = receivedcell.salt
                            signature = receivedcell.signature
                            identity = receivedcell.payload

                            try:
                                tempopen = open(
                                    "publics/publictest" + str(identity) + ".pem", "rb")
                                theirpublickey = serialization.load_pem_private_key(tempopen.read(
                                ), password=None, backend=default_backend())  # used for signing, etc.
                                tempopen.close()
                            except FileNotFoundError:
                                # i.e the identity is not established.
                                continue

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

                            ipaddress, port = serversocket.getpeername()  # obtain the ip and port of that server.
                            self.registered_servers.append(
                                Serverreg(ipaddress, port, serversocket, identity))
                        else:
                            serversocket.close()
                            # reject connection as it does not contain a valid cell.
                            continue
                else:
                    reference = None
                    print("got from existing.")
                    received = i.recv(4096)
                    for k in self.registered_servers:
                        if k.socket == i:
                            # i.e it is part of the thing.
                            reference = k
                    if len(received) == 0:  # disconnect catch
                        print("CLIENT WAS CLOSED! or timed out.")
                        i.socket.close()
                        self.registered_servers.remove(reference)
                        continue
