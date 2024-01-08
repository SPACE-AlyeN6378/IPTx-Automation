from __future__ import annotations

from typing import Any
from components.interfaces.connector import Connector
from components.interfaces.loopback import Loopback
from network_error import NetworkError


class InterfaceList:

    def __init__(self, *args):
        self.connectors = []
        self.loopbacks = []
        self.push(*args)

    def __getitem__(self, port: str):
        expected_item = None

        # Loopback port for e.g. 'l3'
        if port[0].lower() == 'l':
            port = int(port[1:].strip())
            expected_item = self.loopbacks[port]

        # Connector port for e.g. '0/2'
        else:
            for connector in self.connectors:
                if port == connector.port:
                    expected_item = connector
                    break

        return expected_item

    def __iter__(self):
        for interface in self.connectors + self.loopbacks:
            yield interface

    def __and__(self, other):
        result = InterfaceList()
        for interface in self:
            if interface in other:

                if isinstance(interface, Loopback):
                    result.loopbacks.append(interface)
                else:
                    result.connectors.append(interface)

        return result

    def __or__(self, other):
        result = InterfaceList()
        for interface in self:
            if interface not in other:

                if isinstance(interface, Loopback):
                    result.loopbacks.append(interface)
                else:
                    result.connectors.append(interface)

        for interface in other:

            if isinstance(interface, Loopback):
                result.loopbacks.append(interface)
            else:
                result.connectors.append(interface)

        return result

    def __xor__(self, other):
        result = self | other
        for interface in self & other:
            result.pop(interface)

        return result

    def __len__(self):
        return len(self.loopbacks) + len(self.connectors)

    def __str__(self):
        return "[" + ", ".join(str(inf) for inf in self.connectors + self.loopbacks) + "]"

    # Adds a couple of interfaces to the list
    def push(self, *args: Connector | Loopback):

        if not all(isinstance(arg, (Connector, Loopback)) for arg in args):
            raise TypeError("All interfaces should be either a connector (e.g. GigabitEthernet) or a loopback")

        for arg in args:

            # First, you check for matching port number and Network IP, to avoid overlapping
            # For Connectors and Cables
            if isinstance(arg, Connector):
                if arg.ip_address:
                    networks = [inf.network_address() for inf in self.connectors if inf.ip_address]
                    if arg.port in (inf.port for inf in self.connectors) or (arg.network_address() in networks):
                        raise NetworkError(f"ERROR: Overlapping interfaces in '{arg.port}'")

                self.connectors.append(arg)

            # For Loopbacks
            elif isinstance(arg, Loopback):
                arg.port = len(self.loopbacks)
                self.loopbacks.append(arg)

    # Adds a couple of interfaces to the list
    def pop(self, inf: str | Connector | Loopback):
        if isinstance(inf, str):  # If it is a port number
            inf = self[inf]

        if isinstance(inf, Connector):
            self.connectors.remove(inf)
        elif isinstance(inf, Loopback):
            popped_index = self.loopbacks.index(inf)
            self.loopbacks.remove(inf)

            for index, loopback in enumerate(self.loopbacks[popped_index:]):
                loopback.port = index + popped_index

        return inf

    def clear(self) -> None:
        self.connectors.clear()
        self.loopbacks.clear()

    def show(self):
        return "\n".join(str(inf) for inf in self.connectors + self.loopbacks)
