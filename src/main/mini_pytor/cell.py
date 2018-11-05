"""Cell class definition"""

class Cell():
    """Cell class"""
    _Types = [
        "AddCon",
        "Req",
        "ConnectResp",
        "FAILED",
        "relay connect",
        "relay",
        "giveDirect",
        "getDirect",
        "checkup"
    ]

    def __init__(self, payload, IV=None, salt=None, signature=None, Type=None):
        self.payload = payload
        self.signature = signature
        self.IV = IV  # save the IV since it's a connection cell.
        self.salt = salt
        if (Type is not None):
            if (Type == "failed"):
                self.type = self._Types[3]  # indicates failure
            elif(Type == "relay connect"):
                # indicates to make a connection to a new server.
                self.type = self._Types[4]
            elif (Type == "AddCon"):
                # is a connection request. so essentially some key is being pushed out here.
                self.type = self._Types[0]
            elif (Type == "Req"):
                # is a plain request. so essentially some key is being pushed out here.
                self.type = self._Types[1]
            elif (Type == "ConnectResp"):
                self.type = self._Types[2]  # is a response to a connection
            elif(Type == "relay"):
                self.type = self._Types[5]  # indicates relay
            elif (Type == "giveDirect"):
                self.type = self._Types[6]  # indicates relay
            elif (Type == "getDirect"):
                self.type = self._Types[7]  # indicates relay
            elif (Type == "checkup"):
                self.type = self._Types[8]  # indicates relay
