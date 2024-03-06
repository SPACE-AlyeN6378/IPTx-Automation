from components.topologies.autonomous_system.autonomous_system import AutonomousSystem, RouterInterface, Router

# Step 1 - Create an Autonomous System
my_topology = AutonomousSystem(as_number=58587, name="Test Topology", devices=[

    Router(
        router_id="10.255.255.1",
        hostname="P1",
        interfaces=[
            RouterInterface("FastEthernet", "0/0/0/0"),
            RouterInterface("GigabitEthernet", "0/0/0/1"),
            RouterInterface("GigabitEthernet", "0/0/0/2")
        ],
        ios_xr=True
    ),

    Router(
        router_id="10.255.255.2",
        hostname="P2",
        interfaces=[
            RouterInterface("GigabitEthernet", "0/0/0/0"),
            RouterInterface("GigabitEthernet", "0/0/0/1"),
            RouterInterface("GigabitEthernet", "0/0/0/2")
        ],
        ios_xr=True
    ),

    Router(
        router_id="10.255.255.3",
        hostname="P3",
        interfaces=[
            RouterInterface("GigabitEthernet", "0/0/0/0"),
            RouterInterface("GigabitEthernet", "0/0/0/1"),
            RouterInterface("GigabitEthernet", "0/0/0/2")
        ],
        ios_xr=True
    ),

    Router(
        router_id="10.255.255.4",
        hostname="P4",
        interfaces=[
            RouterInterface("GigabitEthernet", "0/0/0/0"),
            RouterInterface("GigabitEthernet", "0/0/0/1"),
            RouterInterface("GigabitEthernet", "0/0/0/2")
        ],
        ios_xr=True
    )
],
                               route_reflector_id="10.255.255.1",
                               )

# Step 2 - Connect all the devices
my_topology.connect_devices("10.255.255.1", "0/0/0/0", "10.255.255.2", "0/0/0/0",
                            network_address="10.0.12.0")
my_topology.connect_devices("10.255.255.2", "0/0/0/1", "10.255.255.3", "0/0/0/0",
                            network_address="10.0.23.0", cable_bandwidth=10000)
my_topology.connect_devices("10.255.255.3", "0/0/0/1", "10.255.255.4", "0/0/0/0",
                            network_address="10.0.43.0", cable_bandwidth=1000)
my_topology.connect_devices("10.255.255.4", "0/0/0/1", "10.255.255.1", "0/0/0/1",
                            network_address="10.0.41.0", cable_bandwidth=1000)
my_topology.connect_devices("10.255.255.4", "0/0/0/2", "10.255.255.2", "0/0/0/2",
                            network_address="10.0.5.0", scr=1220, cable_bandwidth=50000)

my_topology.print_links()  # Show the connections

my_topology.add_vrf("RED")
my_topology.add_vrf("GREEN")
my_topology.add_vrf("BLUE")
my_topology.vpn_connection()

print(my_topology.get_vrf(rd=2))


# my_topology["10.255.255.2"].add_vrf(10, "RED", 20)
# my_topology["10.255.255.2"].interface("0/0/0/0").vrf_name = "ALLAHU-AKBAR"
# # my_topology["10.255.255.2"].begin_igp_routing()
# # my_topology["10.255.255.2"].begin_ibgp_routing()
# my_topology["10.255.255.2"].send_script()
