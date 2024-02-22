from components.interfaces.interface import Interface
from components.topologies.autonomous_system.autonomous_system import AutonomousSystem, RouterInterface, Router
my_topology = AutonomousSystem(as_number=58587, name="My AS", devices=[

    Router(
        router_id="10.255.255.1",
        hostname="P1",
        interfaces=[
            RouterInterface("FastEthernet", "0/0/0/0"),
            RouterInterface("GigabitEthernet", "0/0/0/1"),
            RouterInterface("GigabitEthernet", "0/0/0/2")
        ],
        ios_xr=False
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
])

my_topology.connect_devices("10.255.255.1", "0/0/0/0", "10.255.255.2", "0/0/0/0",
                            network_address="10.0.12.0", cable_bandwidth=100000)
my_topology.connect_devices("10.255.255.2", "0/0/0/1", "10.255.255.3", "0/0/0/0",
                            network_address="10.0.23.0", cable_bandwidth=10000)
my_topology.connect_devices("10.255.255.3", "0/0/0/1", "10.255.255.4", "0/0/0/0",
                            network_address="10.0.43.0", cable_bandwidth=1000)
my_topology.connect_devices("10.255.255.4", "0/0/0/1", "10.255.255.1", "0/0/0/1",
                            network_address="10.0.41.0", cable_bandwidth=1000)
my_topology.connect_devices("10.255.255.4", "0/0/0/2", "10.255.255.2", "0/0/0/2",
                            scr=1220, cable_bandwidth=50000)

my_topology.update_ref_bw_rtrs()

my_topology.get_device("10.255.255.3").initialize_route()
my_topology.get_device("10.255.255.3").send_script()
