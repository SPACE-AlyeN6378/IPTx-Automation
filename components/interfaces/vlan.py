from components.interfaces.interface_list import InterfaceList
from components.interfaces.interface import Interface
from components.interfaces.connector import Connector
from components.interfaces.loopback import Loopback
from typing import List


# ENUMS

class VLAN:

    @staticmethod
    def valid_id_check(vlan_id: int):
        # VLAN 4095 is a special VLAN used to represent a "wildcard" or "unassigned" VLAN.
        if 1 <= vlan_id <= 4095:
            if vlan_id == 1:
                raise ConnectionError("VLAN 1 is the default VLAN. Best practice to avoid using it for user data traffic due to security considerations.")
            
            elif vlan_id == 4095:
                raise ConnectionError("VLAN 4095 is a special VLAN used to represent a \"wildcard\" or \"unassigned\" VLAN. Rather serves as a placeholder for certain configuration or management purposes.")
            
        else:
            raise ValueError(f"Invalid ID '{vlan_id}' - The VLAN ID must be between 2 and 4095")
        

    def __init__(self, vlan_id: int, name: str="untitled", cidr: str=None) -> None:
        VLAN.valid_id_check(vlan_id)
        self.vlan_id = vlan_id
        self.name = name
        self.svi = Interface("VLAN", vlan_id, cidr)    # For SVI routing


    def __getitem__(self, port: str):
        return self.interfaces[port]
    
    def config(self, name: str=None, cidr: str=None, generate_cmd=True):
        # Update
        if name: 
            self.name = name

        if cidr:
            self.svi.config(cidr=cidr, generate_cmd=False)

        # Generate Cisco command
        if generate_cmd:
            commands = []
            commands.append(f"vlan {self.vlan_id}")

            if self.name:  
                commands.append(f"name {self.name}")

            if self.svi.ip_address:
                commands.append(f"interface vlan {self.vlan_id}")
                commands.append(f"ip address {self.svi.ip_address} {self.svi.subnet_mask}")

            return commands
        
        return None