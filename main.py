from components.devices.router.router import Router, RouterInterface



# my_interface.xr_mode = True

my_router = Router(
    router_id="1.1.1.1",
    hostname="ProviderEdge",
    interfaces=[
        RouterInterface("GigabitEthernet", "0/0/1", "102.21.4.4/30"),
        RouterInterface("GigabitEthernet", "0/0/2", "102.21.5.1/30")
    ]
)

my_router.interface("0/0/1").ospf_config(Router.OSPF_PROCESS_ID)
my_router.interface("0/0/2").ospf_area = 1
my_router.interface("0/0/2").ospf_config(Router.OSPF_PROCESS_ID)

my_router.send_script()
