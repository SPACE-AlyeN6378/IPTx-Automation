from components.interfaces.physical_interface import PhysicalInterface
import components.nodes.router as rt

class RouterInterface(PhysicalInterface):
    def __init__(self, int_type: str, port: str | int, cidr: str = None, egp: bool = False) -> None:
        super().__init__(int_type, port, cidr)
        self.egp = egp



