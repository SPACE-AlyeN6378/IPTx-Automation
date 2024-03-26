from typing import List

from components.interfaces.interface import Interface


class Loopback(Interface):

    def __init__(self, cidr: str, loopback_id: int = 0, description: str = None) -> None:
        super().__init__(int_type="Loopback", port=loopback_id, cidr=cidr)

        self.config(description=description)
        self.ospf_area = 0
        self.ospf_allow_hellos = False    # Allow hello packets to be sent at fixed intervals
        self.xr_mode = False

        self._cisco_commands.update({
            "ospf": []
        })

        # A separate list of commands for XR configuration for the OSPF configuration
        self.__ospf_xr_commands = []

    # OSPF Initialization
    def ospf_config(self, process_id: int, area: int = None, allow_hellos: bool = None) -> None:
        if not (self.ip_address and self.subnet_mask):
            raise NotImplementedError("The IP address and subnet mask are missing")

        if area is not None:    # If area number needs to be changed
            self.ospf_area = area

        if allow_hellos is not None:    # If you want to allow hello packets to be sent
            self.ospf_allow_hellos = allow_hellos

        if self.xr_mode:  # For Cisco XR routers
            if self.ospf_allow_hellos:
                self.__ospf_xr_commands = ["passive disable", "network point-to-multipoint"]
            else:
                self.__ospf_xr_commands = ["passive enable"]
        else:
            self._cisco_commands["ospf"] = [
                f"ip ospf {process_id} area {self.ospf_area}"
            ]

    def generate_command_block(self):
        if self.xr_mode:
            if self._cisco_commands["ip address"]:
                self._cisco_commands["ip address"][0] = self._cisco_commands["ip address"][0].replace("ip", "ipv4")

        return super().generate_command_block()

    def generate_ospf_xr_commands(self) -> List[str]:
        if self.__ospf_xr_commands:
            commands = [f"interface {str(self)}"]
            commands.extend(self.__ospf_xr_commands)
            commands.append("exit")

            self.__ospf_xr_commands.clear()
            return commands
        else:
            return []



