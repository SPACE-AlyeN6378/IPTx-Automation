from components.interfaces.interface import Interface
from components.interfaces.interface_list import InterfaceList, Loopback
from components.interfaces.connector import Connector
from components.interfaces.vlan import VLAN
from components.nodes.network_device import NetworkDevice
from components.nodes.switch import Switch, SwitchInterface, ECNProtocol


def connect_devices(device1: NetworkDevice, device1_port: str, device2: NetworkDevice, device2_port: str):
    device1.connect(device1_port, device2, device2_port)
    device2.connect(device2_port, device1, device1_port)


switch1 = Switch(
    node_id=1,
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
    node_id=1,
    hostname="MySwitch2",
    interfaces=[
        SwitchInterface("GigabitEthernet", "0/0"),
        SwitchInterface("GigabitEthernet", "0/1"),
        SwitchInterface("GigabitEthernet", "0/2"),
        SwitchInterface("GigabitEthernet", "0/3")
    ],
    vlan_ids={2, 3, 4, 5}
)


connect_devices(switch1, "0/0", switch2, "0/2")
connect_devices(switch1, "0/1", switch2, "0/3")

switch1.set_default_trunk("0/0", "0/1")
switch2.set_default_trunk("0/2", "0/3")

tr
switch1.create_etherchannel(["0/0", "0/2"], 1, protocol=ECNProtocol.PAGP, unconditional=False)
switch1.submit_script()
# add_vlans(switch1)
