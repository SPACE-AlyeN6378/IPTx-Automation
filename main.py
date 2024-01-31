from list_helper import next_number
from components.nodes.switch import Switch, SwitchInterface
from components.topologies.topology import Topology

# Create instances of the Person class
switch1 = Switch(
    hostname="MySwitch1",
    interfaces=[
        SwitchInterface("GigabitEthernet", "0/0"),
        SwitchInterface("GigabitEthernet", "0/1"),
        SwitchInterface("GigabitEthernet", "0/2"),
        SwitchInterface("GigabitEthernet", "0/3")
    ],
    vlan_ids={2, 3, 4, 5}
)

switch2 = Switch(
    hostname="MySwitch2",
    interfaces=[
        SwitchInterface("Ethernet", "0/0"),
        SwitchInterface("GigabitEthernet", "0/1"),
        SwitchInterface("GigabitEthernet", "0/2"),
        SwitchInterface("GigabitEthernet", "0/3")
    ],
    vlan_ids={2, 3, 4}
)

switch3 = Switch(
    hostname="MySwitch3",
    interfaces=[
        SwitchInterface("GigabitEthernet", "0/0"),
        SwitchInterface("GigabitEthernet", "0/1"),
        SwitchInterface("GigabitEthernet", "0/2"),
        SwitchInterface("GigabitEthernet", "0/3")
    ],
    vlan_ids={100, 200}
)

switch4 = Switch(
    hostname="MySwitch4",
    interfaces=[
        SwitchInterface("Ethernet", "0/0"),
        SwitchInterface("GigabitEthernet", "0/1"),
        SwitchInterface("GigabitEthernet", "0/2"),
        SwitchInterface("GigabitEthernet", "0/3")
    ],
    vlan_ids={5, 6, 7}
)

topology = Topology(3200, [switch1, switch2, switch3, switch4])
topology.connect_devices(1, "0/0", "MySwitch2", "0/0")
topology.connect_devices(2, "0/1", 3, "0/0")
topology.connect_devices(3, "0/1", 4, "0/0")
topology.connect_devices(4, "0/1", 1, "0/1")

topology[1].send_script()

