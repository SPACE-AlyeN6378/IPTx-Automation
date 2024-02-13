from components.devices.router.router import Router, RouterInterface
from iptx_utils import print_log

print_log("Hello! Starting project...")

my_router = Router(
    router_id="10.255.255.1",
    hostname="ProviderEdge",
    interfaces=[
        RouterInterface("GigabitEthernet", "0/0/1", "102.21.4.4/30"),
        RouterInterface("Ethernet", "0/0/2", "102.21.5.1/30", egp=True),
        RouterInterface("Serial", "0/0/3", "102.21.6.1/30")
    ],
    ios_xr=False
)

my_router.set_ospf_area(2, "0/0/3")

my_router.initialize_route()

my_router.send_script()
