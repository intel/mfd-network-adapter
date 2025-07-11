# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for NM feature for Linux systems."""

import logging

from mfd_common_libs import add_logging_level, log_levels

from mfd_network_adapter.data_structures import State
from .base import BaseNMFeature
from ...exceptions import NMFeatureCalledError, NMFeatureException

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxNM(BaseNMFeature):
    """Linux class for NM feature."""

    def remove_device(self, device: str) -> None:
        """
        Remove device from kernel managed device list.

        :param device: Device name to remove
        :raises NMFeatureCalledError: on failure to remove device
        """
        self.set_managed(device=device, state=State.DISABLED)

    def set_managed(self, device: str, state: State) -> None:
        """
        Change GENERAL.NM-MANAGED to the new state.

        :param device: Device name to set
        :param state: State.ENABLED - enable, DISABLED - disable managing interface by NM
        :raises NMFeatureCalledError: on failure to set device
        """
        state = "yes" if state is State.ENABLED else "no"
        # change to desired state
        self._connection.execute_command(
            f"nmcli device set {device} managed {state}", custom_exception=NMFeatureCalledError
        )

    def get_managed_state(self, device: str) -> State:
        """
        Get state of managed property.

        :param device: Device name to set
        :return: State of managed by network manager.
        :raises NMFeatureCalledError: on failure to get state
        :raises NMFeatureException: if found any error in command
        """
        command = f"nmcli -p -f general dev show {device} | grep GENERAL.NM-MANAGED | tr -s ' ' | cut -d ' ' -f 2"
        output = self._connection.execute_command(
            command, shell=True, custom_exception=NMFeatureCalledError, stderr_to_stdout=True
        ).stdout
        if "error" in output.casefold():
            raise NMFeatureException(f"Found error from network manager '{output}'")
        return State.ENABLED if output.rstrip() == "yes" else State.DISABLED

    def verify_managed(self, device: str, expected_state: State) -> bool:
        """
        Compare the value of the NetworkManager GENERAL.NM-MANAGED property expected one.

        :param device: Device name to verify
        :param expected_state: ENABLED - if we expect the parameter to be "yes", False if parameter should be "no"
        :return: True if parameter value is equal to expected, False if it is not
        :raises NMFeatureCalledError: on failure to get state of device
        :raises NMFeatureException: if found any error in command
        """
        nm_managed = self.get_managed_state(device)
        if nm_managed is expected_state:
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f'NetworkManager GENERAL.NM-MANAGED value is correct: "{nm_managed}"',
            )
            return True
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f'NetworkManager GENERAL.NM-MANAGED value is not correct: "{nm_managed}"',
        )
        return False

    def _glob_glob_method(self, path_to_search: str, search_string: str) -> list[str]:
        """
        Find path using search string.

        :param path_to_search: For linux/bsd root directory of search.
        :param search_string: String with or without wildcards to find entries.
        :return: List of strings with paths.
        # todo Issue#1
        """
        return self._connection.execute_command(f"find {path_to_search} -ipath '{search_string}'").stdout.splitlines()

    def prepare_adapter_config_file_for_network_manager(self, interface_name: str) -> None:
        """
        Create config file for interface.

        Config file for interface is needed, so after reboot VLAN interface is present on VM

        :param interface_name: Interface name
        :raises: RuntimeError: Host has other distribution than Red Hat
        """
        os = self._connection.get_system_info().os_name.lower()
        if "red hat" not in os:
            raise RuntimeError("Method does not work for OS other than Red Hat")

        result = self._glob_glob_method(
            path_to_search="/etc/sysconfig/network-scripts/", search_string=f"ifcfg-{interface_name}"
        )
        if result:
            return
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Create interface config file for interface ({interface_name}), "
            "so after reboot, IP address stays the same",
        )
        mng_adapter_config_file = (
            'TYPE="Ethernet"\n'
            'BOOTPROTO="dhcp"\n'
            'DEFROUTE="yes"\n'
            'IPV4_FAILURE_FATAL="no"\n'
            'IPV6INIT="yes"\n'
            'IPV6_AUTOCONF="yes"\n'
            'IPV6_DEFROUTE="yes"\n'
            'IPV6_FAILURE_FATAL="no"\n'
            f'NAME="{interface_name}"\n'
            f'DEVICE="{interface_name}"\n'
            'ONBOOT="yes"\n'
            'PEERDNS="yes"\n'
            'PEERROUTES="yes"\n'
            'IPV6_PEERDNS="yes"\n'
            'IPV6_PEERROUTES="yes"\n'
            'IPV6_PRIVACY="no"\n'
            'NM_CONTROLLED="no"\n'
        )

        self._connection.execute_command(
            f"echo '{mng_adapter_config_file}' > /etc/sysconfig/network-scripts/ifcfg-{interface_name}",
            expected_return_codes={0},
        )
