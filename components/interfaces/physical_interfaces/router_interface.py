from components.interfaces.physical_interfaces.physical_interface import PhysicalInterface
from typing import List, TYPE_CHECKING
from components.devices.switch.switch import Switch
from colorama import Fore, Style

if TYPE_CHECKING:
    from components.devices.network_device import NetworkDevice


class RouterInterface(PhysicalInterface):
    def __init__(self, int_type: str, port: str | int, cidr: str = None, egp: bool = False) -> None:
        super().__init__(int_type, port, cidr)
        self.egp = egp
        self.xr_mode = False

        # OSPF Attributes
        self.process_id = None
        self.ospf_area = 0
        self.ospf_p2p = True
        self.ospf_priority = 1
        self.__md5_passwords = dict()

        self._cisco_commands.update({
            "ospf_advertise": []
        })

        # OSPF commands
        self.__more_ospf_commands = {
            "network": [],
            "priority": [],
            "md5_auth": []
        }

    # OSPF Setters and Configuration
    def ospf_config(self, process_id: int = None, area: int = None, p2p: bool = None, priority: bool = None) -> None:
        # This interface should not be in EGP mode
        if not self.egp:
            if area:
                self.ospf_area = area

            if process_id:
                self.process_id = process_id
                if not self.xr_mode:
                    self.__more_ospf_commands["ospf_advertise"] = [f"ip ospf {self.process_id} area {self.ospf_area}"]

            if p2p is not None:
                self.ospf_p2p = p2p

                if self.ospf_p2p:
                    self.__more_ospf_commands["ospf_p2p"] = ["network point-to-point"]
                else:
                    self.__more_ospf_commands["ospf_p2p"] = ["network point-to-multipoint"]

            if priority is not None:
                if not self.ospf_p2p:
                    if not (0 <= priority <= 255):
                        raise ValueError(f"Invalid priority number '{priority}': Must be between 0 and 255")

                    self.ospf_priority = priority
                    self.__more_ospf_commands["priority"] = [f"priority {priority}"]

                else:
                    print(f"{Fore.MAGENTA}DENIED:{Fore}")

        else:
            print(f"{Fore.MAGENTA}DENIED: This interface is for inter-autonomous routing{Style.RESET_ALL}")

    def connect_to(self, remote_device: 'NetworkDevice', remote_port: str, new_bandwidth: int = None) -> None:
        super().connect_to(remote_device, remote_port, new_bandwidth)

        if isinstance(remote_device, Switch):
            self.config()


    def set_ospf_priority(self, enable: bool) -> None:
        self.p2p = enable
        no_ = "" if enable else "no "
        self._cisco_commands["p2p"] = f"{no_}ip ospf network point-to-point"

    # Generate OSPF advertisement command
    def get_ospf_command(self) -> List[str]:
        if not self.egp:
            if not (self.ip_address and self.subnet_mask):
                raise NotImplementedError("The IP address and subnet mask are missing")

            return [f"network {self.network_address()} {self.wildcard_mask()} area {self.ospf_area}"]
        else:
            return [f"passive-interface {str(self)}"]

    # Generate IBGP neighbor establishment command


