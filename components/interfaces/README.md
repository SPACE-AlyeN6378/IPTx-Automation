# Network Interface

A Network Interface, in the realm of computer networks, acts as the 
point of interaction between a device and another device or the network it's connected to.
It serves as the gateway for data to flow in and out of the device, managing 
the communication protocols and handling the transmission and reception of 
data packets. Essentially, a Network Interface enables devices to connect, 
communicate, and participate in a network, playing a fundamental role in 
facilitating the exchange of information and ensuring effective network operations.


The class module `Interface` holds the following attributes:

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



