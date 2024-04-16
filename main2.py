from components.interfaces.physical_interfaces.router_interface import RouterInterface
from components.devices.device_creator import cisco_xr_9000
from components.devices.network_device import NetworkDevice
from colorama import Fore

my_router = cisco_xr_9000("10.255.255.6", "Dhaka-R1")

my_router.l2vpn_xc_config("DHAKA-GROUP", "DHAKA-P2P")

my_router.interface("0/0/0/0").pseudowire_config(330, "10.255.255.3")
my_router.interface("0/0/0/0").pseudowire_config(1034, "10.255.255.4")

my_router.l2vpn_xc_config("DHAKA-GROUP", "DHAKA-P2P")

NetworkDevice.print_script(my_router.generate_script(), Fore.MAGENTA)

