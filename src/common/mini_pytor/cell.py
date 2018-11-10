"""Cell class definition"""
from enum import Enum


class CellType(Enum):
    """Cell type enum"""
    ADD_CON = 0
    REQ = 1
    CONNECT_RESP = 2
    FAILED = 3
    RELAY_CONNECT = 4
    RELAY = 5
    GIVE_DIRECT = 6
    GET_DIRECT = 7
    CONTINUE = 8
    FINISHED = 9


class Cell():
    """Cell class"""

    def __init__(self, payload, IV=None, salt=None, signature=None, ctype=None):
        self.payload = payload
        self.signature = signature
        self.init_vector = IV  # save the IV since it's a connection cell.
        self.salt = salt
        if ctype is None:
            raise Exception("SHIT GONE WRONG!")  # that is very true.
        elif isinstance(ctype, CellType):
            self.type = ctype
