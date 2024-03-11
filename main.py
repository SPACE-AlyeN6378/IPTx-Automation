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
                            network_address="10.0.12.0", scr=8)
my_topology.connect_devices("10.255.255.2", "0/0/0/1", "10.255.255.3", "0/0/0/0",
                            network_address="10.0.23.0", cable_bandwidth=10000)
my_topology.connect_devices("10.255.255.3", "0/0/0/1", "10.255.255.4", "0/0/0/0",
                            network_address="10.0.43.0", cable_bandwidth=1000)
my_topology.connect_devices("10.255.255.4", "0/0/0/1", "10.255.255.1", "0/0/0/1",
                            network_address="10.0.41.0", cable_bandwidth=1000)

my_topology.print_links()  # Show the connections

my_topology.add_vrf("INDIGO", "10.255.255.1", "0/0/0/2")
my_topology.add_vrf("CORAL")
my_topology.add_vrf("TEAL")
my_topology.add_vrf("LAVENDER")
my_topology.add_vrf("RUBY")
# my_topology.add_vrf("EMERALD")
# my_topology.add_vrf("SAPPHIRE")
# my_topology.add_vrf("AMBER")
# my_topology.add_vrf("CYAN")
# my_topology.add_vrf("MAROON")
# my_topology.add_vrf("TURQUOISE")
# my_topology.add_vrf("CRIMSON")
# my_topology.add_vrf("PLUM")
# my_topology.add_vrf("GOLD")
# my_topology.add_vrf("SILVER")
# my_topology.add_vrf("OLIVE")

my_topology.vrf_hub_and_spoke("TEAL")

my_topology.set_interface_in_vrf("CORAL", "10.255.255.1", "0/0/0/2")

my_topology["10.255.255.1"].send_script(print_to_console=False)
my_topology["10.255.255.1"].add_vrf(34, "ROBI")
my_topology["10.255.255.1"].send_script()

