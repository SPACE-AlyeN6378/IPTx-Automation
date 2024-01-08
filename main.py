from components.interfaces.interface import Interface
from components.interfaces.interface_list import InterfaceList, Loopback
from components.interfaces.connector import Connector
from components.nodes.switch_int import SwitchInterface
from components.interfaces.vlan import VLAN
from components.nodes.node import Node

# exec(open("main.py").read())

def print_cmd(cmd_list):
    for cmd in cmd_list:
        print(cmd)
    print()


# interfaces1 = InterfaceList(
#     Loopback("192.168.1.1"),
#     Loopback("192.168.1.2"),
#     Loopback("192.168.1.3"),
#     Loopback("192.168.1.4"),
#     Loopback("192.168.1.5"),
#     Connector("FastEthernet", "0/0", "10.1.1.2/24"),
#     Connector("FastEthernet", "0/1", "10.1.2.2/24"),
#     Connector("FastEthernet", "0/2", "10.1.3.2/24"),
# )
#
interfaces2 = InterfaceList(
    Connector("FastEthernet", "0/1"),
    Connector("FastEthernet", "0/2", "10.1.3.2/24"),
    Connector("FastEthernet", "0/3", "10.1.4.4/24"),
    Connector("FastEthernet", "0/4", "10.1.5.4/24"),
    SwitchInterface("GigabitEthernet", "1/0", "10.1.6.1/24")
)


node = Node(node_id=123, interfaces=interfaces2)
print(node.interfaces)

int_list = node.get_ints("0/2", "0/3", "0/4")
int_list[0].int_type = "Serial"

print([str(inf) for inf in int_list])
print(node.interfaces)

# vlan = VLAN(vlan_id=3, name="IP Department")
#
#
# for cmd in vlan.config():
#     print(cmd)
