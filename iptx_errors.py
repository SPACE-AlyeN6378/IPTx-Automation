class NetworkError(Exception):
    def __init__(self, message="There's something wrong with your network"):
        self.message = message
        super().__init__(self.message)

class SwitchportError(Exception):
    def __init__(self, message="There's something wrong with the switchport"):
        self.message = message
        super().__init__(self.message)

class NotFoundError(Exception):
    def __init__(self, message="Not found"):
        self.message = message
        super().__init__(self.message)