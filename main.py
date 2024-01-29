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
        SwitchInterface("GigabitEthernet", "0/3"),
        SwitchInterface("GigabitEthernet", "1/0"),
        SwitchInterface("GigabitEthernet", "1/1"),
    ],
    vlan_ids={2, 3, 4, 5}
)


connect_devices(switch1, "0/0", switch2, "0/2")
connect_devices(switch1, "0/1", switch2, "0/3")
connect_devices(switch1, "0/2", switch2, "1/0")
connect_devices(switch1, "0/3", switch2, "1/1")

# switch1.assign_vlans(2, ports="0/0")
# switch1.assign_vlans(2, ports="0/1")

switch1.send_script(print_to_console=False)
switch1.etherchannel(["0/0", "0/1"], 1, ECNProtocol.LACP, True)
switch1.send_script()

switch1.etherchannel(switch1.port_channels[1], 3, ECNProtocol.PAGP, False)

print('\n')
switch1.send_script()
print(switch1.port_channels)

switch1.etherchannel(["0/2", "0/3"], 3, ECNProtocol.PAGP, False)

print('\n')
switch1.send_script()

print(switch1.port_channels)


