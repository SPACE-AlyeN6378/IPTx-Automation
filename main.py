from components.interfaces.loopback import Loopback
from list_helper import next_number
from components.nodes.switch import Switch, SwitchInterface
from components.nodes.network_device import NetworkDevice
from components.topologies.topology import Topology
from components.interfaces.physical_interface import PhysicalInterface

# Create instances of the Person class
# device = NetworkDevice()
loopback = Loopback("1.1.1.1/24")
loopback.set_ospf_p2p(False)

for command in loopback.generate_command_block():
    print(command)


