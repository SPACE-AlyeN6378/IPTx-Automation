from components.interfaces.physical_interfaces.router_interface import RouterInterface
from components.devices.network_device import NetworkDevice
from colorama import Fore


my_interface = RouterInterface("FastEthernet", "0/0/2", "192.168.12.1/24")
my_interface.config(mtu=9178)

my_interface.add_sub_if(2024)
my_interface.add_sub_if(3192)
my_interface.add_sub_if(1024)
my_interface.add_sub_if(335)

my_interface.get_sub_if(2024).generate_pseudowire_config("10.255.255.3")

NetworkDevice.print_script(my_interface.generate_config(), color=Fore.CYAN)
