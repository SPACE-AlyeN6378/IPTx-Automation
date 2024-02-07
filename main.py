from components.devices.network_device import NetworkDevice
from components.interfaces.physical_interfaces.physical_interface import PhysicalInterface

my_interface = PhysicalInterface("GigabitEthernet", "0/0")
device = NetworkDevice(2, "Router", interfaces=[
    PhysicalInterface("FastEthernet", "2/0")
])

print(str(my_interface.bandwidth))
my_interface.connect_to(device, "2/0")
print(str(my_interface.bandwidth))



