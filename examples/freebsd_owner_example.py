# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from ipaddress import IPv4Interface

from mfd_connect import RPyCConnection
from mfd_network_adapter.network_adapter_owner.freebsd import FreeBSDNetworkAdapterOwner

owner = FreeBSDNetworkAdapterOwner(connection=RPyCConnection("10.10.10.1"))

# vxlan feature example
vxlan_created = owner.vxlan.create_setup_vxlan(
    local_ip_addr=IPv4Interface("10.10.10.10/24"),
    vni=40,
    group_addr=IPv4Interface("10.10.10.10"),
    interface_name="ixl0",
    vxlan_ip_addr=IPv4Interface("10.10.10.10/24"),
)
print(vxlan_created)
"""Output: vxlan10"""
owner.vxlan.delete_vxlan(vxlan_name="vxlan10")
