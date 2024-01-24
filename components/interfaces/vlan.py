from components.interfaces.interface_list import InterfaceList
from components.interfaces.interface import Interface
from typing import List


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
        self.interface = Interface("VLAN", vlan_id, cidr)  # For SVI routing

        self._stp_primary_device = None

    def config(self, name: str = None, cidr: str = None):

        # Generate Cisco command
        ios_commands = [f"vlan {self.vlan_id}"]

        # Update
        if name:
            self.name = name

        if self.name:
            ios_commands.append(f"name {self.name}")

        ios_commands.append("exit")

        if cidr:
            self.interface.config(cidr=cidr)
            ios_commands.extend(self.interface.get_command_block())

        return ios_commands
