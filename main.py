from components.devices.device_creator import cisco_7200
from components.topologies.autonomous_system.backbone import Backbone
from components.devices.network_device import NetworkDevice

backbone = Backbone(9000,
                    "Fiber@Home",
                    [
                        cisco_7200("1.1.1.1", "R1"),
                        cisco_7200("2.2.2.2", "R2"),
                        cisco_7200("3.3.3.3", "R3"),
                        cisco_7200("4.4.4.4", "R4")
                    ])

backbone.connect_internal_devices("1.1.1.1", "0/0", "2.2.2.2", "0/0",
                                  "10.1.1.0")
backbone.connect_internal_devices("2.2.2.2", "0/1", "3.3.3.3", "0/0",
                                  "10.1.2.0")
backbone.connect_internal_devices("3.3.3.3", "0/1", "4.4.4.4", "0/0",
                                  "10.1.3.0")
backbone.connect_internal_devices("4.4.4.4", "0/1", "1.1.1.1", "0/1",
                                  "10.1.4.0")

[router.begin_internal_routing(mpls_ldp_sync=True) for router in backbone.get_all_routers()]

NetworkDevice.print_script(backbone.get_device("1.1.1.1").generate_script())
