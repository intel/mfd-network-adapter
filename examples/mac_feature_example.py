# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""MAC Feature examples."""
from mfd_connect import RPyCConnection
from mfd_typing import MACAddress

from mfd_network_adapter import NetworkAdapterOwner

ip = "1.1.1.1"
connection = RPyCConnection(ip=ip)

owner = NetworkAdapterOwner(connection=connection)

nics = owner.get_interfaces()
interface_under_test = nics[0]
print(interface_under_test)
print(interface_under_test.mac.get_multicast_mac_number())

mac_address = MACAddress("00:00:00:00:00:00")
owner.mac.set_mac(interface_name=interface_under_test.name, mac=mac_address)
owner.mac.delete_mac(interface_name=interface_under_test.name, mac=mac_address)
print(owner.mac.get_default_mac(interface_name=interface_under_test.name))
owner.mac.set_mac_for_vf(interface_name=interface_under_test.name, vf_index=0, mac_address=mac_address)
