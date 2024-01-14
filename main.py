from components.interfaces.interface import Interface
from components.interfaces.interface_list import InterfaceList, Loopback
from components.interfaces.connector import Connector
from components.interfaces.vlan import VLAN
from components.nodes.node import Node
from components.nodes.switch import Switch, SwitchInterface


vlan_ids = [10, 20, 30]


def add_vlans(*switches):
    global vlan_ids
    for switch in switches:
        for vlan in vlan_ids:
            switch.add_vlan(vlan)

# switch1 = Switch(
#     node_id=1,
#     hostname="SW1",
#     interfaces=[
#         SwitchInterface("GigabitEthernet", "0/0", "192.168.1.1/24"),
#         SwitchInterface("GigabitEthernet", "0/1", "192.168.2.2/24")
#     ]
# )

# interfaces = InterfaceList(
#     SwitchInterface("GigabitEthernet", "0/0", "192.168.1.1/24"),
#     SwitchInterface("GigabitEthernet", "0/1", "192.168.2.2/24")
# )

node = Node(
    node_id=1,
    hostname="Node1",
    interfaces=[
        SwitchInterface("GigabitEthernet", "0/0", "192.168.1.1/24"),
        Loopback("172.168.3.2/32")
    ]    
)

# add_vlans(switch1)
node.send_command()



