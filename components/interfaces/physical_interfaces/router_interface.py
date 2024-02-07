from components.interfaces.physical_interfaces.physical_interface import PhysicalInterface
from typing import List


class RouterInterface(PhysicalInterface):
    def __init__(self, int_type: str, port: str | int, cidr: str = None, egp: bool = False) -> None:
        super().__init__(int_type, port, cidr)
        self.egp = egp

        # OSPF Attributes
        self.ospf_area = 0
        self.p2p = False
        self.__ospf_priority = 1
        self.__md5_auth = False
        self.__md5_passwords = dict()

        self._cisco_commands.update({
            "p2p": [],
            "priority": [],
            "md5_auth": []
        })

    # OSPF Setters --------------------------------------------------------------------------------
    def set_ospf_p2p(self, enable: bool) -> None:
        self.p2p = enable
        no_ = "" if enable else "no "
        self._cisco_commands["p2p"] = [f"{no_}ip ospf network point-to-point"]

    def set_ospf_priority(self, priority: int) -> None:
        if not (0 <= priority <= 255):
            raise ValueError(f"Invalid priority number '{priority}': Must be between 0 and 255")

        self.__ospf_priority = priority
        self._cisco_commands["priority"] = [f"ip ospf priority {priority}"]
    def ip_ospf_config(self, p2p: bool = None, priority: bool = None, md5_auth_pwd: str = None) -> None:
        # This interface should not be in EGP mode
        if not self.egp:
            if p2p is not None:
                self.p2p = p2p
                no_ = "" if p2p else "no "
                self._cisco_commands["p2p"] = [f"{no_}ip ospf network point-to-point"]

            if priority is not None:
                if not (0 <= priority <= 255):
                    raise ValueError(f"Invalid priority number '{priority}': Must be between 0 and 255")

                self.__ospf_priority = priority
                self._cisco_commands["priority"] = [f"ip ospf priority {priority}"]

            if md5_auth_pwd is not None:
                if not md5_auth_pwd.strip():
                    raise ValueError("ERROR: Cannot accept empty stringed passwords")

                self.__md5_auth_pwd = md5_auth_pwd
                self._cisco_commands["md5_auth"].append()

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


