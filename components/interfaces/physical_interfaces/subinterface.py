from components.interfaces.interface import Interface


class SubInterface(Interface):
    def __init__(self, int_type: str, port: str | int, vlan_id: int, cidr: str = None,
                 mtu: int = 1500) -> None:

        super().__init__(int_type, port, cidr)
        self.vlan_id: int = vlan_id
        self.mtu: int = mtu
        self.xr_mode: bool = False

        self.neighbor_ids = set()

        self.pw_redundancy_configured = False
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

    def pseudowire_config(self, neighbor_id: str = None) -> None:

        if not self._cisco_commands["pseudo-wire"]:
            self._cisco_commands["pseudo-wire"] = [
                f"encapsulation dot1q {self.vlan_id}",
                f"mtu {self.mtu}"
            ]

        if not self.xr_mode:
            self._cisco_commands["pseudo-wire"].insert(-1, f"xconnect {neighbor_id} "
                                                           f"{self.vlan_id} encapsulation mpls")

        if neighbor_id in self.neighbor_ids:
            self.pw_redundancy_configured = False
        else:
            self.neighbor_ids.add(neighbor_id)

    def generate_config(self):
        configs = super().generate_config()

        if configs and self.xr_mode:
            configs[0] += " l2transport"

        return configs

    def generate_pw_redundancy_config(self) -> list[str]:
        # This function goes inside the L2VPN section in IOS-XR
        configs = []
        if not self.pw_redundancy_configured:
            configs = [
                f"interface {str(self)}",
                "exit"
            ]
            for neighbor_id in self.neighbor_ids:
                configs.insert(-1, f"neighbor ipv4 {neighbor_id} pw-id {self.vlan_id}")
                configs.insert(-1, "exit")

            self.pw_redundancy_configured = True

        return configs
