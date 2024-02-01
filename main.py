from components.interfaces.loopback import Loopback
from list_helper import next_number
from components.nodes.switch import Switch, SwitchInterface
from components.topologies.topology import Topology

# Create instances of the Person class
loopback = Loopback("1.1.1.1/24")

for command in loopback.generate_command_block():
    print(command)

