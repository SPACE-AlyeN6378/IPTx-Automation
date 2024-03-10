from components.topologies.topology import Topology, Switch, Router, plt
import networkx as nx
from components.interfaces.physical_interfaces.router_interface import RouterInterface
from typing import Iterable, List, Dict, Any

from iptx_utils import NetworkError, NotFoundError, print_log, print_table, print_warning, print_success
from itertools import permutations


class AutonomousSystem(Topology):
    def __init__(self, as_number: int, name: str, devices: Iterable[Switch | Router] = None,
                 route_reflector_id: str = None,
                 mpls: bool = True):

        print(f"\n==================== AUTONOMOUS SYSTEM {as_number}: '{name}' ====================\n")
        super().__init__(as_number, devices)

        self.name: str = name
        self.mpls: bool = mpls
        self.reference_bw: int = 1  # Reference bandwidth in M bits/s

        if route_reflector_id:
            self.route_reflector: str = route_reflector_id
            self.select_route_reflector(route_reflector_id)
        else:
            self.route_reflector: str | None = None

        # VPN Configuration
        self.__vpn_graph = nx.MultiDiGraph()
        self.__vrf_index = 0

    def print_links(self) -> None:
        links = sorted(self._graph.edges(data=True), key=lambda link: link[2]["scr"])
        table = [[
            str(edge[2]['scr']),
            f"{edge[0]} ({edge[2]['d1_port']}) ---> {edge[1]} ({edge[2]['d2_port']})",
            edge[2]['network_address'],
            f"{edge[2]['bandwidth']} KB/s",
            str(edge[2]['egp'])
        ] for edge in links]

        table.insert(0, ["SCR", "Source/Destination", "Network IP", "Bandwidth", "External?"])

        print()
        print_log("The following connections have been established:")
        print_table(table)
        print()

    def __update_reference_bw(self, new_bandwidth: int) -> None:  # new_bandwidth in k bits/s
        if (new_bandwidth // 1000) > self.reference_bw:
            self.reference_bw = new_bandwidth // 1000

    def select_route_reflector(self, router_id: str) -> None:
        # Route-reflection is of no use with a single router
        if len([router.id() for router in self.get_all_routers()]) <= 2:
            print_warning("This autonomous system only has one or two routers. So there's no use of route-reflecting")

        # The route-reflector attribute is set to True for the router with a matching router ID
        self.route_reflector = router_id
        self.get_device(router_id).route_reflector = True

        # Iterate through each spoke in the topology
        for router in self.get_all_routers():
            # router_id --> ID of route-reflector router
            # router.id() --> ID of other routers
            if router_id != router.id():
                router.ibgp_adjacent_router_ids.append(router_id)
                self.get_device(router_id).ibgp_adjacent_router_ids.append(router.id())

        print_success(f"{self.get_device(router_id)} with ID {router_id} chosen as Route-reflector client")
        self.get_device(router_id).set_hostname(self.get_device(router_id).hostname + "-RR")

    def assign_network_ip_address(self, network_address: str,
                                  device_id1: str = None,
                                  device_id2: str = None,
                                  scr: int = None) -> None:

        network_addresses = [edge[2]["network_address"] for edge in self._graph.edges(data=True)
                             if "network_address" in edge[2]]

        if network_address in network_addresses:
            raise NetworkError(f"Network address '{network_address}' is already used in another network.")

        if device_id1 and device_id2:
            edge = self.get_link(device_id1, device_id2)
        elif scr:
            edge = self.get_link_by_key(scr)
        else:
            raise TypeError("Please provide either both device_id1 and device_id2, or just the SCR/key")

        edge[2]["network_address"] = network_address

        port1 = edge[2]["d1_port"]
        port2 = edge[2]["d2_port"]

        if isinstance(self[device_id1], Router) and isinstance(self[device_id2], Router):
            ip1, ip2 = RouterInterface.p2p_ip_addresses(network_address)
            self[device_id1].interface(port1).config(cidr=ip1)
            self[device_id2].interface(port2).config(cidr=ip2)

    def connect_devices(self, device_id1: str | int, port1: str, device_id2: str | int, port2: str,
                        scr: int = None, network_address: str = None, cable_bandwidth: int = None) -> None:

        self.print_log(f"Connecting devices {self[device_id1]} to {self[device_id2]}...")
        super().connect_devices(device_id1, port1, device_id2, port2, scr, cable_bandwidth)

        # Update the reference bandwidth
        new_ref_bandwidth: int = self.get_link(device_id1, device_id2)[2]["bandwidth"]
        self.__update_reference_bw(new_ref_bandwidth)

        # Links are identified using SCRs (Service Connection Request) in F@H instead of keys, so 'key'
        # is replaced with 'scr'
        self.get_link(device_id1, device_id2)[2]["scr"] = self.get_link(device_id1, device_id2)[2].pop("key")

        # Network address is given, so put it in
        if network_address:
            self.assign_network_ip_address(network_address, device_id1, device_id2)
        else:
            self.get_link(device_id1, device_id2)[2]["network_address"] = None

        # Enable MPLS to all the routers
        self[device_id1].interface(port1).mpls_enable()
        self[device_id2].interface(port2).mpls_enable()

        # This is an intra-autonomous connection, so EGP is always False
        self.get_link(device_id1, device_id2)[2]["egp"] = False

    def get_all_vrfs(self, name_only: bool = False) -> List[tuple[int, Dict[str, Any]] | str]:
        if name_only:
            return [data["name"] for rd, data in self.__vpn_graph.nodes(data=True)]

        return self.__vpn_graph.nodes(data=True)

    def get_vrf(self, rd_or_name: str | int) -> tuple[int, Dict[str, Any]]:
        if isinstance(rd_or_name, str):
            for rd_, data in self.__vpn_graph.nodes(data=True):
                if rd_or_name == data["name"]:
                    return rd_, data

            raise NotFoundError(f"VRF with name '{rd_or_name}' cannot be found")

        else:
            try:
                return rd_or_name, self.__vpn_graph.nodes[rd_or_name]
            except KeyError:
                raise NotFoundError(f"VRF with RD '{rd_or_name}' cannot be found")

    def add_vrf(self, vrf_name: str, device_id: str = None, port: str = None) -> None:
        # Check for any existing names
        if vrf_name in self.get_all_vrfs(name_only=True):
            raise NetworkError(f"VRF with name '{vrf_name}' already exists")

        rd = len(self.get_all_vrfs(name_only=True)) + 1  # rd = route-distinguisher
        self.__vpn_graph.add_node(rd, name=vrf_name, device=None, interface=None)

        self.set_interface_in_vrf(rd, device_id, port)

    def remove_vrf(self, rd_or_name: str | int) -> None:
        if isinstance(rd_or_name, str):
            rd_or_name = self.get_vrf(rd_or_name)[0]

        self.__vpn_graph.remove_node(rd_or_name)

    def set_interface_in_vrf(self, rd_or_name: int | str, device_id: str = None, port: str = None) -> None:

        if device_id and port:
            device = self.get_device(device_id)
            interface = device.interface(port)

            # If VRF name is used, get the corresponding VRFs
            if isinstance(rd_or_name, str):
                rd_or_name = self.get_vrf(rd_or_name)[0]

            # If the VRF is already assigned in another router interface
            for vrf in self.__vpn_graph.nodes(data=True):
                if interface == vrf[1]["interface"] and device == vrf[1]["device"]:
                    vrf[1]["device"] = None
                    vrf[1]["interface"] = None

            self.__vpn_graph.nodes[rd_or_name]['device'] = device
            self.__vpn_graph.nodes[rd_or_name]['interface'] = interface

    def print_vrfs(self) -> None:
        vrfs = sorted(self.__vpn_graph.nodes(data=True))
        table = [
            [
                str(vrf[0]),
                str(vrf[1]['name']),
                str(vrf[1]['device']),
                str(vrf[1]['interface']),
                str([edge[1] for edge in self.__vpn_graph.out_edges(vrf[0])])
            ]
            for vrf in vrfs
        ]

        table.insert(0, ["RD", "VRF Name", "Device", "Interface", "Exported to"])

        print()
        print_log("The following VRFs are created:")
        print_table(table)
        print()

    def vpn_connection(self, source: int | str, destination: int | str, two_way=False) -> None:

        # If a name is passed for the VRF source, take the corresponding RD
        if isinstance(source, str):
            source = self.get_vrf(source)[0]

        # If a name is passed for the VRF destination, take the corresponding RD
        if isinstance(destination, str):
            destination = self.get_vrf(destination)[0]

        # Prevent duplicate edges
        if self.__vpn_graph.has_edge(source, destination):
            raise ValueError(f"Connection from {self.__vpn_graph.nodes[source]['name']} to "
                             f"{self.__vpn_graph.nodes[destination]['name']} already exists.")

        self.__vpn_graph.add_edge(source, destination)

        if two_way:
            # Prevent duplicate edges for the other way around
            if self.__vpn_graph.has_edge(destination, source):
                raise ValueError(f"Connection from {self.__vpn_graph.nodes[destination]['name']} to "
                                 f"{self.__vpn_graph.nodes[source]['name']} already exists.")

            self.__vpn_graph.add_edge(destination, source)

            print_log(f"VRF Route-target: {self.__vpn_graph.nodes[source]['name']} <---> "
                      f"{self.__vpn_graph.nodes[destination]['name']}", 0)

        else:
            print_log(f"VRF Route-target: {self.__vpn_graph.nodes[source]['name']} ---> "
                      f"{self.__vpn_graph.nodes[destination]['name']}", 0)

    def vrf_hub_and_spoke(self, hub: int | str, allow_print_log=True) -> None:
        if isinstance(hub, str):
            hub = self.get_vrf(hub)[0]

        if allow_print_log:
            print_log(f"VRF Hub and spoke confirmed, with {self.__vpn_graph.nodes[hub]['name']} as the hub")

        for rd in self.__vpn_graph.nodes():
            if rd != hub:
                self.vpn_connection(hub, rd, two_way=True)

    def vrf_full_mesh(self) -> None:

        print_log(f"VRF Full mesh confirmed")
        edges = list(permutations(self.__vpn_graph.nodes(), 2))
        for src, dest in edges:
            self.vpn_connection(src, dest)

    def show_vpn_graph(self) -> None:
        pos = nx.spring_layout(self.__vpn_graph)  # Positions for all nodes
        nx.draw(self.__vpn_graph, pos, with_labels=True, arrows=True, width=2, node_size=1000,
                labels={node_id: data["name"] for node_id, data in self.__vpn_graph.nodes(data=True)})
        plt.show()

    def begin_internal_routing(self) -> None:
        for router in self.get_all_routers():
            print_log(f"Beginning route in {str(router)}...")
            router.reference_bw = self.reference_bw
            router.begin_igp_routing()
            router.send_script()
