from components.devices.device_creator import cisco_xr_9000, cisco_7200
from components.topologies.autonomous_system.backbone import Backbone

backbone = Backbone(9000,
                    "Fiber@Home",
                    [
                        cisco_xr_9000("1.1.1.1", "R1"),
                        cisco_7200("2.2.2.2", "R2"),
                        cisco_7200("3.3.3.3", "R3"),
                        cisco_7200("4.4.4.4", "R4")
                    ])

backbone.connect_devices("1.1.1.1", "0/0/0/0", "2.2.2.2", "0/0")
backbone.connect_devices("2.2.2.2", "0/1", "3.3.3.3", "0/0")
backbone.connect_devices("3.3.3.3", "0/1", "4.4.4.4", "0/0")
backbone.connect_devices("4.4.4.4", "0/1", "1.1.1.1", "0/0/0/1")

backbone.show_topology_graph("circular")

