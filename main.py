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

switch1 = Switch(
    node_id=1,
    hostname="SW1",
    interfaces=InterfaceList(
        SwitchInterface("GigabitEthernet", "0/0"),
        SwitchInterface("GigabitEthernet", "0/1"),
        SwitchInterface("GigabitEthernet", "0/2"),
        SwitchInterface("GigabitEthernet", "0/3"),
    )
)

add_vlans(switch1)
switch1.default_trunk(*Interface.range_(0, range(4)))

switch2 = Switch(
    node_id=1,
    hostname="SW2",
    interfaces=InterfaceList(
        SwitchInterface("GigabitEthernet", "0/0"),
        SwitchInterface("GigabitEthernet", "0/1"),
        SwitchInterface("GigabitEthernet", "0/2"),
        SwitchInterface("GigabitEthernet", "0/3"),
    )
)

add_vlans(switch2)
switch2.default_trunk(*Interface.range_(0, range(4)))

switch3 = Switch(
    node_id=1,
    hostname="SW3",
    interfaces=InterfaceList(
        SwitchInterface("GigabitEthernet", "0/0"),
        SwitchInterface("GigabitEthernet", "0/1"),
        SwitchInterface("GigabitEthernet", "0/2"),
        SwitchInterface("GigabitEthernet", "0/3"),
    )
)

add_vlans(switch3)
switch3.default_trunk(*Interface.range_(0, range(4)))


prompt = ""
while prompt != "exit":
    prompt = input(">>>")
    if prompt.lower() == switch1.hostname.lower():
        switch1.send_command()
    elif prompt.lower() == switch2.hostname.lower():
        switch2.send_command()
    elif prompt.lower() == switch3.hostname.lower():
        switch3.send_command()


