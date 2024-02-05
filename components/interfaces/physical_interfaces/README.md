# Physical Interface

The "Physical Interface" class, an extension of the base [`Interface`](..) class, serves as a comprehensive representation of network interfaces within the realm of network automation. This class introduces additional attributes crucial for managing and optimizing network connections, including features like bandwidth regulation, Maximum Transmission Unit (MTU) configuration, shutdown control, and facilitation of connections to remote devices. With a focus on enhancing the capabilities for automated network management, the "Physical Interface" class provides a versatile and robust foundation for developers working on network automation solutions, enabling seamless integration and efficient handling of diverse physical interface functionalities.

### New Attributes
- `BANDWIDTHS: dict[str, int]` - Static dictionary containing a key-value pairs of acceptable interface types for a physical interface. They consist of the following:
    - ATM: 622000 bps
    - Ethernet: 10000 bps
    - FastEthernet: 100000 bps
    - GigabitEthernet: 1000000 bps
    - TenGigabitEthernet: 10000000 bps 
    - Serial: 1544 bps
    - wlan-gigabitethernet: 1000000 bps
- `shutdown_state: bool`: Shows whether the interface is shutdown or not
- `max_bandwidth: int`: Maximum permittable bandwidth (used for configuration)
- `bandwidth: int`:  Bandwidth of this interface
- `mtu: int`: Maximum Transmission Unit, largest amount of data that can be transmitted in a single packet on a network
- `duplex: int`:  Ability of two different points or devices to engage in two-way communication. The acceptable modes are:
    * **full** - For simultaneous transmission and receipt
    * **half** - For signals travelling in one direction, not simultaneously in both direction
    * **auto** (default) - Lets the router/switch negotiate between **full** and **half**
- `remote_device: Switch | Router`: The device the interface is connected to on the other side
- `remote_port: str`: The port of the remote device where the interface is connected to

### Overridden Functions
#### Configuration `config(self, cidr: str, bandwidth: int, mtu: int, duplex: str) -> None`
This changes one of the attributes of this interface in the given parameters. But for this class structure, the new attributes like bandwidth, MTU, and Duplex can be altered.

Example:
```python
my_interface = PhysicalInterface("GigabitEthernet", "0/0", "192.168.12.2/24")

# Changing the bandwidth and MTU from the previous interface
my_interface.config(bandwidth=10000, mtu=2000)
print(my_interface.bandwidth, my_interface.mtu)
# Output: 10000 2000
```

### New Public Functions
Name|Parameters|Description|Returns
----|----------|-----------|-------
`shutdown()`|-|Shuts down the interface|None
`release()`|-|Releases the interface, only when it is connected to a remote device|None
`connect_to()`|`device: NetworkDevice`, `remote_port: int`|Established a connection. It basically sets the remote device and its respective port to the ones given in the parameter|None
`disconnect()`|-|Disconnects the interface by just nullifying the remote device and the port|None

### Example
Let's just say, an interface GigabitEthernet0/0 with IP Address 192.168.12.2/24 has been introduced to the environment. The following tasks have been done:
- The bandwidth is changed to 10000 bps, and the MTU is changed to 2000
- This interface is connected to [NetworkDevice](../../nodes) "SOME_DEVICE" at port 1/2
- Generated the Cisco command

```python
my_interface = PhysicalInterface("GigabitEthernet", "0/0", "192.168.12.2/24")
SOME_DEVICE = NetworkDevice(...)

# Changing the bandwidth and MTU from the previous interface
my_interface.config(bandwidth=10000, mtu=2000)
print(my_interface.bandwidth, my_interface.mtu)
# Output: 10000 2000

my_interface.connect_to(SOME_DEVICE, "1/2")
for command in my_interface.generate_command_block(self):
    print(command)

'''
Expected Output: 
interface FastEthernet0/0
no shutdown
ip address 192.168.12.2 255.255.255.0
bandwidth 10000
mtu 2000
duplex auto
exit
'''
```

This `PhysicalInterface` will be used for debugging purposes, and will not be used for deployment. Because in both routers and switches, they both use a special interface derived from the `PhysicalInterface` class, and one of them serves different purposes:
- `SwitchInterface` handles VLANs and QinQ tunnelling
- `RouterInterface` manages routing protocols like OSPF, BGP, etc.

Both these interfaces are discussed below.

## Physical Interface for Router
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam ac justo et odio varius finibus. Integer vel tortor nec nulla feugiat tristique. Vivamus auctor diam id justo ullamcorper, id hendrerit eros convallis. Suspendisse potenti. Duis interdum justo ac nisl ullamcorper, vel rhoncus mauris posuere. Fusce sit amet dapibus turpis. In hac habitasse platea dictumst. Curabitur commodo bibendum risus, vitae tincidunt justo luctus non. Nunc volutpat, justo eget fringilla fermentum, augue justo cursus lectus, ut fermentum leo mauris vel ligula. Suspendisse potenti. Proin non turpis vel velit scelerisque bibendum.
