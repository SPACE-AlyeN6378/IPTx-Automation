from components.interfaces.interface_list import InterfaceList, Loopback
from components.interfaces.connector import Connector
from components.interfaces.vlan import VLAN
# from components.nodes.node import Node

# exec(open("main.py").read())

def print_cmd(cmd_list):
    for cmd in cmd_list:
        print(cmd)
    print()

interfaces1 = InterfaceList(
    Loopback("192.168.1.1"),
    Loopback("192.168.1.2"),
    Loopback("192.168.1.3"),
    Connector("FastEthernet", "0/0", "10.1.1.2/24"),
    Connector("FastEthernet", "0/1", "10.1.2.2/24"),
    Connector("FastEthernet", "0/2", "10.1.3.2/24"),
)

interfaces2 = InterfaceList(
    Connector("FastEthernet", "0/1"),
    Connector("FastEthernet", "0/2", "10.1.3.2/24"),
    Connector("FastEthernet", "0/3", "10.1.4.4/24"),
    Connector("FastEthernet", "0/4", "10.1.5.4/24"),
)

vlan = VLAN(vlan_id=3, name="IP Department")


for cmd in vlan.config():
    print(cmd)

