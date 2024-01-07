from components.interfaces.interface import Interface

class Loopback(Interface):

    def __init__(self, cidr: str="0.0.0.0/32") -> None:
        super().__init__(int_type="Loopback", port=0, cidr=cidr)

    def __eq__(self, other):
        if isinstance(other, Interface):
            return self.int_type == other.int_type \
            and self.ip_address == other.ip_address and self.subnet_mask == other.subnet_mask

        return False
    
    def __contains__(self, item):
        return self.int_type == item.int_type \
        and self.ip_address == item.ip_address and self.subnet_mask == item.subnet_mask