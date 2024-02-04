# Network Interface

A Network Interface, in the realm of computer networks, acts as the 
point of interaction between a device and another device or the network it's connected to.
It serves as the gateway for data to flow in and out of the device, managing 
the communication protocols and handling the transmission and reception of 
data packets. Essentially, a Network Interface enables devices to connect, 
communicate, and participate in a network, playing a fundamental role in 
facilitating the exchange of information and ensuring effective network operations.

### Public Attributes
* `int_type: str` - Type of this interface (must be one of the type in `DEFAULT_TYPES`)
* `port: str` - Port number in format x/x/... (e.g. 0/0/1, 2/2, etc.). This is used as an *identity key* from a list of interfaces in the [NetworkDevice]() module
* `ip_address: str` - IP Address of the interface
* `subnet_mask: str` - Subnet mask of the interface

### Static attributes
* `DEFAULT_TYPES: tuple[str] (static)` - Acceptable interface types which consists of **ATM**,
**Ethernet**, **FastEthernet**, **GigabitEthernet**, **TenGigabitEthernet**,
**Serial**, **wlan-gigabitethernet**, **Loopback**, **Tunnel**, and **VLAN**

### Protected attributes
* `_cisco_commands: dict[str, str]` - Dictionary holding cisco commands for each attribute (e.g. `"bandwidth" -> "bandwidth 1000000"`)

## Methods

### Constructor
To construct the object, declare the constructor this way, for example:
```python
interface = Interface("FastEthernet", "0/0", "192.168.1.1")
```
This example shows that an interface, 'FastEthernet0/0' with CIDR '192.168.1.1/32' has been introduced to the environment.

> **NOTE**: This is a parent class module which will not be used while initiating the project. Because the interfaces like loopbacks, port channels, VLANs and phyiscal interfaces will be inherited from this class, and be used in the project.

### Public Methods
Function Name|Parameters|Description|Return
-------------|----------|-----------|------
`config`|cidr: str|Changes any or all of the attributes in a single line|Nothing
`network_address`|-|Calculates the network address from the IPv4 Address and subnet mask of this interface|The network address in `str` format
`wildcard_mask`|-|Calculates the wildcare from the IPv4 subnet mask of this interface|The wilcard mask in `str` format
`generate_command_block`|-|Generates a block of Cisco IOS commands|List of commands in `List[str]` format

#### Configuration `config(self, cidr: str = None) -> None`
Simply put, this function alters any or all of the attributes in a single line. For example:
```python
# Using 'interface' variable from the previous code
print(interface.ip_address, interface.subnet_mask)
# Output: 192.168.1.1 255.255.255.255

interface.config(cidr="192.168.12.50/24")
print(interface.ip_address, interface.subnet_mask)
# Output: 192.168.12.50 255.255.255.0
```
During automation, this is particularly useful when a router/switch needs to modify some parameters like IPv4 address, bandwidth, MTU, etc., according to such circumstances for regulation purposes.

#### Network Address `network_address(self) -> str:`
A Network Address refers to a numeric identifier assigned to a network, distinguishing it within a larger network infrastructure. It is often a part of the larger IP address space allocated to a specific organization or entity. The Network Address is more encompassing and represents a range of IP addresses, an IP Address pinpoints a specific device within that network, facilitating the routing of data packets across the global internet or a local network.

The network address is determined by performing a bitwise logical AND operation between the IP address and the subnet mask. The algorithm is explained in the `interfaces.py` module.

For example:
```python
# Using 'interface' variable from the previous code
print(interface.network_address())
# Output: 192.168.12.0
```

This will be used during OSPF/BGP routing, address-family, and summarization, etc.


#### Wildcard Mask `wildcard_mask(self) -> str:`
A wildcard mask in networking is a bitmask used for access control lists (ACLs) and routing. It complements the subnet mask and is used to specify which portions of an IP address should be ignored or treated as "wildcards" when matching against a set of addresses. In essence, it defines the range of addresses to which a rule or configuration applies, allowing for more flexible and granular control in network policies. The wildcard mask is commonly used in conjunction with Cisco devices and other networking equipment to define access control entries (ACEs) in ACLs.

To calculate a wildcard mask from a subnet mask, you can subtract each octet of the subnet mask from 255. For example, if the subnet mask is 255.255.240.0, the corresponding wildcard mask would be 0.0.15.255. This process involves subtracting each octet value from 255, creating a mask that designates which portions of the IP address are subject to wildcard matching in access control lists or routing configurations.

For example:
```python
# Using 'interface' variable from the previous code
interface.config(cidr="192.168.12.50/255.255.240.0")


print(interface.wildcard_mask())
# Output: 0.0.15.255
```

This is required during OSPF advertisement, which takes the wildcard mask and advertises the Network IP to their adjacent devices.


#### Cisco Command block generator `def generate_command_block(self) -> List[str]:`
This code generates a section of the configuration command, (which is the interface portion), and returns it. 
```python
# For this example, an interface 
for command in interface.generate_command_block(self):
    print(command)

'''
Output: 
interface FastEthernet0/0
ip address 192.168.12.50 255.255.240.0
exit
'''
```

This will be used to integrate to the the full configuration command while being generated in the `NetworkDevice`.

### Overloaded operator
- Equals `==`: Equality check using `int_type`, `port`, `ip_address` and `subnet_mask`
- Contains `__contains__`: To see if an interface exists in a collection of interfaces (e.g. `interface in interface_list`)