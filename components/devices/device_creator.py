from components.devices.router.router import Router, RouterInterface
from components.devices.router.xr_router import XRRouter
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


def cisco_7200_v1(rtr_id: str, name: str, as_number: int = None) -> Router:
    port_numbers = ["0/0", "1/0"]
    router = Router(
        router_id=rtr_id,
        hostname=name,
        interfaces=[RouterInterface("FastEthernet", port_number) for port_number in port_numbers]
    )
    if as_number:
        router.as_number = as_number

    return router


def cisco_7200(rtr_id: str, name: str, as_number: int = None) -> Router:
    router = Router(
        router_id=rtr_id,
        hostname=name,
        interfaces=[
            RouterInterface("FastEthernet", "0/0"),
            RouterInterface("FastEthernet", "0/1")
        ]
    )
    router.add_interface(RouterInterface("GigabitEthernet", "1/0"))
    if as_number:
        router.as_number = as_number

    return router


def cisco_xr_9000(rtr_id: str, name: str) -> Router:
    return XRRouter(
        router_id=rtr_id,
        hostname=name,
        interfaces=[
            RouterInterface("GigabitEthernet", "0/0/0/0"),
            RouterInterface("GigabitEthernet", "0/0/0/1"),
            RouterInterface("GigabitEthernet", "0/0/0/2"),
            RouterInterface("GigabitEthernet", "0/0/0/3"),
            RouterInterface("GigabitEthernet", "0/0/0/4"),
            RouterInterface("GigabitEthernet", "0/0/0/5"),
            RouterInterface("GigabitEthernet", "0/0/0/6"),
            RouterInterface("GigabitEthernet", "0/0/0/7")
        ],
    )
