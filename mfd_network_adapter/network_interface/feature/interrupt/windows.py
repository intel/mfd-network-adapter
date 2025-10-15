# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Interrupt feature for Windows."""

import logging
import time
import re
from typing import TYPE_CHECKING, Tuple

from mfd_common_libs import add_logging_level, log_levels
from mfd_win_registry import WindowsRegistry
from mfd_network_adapter.data_structures import State
from .data_structures import (
    InterruptInfo,
    InterruptModerationRate,
    InterruptMode,
    ITRValues,
    INT_RATE_CONVERSIONS,
    MAX_INTERRUPTS_PER_S,
    StatusToQuery,
)
from .const import timestamp_data_pattern
from mfd_const import Speed
from mfd_network_adapter.network_interface.feature.utils.base import BaseFeatureUtils
from mfd_network_adapter.network_interface.feature.ip.data_structures import IPFlag
from mfd_typing.utils import strtobool
from mfd_typing.network_interface import InterfaceType
from mfd_devcon import Devcon

from ..link import LinkState
from ...exceptions import InterruptFeatureException

from .base import BaseFeatureInterrupt

try:
    from mfd_const_internal import DEVICE_IDS
except ImportError:
    from mfd_const import DEVICE_IDS

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsInterrupt(BaseFeatureInterrupt):
    """Windows class for Interrupt feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Windows Interrupt feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._win_registry = WindowsRegistry(connection=self._connection)
        self._devcon = Devcon(connection=self._connection)

    def set_interrupt_moderation(self, enabled: State) -> None:
        """Set Interrupt Moderation (Coalescence) enable/disable setting.

        :param enabled: enable/disable setting
        """
        feature_value = "1" if enabled is State.ENABLED else "0"
        self._win_registry.set_feature(
            interface=self._interface().name, feature=InterruptInfo.INTERRUPT_MODERATION, value=feature_value
        )
        self._interface().link.set_link(LinkState.DOWN)
        time.sleep(1)
        self._interface().link.set_link(LinkState.UP)

    def get_interrupt_moderation(self) -> str:
        """Get interrupt moderation value.

        :raises InterruptFeatureException: If feature is not present
        """
        feature_value = self._win_registry.get_feature_list(interface=self._interface().name)
        value = feature_value.get(InterruptInfo.INTERRUPT_MODERATION)
        if not value:
            raise InterruptFeatureException(
                f"InterruptModeration is not present for interface: {self._interface().name}"
            )
        return value

    def get_num_interrupt_vectors(self) -> int:
        """Get number of interrupt vectors per interface.

        :return: num interrupts
        :raises InterruptFeatureException: If NetAdapterHardwareInfo not present
        """
        cmd = f"(Get-NetAdapterHardwareInfo -Name '{self._interface().name}').NumMsixTableEntries"
        result = self._connection.execute_powershell(cmd, expected_return_codes={0}).stdout
        if not result:
            raise InterruptFeatureException(
                f"Couldn't find NumMsixTableEntries field for interface: {self._interface().name}"
            )
        return int(result.strip())

    def get_interrupt_moderation_rate(self) -> str:
        """Get interrupt moderation rate value.

        :return Interrupt Moderation Rate value
        :raises InterruptFeatureException: If feature is not present
        """
        feature_value = self._win_registry.get_feature_list(interface=self._interface().name)
        value = feature_value.get(InterruptInfo.INTERRUPT_MODERATION_RATE)
        if not value:
            raise InterruptFeatureException(
                f"InterruptModerationRate is not present for interface: {self._interface().name}"
            )
        return value

    def set_interrupt_moderation_rate(self, setting: InterruptModerationRate) -> None:
        """Set interrupt moderation rate value.

        :param setting: value to set
        """
        feature = InterruptInfo.INTERRUPT_MODERATION_RATE
        feature_enum = self._win_registry.get_feature_enum(self._interface().name, feature)
        feature_enum = {v: k for k, v in feature_enum.items()}
        feature_value = feature_enum[setting.value]
        self._win_registry.set_feature(self._interface().name, feature=feature, value=feature_value)
        self._interface().link.set_link(LinkState.DOWN)
        time.sleep(1)
        self._interface().link.set_link(LinkState.UP)

    def set_adaptive_interrupt_mode(self, mode: State) -> None:
        """Set adaptive interrupt mode.

        :param mode: enabled or disabled
        """
        if mode is State.ENABLED:
            self.set_interrupt_moderation_rate(InterruptModerationRate.ADAPTIVE)
        else:
            self.set_interrupt_moderation_rate(InterruptModerationRate.OFF)

    def get_interrupt_mode(self) -> Tuple[InterruptMode, int | None]:
        """Get interrupt mode.

        :return interrupt mode
        """
        cmd = (
            r"(get-itemproperty -path 'hklm:\system\CurrentControlSet\enum"
            rf"\{self._interface().pnp_device_id}\Device"
            r" Parameters\Interrupt Management\MessageSignaledInterruptProperties')"
        )
        MSISupported = int(self._connection.execute_powershell(f"{cmd}.MSISupported", expected_return_codes={0}).stdout)
        MessageNumberLimit = int(
            self._connection.execute_powershell(f"{cmd}.MessageNumberLimit", expected_return_codes={0}).stdout
        )

        if MSISupported == 0:
            return InterruptMode.LEGACY, None

        if MessageNumberLimit == 1:
            return InterruptMode.MSI, None
        elif MessageNumberLimit > 1:
            return InterruptMode.MSIX, MessageNumberLimit
        else:
            return InterruptMode.MSIX, None

    def get_expected_max_interrupts(self, itr_val: ITRValues, virtual: bool = False) -> int:
        """Get expected maximum number of interrupts.

        :param itr_value: ITR value
        :param virtual: True/False based on interface
        :return int: max interrupts value
        """
        itr_val_num = INT_RATE_CONVERSIONS[itr_val.value]
        if itr_val_num == 0:
            if BaseFeatureUtils.is_speed_eq(self, Speed.G10):
                if not virtual:
                    if self._get_lro():
                        return MAX_INTERRUPTS_PER_S["10g_adapter_lro_on"]
                return MAX_INTERRUPTS_PER_S["10g_adapter"]
            return MAX_INTERRUPTS_PER_S["default"]

        # For Windows the value programmed to the hardware is actually bit shifted right
        # three places rather than using the value directly from the INF.
        itr_val_num = int(itr_val_num) >> 3

        # In Windows, adapters before CPK define ITR in increments of 2 usecs
        granularity = 1.0
        if not BaseFeatureUtils.is_speed_eq(self, Speed.G100):
            granularity = 2.0

        # According to the EAS, this is the formula for interrupts per second:
        #     1 second / (itr_val * usecs * granularity)
        expected_max_ints = 1.0 / (float(itr_val_num) * 0.000001 * granularity)

        # Return an int because the exactness is not important
        return int(expected_max_ints)

    def _get_lro(self) -> bool:
        """Get LRO/RSC feature setting."""
        # check if RSC is affected by winpcap/npcap installation.. If either one is installed
        # RSC will not be operational (obtained through OperationalState) and is considered
        # disabled
        is_operational = self.get_rsc_operational_enabled(
            ip_flag=IPFlag.IPV4, status_to_query=StatusToQuery.OPERATIONALSTATE
        )
        # if Get-NetAdapterRsc command doesn't work, query RSC status through old method
        # of get_feature and verify_if_feature_is_not_supported
        if not is_operational:
            output = self._win_registry.get_feature_list(self._interface().name)
            value = output.get(InterruptInfo.LARGE_RECEIVE_OFFLOAD_IPV4)
            # if the result of _get_feature_list returns a 1, that means lro is enabled on the adapter
            return "1" == value
        # if RSC is operational, check whether RSC is enabled or not (via Get-RSC Enabled)
        return self.get_rsc_operational_enabled(ip_flag=IPFlag.IPV4, status_to_query=StatusToQuery.ENABLED)

    def get_rsc_operational_enabled(self, ip_flag: IPFlag, status_to_query: StatusToQuery) -> bool:
        """Get the RSC/LRO operational state or enabled status through Get-NetAdapterRsc cmdlet.

        :param ip_flag: ip version to check
        :param status_to_query: used to determine what status to get
        :raises InterruptFeatureException if Get-NetAdapterRsc fails
        :return bool: True or False
        """
        cmd = (
            f"Get-NetAdapterRsc -Name '{self._interface().name}' | Select {ip_flag}{status_to_query} | ft "
            "-HideTableHeaders"
        )
        try:
            result = self._connection.execute_powershell(cmd, expected_return_codes={0}).stdout
            return strtobool(result)
        except Exception:
            raise InterruptFeatureException("Unable to execute Get-NetAdapterRsc")

    def check_itr_value_set(self, expected_value: int) -> bool:
        """
        Check if ITR is set correctly.

        The OID_INTEL_CURRENT_ITR  value is not supported on VF,
        they will not show up as a value in the OID tool
        ITR value is checked for PF only

        :param expected_value: expected ITR value
        :return: True if match found
        :raises InterruptFeatureException: if 40g adapters and expected value not matched
        """
        current_type = self._interface().interface_type
        if current_type != InterfaceType.GENERIC:
            raise InterruptFeatureException("OID_INTEL_CURRENT_ITR value is supported only on Generic Interface")

        if BaseFeatureUtils.is_speed_eq(self, Speed.G40):
            raise InterruptFeatureException(
                "40g adapters do not support OID_INTEL_CURRENT_ITR so this check is skipped"
            )

        stat = self._interface().stats.get_stats(["OID_INTEL_CURRENT_ITR"])
        actual_value = int(stat["OID_INTEL_CURRENT_ITR"])

        if actual_value != expected_value:
            raise InterruptFeatureException("Expected value is not matching.")

        return True

    def get_per_queue_interrupts_per_sec(self, interval: int = 5, samples: int = 5) -> dict[str, int]:
        """
        Get the adapter per queue interrupts per second data.

        :param interval: sample interval in seconds
        :param samples: number of samples to get from each counter
        :return: dictionary where key=counter name and value=per second interrupts
        """
        card_name = self._interface().branding_string
        perf_counter = rf"\Per Processor Network Interface Card Activity(*, {card_name})\Interrupts/sec"
        perf_data = self._get_performance_collection(perf_counter, interval=interval, samples=samples)
        return self._parse_performance_collection(perf_data)

    def _get_performance_collection(self, counter: str, interval: int, samples: int) -> dict[str, dict[str, str]]:
        """
        Get performance counter data for a set of counters.

        :param counter: performance counter path
        :param interval: sample interval in seconds
        :param samples: number of samples to get from each counter
        :return: dictionary of counter name and per second interrupts
        """
        cmd_params = f"-MaxSamples {str(samples)} -SampleInterval {str(interval)}"
        cmd = f"Get-counter -Counter '{counter}' {cmd_params} | Format-List"
        cmd_output = self._connection.execute_powershell(cmd, expected_return_codes={0}).stdout
        stats = {}
        for match in timestamp_data_pattern.finditer(cmd_output):
            result = match.groupdict()
            ts = result["timestamp"]
            content = result["content"]
            lines = re.split(r"^\s+$", content.split("Readings  :")[-1], flags=re.MULTILINE)
            lines.pop()
            for line in lines:
                item = re.sub(r"\n\s+", "", line)
                key_val = item.split(" :")
                if not key_val:
                    continue
                stat_name = bytes(key_val[0], "utf-8").decode("unicode_escape")
                val = key_val[1].replace("\n", "")
                stats.setdefault(stat_name, {})[ts] = val
        return stats

    def _parse_performance_collection(self, raw_perf_data: dict[str, dict[str, str]]) -> dict[str, float]:
        """
        Parse the raw data from get_performance_collection and calculate mean/average the data.

        :param raw_perf_data: raw data from _get_performance_collection
        :return: parsed data
        """
        data_dict = {}
        for key in sorted(raw_perf_data):
            new_key = key.strip()[key.strip().find("(") + 1 :].replace(")\\", "_")
            data_dict[new_key] = self._mean_data(raw_perf_data[key])
        return data_dict

    def _mean_data(self, time_data_dict: dict[str, str]) -> float:
        """
        Calculate the mean/average data for a Windows performance counter dictionary.

        :param time_data_dict: Key value from the performance dictionary
        :return: mean value
        """
        data_len = len(time_data_dict)
        if data_len == 0:
            return 0.0

        total = sum(float(value) for value in time_data_dict.values())
        return total / data_len

    def set_interrupt_mode(self, mode: InterruptMode, interrupt_limit: int | None = None) -> None:
        """
        Set interrupt mode for the interface.

        :param InterruptMode: interrupt mode to set
        :param interrupt_limit: maximum number of MSIs to allocate. Overrides predefined settings.\
                Must be None for MSI or Legacy modes.
        """
        if mode not in self._get_supported_interrupt_modes():
            raise InterruptFeatureException(
                f"Not supported interrupt mode: {mode} Supported modes are {self._get_supported_interrupt_modes()}"
            )

        if mode is InterruptMode.MSIX:
            msg_num_limit = 33 if interrupt_limit is None else interrupt_limit
            msi_supported = 1
        elif mode is InterruptMode.MSI:
            msg_num_limit = 1
            msi_supported = 1
        else:
            msg_num_limit = 1
            msi_supported = 0

        path = (
            rf"hklm:\system\CurrentControlSet\enum\{self._interface().pnp_device_id}\Device "
            r"Parameters\Interrupt Management\MessageSignaledInterruptProperties"
        )

        try:
            self._win_registry.set_itemproperty(path=path, name="MessageNumberLimit", value=str(msg_num_limit))
            self._win_registry.set_itemproperty(path=path, name="MSISupported", value=str(msi_supported))
        except Exception:
            raise InterruptFeatureException(
                f"Can't set interrupt mode to ({mode}, {interrupt_limit}) on {self._interface().name}"
            )

        self._interface().link.set_link(LinkState.DOWN)
        time.sleep(1)
        self._interface().link.set_link(LinkState.UP)

        # verify IRQs settings
        irqs = self._devcon.get_resources(device_id=self._interface().pnp_device_id, resource_filter="irq")
        if not irqs:
            raise InterruptFeatureException("No IRQs assigned to the interface")

        irq_count = str(irqs).count("IRQ")
        if mode == InterruptMode.MSIX:
            min_mode = 2
        else:
            min_mode = 1
        if irq_count < min_mode:
            raise InterruptFeatureException("Number of IRQs assigned mismatch")

    def _get_supported_interrupt_modes(self) -> list[InterruptMode]:
        """
        Get interrupt modes supported by the interface.

        :return: supported interrupt modes, combination of 'msix', 'msi', 'legacy'
        """
        # For CPK MSI-X is only supported and all modes are supported for rest by default
        if f"0x{self._interface().pci_device.device_id}" in DEVICE_IDS["CPK"]:
            return [InterruptMode.MSIX]
        else:
            return [InterruptMode.MSIX, InterruptMode.MSI, InterruptMode.LEGACY]
