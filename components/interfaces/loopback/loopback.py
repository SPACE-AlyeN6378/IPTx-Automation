from typing import List

from components.interfaces.interface import Interface


class Loopback(Interface):

    def __init__(self, cidr: str, loopback_id: int = 0, description: str = None) -> None:
        super().__init__(int_type="Loopback", port=loopback_id, cidr=cidr)

        self.config(description=description)
        self.ospf_area = 0
        self.allow_hellos = False    # Allow hello packets to be sent at fixed intervals
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
            self.allow_hellos = allow_hellos

        if self.xr_mode:  # For Cisco XR routers
            if self.allow_hellos:
                self.__ospf_xr_commands = ["passive disable", "network point-to-multipoint"]
            else:
                self.__ospf_xr_commands = ["passive enable"]
        else:
            self._cisco_commands["ospf"] = [
                f"ip ospf {process_id} area {self.ospf_area}"
            ]

    def get_ospf_xr_commands(self) -> List[str]:
        if self.__ospf_xr_commands:
            commands = [f"interface {str(self)}"]
            commands.extend(self.__ospf_xr_commands)
            commands.append("exit")

            self.__ospf_xr_commands.clear()
            return commands
        else:
            return []

    # Generate IBGP neighbor establishment command
    def get_ibgp_command(self, as_num: int) -> List[str]:
        if not self.ip_address:
            raise NotImplementedError("The IP address is missing")

        return [
            f"neighbor {self.ip_address} remote-as {as_num}",
            f"neighbor {self.ip_address} update-source {str(self)}"
        ]

