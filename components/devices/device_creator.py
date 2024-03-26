from components.devices.router.router import Router, RouterInterface
from components.interfaces.interface import Interface
from iptx_utils import range_


def cisco_3600(rtr_id: str, name: str, as_number: int = None) -> Router:
    port_numbers = ["0/0", "0/1", "1/0", "1/1", "2/0", "2/1", "3/0", "3/1"]
    router = Router(
        router_id=rtr_id,
        hostname=name,
        interfaces=[RouterInterface("FastEthernet", port_number) for port_number in port_numbers]
    )
    router.add_interface(RouterInterface("GigabitEthernet", "4/0"))
    if as_number:
        router.as_number = as_number

    return router


def cisco_xr_9000(rtr_id: str, name: str) -> Router:
    port_numbers = Interface.range("0/0/0", range_(0, 7))
    return Router(
        router_id=rtr_id,
        hostname=name,
        interfaces=[RouterInterface("GigabitEthernet", port_number) for port_number in port_numbers],
    )
