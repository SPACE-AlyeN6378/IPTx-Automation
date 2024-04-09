from typing import List, Union, TYPE_CHECKING
from components.interfaces.interface import Interface
from colorama import Fore, Style
from enum import Enum
from components.interfaces.physical_interfaces.subinterface import SubInterface

if TYPE_CHECKING:
    from components.devices.network_device import NetworkDevice

class Mode(Enum):  # ENUM for switchport modes
    NULL = 0
    ACCESS = 1
    TRUNK = 2


class PhysicalInterface(Interface):
    BANDWIDTHS = {
        "ATM": 622000,
        "Ethernet": 10000,
        "FastEthernet": 100000,
        "GigabitEthernet": 1000000,
        "TenGigabitEthernet": 10000000,
        "Serial": 1544,
        "wlan-gigabitethernet": 1000000
    }

    def __init__(self, int_type: str, port: Union[str, int], cidr: str = None) -> None:

        super().__init__(int_type, port, cidr)
        self.description = "UNCONNECTED"
        self.validate_interface_type()

        # New attributes
        self.shutdown_state = True
        self.max_allowable_bw = PhysicalInterface.BANDWIDTHS[int_type]
        self.bandwidth = PhysicalInterface.BANDWIDTHS[int_type]
        self.mtu = 1500
        self.duplex = "auto"
        self.egp = False

        # List of Sub-interfaces
        self.sub_interfaces: set[SubInterface] = set()

        # Used when a connection is established, otherwise
        self.remote_device = None
        self.remote_port = None

        # Cisco commands
        self._cisco_commands.update({
            "description": [f"description \"{self.description}\""],
            "shutdown": ["shutdown"],
            "bandwidth": [],
            "mtu": [],
            "duplex": [],
            "other": ["load-interval 30", "negotiation auto"]
        })

    def validate_interface_type(self) -> None:
        # Check if the interface type is actually a physical interface (e.g. Ethernet)
        default_types = PhysicalInterface.BANDWIDTHS.keys()

        if self.int_type not in default_types:
            raise TypeError(
                f"ERROR: Invalid interface type '{self.int_type}' - Please use the following "
                f"interfaces {', '.join(default_types)}")

    def config(self, cidr: str = None, description: str = None, bandwidth: int = None, mtu: int = None,
               duplex: str = None) -> None:
        super().config(cidr, description)

        if mtu:
            self.mtu = mtu
            self._cisco_commands["mtu"] = [f"mtu {self.mtu}"]

        if bandwidth:
            """
            If the bandwidth exceeds the maximum allowable bandwidth, then it caps it down to the given maximum
            """
            if bandwidth > self.max_allowable_bw:
                print(f"{Fore.YELLOW}WARNING: The bandwidth {bandwidth} bps in the parameter exceeds the maximum "
                      f"bandwidth {self.max_allowable_bw} bps. Capping it to the given maximum...{Style.RESET_ALL}")
                self.bandwidth = self.max_allowable_bw
            else:
                self.bandwidth = bandwidth

            self._cisco_commands["bandwidth"] = [f"bandwidth {self.bandwidth}"]

        if duplex:
            if duplex not in ["auto", "full", "half"]:
                raise ValueError(f"ERROR: Inappropriate configuration for duplex \'{duplex}\'")
            
            self.duplex = duplex
            self._cisco_commands["duplex"] = [f"duplex {self.duplex}"]

    # Shuts down the interface
    def shutdown(self) -> None:
        if self.shutdown_state:
            print(f"{Fore.MAGENTA}DENIED: This connector is already shut down.{Style.RESET_ALL}")
        else:
            self.shutdown_state = True
            self._cisco_commands["shutdown"] = ["shutdown"]

    # Releases the interface
    def release(self) -> None:
        if not self.shutdown_state:
            print(f"{Fore.MAGENTA}DENIED: This connector has already opened.{Style.RESET_ALL}")
        else:
            if not self.remote_device:
                print(f"{Fore.MAGENTA}DENIED: Unconnected physical interface, so it remains shut{Style.RESET_ALL}")

            else:
                self.shutdown_state = False
                self._cisco_commands["shutdown"] = ["no shutdown"]

    def connect_to(self, remote_device: 'NetworkDevice', remote_port: str, cable_bandwidth: int = float('inf')) -> None:
        """
        Description: Establishes a connection. It basically sets the remote device
        and its respective port to the ones given in the parameter.

        Parameters: Network device, its port and the new bandwidth. (In case if an ethernet cable of lower bandwidth is
        used,
        the 'new_bandwidth' parameter is used to reduce the bandwidth)
        """
        # NOTE: In case a cable of slower bandwidth is used, the 'cable_bandwidth' is used

        # Check if the interface is already connected to another device
        if self.remote_device is not None:
            raise ConnectionError("This interface is already connected. Please try another one.")

        # Assign the network device and port number
        self.remote_device = remote_device
        self.remote_port = remote_port

        # Change the description
        self.config(description=f"BACKBONE_P2P_CONN_WITH_{self.remote_device}")

        # Release the interface
        self.release()

        # Reduce the bandwidth, if necessary
        remote_int_bandwidth = self.remote_device.interface(remote_port).bandwidth  # Bandwidth on the remote device
        self.max_allowable_bw = min(remote_int_bandwidth, self.bandwidth)
        new_bandwidth = min(remote_int_bandwidth, self.bandwidth, cable_bandwidth)
        self.config(bandwidth=new_bandwidth)

        # Maximize the MTU
        remote_int_mtu = self.remote_device.interface(remote_port).mtu
        if remote_int_mtu > self.mtu:  # If the MTU at the remote port is higher
            self.config(mtu=remote_int_mtu)

        # Set the duplex to 'auto' if necessary
        remote_int_duplex = self.remote_device.interface(remote_port)
        if remote_int_duplex != self.duplex and self.duplex != "auto" and remote_int_duplex != "auto":
            self.config(duplex="auto")

    def disconnect(self) -> None:
        # Nullify the variables
        self.remote_device = None
        self.remote_port = None

        # Change the description
        self.config(description=f"UNCONNECTED")

        # Set the bandwidth to default
        self.max_allowable_bw = self.bandwidth = PhysicalInterface.BANDWIDTHS[self.int_type]
        self.shutdown()

    def __eq__(self, other):
        if isinstance(other, PhysicalInterface):
            return self.int_type == other.int_type \
                and self.port == other.port \
                and self.ip_address == other.ip_address \
                and self.subnet_mask == other.subnet_mask \
                and self.device_id == other.device_id \
                and self.mtu == other.mtu \
                and self.duplex == other.duplex \
                and self.remote_device == other.remote_device

        return False

    def __hash__(self) -> int:
        return hash((self.int_type, self.port,
                     self.ip_address, self.subnet_mask,
                     self.device_id, self.mtu, self.duplex,
                     self.remote_device))

    def add_sub_if(self, vlan_id: int) -> None:
        self.sub_interfaces.add(SubInterface(self.int_type, self.port, vlan_id, mtu=self.mtu))

    def get_sub_if(self, vlan_id: int) -> SubInterface | None:
        for interface in self.sub_interfaces:
            if interface.vlan_id == vlan_id:
                return interface

        return None

    def generate_config(self) -> List[str]:
        main_config = super().generate_config()
        for sub_interface in self.sub_interfaces:
            main_config.extend(sub_interface.generate_config())

        return main_config
