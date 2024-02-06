# Network Device

The `NetworkDevice` class serves as a versatile and central node within a network topology, designed to encapsulate the functionality of various network entities such as switches, routers, or endpoints like servers and PCs. This class encompasses key attributes and methods essential for managing and orchestrating communication within a network, offering a unified interface for developers to interact with diverse network elements. Whether it's routing data, managing connections, or handling specific device functionalities, the "Network Device" class provides a flexible and scalable foundation for building and simulating complex network topologies in a comprehensive and efficient manner.

> **NOTE**: This, again, is just the base model and will not be used in the main project, but for debugging purposes.

As obvious, some of the derived network devices that is used in the project are:
- Routers (*can be used as endpoints too*)
- Switches
- Endpoints (e.g. Client-side PCs and servers)

### Attributes

- `__device_id: str`: Device ID as IP Address
- `hostname`: Hostname of the device
- `__phys_interfaces: List[PhysicalInterface]`: List of Physical Interfaces
- `__phys_interfaces: List[Loopback]`: List of loopbacks
- `_cisco_commands: Dict[str, str]`: Dictionary holding Cisco commands for each attribute

### Getters
| Function Name           | Parameters              | Description                                                    | Returns                                                 |
|-------------------------|-------------------------|----------------------------------------------------------------|---------------------------------------------------------|
| `id()`                  | -                       | Gets the ID of the device                                      | Device ID in `str`                                      |
| `interface`             | Port number `port: str` | Retrieves a physical interface by its port number              | `PhysicalInterface` object                              |
| `loopback`              | Loopback ID `int`       | Retrieves a loopback by its number                             | `Loopback` object                                       |
| `all_phys_interfaces()` | -                       | Gets a list of all the physical interfaces                     | All interfaces as `List[PhysicalInterface]`             |
| `all_loopbacks()`       | -                       | Gets a list of all the loopbacks                               | All loopbacks as `List[Loopback]`                       |
| `all_interfaces()`      | -                       | Gets a combined list of all the interfaces                     | All interfaces as `List[PhysicalInterface \| Loopback]` |
| `remote_device()`       | Port number `port: str` | Gets the remote device on the other side                       | Remote Device as `NetworkDevice \| Router \| Switch`    |
| `remote_port()`         | Port number `port: str` | Gets the connected port of the remote device on the other side | Remote port as `str`                                    |

### Setters and Modifiers
| Function Name        | Parameters                                                                                    | Description                                            | Returns           |
|----------------------|-----------------------------------------------------------------------------------------------|--------------------------------------------------------|-------------------|
| `update_id()`        | `new_id: int \| str`                                                                          | Changes the ID with the one specified in the parameter | None              |
| `set_hostname()`     | `hostname: str`                                                                               | Changes the hostname                                   | None              |
| `add_interface()`    | Variable number of `new_interfaces: PhysicalInterface \| Loopback`                            | Adds new interfaces specified in the parameters        | None              |
| `remove_interface()` | Port number or the interface itself `interface_or_port: str \| PhysicalInterface \| Loopback` | Removes an interface by its port number                | Removed interface |

### Configuration Script Generator [`send_script()`](./network_device.py#L174)

This generates a complete Cisco command and sends it to the networking devices. (For now, it copy/pastes using `pyperclip` library)