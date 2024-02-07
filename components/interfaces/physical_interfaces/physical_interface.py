from typing import List, Union, TYPE_CHECKING
from components.interfaces.interface import Interface
# import components.devices.network_device as device
from colorama import Fore, Style
from enum import Enum

if TYPE_CHECKING:
    from components.devices.network_device import NetworkDevice


class Mode(Enum):  # ENUM for switchport modes
    NULL = 0
    ACCESS = 1
    TRUNK = 2


class PhysicalInterface(Interface):
    BANDWIDTHS = {"ATM": 622000, "Ethernet": 10000, "FastEthernet": 100000, "GigabitEthernet": 1000000,
                  "TenGigabitEthernet": 10000000, "Serial": 1544, "wlan-gigabitethernet": 1000000}

    def __init__(self, int_type: str, port: Union[str, int], cidr: str = None) -> None:

        super().__init__(int_type, port, cidr)
        self.validate_interface_type()

        # New attributes
        self.shutdown_state = True
        self.max_bandwidth = PhysicalInterface.BANDWIDTHS[int_type]     # Initial assumption about the bandwidth
        self.bandwidth = PhysicalInterface.BANDWIDTHS[int_type]
        self.mtu = 1500
        self.duplex = "auto"

        # Used when a connection is established, otherwise
        self.remote_device = None
        self.remote_port = None

        # Cisco commands
        self._cisco_commands.update({
            "shutdown": "shutdown",
            "bandwidth": f"bandwidth {self.bandwidth}",
            "mtu": f"mtu {self.mtu}",
            "duplex": f"duplex {self.duplex}"
        })

    # Check if the interface type is actually a physical interface (e.g. Ethernet)
    def validate_interface_type(self) -> None:
        default_types = PhysicalInterface.BANDWIDTHS.keys()

        if self.int_type not in default_types:
            raise TypeError(
                f"ERROR: Invalid interface type '{self.int_type}' - Please use the following "
                f"interfaces {', '.join(default_types)}")

    def config(self, cidr: str = None, bandwidth: int = None, mtu: int = None,
               duplex: str = None) -> None:
        super().config(cidr)

        if mtu:
            self.mtu = mtu
            self._cisco_commands["mtu"] = f"mtu {self.mtu}"

        if bandwidth:
            """
            If the bandwidth exceeds the maximum permittable bandwidth, then it caps it down to the given maximum
            """
            if bandwidth > self.max_bandwidth:
                print(f"{Fore.YELLOW}WARNING: The bandwidth {bandwidth} bps in the parameter exceeds the maximum "
                      f"bandwidth {self.max_bandwidth} bps. Capping it to the given maximum...{Style.RESET_ALL}")
                self.bandwidth = self.max_bandwidth
            else:
                self.bandwidth = bandwidth

            self._cisco_commands["bandwidth"] = f"bandwidth {self.bandwidth}"

        if duplex:
            if duplex not in ["auto", "full", "half"]:
                raise ValueError(f"ERROR: Inappropriate configuration for duplex \'{duplex}\'")
            
            self.duplex = duplex
            self._cisco_commands["duplex"] = f"duplex {self.duplex}"

    # Shuts down the interface
    def shutdown(self) -> None:
        if self.shutdown_state:
            print(f"{Fore.MAGENTA}DENIED: This connector is already shut down.{Style.RESET_ALL}")
        else:
            self.shutdown_state = True
            self._cisco_commands["shutdown"] = "shutdown"

    # Releases the interface
    def release(self) -> None:
        if not self.shutdown_state:
            print(f"{Fore.MAGENTA}DENIED: This connector has already opened.{Style.RESET_ALL}")
        else:
            if not self.remote_device:
                print(f"{Fore.MAGENTA}DENIED: Unconnected physical interface, so it remains shut{Style.RESET_ALL}")

            else:
                self.shutdown_state = False
                self._cisco_commands["shutdown"] = "no shutdown"

    """
    Description: Establishes a connection. It basically sets the remote device 
    and its respective port to the ones given in the parameter.
    
    Parameters: Network device, its port and the new bandwidth. (In case if an ethernet cable of lower bandwidth is used, 
    the 'new_bandwidth' parameter is used to reduce the bandwidth)
    """
    def connect_to(self, remote_device: 'NetworkDevice', remote_port: str, new_bandwidth: int = None) -> None:
        # Assign the network device and port number
        # if isinstance(remote_device, device.NetworkDevice):
        #     raise TypeError(f"ERROR: This object '{str(remote_device)}' is not a network device")

        self.remote_device = remote_device
        self.remote_port = remote_port

        # Release the interface
        self.release()

        # Reduce the bandwidth, maximize the MTU and set the duplex to auto if necessary
        remote_int_bandwidth = self.remote_device.interface(remote_port).bandwidth  # Bandwidth on the remote device
        if remote_int_bandwidth < self.bandwidth:   # If the bandwidth at the remote port is lower
            self.max_bandwidth = remote_int_bandwidth   # Set the maximum bandwidth
            if new_bandwidth:
                self.config(bandwidth=new_bandwidth)
            else:
                self.config(bandwidth=self.max_bandwidth)

        remote_int_mtu = self.remote_device.interface(remote_port).mtu
        if remote_int_mtu > self.mtu:  # If the MTU at the remote port is higher
            self.config(bandwidth=remote_int_mtu)

        remote_int_duplex = self.remote_device.interface(remote_port)
        if remote_int_duplex != self.duplex and self.duplex != "auto" and remote_int_duplex != "auto":
            self.config(duplex="auto")

    def disconnect(self) -> None:
        # Nullify the variables
        self.remote_device = None
        self.remote_port = None

        # Set the bandwidth to default
        self.max_bandwidth = self.bandwidth = PhysicalInterface.BANDWIDTHS[self.int_type]
        self.shutdown()

    def __eq__(self, other):
        if isinstance(other, PhysicalInterface):
            return self.int_type == other.int_type \
                and self.port == other.port \
                and self.ip_address == other.ip_address \
                and self.subnet_mask == other.subnet_mask \
                and self.bandwidth == other.bandwidth \
                and self.mtu == other.mtu \
                and self.duplex == other.duplex \
                and self.remote_device == other.remote_device

        return False
    
    # Generates a block of commands
    def generate_command_block(self):
        # Gets a new list of commands
        command_block = [f"interface {self.__str__()}"]
        
        for attr in self._cisco_commands.keys():
            # Check if each line of the command exists
            if self._cisco_commands[attr]:
                # Add to command_block and clear the string
                command_block.append(self._cisco_commands[attr])
                self._cisco_commands[attr] = ""

        # If the generated command exists, return the full list of commands, otherwise return an empty list
        if len(command_block) > 1:
            command_block.append("exit")
            return command_block
        
        return []


