# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Virtualization feature for Windows."""

import logging

from mfd_common_libs import add_logging_level, log_levels
from mfd_typing.network_interface import InterfaceType
from mfd_typing.utils import strtobool

from mfd_network_adapter.network_interface.exceptions import (
    VirtualizationFeatureNotFoundError,
    VirtualizationNotSupportedError,
)
from mfd_network_adapter.network_interface.feature.virtualization import BaseFeatureVirtualization

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsVirtualization(BaseFeatureVirtualization):
    """Windows class for Virtualization feature."""

    def set_sriov(self, sriov_enabled: bool, no_restart: bool = False) -> None:
        """
        Set network interface SRIOV.

        :param sriov_enabled: adapter SRIOV status value to be set.
        :param no_restart: whether to restart adapter after changing its settings.
        """
        action = "Enable" if sriov_enabled else "Disable"
        restart = " -NoRestart" if no_restart else ""
        self._connection.execute_powershell(f'{action}-NetAdapterSriov -Name "{self._interface().name}"{restart}')

    def set_vmq(self, vmq_enabled: bool, no_restart: bool = False) -> None:
        """
        Set network interface VMQ.

        :param vmq_enabled: adapter VMQ status value to be set.
        :param no_restart: whether to restart adapter after changing its settings.
        """
        action = "Enable" if vmq_enabled else "Disable"
        restart = " -NoRestart" if no_restart else ""
        self._connection.execute_powershell(f'{action}-NetAdapterVmq -Name "{self._interface().name}"{restart}')

    def is_vmq_enabled(self) -> bool:
        """
        Check VMQ is enabled on PF.

        :return: bool confirmation that VMQ is enabled or not.
        :raises: FeatureNotFoundError when cannot verify that feature is enabled.
        """
        if self._interface().interface_type != InterfaceType.PF:
            raise VirtualizationNotSupportedError(
                f"Calling {self.is_vmq_enabled.__name__} for {self._interface().name} is not supported,"
            )
        cmd = f"Get-NetAdapterVmq -Name '{self._interface().name}' | select -ExpandProperty Enabled"
        res = self._connection.execute_powershell(cmd, expected_return_codes={0}).stdout
        if not res:
            raise VirtualizationFeatureNotFoundError(
                "Could not find looking for field for verifying that VMQ is enabled."
            )
        return strtobool(res.strip())

    def is_sriov_enabled(self) -> bool:
        """
        Check SRIOV is enabled on PF.

        :return: bool confirmation that SRIOV is enabled or not.
        :raises: FeatureNotFoundError when cannot verify that feature is enabled.
        """
        if self._interface().interface_type != InterfaceType.PF:
            raise VirtualizationNotSupportedError(
                f"Calling {self.is_sriov_enabled.__name__} for {self._interface().name} is not supported,"
            )
        cmd = f"(Get-NetAdapterSriov -Name '{self._interface().name}').Enabled"
        res = self._connection.execute_powershell(cmd, expected_return_codes={0}).stdout
        if not res:
            raise VirtualizationFeatureNotFoundError(
                "Could not find looking for field for verifying that SRIOV is enabled."
            )
        return strtobool(res.strip())

    def is_sriov_supported(self) -> bool:
        """
        Check SRIOV is enabled on PF.

        :return: bool confirmation that VMQ is enabled or not.
        :raises: FeatureNotFoundError when cannot verify that feature is supported.
        """
        if self._interface().interface_type != InterfaceType.PF:
            raise VirtualizationNotSupportedError(
                f"Calling {self.is_sriov_supported.__name__} for {self._interface().name} is not supported,"
            )
        cmd = f"(Get-NetAdapterSriov -Name '{self._interface().name}').SriovSupport"
        res = self._connection.execute_powershell(cmd, expected_return_codes={0}).stdout
        if not res:
            raise VirtualizationFeatureNotFoundError(
                "Could not find looking for field for verifying that SRIOV is supported."
            )
        return res.strip().casefold() == "supported"

    def enable_pf_npcap_binding(
        self,
    ) -> None:
        """Enable PF NPCAP after creating vSwitch."""
        self._connection.execute_powershell(
            f"Enable-NetAdapterBinding -Name '{self._interface().name}' -DisplayName 'Npcap Packet Driver (NPCAP)'",
            expected_return_codes={0},
        )
