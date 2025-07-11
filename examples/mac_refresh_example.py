# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""MAC refresh example."""
import logging

from mfd_common_libs import log_levels
from mfd_connect import RPyCConnection
from mfd_typing import MACAddress

from mfd_network_adapter import NetworkAdapterOwner

logger = logging.getLogger(__name__)
logging.basicConfig(level=log_levels.MODULE_DEBUG)

host_ip = "1.1.1.1"
interface_name = "eth1"
mac_to_be_set = MACAddress("00:00:00:00:00:00")
connection = RPyCConnection(ip=host_ip)
owner = NetworkAdapterOwner(connection=connection)

logger.log(log_levels.MODULE_DEBUG, "1. Create interface")
nic = [x for x in owner.get_interfaces() if x.name == interface_name][0]

logger.log(log_levels.MODULE_DEBUG, "2. Read MAC address")

if nic.mac_address != mac_to_be_set:
    logger.log(log_levels.MODULE_DEBUG, "3. Set new MAC address")
    owner.mac.set_mac(interface_name=nic.name, mac=mac_to_be_set)
    logger.log(log_levels.MODULE_DEBUG, "4. Refresh interface object")
    # in mfd_host, in Host object there is a refresh_network_interfaces() method available
    nic = [x for x in owner.get_interfaces() if x.name == interface_name][0]
    logger.log(log_levels.MODULE_DEBUG, "5. Read new MAC address and check if it is correctly set")
    assert (
        nic.mac_address == mac_to_be_set
    ), f"MAC address is not set correctly. Expected: {mac_to_be_set}, Actual: {nic.mac_address}"

else:
    logger.log(log_levels.MODULE_DEBUG, "3. Correct MAC address is already set")
