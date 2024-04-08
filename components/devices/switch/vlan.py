from components.interfaces.interface import Interface
from typing import List

from components.interfaces.physical_interfaces.physical_interface import PhysicalInterface


# ENUMS

class VLAN:

    @staticmethod
    def valid_id_check(vlan_id: int):
        # VLAN 4095 is a special VLAN used to represent a "wildcard" or "unassigned" VLAN.
        if 1 <= vlan_id <= 4095:
            if vlan_id == 4095:
                raise ConnectionError("VLAN 4095 is a special VLAN used to represent a \"wildcard\" or \"unassigned\" "
                                      "VLAN. Rather serves as a placeholder for certain configuration or management "
                                      "purposes.")

        else:
            raise ValueError(f"Invalid ID '{vlan_id}' - The VLAN ID must be between 2 and 4094")

    def __init__(self, vlan_id: int, name: str = None, cidr: str = None) -> None:
        VLAN.valid_id_check(vlan_id)
        self.vlan_id = vlan_id
        self.name = name
        self.vlan_as_interface = Interface("VLAN", vlan_id, cidr)  # For SVI routing
        self.assigned_routers: set[PhysicalInterface] = set()

        self._stp_primary_device = None

    def config(self, name: str = None, cidr: str = None) -> None:
        if name:
            self.name = name

        if cidr:
            self.vlan_as_interface.config(cidr=cidr)

    # For switches =======================================
    def generate_init_cmd(self) -> List[str]:
        return [
            f"vlan {self.vlan_id}",
            f"name {self.name}",
            "exit"
        ]

    def generate_interface_cmd(self) -> List[str]:
        configs = self.vlan_as_interface.generate_command_block()
        configs.insert(-1, "no shutdown")
        return configs
