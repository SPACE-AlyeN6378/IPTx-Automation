class NetworkError(Exception):
    def __init__(self, message="There's something wrong with your network"):
        self.message = message
        super().__init__(self.message)