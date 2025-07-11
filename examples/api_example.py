# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from mfd_connect import RPyCConnection

from mfd_network_adapter.api.basic.linux import get_mac_address

connection = RPyCConnection(ip="...")
get_mac_address(connection, interface_name="eth1", namespace="ns1")
