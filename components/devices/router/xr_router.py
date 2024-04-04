from components.devices.router.router import (Router, RouterInterface, Loopback, Iterable, NetworkError,
                                              NetworkDevice, List, Fore)


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
            "external": [],
            "close": []
        }

    def __str__(self) -> str:
        name = "XR " + super().__str__()
        return name

    def add_interface(self, *new_interfaces: RouterInterface | Loopback) -> None:
        for interface in new_interfaces:
            interface.xr_mode = True

        super().add_interface(*new_interfaces)

    def _consolidate_vrf_setup_commands(self) -> None:
        self._starter_commands["vrf"].clear()
        for vrf in self.vrfs:
            self._starter_commands["vrf"].extend(vrf.get_xr_setup_cmd())

    def begin_internal_routing(self, mpls_ldp_sync: bool = True) -> None:
        super().begin_internal_routing()

        # Regenerate Cisco command to translate to XR configuration script
        self._routing_commands["ospf"] = [
            f"router ospf {self.OSPF_PROCESS_ID}",  # Define the process ID
            f"router-id {self.id()}",  # Router ID
            f"auto-cost reference-bandwidth {self.reference_bw}",  # Cost is autoconfigured using reference BW
        ]

        # Iterate through each area
        for area_number in self.get_all_areas():
            self._routing_commands["ospf"].append(f"area {area_number}")

            # Iterate through each interface by area number
            for interface in self.get_ints_by_ospf_area(area_number):

                if interface.int_type == "Loopback":
                    # Add the XR commands
                    self._routing_commands["ospf"].extend(interface.generate_ospf_xr_commands(mpls_ldp_sync))

                elif interface.remote_device is not None and not interface.egp:
                    # Add the XR commands
                    self._routing_commands["ospf"].extend(interface.generate_ospf_xr_commands(mpls_ldp_sync))

            self._routing_commands["ospf"].append("exit")

        self._routing_commands["ospf"].append("exit")

    def bgp_routing(self, initialization: bool = False, ibgp_neighbor_ids: Iterable[str] = None,
                    redistribution_to_egp: bool = False) -> None:

        # Step 1/2 is executed from the superclass
        super().bgp_routing(initialization=initialization, ibgp_neighbor_ids=None, redistribution_to_egp=False)
        # I have no idea how this 'af_vpn_v4' key got here, so I had to pop it off 😂
        self._bgp_commands.pop("af_vpn_v4")

        # Step 3: Initialize address families
        def address_families():
            # IPv4 Unicast
            self._bgp_commands["address_families"] = [
                "address-family ipv4 unicast",
                "exit"
            ]

            if self._any_mpls_interfaces():
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
            if self._any_mpls_interfaces():
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
                if rtr_id not in self.ibgp_adjacent_router_ids:
                    self.ibgp_adjacent_router_ids.add(rtr_id)

                    self._bgp_commands["neighbor"].extend([
                        f"neighbor {rtr_id}",
                        f"use neighbor-group {ibgp_nbrgrp_name()}",
                        "exit"
                    ])

        # Step 6: Introduce the PASS routing policy to allow all the prefixes in
        def pass_routing_policy():
            self._routing_commands["route-policy"].extend([
                "route-policy PASS",
                "pass",
                "end-policy"
            ])

        # Step 7: Redistribute connected routers to the external routes
        def redistribution_to_external_routes():
            # Iterate through each VRF
            for vrf in self.vrfs:
                # Establish neighborhood adjacency for each remote interfaces
                self._bgp_commands["external"].extend(vrf.generate_af_command(self.id(), ios_xr=True))

        def close_out():
            self._bgp_commands["close"] = ["exit"]

        def execute_function():
            if initialization:
                config_ibgp_neighbor_group()
                address_families()
                pass_routing_policy()
            if ibgp_neighbor_ids:
                assign_ibgp_neighbors()
            if redistribution_to_egp:
                redistribution_to_external_routes()
            close_out()

        execute_function()

    def __mpls_ldp_activate(self) -> None:
        if self._any_mpls_interfaces() and not self.__mpls_configured:
            self._routing_commands["mpls"] = [
                "mpls ldp",
                f"router-id {self.id()}"
            ]

            for interface in self.all_phys_interfaces():
                if interface.mpls_enabled:
                    self._routing_commands["mpls"].append(f"interface {str(interface)}")
                    self._routing_commands["mpls"].append("exit")

            self._routing_commands["mpls"].append("exit")
            self.__mpls_configured = True

    def client_connection_routing(self, interface_port: str) -> None:
        chosen_interface = self.interface(interface_port)
        if not chosen_interface.egp:
            raise NetworkError("This is not an inter-autonomous connection")

        remote_device: Router = chosen_interface.remote_device
        remote_port: str = chosen_interface.remote_port
        remote_int_ip_address = remote_device.interface(remote_port)

        if chosen_interface.static_routing:
            self._routing_commands["client-connection"] = [
                "router static",
                "address-family ipv4 unicast",
                f"{remote_device.id()} 255.255.255.255 {remote_int_ip_address}",
                "exit", "exit"
            ]

        else:
            remote_as = remote_device.as_number

            if self._routing_commands["client-connection"]:
                self._routing_commands["client-connection"] = [
                    f"router bgp {self.as_number}",
                    "address-family ipv4 unicast",
                    "exit-address-family",
                    "exit"
                ]

            self._routing_commands["client-connection"].insert(1,
                                                               f"neighbor {remote_int_ip_address} "
                                                               f"remote-as {remote_as}")

            self._routing_commands["client-connection"].insert(-2, f"neighbor {remote_int_ip_address} activate")

    def generate_script(self) -> List[str]:
        script = super().generate_script()
        script.remove("do write memory")

        return script
