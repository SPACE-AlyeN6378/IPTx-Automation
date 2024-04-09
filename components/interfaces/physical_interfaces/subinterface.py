from components.interfaces.interface import Interface


class SubInterface(Interface):
    def __init__(self, int_type: str, port: str | int, vlan_id: int, cidr: str = None,
                 mtu: int = 1500) -> None:

        super().__init__(int_type, port, cidr)
        self.vlan_id: int = vlan_id
        self.mtu: int = mtu
        self.xr_mode: bool = False

        self._cisco_commands.update({
            "pseudo-wire": []
        })

    def __str__(self) -> str:
        return super().__str__() + f".{self.vlan_id}"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other) -> bool:
        if not isinstance(other, SubInterface):
            return False

        if not super().__eq__(other):
            return False

        return self.vlan_id == other.vlan_id

    def __hash__(self) -> int:
        return hash((self.int_type, self.port, self.ip_address, self.subnet_mask, self.device_id, self.vlan_id))

    def __contains__(self, item) -> bool:
        # Check if the item is contained in any of the attributes
        if item in [self.int_type, self.port, self.ip_address, self.subnet_mask, self.device_id, self.vlan_id]:
            return True

        return False

    def generate_pseudowire_config(self, neighbor_id: int) -> None:
        self._cisco_commands["pseudo-wire"] = [
            f"encapsulation dot1q {self.vlan_id}",
            f"mtu {self.mtu}"
        ]

        if not self.xr_mode:
            self._cisco_commands["pseudo-wire"].insert(1, f"xconnect {neighbor_id} "
                                                          f"{self.vlan_id} encapsulation mpls")

    def generate_config(self):
        configs = super().generate_config()

        if configs and self.xr_mode:
            configs[0] += " l2transport"

        return configs
