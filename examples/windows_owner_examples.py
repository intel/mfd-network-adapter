# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Simple example of usage Window Owner features."""
import logging
from ipaddress import IPv4Interface

from mfd_connect import RPyCConnection

from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_adapter_owner.data_structures import DefInOutBoundActions
from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


conn = RPyCConnection(ip="10.10.10.10")
owner = WindowsNetworkAdapterOwner(connection=conn)


def owner_test_arp_feature():
    """Example of read_arp() and read_ndp_neighbors() usage from ARP feature."""
    owner.arp.read_arp_table()
    owner.arp.read_ndp_neighbors(ip=IPv4Interface("10.10.10.1"))


def owner_test_firewall_feature():
    """Example of set_firewall_default_action and set_firewall_profile."""
    owner.firewall.set_firewall_default_action(
        profile=["Domain", "Public", "Private"],
        def_inbound_action=DefInOutBoundActions.ALLOW,
        def_outbound_action=DefInOutBoundActions.ALLOW,
    )
    owner.firewall.set_firewall_profile(profile=["Domain", "Public", "Private"], enabled=State.ENABLED)


def test_change_state_family_interfaces():
    """Example of usage change_state_family_interfaces()"""
    owner.driver.change_state_family_interfaces(driver_filename="v40e65.sys", enable=State.ENABLED)
    owner.driver.change_state_family_interfaces(driver_filename="v40e65.sys", enable=State.DISABLED)


def owner_test_link_aggregation_feature():
    teams = owner.link_aggregation.get_nic_teams()
    logger.log(level=logging.INFO, msg=f"List of NIC Teams: {teams}")
    new_nic_team_name = "TeamBlue"
    interfaces = owner.get_interfaces(interface_names=["Ethernet 9"])
    owner.link_aggregation.create_nic_team(interfaces, new_nic_team_name)
    teams = owner.link_aggregation.get_nic_teams()
    logger.log(level=logging.INFO, msg=f"List of NIC Teams after creating new one: {teams}")
    interface = owner.get_interfaces(interface_names=["Ethernet 10"])[0]
    interface.nic_team.add_interface_to_nic_team(new_nic_team_name)
    owner.link_aggregation.get_nic_team_interfaces(team_name=new_nic_team_name)
    owner.link_aggregation.wait_for_nic_team_status_up(team_name=new_nic_team_name, count=3)
    owner.link_aggregation.remove_nic_team(new_nic_team_name)
