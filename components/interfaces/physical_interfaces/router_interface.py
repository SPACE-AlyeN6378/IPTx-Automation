from components.interfaces.physical_interfaces.physical_interface import PhysicalInterface
from typing import List, TYPE_CHECKING, Dict
from components.devices.switch.switch import Switch
from colorama import Fore, Style
from iptx_utils import NetworkError, print_log
import ipaddress

if TYPE_CHECKING:
    from components.devices.network_device import NetworkDevice


class RouterInterface(PhysicalInterface):
    def __init__(self, int_type: str, port: str | int, cidr: str = None) -> None:
        super().__init__(int_type, port, cidr)

        # Permanent data types
        self.__xr_mode: bool = False
        self.egp: bool = False

        # OSPF Attributes
        self.ospf_process_id: int = 0
        self.ospf_area: int = 0
        self.ospf_p2p: bool = True
        self.ospf_priority: int = 1
        self.__md5_auth_enabled: bool = False
        self.__md5_passwords: Dict[int, str] = dict()

        # MPLS Attributes
        self.__mpls_enabled: bool = False

        self._cisco_commands.update({
            "ospf": [],
            "mpls": []
        })

        # OSPF commands (segregated for XR configuration)
        self.__more_ospf_commands = {
            "network": [],
            "passive": [],
            "priority": [],
            "md5_auth": [],
            "mpls": []
        }

    @staticmethod
    def p2p_ip_addresses(network_address: str):

        if network_address.split('.')[3] != '0':
            raise ValueError("The last octet should to be 0 for an IPv4 Network Address")

        network_address_obj = ipaddress.IPv4Network(f'{network_address}/30')
        ip_int1, ip_int2 = int(network_address_obj[0]) + 1, int(network_address_obj[0]) + 2
        ip1, ip2 = ipaddress.IPv4Address(ip_int1), ipaddress.IPv4Address(ip_int2)

        return str(ip1)+'/30', str(ip2)+'/30'

    def ospf_config(self, process_id: int = None, area: int = None, p2p: bool = None) -> None:

        # ===================== ERROR HANDLING =======================================================
        # Is it connected?
        if not self.remote_device:
            raise NetworkError("Dangling/unconnected interface. There's no use in configuring OSPF.")
        # ============================================================================================

        # This interface should not be in EGP mode
        if not self.egp:
            if area:  # If area needs to be changed
                if not (0 <= area <= 4294967295):
                    raise ValueError(f"Invalid area number '{area}': Must be between 0 and 4294967295")

                self.ospf_area = area

            if process_id:
                self.ospf_process_id = process_id
                if not self.__xr_mode:
                    self._cisco_commands["ospf"] = [f"ip ospf {self.ospf_process_id} area {self.ospf_area}"]

            if p2p is not None:
                self.ospf_p2p = p2p

                if self.ospf_p2p:
                    self.__more_ospf_commands["network"] = ["network point-to-point"]
                else:
                    self.__more_ospf_commands["network"] = ["network point-to-multipoint"]

        else:   # In EGP mode
            if area or p2p:  # If any of these parameters are included
                print(f"{Fore.MAGENTA}DENIED: This interface is for routing across autonomous systems, "
                      f"so OSPF cannot be configured{Style.RESET_ALL}")

            # That's EGP, so passive interface is enabled to prevent OSPF hello packets from being sent
            if self.__xr_mode:
                self.__more_ospf_commands["passive"] = ["passive enable"]

    def ospf_set_priority(self, priority) -> None:

        if not self.ospf_p2p:
            if not (0 <= priority <= 255):
                raise ValueError(f"Invalid priority number '{priority}': Must be between 0 and 255")

            self.ospf_priority = priority
            self.__more_ospf_commands["priority"] = [f"priority {priority}"]

        else:
            print(f"{Fore.MAGENTA}DENIED: This is configured as a point-to-point interface, so priority "
                  f"cannot be changed.{Style.RESET_ALL}")

    def ospf_set_password(self, key: int, password: str) -> None:

        if not self.ospf_process_id:
            raise NetworkError("OSPF not initialized yet. Please set the process ID using ospf_config()")

        # Set the password for a particular key
        self.__md5_passwords[key] = password
        if self.ospf_p2p and len(self.__md5_passwords) > 1:
            raise NetworkError("Only one password can be added or modified")

        if not self.__md5_auth_enabled:
            self.__more_ospf_commands["md5_auth"].append("authentication message-digest")
            self.__md5_auth_enabled = True

        self.__more_ospf_commands["md5_auth"].append(f"message-digest-key {key} md5 7 {password}")

    def connect_to(self, remote_device: 'NetworkDevice', remote_port: str, cable_bandwidth: int = None) -> None:
        super().connect_to(remote_device, remote_port, cable_bandwidth)

        if isinstance(remote_device, Switch):
            if not self.egp:  # Don't connect to switches for EGP routing
                raise NetworkError("ERROR: This interface is for routing between autonomous systems, so this "
                                   "should not be connected to switches during EGP routing")

            self.ospf_p2p = False  # Must be mult-point configuration

        if self.egp and self.__xr_mode:
            self.ospf_config()  # Configure as passive interface

    def toggle_mpls(self):

        # ===================== ERROR HANDLING =======================================================
        # Is it connected?
        if not self.remote_device:
            raise NetworkError("Dangling/unconnected interface. There's no use in configuring MPLS.")
        # ============================================================================================

        # Just invert the boolean
        self.__mpls_enabled = not self.__mpls_enabled

        if self.__mpls_enabled:
            # Display the log check if MPLS is enabled or not
            print_log("Enabling MPLS")

            # Generate the Cisco command
            if self.__xr_mode:
                self.__more_ospf_commands["mpls"] = ["no mpls ldp sync"]
            else:
                self._cisco_commands["mpls"] = ["mpls ip"]

        else:
            print_log("Disabling MPLS")
            if self.__xr_mode:
                self.__more_ospf_commands["mpls"] = ["no mpls ldp sync"]
            else:
                self._cisco_commands["mpls"] = ["no mpls ip", "no mpls label protocol ldp"]

    # Get the portion of the command block
    def generate_command_block(self) -> List[str]:
        if not self.__xr_mode:

            if not self.egp:
                # Transfer all the OSPF commands to the main self._cisco_commands, except for passive
                for attribute in self.__more_ospf_commands.keys():
                    if attribute != "passive":
                        self._cisco_commands["ospf"].extend(f"ip ospf {line}" for
                                                            line in self.__more_ospf_commands[attribute])

                    self.__more_ospf_commands[attribute].clear()

        else:
            # Replace IP with IPv4 in one of the Cisco command lines
            if self._cisco_commands["ip address"]:
                if 'ipv6' not in self._cisco_commands["ip address"][0]:
                    self._cisco_commands["ip address"][0] = self._cisco_commands["ip address"][0].replace("ip", "ipv4")

        return super().generate_command_block()

    # Generate OSPF XR advertisement command
    def generate_ospf_xr_commands(self) -> List[str]:
        # First, generate the command
        commands = [line for lines in self.__more_ospf_commands.values() for line in lines]
        commands.insert(0, f"interface {str(self)}")
        commands.append("exit")

        # Clear the dictionary of commands
        self.__more_ospf_commands = {
            "network": [],
            "passive": [],
            "priority": [],
            "md5_auth": []
        }

        return commands
