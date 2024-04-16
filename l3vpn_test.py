from components.topologies.autonomous_system.l3vpnbackbone import L3VPNBackbone
from components.devices.device_creator import gns3_c7200, gns3_ce_router

test_ring = L3VPNBackbone(
    as_number=45700,
    name="Testing Ring",
    devices=[
        gns3_c7200("10.255.255.1", "RingR1"),
        gns3_c7200("10.255.255.2", "RingR2"),
        gns3_c7200("10.255.255.3", "RingR3"),
        gns3_c7200("10.255.255.4", "RingR4"),
        gns3_c7200("10.255.255.5", "RingR5")
    ],
    route_reflector_id="10.255.255.2"
)

# Backbone Connection
device_ids = [device.id() for device in test_ring.get_all_devices()]

for i, device_id in enumerate(device_ids):
    print(i, device_ids[i-1], device_id)
    test_ring.connect_internal_devices(
        device_id1=device_ids[i-1], port1="0/0",
        device_id2=device_id, port2="0/1",
        network_address=f"12.176.{i}.0"
    )

test_ring.begin_internal_routing()
test_ring.explore_configs()

# Connecting a couple of clients
clients = {
    ("10.255.255.1", "192.168.11.0"): gns3_ce_router("1.1.1.1", "BDCOM-Edge1", 200),
    ("10.255.255.3", "192.168.12.0"): gns3_ce_router("2.2.2.2", "BDCOM-Edge2", 200),
    ("10.255.255.4", "192.168.13.0"): gns3_ce_router("3.3.3.3", "BDCOM-Edge3", 200)
}


for ip_address_tuple, client in clients.items():
    rtr_id, network_address = ip_address_tuple

    test_ring.connect_client(
        client_device=client,
        client_port="0/0",
        bkb_router_id=rtr_id,
        bkb_router_port="2/0",
        network_address=network_address,
        new_vrf="BDCOM",
        static_routing=False
    )

test_ring.print_client_links()

# Establishing routes
test_ring.vpn_route_target("BDCOM-1", "BDCOM-2", two_way=True)
test_ring.vpn_route_target("BDCOM-1", "BDCOM-3", two_way=True)
test_ring.print_vrfs()
test_ring.explore_configs()

# BGP connection
test_ring.begin_bgp_routing()
test_ring.clear_vrf_setup_commands()
test_ring.explore_configs()
