from components.interfaces.interface import Interface


class Loopback(Interface):

    def __init__(self, cidr: str, port: int = 0) -> None:
        super().__init__(int_type="Loopback", port=port, cidr=cidr)
        self.p2p = False
        self._cisco_commands.update({
            "p2p_cmd": ""
        })

    def set_ospf_p2p(self, enable: bool) -> None:
        self.p2p = enable
        no_ = "" if enable else "no "
        self._cisco_commands["p2p_cmd"] = f"{no_}ip ospf network point-to-point"
