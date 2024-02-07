from typing import List

from components.interfaces.interface import Interface


class Loopback(Interface):

    def __init__(self, cidr: str, port: int = 0) -> None:
        super().__init__(int_type="Loopback", port=port, cidr=cidr)

        self.p2p = False
        self.ospf_area = 0

        self._cisco_commands.update({
            "p2p_cmd": ""
        })

    # Enable/disable OSPF point-to-point
    def set_ospf_p2p(self, enable: bool) -> None:
        self.p2p = enable
        no_ = "" if enable else "no "
        self._cisco_commands["p2p_cmd"] = f"{no_}ip ospf network point-to-point"

    # Generate OSPF advertisement command
    def get_ospf_command(self) -> List[str]:
        if not (self.ip_address and self.subnet_mask):
            raise NotImplementedError("The IP address and subnet mask are missing")

        return [f"network {self.network_address()} {self.wildcard_mask()} area {self.ospf_area}"]

    # Generate IBGP neighbor establishment command
    def get_ibgp_command(self, as_num: int) -> List[str]:
        if not self.ip_address:
            raise NotImplementedError("The IP address is missing")

        return [
            f"neighbor {self.ip_address} remote-as {as_num}",
            f"neighbor {self.ip_address} update-source {str(self)}"
        ]

