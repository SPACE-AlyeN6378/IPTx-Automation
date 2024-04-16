from components.devices.device_creator import cisco_7200, cisco_xr_9000
from components.topologies.autonomous_system.l2vpnbackbone import L2VPNBackbone
from components.devices.network_device import NetworkDevice

backbone = L2VPNBackbone(9560,
                         "Fiber@Home",
                         [
                             cisco_7200("1.1.1.1", "R1"),
                             cisco_xr_9000("2.2.2.2", "R2"),
                             cisco_xr_9000("3.3.3.3", "R3"),
                             cisco_7200("4.4.4.4", "R4")
                         ])

backbone.connect_internal_devices("1.1.1.1", "0/0", "2.2.2.2", "0/0/0/0",
                                  "10.1.1.0")
backbone.connect_internal_devices("2.2.2.2", "0/0/0/1", "3.3.3.3", "0/0/0/0",
                                  "10.1.2.0")
backbone.connect_internal_devices("3.3.3.3", "0/0/0/1", "4.4.4.4", "0/0",
                                  "10.1.3.0")
backbone.connect_internal_devices("4.4.4.4", "0/1", "1.1.1.1", "0/1",
                                  "10.1.4.0")

for router in backbone.get_all_routers():
    router.begin_internal_routing(mpls_ldp_sync=True)

backbone.connect_client(
    client_device=cisco_7200("10.255.255.2", "Client1", 100),
    client_port="0/0",
    bkb_router_id="2.2.2.2",
    bkb_router_port="0/0/0/2",
)

backbone.connect_client(
    client_device=cisco_7200("10.255.255.3", "Client2", 200),
    client_port="0/0",
    bkb_router_id="3.3.3.3",
    bkb_router_port="0/0/0/2",
)

backbone.connect_client(
    client_device=cisco_7200("10.255.255.4", "Client3", 300),
    client_port="0/0",
    bkb_router_id="4.4.4.4",
    bkb_router_port="1/0",
)

backbone.print_backbone_links()
backbone.print_client_links()

backbone.establish_pseudowire("10.255.255.2", "10.255.255.3", 355,
                              "Robi", "Robi-XC", "Robi-P2P")
backbone.establish_pseudowire("10.255.255.2", "10.255.255.4", 356)


NetworkDevice.print_script(backbone["2.2.2.2"].generate_script())
