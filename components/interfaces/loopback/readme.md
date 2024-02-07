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
* `p2p: bool` (*public*): Indicates whether the loopback can be advertised point-to-point or not
* `ospf_area: int` (*public*): Area number or part of the autonomous system where the OSPF is advertised to

## Public methods
| Function Name                                                                  | Parameters              | Description                                                                            | Return                                 |
|--------------------------------------------------------------------------------|-------------------------|----------------------------------------------------------------------------------------|----------------------------------------|
| [`config`](../interfaces/interface.py#Lconfig)                                 | `cidr: str`             | Changes any or all of the attributes in a single line                                  | Nothing                                |
| [`network_address`](../interfaces/interface.py#Lnetwork_address)               | -                       | Calculates the network address from the IPv4 Address and subnet mask of this interface | The network address in `str` format    |
| [`wildcard_mask`](../interfaces/interface.py#Lwildcard_mask)                   | -                       | Calculates the wildcard mask from the IPv4 subnet mask of this interface               | The wildcard mask in `str` format      |
| [`generate_command_block`](../interfaces/interface.py#Lgenerate_command_block) | -                       | Generates a block of Cisco IOS commands                                                | List of commands in `List[str]` format |
| [`set_ospf_p2p`](./loopback.py)                                                | `enable: bool`          | Enables/disable OSPF point-to-point advertisement                                      | None                                   |
| [`get_ospf_command`](./loopback.py)                                            | -                       | Generates the OSPF advertisement command                                               | List of Cisco command strings          |
| [`get_ibgp_command`](./loopback.py)                                            | AS Number `as_num: int` | Generates the IBGP neighbor establishment commands for the remote device               | List of Cisco command strings          |

## Example Code
First, let's **construct** the Loopback. It just requires `int_type: str` and `port: str` (which is 0 by default):
```python
my_loopback = Loopback(cidr="10.255.255.1/24", port=2)
```

Setting the OSPF area, where the loopback will be advertised, to 2:
```python
my_loopback.ospf_area = 2
```

Generating the cisco commands for OSPF advertisement:
```python
print("# Generating OSPF Advertisement commands:")
for line in my_loopback.get_ospf_command():
    print(line)

"""
Output:
# Generating OSPF Advertisement commands:
network 10.255.255.0 0.0.0.255 area 2
"""
```

Generating the cisco commands for IBGP configuration:
```python
print("# Generating BGP neighborhood configuration commands in AS 300:")
for line in my_loopback.get_ibgp_command(as_num=300):
    print(line)

"""
Output:
# Generating BGP neighborhood configuration commands in AS 300:
neighbor 10.255.255.1 remote-as 300
neighbor 10.255.255.1 update-source Loopback2
"""
```
>[!NOTE]
> These commands based on routing protocol will not be stored within the command block interface, but rather be stored inside the `Router` class. Because they need to be configured separately.

