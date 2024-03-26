from components.topologies.topology import Router, plt
import networkx as nx
from typing import Iterable, List

from components.topologies.autonomous_system.backbone import Backbone, tabulate, print_log
from components.devices.router.virtual_route_forwarding import VRF
from iptx_utils import NetworkError, NotFoundError, print_warning, print_success


class L3VPNBackbone(Backbone):
    def __init__(self, as_number: int, name: str, devices: Iterable[Router] = None,
                 route_reflector_id: str = None):

        print(f"\n==================== IPTx L3VPN BACKBONE {as_number}: '{name}' ====================\n")
        super().__init__(as_number, name, devices)

        if route_reflector_id:
            self.route_reflector: str = route_reflector_id
            self.select_route_reflector(route_reflector_id)
        else:
            self.route_reflector: str | None = None

        # VPN Configuration
        self.__vpn_graph = nx.MultiDiGraph()
        self.__vrf_index = 0
        self.__color_index = 0

    def select_route_reflector(self, router_id: str) -> None:
        # Route-reflection is of no use with a single router
        if len([router.id() for router in self.get_all_routers()]) <= 2:
            print_warning("This autonomous system only has one or two routers. So there's no use of route-reflecting")

        # If this autonomous system already has a router
        if any(router.route_reflector for router in self.get_all_routers()):
            raise NetworkError(f"This autonomous system already has a route-reflector with ID {self.route_reflector}")

        self.route_reflector = router_id
        self.get_device(router_id).set_as_route_reflector()

        print_success(f"{self.get_device(router_id)} with ID {router_id} chosen as Route-reflector client")

    def get_all_vrfs(self, name_rd_only: bool = False) -> List[VRF] | List[str]:
        if name_rd_only:
            return [vrf_id for vrf_id, data in self.__vpn_graph.nodes(data=True)]
        else:
            return [data["node_object"] for vrf_id, data in self.__vpn_graph.nodes(data=True)]

    def get_vrf(self, vrf_id: str) -> VRF:
        try:
            return self.__vpn_graph.nodes[vrf_id]['node_object']
        except KeyError:
            raise NotFoundError(f"VRF with name-rd '{vrf_id}' cannot be found")

    def add_vrf(self, vrf_name: str, router_id: str = None, port: str = None) -> str:

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

        rd = len(self.get_all_vrfs(name_rd_only=True)) + 1  # rd = route-distinguisher
        vrf_id = f"{vrf_name}-{rd}"

        self.__vpn_graph.add_node(node_for_adding=vrf_id,
                                  node_object=VRF(rd, vrf_name, self.as_number, get_colour()))

        if router_id and port:
            self.set_vrf_to_port(f"{vrf_name}-{rd}", router_id, port)

        return vrf_id

    def set_vrf_to_port(self, vrf_id: str, router_id: str, port: str) -> None:

        if self[router_id].as_number != self.as_number:
            raise NetworkError(f"This router with ID {router_id} is not within the AS")

        self.get_vrf(vrf_id).add_router(self[router_id])
        self.get_vrf(vrf_id).assign_interface(router_id, port)

    def print_vrfs(self) -> None:
        # vrfs = sorted(self.__vpn_graph.nodes(data=True))
        data = [data["node_object"].get_dictionary() for vrf_id, data in self.__vpn_graph.nodes(data=True)]

        # Print the table
        print()
        print_log("These are the following VRFs:")
        print(tabulate(data, headers="keys", tablefmt='grid'))
        print()

    def vpn_connection(self, source: str, destination: str, allow_log: bool = True) -> None:

        # Prevent duplicate edges
        if not self.__vpn_graph.has_edge(source, destination):
            self.__vpn_graph.add_edge(source, destination)

        # Assign the destination RD inside the VRF
        destination_rd: int = self.get_vrf(destination).rd
        self.get_vrf(source).set_route_targets(destination_rd)

        # if allow_log:
        #     print_log(f"VRF Route-target: {self.__vpn_graph.nodes[source]['name']} ---> "
        #               f"{self.__vpn_graph.nodes[destination]['name']}", 0)

    # def vpn_two_way_connection(self, vrf1: int | str, vrf2: int | str) -> None:
    #     # If a name is passed for the VRF 1, take the corresponding RD
    #     if isinstance(vrf1, str):
    #         source = self.get_vrf(vrf1)[0]
    #
    #     # If a name is passed for the VRF 2, take the corresponding RD
    #     if isinstance(vrf2, str):
    #         destination = self.get_vrf(vrf2)[0]
    #
    #     # Use the previous function to establish route-targets, but do not print the log
    #     self.vpn_connection(vrf1, vrf2, allow_log=False)
    #     self.vpn_connection(vrf2, vrf1, allow_log=False)
    #
    #     # Log-printing will be used here
    #     print_log(f"VRF Route-target: {self.__vpn_graph.nodes[vrf1]['name']} <---> "
    #               f"{self.__vpn_graph.nodes[vrf2]['name']}", 0)
    #
    # def vrf_hub_and_spoke(self, hub: int | str) -> None:
    #     if isinstance(hub, str):
    #         hub = self.get_vrf(hub)[0]
    #
    #     print_log(f"VRF Hub and spoke confirmed, with {self.__vpn_graph.nodes[hub]['name']} as the hub")
    #
    #     for rd in self.__vpn_graph.nodes():
    #         if rd != hub:
    #             self.vpn_two_way_connection(hub, rd)
    #
    #     print()
    #
    # def vrf_full_mesh(self) -> None:
    #
    #     print_log(f"VRF Full mesh confirmed")
    #     edges = list(permutations(self.__vpn_graph.nodes(), 2))
    #     for src, destination in edges:
    #         self.vpn_connection(src, destination, allow_log=False)
    #
    #     print_log(f"VRF Route-target: ALL <---> ALL", 0)
    #     print()

    def get_receivers(self, client_id: str):
        def get_vrf_by_client_id(client_id: str):
            for link in self._graph.edges(data=True):
                if link[2]['external'] and link[1].id() == client_id:

                    return link[2]["vrf"]

            return None
        print(get_vrf_by_client_id(client_id))

    def show_vpn_graph(self) -> None:
        pos = nx.spring_layout(self.__vpn_graph)  # Positions for all nodes
        nx.draw(self.__vpn_graph, pos, with_labels=True, arrows=True,
                node_color=[vrf.color for vrf in self.get_all_vrfs()],
                labels={node_id: node_id for node_id, data in self.__vpn_graph.nodes(data=True)},
                width = 2, node_size = 1000)
        plt.show()

    def connect_client(self, client_device: Router, client_port: str,
                       bkb_router_id: str, bkb_router_port: str, cable_bandwidth: int = None,
                       network_address: str = None, new_vrf: str = None, existing_vrf_id: str = None,
                       static_routing: bool = False) -> None:

        if not (new_vrf or existing_vrf_id):
            raise TypeError("Missing parameters for either 'new_vrf' or 'existing_vrf': VRF is required!")

        super().connect_client(client_device, client_port, bkb_router_id, bkb_router_port, cable_bandwidth)

        # Network Address Assignment
        self.assign_network_ip_address(network_address, bkb_router_id, client_device.id())

        # VRF Assignment
        if new_vrf is not None:
            vrf: str = self.add_vrf(new_vrf, bkb_router_id, bkb_router_port)
            self.get_link(client_device.id(), bkb_router_id)[2]["vrf"] = vrf
            self[client_device.id()].node_color = self.get_vrf(vrf).color

        elif existing_vrf_id is not None:
            self.set_vrf_to_port(existing_vrf_id, bkb_router_id, bkb_router_port)
            self.get_link(client_device.id(), bkb_router_id)[2]["vrf"] = existing_vrf_id
            self[client_device.id()].node_color = self.get_vrf(existing_vrf_id).color

        # Static or dynamic
        self[client_device.id()].interface(client_port).static_routing = static_routing
        self[bkb_router_id].interface(bkb_router_port).static_routing = static_routing
        self.get_link(client_device.id(), bkb_router_id)[2]["static_routing"] = static_routing

        # Client routing configuration
        self[client_device.id()].client_connection_routing(client_port)
        self[client_device.id()].send_script()

    def print_client_links(self) -> None:
        def bool_to_str(bool_value: bool) -> str:
            return "Static" if bool_value else "Dynamic"

        links = sorted(self._graph.edges(data=True), key=lambda link: link[2]["scr"])

        data = [[
            str(link[2]['scr']),
            f"{link[0]} ({link[2]['d1_port']}) ---> {link[1]} ({link[2]['d2_port']})",
            f"{link[2]["network_address"]}",
            f"{link[2]["vrf"]}",
            f"{link[2]['bandwidth']}",
            f"{bool_to_str(link[2]["static_routing"])}"
        ] for link in links if link[2]['external']]

        headers = ["SCR", "Source/Destination", "Network Address", "VRF", "Bandwidth (KB/s)", "Routing Type"]

        print()
        print_log("The following external connections have been acknowledged from the clients:")
        print(tabulate(data, headers=headers))
        print()

    def begin_internal_routing(self, print_to_console: bool = True) -> None:
        for router in self.get_all_routers():
            print_log(f"Beginning route in {str(router)}...")
            router.reference_bw = self.reference_bw
            router.begin_internal_routing()

            router.send_script(print_to_console)

    def begin_bgp_routing(self, print_to_console: bool = True) -> None:
        provider_edges = [router for router in self.get_all_routers() if router.as_number == self.as_number
                          and router.is_provider_edge() and not router.route_reflector]

        if print_to_console:
            print_log(f"Beginning BGP routing in {self[self.route_reflector]}...")
        self.get_device(self.route_reflector).bgp_routing(
            initialization=True,
            ibgp_neighbor_ids=[router.id() for router in provider_edges],
            redistribution_to_egp=True
        )
        self.get_device(self.route_reflector).send_script(print_to_console)

        for router in provider_edges:
            if print_to_console:
                print_log(f"Beginning BGP routing in {router}...")
            router.bgp_routing(
                initialization=True,
                ibgp_neighbor_ids=[self.route_reflector],
                redistribution_to_egp=True
            )
            router.send_script(print_to_console)
