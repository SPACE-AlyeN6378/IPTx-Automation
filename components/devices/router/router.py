from components.devices.network_device import NetworkDevice
from components.interfaces.physical_interfaces.router_interface import RouterInterface
from components.interfaces.loopback.loopback import Loopback
from typing import Iterable, Dict, List


class Router(NetworkDevice):
    OSPF_PROCESS_ID = 65000

    def __init__(self, router_id: str, hostname: str = "Router",
                 interfaces: Iterable[RouterInterface | Loopback] = None, ios_xr: bool = False) -> None:
        self.ios_xr: bool = ios_xr
        super().__init__(device_id=router_id, hostname=hostname, interfaces=interfaces)
        self.ospf_areas: Dict[int, List[str]] = dict()

        self.routing_commands: Dict[str, List[str]] = {
            "ospf": [],
            "ospf_mpls": [],
            "bgp": []
        }

    # Overriden from NetworkDevice for changing type alias
    def interface(self, port: str) -> RouterInterface:
        return super().interface(port)

    # Overriden from NetworkDevice for changing type alias
    def interface_range(self, *ports: str) -> List[RouterInterface]:
        return super().interface_range(*ports)

    # Overriden from NetworkDevice for changing type alias
    def all_phys_interfaces(self) -> List[RouterInterface]:
        return super().all_phys_interfaces()

    # Overriden from NetworkDevice for changing type alias
    def all_interfaces(self) -> List[RouterInterface | Loopback]:
        return super().all_interfaces()

    # Overriden from NetworkDevice
    def add_interface(self, *new_interfaces: RouterInterface | Loopback) -> None:
        if not all(isinstance(interface, (RouterInterface, Loopback)) for interface in new_interfaces):
            raise TypeError("All interfaces should either be a RouterInterface or a Loopback")

        if self.ios_xr:
            for interface in new_interfaces:
                interface.xr_mode = True

        super().add_interface(*new_interfaces)



