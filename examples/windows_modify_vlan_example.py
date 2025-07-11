# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Simple example of usage."""
import logging

from mfd_connect import RPyCConnection
from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


conn = RPyCConnection(ip="10.10.10.10")
owner = WindowsNetworkAdapterOwner(connection=conn)


def windows_modify_vlan():
    vlan_id, new_vlan_id = 191, 192
    team_name="AddRemoveVLANsTeam"
    interfaces=owner.get_interfaces(interface_names=["SLOT 2 Port 1"])
    new_vlan_name=f"VLAN{new_vlan_id}"
    logger.info("Creating NIC team")
    owner.ans.create_nic_team(
        interfaces=interfaces,
        team_name=team_name,
        teaming_mode="AdaptiveLoadBalancing",
    )
    owner.vlan.create_vlan(vlan_id=vlan_id, method="proset", interface_name=team_name)
    logger.info("Modifying vlan")
    owner.vlan.modify_vlan(vlan_id=vlan_id, nic_team_name=team_name,new_vlan_id=new_vlan_id, new_vlan_name=new_vlan_name)
    logger.info("Removing the NIC team")
    owner.ans.remove_nic_team(team_name=team_name)


if __name__ == "__main__":
    windows_modify_vlan()
