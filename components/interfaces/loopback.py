from components.interfaces.interface import Interface


class Loopback(Interface):

    def __init__(self, cidr: str, port: int = 0) -> None:
        super().__init__(int_type="Loopback", port=port, cidr=cidr)