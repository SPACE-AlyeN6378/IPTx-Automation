from components.devices.router.xr_router import XRRouter
from components.topologies.autonomous_system.backbone import Backbone, Router, RouterInterface
from components.devices.switch.vlan import VLAN
from typing import Iterable

from iptx_utils import print_success

class L2VPNBackbone(Backbone):
    def __init__(self, as_number: int, name: str, devices: Iterable[Router] = None):

        print(f"\n==================== IPTx L2VPN BACKBONE {as_number}: '{name}' ====================\n")
        super().__init__(as_number, name, devices)
        self.__vlans: list[VLAN] = []
        self.__color_index = 0
        self.mtu = 9178

    def get_vlan(self, vlan_id: int) -> VLAN | None:
        for vlan in self.__vlans:
            if vlan.vlan_id == vlan_id:
                return vlan

        return None

    def add_vlan(self, vlan_id: int, name: str = None, cidr: str = None):
        def get_colour():
            # Helper function for colour picking, to help distinguish between routes
            colors = [
                "#0000FF",  # Blue
                "#FF0000",  # Red
                "#008000",  # Green
                "#FFA500",  # Orange
                "#800080",  # Purple
                "#FFFF00",  # Yellow
                "#00FFFF",  # Cyan
                "#FF00FF",  # Magenta
                "#008080",  # Teal
                "#FFC0CB",  # Pink
                "#00FF00",  # Lime
                "#E6E6FA",  # Lavender
                "#A52A2A",  # Brown
                "#F5F5DC",  # Beige
                "#800000",  # Maroon
                "#000080",  # Navy
                "#808000",  # Olive
                "#FFDAB9",  # Peach
                "#40E0D0",  # Turquoise
                "#4B0082"  # Indigo
            ]
            color = colors[self.__color_index]
            self.__color_index = (self.__color_index + 1) % len(colors)

            return color

        if self.get_vlan(vlan_id):
            raise ValueError(f"VLAN {vlan_id} already exists")

        self.__vlans.append(VLAN(vlan_id, name, cidr, get_colour()))
        print_success(f"VLAN {vlan_id} with name '{name}' added!")

    def connect_devices(self, device_id1: str, port1: str, device_id2: str, port2: str,
                        scr: int = None, cable_bandwidth: int = float('inf')) -> None:

        super().connect_devices(device_id1, port1, device_id2, port2, scr, cable_bandwidth)

        # Change the MTU
        interfaces = (self[device_id1].interface(port1), self[device_id2].interface(port2))

        for interface in interfaces:
            if isinstance(interface, RouterInterface):
                if interface.xr_mode:
                    interface.config(mtu=self.mtu + 14)
                else:
                    interface.config(mtu=self.mtu)
            else:
                interface.config(mtu=self.mtu)

    def establish_pseudowire(self, client_id1: str, client_id2: str, vlan_id: int, vlan_name: str = None,
                             xc_group_name: str = None, p2p_identifier: str = None) -> None:
        if self.get_vlan(vlan_id) is None:
            self.add_vlan(vlan_id, vlan_name)

        interfaces = (self.get_gateway_inf_from_client(client_id1), self.get_gateway_inf_from_client(client_id2))
        self.get_vlan(vlan_id).establish_pseudowire(*interfaces)

        for interface in interfaces:
            if isinstance(interface, RouterInterface):
                if interface.xr_mode:
                    self[interface.device_id].l2vpn_xc_config(xc_group_name, p2p_identifier)
