"""Suite of utility methods"""

from cryptography.hazmat.primitives import padding

CLIENT_DEBUG = False
RELAY_DEBUG = False


def padder128(data):
    """ pad ip to 256 bits... because this can vary too"""
    padder1b = padding.PKCS7(128).padder()
    p1b = padder1b.update(data)
    p1b += padder1b.finalize()
    return p1b


class RegisteredRelay:
    """Relay data class, minus socket."""
    def __init__(self, ip_addr, portnum, given_key):
        self.ip = ip_addr
        self.port = portnum
        self.key = given_key
