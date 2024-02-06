from components.interfaces.loopback.loopback import Loopback
from components.devices.network_device import NetworkDevice
from components.interfaces.physical_interfaces.physical_interface import PhysicalInterface

# Create instances of the Person class
device = NetworkDevice(1, "Device", [PhysicalInterface("FastEthernet", "0/0", "192.168.1.1/24")])

device.interface("0/0") \
      .shutdown()

loopback = Loopback("1.1.1.1/24")
loopback.set_ospf_p2p(False)

for command in loopback.generate_command_block():
    print(command)


