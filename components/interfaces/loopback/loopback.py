from components.interfaces.interface import Interface


class Loopback(Interface):

    def __init__(self, cidr: str, port: int = 0) -> None:
        super().__init__(int_type="Loopback", port=port, cidr=cidr)
        self.p2p = False
        self.p2p_cmd = ""

    def set_ospf_p2p(self, enable: bool) -> None:
        self.p2p = enable
        no_ = "" if enable else "no "
        self.p2p_cmd = f"{no_}ip ospf network point-to-point"

    def generate_command_block(self):
        commands = super().generate_command_block()
        Interface.insert_cmd(commands, self.p2p_cmd)

        return commands
