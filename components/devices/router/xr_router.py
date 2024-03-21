from components.devices.router.router import (Router, RouterInterface, Loopback, Iterable, VRFKey, NetworkError,
                                              print_warning, NetworkDevice, List, Fore)


class XRRouter(Router):

    def __init__(self, router_id: str, hostname: str = "Router",
                 interfaces: Iterable[RouterInterface | Loopback] = None) -> None:
        super().__init__(router_id, hostname, interfaces)

        self._bgp_commands: dict[str, list[str]] = {
            "start": [],
            "id": [],
            "address_families": [],
            "neighbor_group": [],
            "neighbor": [],
            "external": []
        }

    def __str__(self) -> str:
        name = "XR " + super().__str__()
        return name

    def add_interface(self, *new_interfaces: RouterInterface | Loopback) -> None:
        for interface in new_interfaces:
            interface.xr_mode = True

        super().add_interface(*new_interfaces)

    def add_vrf(self, rd_number: int, name: str) -> None:
        super().add_vrf(rd_number, name)
        self._vrf_commands[rd_number] = [
            f"vrf {name}",
            "address-family ipv4 unicast",
            f"export route-target {self.as_number}:{rd_number}",
            "exit",
            "exit"
        ]

    def __translate_vrf_cmd(self, rd_number: int):
        for i, line in enumerate(self._vrf_commands[rd_number]):
            if "vrf definition" in line:
                self._vrf_commands[rd_number][i] = f"vrf {self.vrfs[rd_number][VRFKey.NAME]}"

            elif line == "address-family ipv4":
                self._vrf_commands[rd_number][i] = line.replace("ipv4", "ipv4 unicast")

            elif "route-target import" in line:
                self._vrf_commands[rd_number][i] = line.replace("route-target import", "import route-target")

    def add_route_targets(self, rd_number: int, new_rts: Iterable[int]) -> None:
        super().add_route_targets(rd_number, new_rts)

        # Translate the IOS commands
        self.__translate_vrf_cmd(rd_number)

    def del_route_target(self, rd_number: int, rt_to_be_removed: int) -> None:
        super().del_route_target(rd_number, rt_to_be_removed)

        # Translate the IOS commands
        self.__translate_vrf_cmd(rd_number)

    def remove_vrf(self, rd_number: int) -> None:
        super().remove_vrf(rd_number)

        # Translate the IOS command
        self._vrf_commands[rd_number] = [self._vrf_commands[rd_number][0].replace("definition ", "")]

    def begin_internal_routing(self) -> None:
        super().begin_internal_routing()

        # Regenerate Cisco command to translate to XR configuration script
        self.__routing_commands["ospf"] = [
            f"router ospf {self.OSPF_PROCESS_ID}",  # Define the process ID
            f"router-id {self.id()}",  # Router ID
            f"auto-cost reference-bandwidth {self.reference_bw}",  # Cost is autoconfigured using reference BW
        ]

        # Iterate through each area
        for area_number in self.get_all_areas():
            self.__routing_commands["ospf"].append(f"area {area_number}")

            # Iterate through each interface by area number
            for interface in self.get_ints_by_ospf_area(area_number):

                if interface.int_type == "Loopback":
                    # Add the XR commands
                    self.__routing_commands["ospf"].extend(interface.generate_ospf_xr_commands())

                elif interface.remote_device is not None and not interface.egp:
                    # Add the XR commands
                    self.__routing_commands["ospf"].extend(interface.generate_ospf_xr_commands())

            self.__routing_commands["ospf"].append("exit")

        self.__routing_commands["ospf"].append("exit")

    def bgp_routing(self, initialization: bool = False, ibgp_neighbor_ids: Iterable[str] = None,
                    redistribution: bool = False) -> None:

        # Step 1/2 is executed from the superclass
        super().bgp_routing(initialization=initialization, ibgp_neighbor_ids=None, redistribution=False)

        # Step 3: Initialize address families
        def address_families():
            # IPv4 Unicast
            self._bgp_commands["address_families"] = [
                "address-family ipv4 unicast",
                "exit"
            ]

            if self.__any_mpls_interfaces():
                # VPNv4 Unicast
                self._bgp_commands["address_families"].extend([
                    "address-family vpnv4 unicast",
                    "exit"
                ])

        # Helper function to assign a name for IBGP neighbor-group
        def ibgp_nbrgrp_name():
            if self.route_reflector:
                return "RR_TO_CLIENT"

            elif self.is_provider_edge():
                return "CLIENT_TO_RR"

            else:
                return "?"

        # Change the parameter 'ibgp_neighbor_ids'
        if ibgp_neighbor_ids is None:
            ibgp_neighbor_ids = []

        # Step 4: Configure neighbor-group
        def config_ibgp_neighbor_group():
            neighbor_config_cmd = "!"

            # Route-reflector or provider edge?
            if self.route_reflector:
                neighbor_config_cmd = "route-reflector-client"

            elif self.is_provider_edge():
                neighbor_config_cmd = "soft-reconfiguration inbound always"

            # Introduce neighbor-group
            self._bgp_commands["neighbor_group"] = [
                f"neighbor-group {ibgp_nbrgrp_name()}",
                f"remote-as {self.as_number}",
                f"update-source {self.loopback(0)}"
            ]

            # Insert the commands
            if self.__any_mpls_interfaces():
                self._bgp_commands["neighbor_group"].extend(
                    ["address-family ipv4 labeled-unicast",
                     neighbor_config_cmd,
                     "exit",
                     "address-family vpnv4 unicast",
                     neighbor_config_cmd,
                     "exit"]
                )

            else:
                self._bgp_commands["neighbor_group"].extend(
                    ["address-family ipv4 unicast",
                     neighbor_config_cmd,
                     "exit"]
                )

            # Exit out
            self._bgp_commands["neighbor_group"].append("exit")

        # Step 5: Assign neighbors
        def assign_ibgp_neighbors():
            # Assign neighbor group to each adjacent routers to establish neighbor
            for rtr_id in ibgp_neighbor_ids:
                self.ibgp_adjacent_router_ids.add(rtr_id)

                self._bgp_commands["neighbor"].extend([
                    f"neighbor {rtr_id}",
                    f"use neighbor-group {ibgp_nbrgrp_name()}",
                    "exit"
                ])

        # Step 6: Redistribute connected routers to the external routes
        def redistribution_to_external_routes():
            vrfs = [(rd, vrf_[VRFKey.NAME]) for rd, vrf_ in self.vrfs.items()]

            # Introduce the PASS routing policy to allow all the prefixes in
            self.__routing_commands["route-policy"].extend([
                "route-policy PASS",
                "pass",
                "end-policy"
            ])

            # Helper functions to establish EBGP neighbors, one with and without VRF
            def establish_ebgp_neighbors(vrf_name=None):
                for interface in filter(lambda i: i.vrf_name == vrf_name and not i.static_routing,
                                        self.all_phys_interfaces()):

                    if interface.remote_device is None:
                        raise NetworkError(f"Interface {str(interface)} is not connected to any remote devices")

                    if not isinstance(interface.remote_device, Router):
                        raise TypeError(f"This remote device '{str(interface.remote_device)}' is not a router")

                    remote_as = interface.remote_device.as_number
                    interface_ip = interface.remote_device.interface(interface.remote_port).ip_address

                    self._bgp_commands["external"].extend([
                        f"neighbor {interface_ip}",
                        f"remote-as {remote_as}",
                        "address-family ipv4 unicast",
                        "route-policy PASS in",
                        "route-policy PASS out",
                        "soft-reconfiguration inbound always",
                        "exit",
                        "exit"
                    ])

            # Iterate through each VRF
            for rd, name in vrfs:
                # Open the VRF configuration section and redistribute the IGP
                self._bgp_commands["external"] = [
                    f"vrf {name}",
                    f"rd {self.as_number}:{rd}",
                    "address-family ipv4 unicast",
                    "label mode per-vrf",
                    "redistribute connected",
                    "exit"
                ]

                # Establish neighborhood adjacency for each remote interfaces
                establish_ebgp_neighbors(name)

                # Exit out
                self._bgp_commands["external"].append("exit")

            if not vrfs:
                self._bgp_commands["address_families"].insert(1, "redistribute connected")
                self._bgp_commands["external"] = []
                establish_ebgp_neighbors()

        def execute_function():
            if initialization:
                address_families()
                config_ibgp_neighbor_group()
            if ibgp_neighbor_ids:
                assign_ibgp_neighbors()
            if redistribution:
                redistribution_to_external_routes()

        execute_function()

    def disable_vrf_redistribution(self, vrf_name: str) -> None:
        super().disable_vrf_redistribution(vrf_name)

        self._starter_commands["vrf_af_disable"][-1] = f"no vrf {vrf_name}"

    def __mpls_ldp_activate(self) -> None:
        if self.__any_mpls_interfaces() and not self.__mpls_configured:
            self.__routing_commands["mpls"] = [
                "mpls ldp",
                f"router-id {self.id()}"
            ]

            for interface in self.all_phys_interfaces():
                if interface.mpls_enabled:
                    self.__routing_commands["mpls"].append(f"interface {str(interface)}")
                    self.__routing_commands["mpls"].append("exit")

            self.__routing_commands["mpls"].append("exit")
            self.__mpls_configured = True

    def send_script(self, print_to_console: bool = True) -> List[str]:
        script = super().send_script(print_to_console=False)
        script.insert(-1, "commit")

        if print_to_console:
            NetworkDevice.print_script(script, Fore.YELLOW)

        return script
