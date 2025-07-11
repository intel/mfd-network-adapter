# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Bonding Example."""
import logging
from ipaddress import IPv4Interface

from mfd_common_libs import log_levels, add_logging_group, LevelGroup
from mfd_connect import RPyCConnection

from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner
from mfd_network_adapter.network_interface.feature.link import LinkState

logger = logging.getLogger(__name__)
logging.basicConfig(level=log_levels.MODULE_DEBUG)

add_logging_group(LevelGroup.MFD)
add_logging_group(LevelGroup.TEST)

conn = RPyCConnection(ip="10.10.10.10")
owner = LinuxNetworkAdapterOwner(connection=conn)

interfaces = owner.get_interfaces()


child_interface = None

for interface in interfaces:
    if interface.name == "eth1":
        logger.info(f"Interface name: {interface.name}")
        logger.info(f"Link status: {interface.link.get_link()}")
        child_interface = interface

if not child_interface:
    logger.info("No interface found!")


bonding_interface_name = "bond0"

logger.info(f"Bond interfaces: {owner.bonding.get_bond_interfaces()}")
logger.info(f"Load module: {owner.bonding.load()}")

logger.info(f"Create Bond interface")
bond_interface = owner.bonding.create_bond_interface(bonding_interface_name)
logger.info(f"Create Bond interface: {bond_interface.name}")

logger.info(f"Bond interfaces: {owner.bonding.get_bond_interfaces()}")

logger.info(f"IPv4")
ipv4 = IPv4Interface("10.10.10.10")

logger.info(f"Add IPv4")
bond_interface.ip.add_ip(ipv4)

logger.info(f"Set bond interface up")
bond_interface.link.set_link(LinkState.UP)

logger.info(
    f"Connect interface {child_interface.name} to bond interface: {bond_interface.name}: "
    f"{owner.bonding.connect_interface_to_bond(child_interface, bond_interface)}"
)
logger.info(f"Set active child: {owner.bonding.set_active_child(bond_interface, child_interface)}")
logger.info(f"Get active child: {owner.bonding.get_active_child(bond_interface)}")
logger.info(f"Get bonding mode: {owner.bonding.get_bonding_mode(bond_interface)}")
logger.info(
    f"Verify active child {child_interface.name}: {owner.bonding.verify_active_child(bond_interface, child_interface)}"
)
