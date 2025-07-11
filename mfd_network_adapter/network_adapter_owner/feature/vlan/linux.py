# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for VLAN feature for Linux systems."""

import logging
import re
from typing import TYPE_CHECKING, Optional

from mfd_common_libs import add_logging_level, log_levels
from mfd_connect.base import ConnectionCompletedProcess
from mfd_kernel_namespace import add_namespace_call_command
from mfd_package_manager import LinuxPackageManager
from mfd_typing import MACAddress

from .base import BaseVLANFeature
from ...exceptions import VLANFeatureException

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_adapter_owner.base import NetworkAdapterOwner

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxVLAN(BaseVLANFeature):
    """Linux class for VLAN feature."""

    def __init__(self, *, connection: "Connection", owner: "NetworkAdapterOwner"):
        """
        Initialize LinuxVLAN class.

        :param connection: Object of mfd-connect
        :param owner: Owner object, parent of feature
        """
        super().__init__(connection=connection, owner=owner)
        # TODO: think about some ref to host,
        # TODO: if host ref present we should use driver feature with already created package manager object
        _package_manager = LinuxPackageManager(connection=self._connection)
        if not _package_manager.is_module_loaded("8021q"):
            _package_manager.load_module("8021q")

    def create_vlan(
        self,
        vlan_id: int,
        interface_name: str,
        vlan_name: Optional[str] = None,
        protocol: Optional[str] = None,
        reorder: bool = True,
        namespace_name: Optional[str] = None,
    ) -> ConnectionCompletedProcess:
        """
        Create VLAN with desired ID on interface.

        :param vlan_id: ID for VLAN.
        :param interface_name: Network interface name.
        :param vlan_name: Name for VLAN interface, if not specified default named as '<interface_name>.<vlan_id>'.
        :param protocol: Specify '802.1ad' or '802.1Q' protocol type.
        :param reorder: Specifies whether ethernet headers are reordered or not.
        :param namespace_name: Namespace of VLAN
        :return: Result of creating VLAN.
        """
        protocol = f" protocol {protocol}" if protocol else ""
        reorder = " reorder_hdr off" if not reorder else ""
        vlan_name = vlan_name if vlan_name else f"{interface_name}.{vlan_id}"

        command = f"ip link add link {interface_name} name {vlan_name} type vlan{protocol} id {vlan_id}{reorder}"
        return self._connection.execute_command(
            add_namespace_call_command(command, namespace=namespace_name), expected_return_codes={0}, shell=True
        )

    def remove_vlan(
        self,
        vlan_name: Optional[str] = None,
        vlan_id: Optional[int] = None,
        interface_name: Optional[str] = None,
        namespace_name: Optional[str] = None,
    ) -> ConnectionCompletedProcess:
        """
        Remove desired VLAN.

        :param vlan_name: Name of existing VLAN interface.
        :param vlan_id: ID of VLAN to remove.
        :param interface_name: Network interface name.
        :param namespace_name: Namespace of VLAN
        :return: Result of removing VLAN.
        """
        vlan_name = vlan_name if vlan_name else f"{interface_name}.{vlan_id}"
        return self._connection.execute_command(
            add_namespace_call_command(f"ip link del {vlan_name}", namespace=namespace_name),
            expected_return_codes={0},
            shell=True,
        )

    def remove_all_vlans(self) -> None:
        """Remove all VLANs from interface."""
        result = self._connection.execute_command("ls /proc/net/vlan", expected_return_codes={0, 2}, shell=True)
        vlans = sorted(
            [vlan_name.strip() for vlan_name in result.stdout.split() if "config" not in vlan_name], reverse=True
        )
        for vlan_name in vlans:
            self.remove_vlan(vlan_name=vlan_name)

    def create_macvlan(self, interface_name: str, mac: MACAddress, macvlan_name: str) -> ConnectionCompletedProcess:
        """Create MACVLAN on interface.

        :param interface_name: Network interface name.
        :param mac: MAC address to set on new interface.
        :param macvlan_name: name of new macvlan interface.
        :return: Result of creating MACVLAN.
        """
        command = f"ip link add link {interface_name} name {macvlan_name} address {str(mac)} type macvlan"
        return self._connection.execute_command(command, expected_return_codes={0}, shell=True)

    def set_ingress_egress_map(
        self, interface_name: str, priority_map: str, direction: str, verify: bool = True
    ) -> None:
        """
        Set and verify ingress/egress map.

        :param interface_name: Network interface name.
        :param priority_map: Priority map, for example: 0:0 1:1 2:2 3:3 4:4 5:5 6:6 7:7
        :param direction: Mapping direction - can be 'ingress', 'egress' or 'both'.
        :param verify: Determines whether verification should be performed.
        :raises VLANFeatureException: When invalid mapping direction provided.
        """
        if direction not in ["egress", "ingress", "both"]:
            raise VLANFeatureException(f"Invalid mapping direction value: '{direction}'")

        direction = ["ingress", "egress"] if direction == "both" else [direction]
        for _dir in direction:
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"Set {_dir} map ({priority_map}) on the {interface_name} interface.",
            )
            self._connection.execute_command(
                f"ip link set {interface_name} type vlan {_dir} {priority_map}",
                expected_return_codes={0},
                shell=True,
            )
            if verify and not self._verify_ingress_egress_map(
                priority_map=priority_map, direction=_dir, interface_name=interface_name
            ):
                raise VLANFeatureException(f"Cannot properly set {_dir} map")

    def _verify_ingress_egress_map(self, interface_name: str, priority_map: str, direction: str) -> bool:
        """
        Verify ingress/egress map.

        :param interface_name: Network interface name.
        :param priority_map: Priority map, for example: 0:0 1:1 2:2 3:3 4:4 5:5 6:6 7:7
        :param direction: Mapping direction - can be 'ingress', 'egress' or 'both'.
        :return: True if provided map is set, False otherwise.
        """
        result = self._connection.execute_command(
            f"cat /proc/net/vlan/{interface_name}", expected_return_codes={0}, shell=True
        )
        pattern = rf" *{direction.upper()}.*$"
        try:
            if priority_map.split() != re.findall(pattern, result.stdout, re.MULTILINE)[0].split()[3:]:
                return False
        except IndexError:
            return False
        return True
