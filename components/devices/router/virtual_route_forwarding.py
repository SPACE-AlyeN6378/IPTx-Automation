from typing import TYPE_CHECKING, List, Any
from components.interfaces.physical_interfaces.router_interface import RouterInterface
from iptx_utils import print_warning, NotFoundError

if TYPE_CHECKING:
    from components.devices.router.router import Router


class VRF:
    def __init__(self, rd: int, name: str, as_number: int, color: str = "gray"):
        self.rd: int = rd
        self.name: str = name
        self.as_number: int = as_number
        self.route_targets: List[int] = []
        self.assigned_routers: set['Router'] = set()

        # Cisco commands
        self.__setup_commands: list[str] = [
            f"vrf definition {name}",
            f"rd {self.as_number}:{self.rd}",
            "address-family ipv4",
            f"route-target export {self.as_number}:{self.rd}",
            "exit-address-family",
            "exit"
        ]

        self.color = color

    def __eq__(self, other: 'VRF') -> bool:
        return self.rd == other.rd

    def __hash__(self):
        return hash(self.rd)

    def get_setup_cmd(self) -> List[str]:
        return self.__setup_commands
    def get_xr_setup_cmd(self) -> List[str]:
        cisco_xr_commands = []

        for line in self.__setup_commands[:]:
            if line == f"rd {self.as_number}:{self.rd}":
                continue

            if "address-family ipv4 vrf" in line:
                line = line.replace("address-family ipv4 ", "")

            if "vrf definition" in line:
                line = f"vrf {self.name}"

            elif line == "address-family ipv4":
                line = line.replace("ipv4", "ipv4 unicast")

            elif "import" in line:
                line = line.replace("route-target import", "import route-target")

            elif "export" in line:
                line = line.replace("route-target export", "export route-target")

            cisco_xr_commands.append(line)

        return cisco_xr_commands

    def clear_setup_cmd(self) -> None:
        self.__setup_commands.clear()

    def get_router(self, router_id: str) -> 'Router':
        for router in self.assigned_routers:
            if router.id() == router_id:
                return router

        raise IndexError("Router with ID {} not found".format(router_id))

    def add_router(self, router: 'Router') -> None:
        if router not in self.assigned_routers:
            router.add_vrf(self)        # Add the VRF to the router
            self.assigned_routers.add(router)      # Add the router to the VRF

        if self.__setup_commands:
            self.__setup_commands: list[str] = [
                f"vrf definition {self.name}",
                f"rd {self.as_number}:{self.rd}",
                "address-family ipv4",
                f"route-target export {self.as_number}:{self.rd}",
                "exit-address-family",
                "exit"
            ]

    def set_route_targets(self, *new_route_targets: int) -> None:
        if not self.__setup_commands:
            self.__setup_commands: list[str] = [
                f"vrf definition {self.name}",
                "address-family ipv4",
                "exit-address-family",
                "exit"
            ]

        for route_target in new_route_targets:
            if route_target not in self.route_targets:
                self.route_targets.append(route_target)
                self.__setup_commands.insert(-2, f"route-target import {self.as_number}:{route_target}")

    def discard_route_targets(self, route_target: int) -> None:
        if not self.__setup_commands:
            self.__setup_commands: list[str] = [
                f"vrf definition {self.name}",
                "address-family ipv4",
                "exit-address-family",
                "exit"
            ]

        # Remove VRF address-family in BGP configuration
        print_warning("The VRF address-family in BGP will been removed from the router", prompt=False)
        self.__setup_commands[0:0] = [
            f"router bgp {self.as_number}",
            f"no address-family ipv4 vrf {self.name}",
            "exit"
        ]

        # Remove VRF address-family in BGP configuration
        self.__setup_commands.insert(-2, f"no route-target import {self.as_number}:{route_target}")

    def get_assigned_interfaces(self, router_id: str, ebgp_unconfirmed_only: bool = False) -> List[RouterInterface]:

        router = self.get_router(router_id)

        if ebgp_unconfirmed_only:
            return [interface for interface in router.all_phys_interfaces() if interface.vrf_name == self.name
                    and not interface.ebgp_neighbor_confirmed]

        else:
            return [interface for interface in router.all_phys_interfaces() if interface.vrf_name == self.name]

    def get_interface(self, router_id: str, port: str) -> RouterInterface:
        for interface in self.get_assigned_interfaces(router_id, ebgp_unconfirmed_only=False):
            if interface.port == port:
                return interface

        raise NotFoundError(f"No interface with port '{port}' found in ID {router_id}, VRF {self.name}")

    def assign_interface(self, router_id: str, port: str) -> None:
        (self.get_router(router_id)
         .interface(port)
         .assign_vrf(self.name))

    def unassign_interface(self, router_id: str, port: str) -> None:
        interface = self.get_router(router_id).interface(port)
        interface.remove_vrf()

    def generate_af_command(self, router_id: str, all_interfaces: bool = False, ios_xr: bool = False,
                            route_policy_name: str = "PASS") -> list[str]:

        cisco_commands = []
        if self.get_assigned_interfaces(router_id, not all_interfaces): # Any interfaces to be configured
            if not ios_xr:
                cisco_commands = [
                    f"address-family ipv4 vrf {self.name}",
                    "redistribute connected",
                    f"exit-address-family"
                ]

            else:
                cisco_commands = [
                    f"vrf {self.name}",
                    f"rd {self.as_number}:{self.rd}",
                    "address-family ipv4 unicast",
                    "label mode per-vrf",
                    "redistribute connected",
                    "exit"
                ]

        for interface in self.get_assigned_interfaces(router_id, not all_interfaces):
            if not interface.static_routing:

                remote_device: Router = interface.remote_device
                remote_ip: str = remote_device.interface(interface.remote_port).ip_address
                remote_as: int = remote_device.as_number

                if not ios_xr:
                    cisco_commands[-2:-2] = [
                        f"neighbor {remote_ip} remote-as {remote_as}",
                        f"neighbor {remote_ip} activate"
                    ]

                else:
                    cisco_commands.extend([
                        f"neighbor {remote_ip}",
                        f"remote-as {remote_as}",
                        "address-family ipv4 unicast",
                        f"route-policy {route_policy_name} in",
                        f"route-policy {route_policy_name} out",
                        "soft-reconfiguration inbound always",
                        "exit",
                        "exit"
                    ])

            interface.ebgp_neighbor_confirmed = True

        if ios_xr:
            cisco_commands.append("exit")

        return cisco_commands

    def get_dictionary(self) -> dict[str, str | int | dict[str, str]]:
        def format_details(key: str, values: List[Any]):
            result = f"{key}: {values[0]}\n"

            if len(values) > 1:
                result += '\n'.join(f"{' '*len(key)}  {str(value)}" for value in values[1:])

                result += "\n"

            return result

        routers_and_ints_data = '\n'.join(format_details(str(router), self.get_assigned_interfaces(router.id()))
                                            for router in self.assigned_routers)

        return {
            "RD": self.rd,
            "Name": self.name,
            "Routers: Interfaces": routers_and_ints_data,
            "Exported to": str(self.route_targets)
        }
