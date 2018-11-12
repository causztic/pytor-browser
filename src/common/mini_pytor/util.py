"""Suite of utility methods"""

import os
import pickle

from cryptography.hazmat.primitives import padding, asymmetric, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


from cell import Cell

RELAY_DEBUG = True
CLIENT_DEBUG = True
RELAY_PACKET_SIZE_1 = 4406
RELAY_PACKET_SIZE_2 = 4598
CLIENT_PACKET_SIZE = 4790

def padder128(data):
    """ pad ip to 256 bits... because this can vary too"""
    padder1b = padding.PKCS7(128).padder()
    p1b = padder1b.update(data)
    p1b += padder1b.finalize()
    return p1b


def aes_encryptor(secret_key, cell):
    """Encrypt something given a secret key. and data."""
    if not isinstance(cell, Cell):
        raise Exception("AES encryptor input is not Cell")
    init_vector = os.urandom(16)
    cipher = Cipher(
        algorithms.AES(secret_key),
        modes.CBC(init_vector),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padder128(pickle.dumps(cell)))
    encrypted += encryptor.finalize()  # finalise decryption
    return encrypted, init_vector


def aes_decryptor(secret_key, cell):
    """Decrypt cell's payload with an AES key"""
    if not isinstance(cell, Cell):
        raise Exception("AES encryptor input is not Cell")
    cipher = Cipher(
        algorithms.AES(secret_key),
        modes.CBC(cell.init_vector),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(cell.payload)
    decrypted += decryptor.finalize()  # finalise decryption
    return decrypted

def rsa_verify(pubkey, signature, message):
    "Verify signature of message using pubkey"
    # Potentially raises InvalidSignature error
    pubkey.verify(
        signature,
        message,
        asymmetric.padding.PSS(
            mgf=asymmetric.padding.MGF1(hashes.SHA256()),
            salt_length=asymmetric.padding.PSS.MAX_LENGTH),
        hashes.SHA256()
    )
