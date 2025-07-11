# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Offload feature for ESXI."""

import logging

from typing import TYPE_CHECKING
from mfd_common_libs import add_logging_level, log_levels
from ...exceptions import OffloadFeatureException
from .base import BaseFeatureOffload
from ...data_structures import State

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class EsxiOffload(BaseFeatureOffload):
    """ESXi class for Offload feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize ESXi Offload feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        # Define ESXi offload names per tool (esxcli and vsish)
        self.esxi_offload_names = {
            "tso": {"esxcli": "ipv4tso", "vsish": "CAP_TSO"},
            "tso6": {"esxcli": "ipv6tso", "vsish": "CAP_TSO6"},
            "tso6ext": {"esxcli": "ipv6tsoext", "vsish": "CAP_TSO6_EXT_HDRS"},
            "tso256k": {"esxcli": "CAP_TSO256k", "vsish": "CAP_TSO256k"},
            "cso": {"esxcli": "ipv4cso", "vsish": "CAP_IP_CSUM"},
            "cso6": {"esxcli": "ipv6cso", "vsish": "CAP_IP6_CSUM"},
            "geneve": {"esxcli": "geneveoffload", "vsish": "CAP_GENEVE_OFFLOAD"},
            "vxlan": {"esxcli": "vxlanencap", "vsish": "CAP_ENCAP"},
            "obo": {"esxcli": "obo", "vsish": "CAP_OFFSET_BASED_OFFLOAD"},
        }
        if self._interface().driver.get_driver_info().driver_name == "ixgben":
            self.esxi_offload_names["geneve"]["esxcli"] = "obo"
            self.esxi_offload_names["geneve"]["vsish"] = "CAP_OFFSET_BASED_OFFLOAD"

    def get_offload_name_for_tools(self, offload: str) -> dict[str, str]:
        """
        Get offload name for tools (esxcli or vsish).

        :param offload: Offload feature to get (tso|tso6|cso|cso6|geneve|vxlan|obo)
        :return: Dictionary with offload names for tools (esxcli and vsish)
        """
        offload = offload.lower()

        tool_ready_offload_names = self.esxi_offload_names.get(offload, None)
        if tool_ready_offload_names is None:
            raise OffloadFeatureException(f"Offload {offload} is not supported.")

        return tool_ready_offload_names

    def change_offload_setting(self, offload: str, enable: State = State.ENABLED) -> None:
        """
        Change HW offload setting on ESXi host.

        :param offload: Offload feature to change (tso|tso6|cso|cso6|geneve|vxlan|obo)
        :param enable: True to enable, False to disable.
        """
        esxcli_offload = self.get_offload_name_for_tools(offload)["esxcli"]

        # --<offload>=false -> turn off SW offload and use HW offload instead
        # --<offload>=true -> turn on SW offload and disable HW offload
        setting = "false" if enable.value else "true"

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Changing {offload} offload setting to {enable.value}")

        if offload == "tso256k":
            self.set_hw_capabilities(offload, enable)
        else:
            command = f"esxcli network nic software set -n {self._interface().name} --{esxcli_offload}={setting}"
            self._connection.execute_command(command=command)
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"{offload} offload setting changed successfully.")

    def check_offload_setting(self, offload: str) -> bool:
        """
        Check if HW offload setting is enabled on ESXi host.

        :param offload: Offload feature to check (tso|tso6|cso|cso6|geneve|vxlan|obo)
        :return: True if HW offload is enabled, False otherwise.
        """
        output = self._get_hw_capabilities(offload)

        if any(status in output for status in ["0", "1"]):
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"{offload} offload status - {'enabled' if '1' in output else 'disabled'}.",
            )
            return "1" in output
        else:
            raise RuntimeError(f"Cannot find information by vsish about offload {offload} setting.")

    def set_hw_capabilities(self, offload: str, enable: State) -> None:
        """
        Set hardware capabilities for offload on PF.

        :param offload: Offload feature to change (tso|tso6|cso|cso6|geneve|vxlan|obo)
        :param enable: 1 to enable, 0 to disable.
        """
        vsish_offload = self.get_offload_name_for_tools(offload)["vsish"]
        command = f"vsish -e set /net/pNics/{self._interface().name}/hwCapabilities/{vsish_offload} {int(enable.value)}"
        self._connection.execute_command(command=command, expected_return_codes={0, 2})
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"{offload} hwCapabilities on PF set to {enable}.")

    def _get_hw_capabilities(self, offload: str) -> str:
        """
        Get hardware capabilities for offload on PF.

        :param offload: Offload feature to get (tso|tso6|cso|cso6|geneve|vxlan|obo)
        :return: '1' if enabled, '0' if disabled.
        """
        vsish_offload = self.get_offload_name_for_tools(offload)["vsish"]
        command = f"vsish -e get /net/pNics/{self._interface().name}/hwCapabilities/{vsish_offload}"
        return self._connection.execute_command(command=command, expected_return_codes={0}).stdout
