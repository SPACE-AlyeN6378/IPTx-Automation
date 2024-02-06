# Loopback Interface

The Loopback Interface, inherited from the [`Interface`](..) class, serves as a virtual network interface on a router, 
primarily utilized for router identification purposes. Unlike physical interfaces, the Loopback Interface does 
not correspond to a physical hardware component but rather exists entirely within the router's software. This 
interface is assigned a unique IP address, often within the range of private IP addresses, allowing the router 
to be uniquely identified within the network. Additionally, the Loopback Interface provides a convenient tool 
for debugging network configurations and testing network connectivity, as it remains operational even if physical 
interfaces are down or disconnected. Its versatility and stability make it an essential component in network 
administration and troubleshooting tasks.

For this project, the IP Address of the first loopback will always be used to as a Router ID. And it can also be used to 
indicate a network device/node, when a single router is being used as a virtual topology of routers, switches 
and endpoints. This is particularly useful for GNS3 simulation to reduce CPU usage.

## Attributes

Some useful attributes inherited from the parent module [`Interface`](..) are:
* `int_type: str`
* `port: str`
* `ip_address: str`
* `subnet_mask: str`

The additional attributes for this class module include:
* `p2p: bool`: Indicates whether the loopback can be advertised point-to-point or not

## Public methods
| Function Name                                 | Parameters     | Description                                                                            | Return                                 |
|-----------------------------------------------|----------------|----------------------------------------------------------------------------------------|----------------------------------------|
| `config`                                      | `cidr: str`    | Changes any or all of the attributes in a single line                                  | Nothing                                |
| `network_address`                             | -              | Calculates the network address from the IPv4 Address and subnet mask of this interface | The network address in `str` format    |
| `wildcard_mask`                               | -              | Calculates the wildcard mask from the IPv4 subnet mask of this interface               | The wildcard mask in `str` format      |
| `generate_command_block`                      | -              | Generates a block of Cisco IOS commands                                                | List of commands in `List[str]` format |
| [`set_ospf_p2p`](./loopback.py#Lset_ospf_p2p) | `enable: bool` | Enables/disable OSPF point-to-point advertisement                                      | None                                   |