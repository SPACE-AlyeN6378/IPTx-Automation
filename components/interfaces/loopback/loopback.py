from typing import List

from components.interfaces.interface import Interface


class Loopback(Interface):

    def __init__(self, cidr: str, port: int = 0) -> None:
        super().__init__(int_type="Loopback", port=port, cidr=cidr)

        self.ospf_area = 0
        self.allow_hellos = False    # Allow hello packets to be sent at fixed intervals

        self._cisco_commands.update({
            "ospf": []
        })

        # A separate list of commands for XR configuration for the OSPF configuration
        self.__ospf_xr_commands = []

    # OSPF Initialization
    def ospf_advertise(self, process_id: int, area: int = None, for_xr: bool = False) -> None:
        if not (self.ip_address and self.subnet_mask):
            raise NotImplementedError("The IP address and subnet mask are missing")

        if area:    # If area number needs to be changed
            self.ospf_area = area

        if for_xr:  # For Cisco XR routers
            if self.allow_hellos:
                self.__ospf_xr_commands = ["passive disable", "network point-to-multipoint"]
            else:
                self.__ospf_xr_commands = ["passive enable"]
        else:
            self._cisco_commands["ospf"] = [
                f"ip ospf {process_id} {self.ospf_area}"
            ]

    def get_ospf_xr_commands(self) -> List[str]:
        if self.__ospf_xr_commands:
            cisco_commands = [f"interface {str(self)}"]
            cisco_commands.extend(self.__ospf_xr_commands)
            cisco_commands.append("exit")
            return cisco_commands
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

