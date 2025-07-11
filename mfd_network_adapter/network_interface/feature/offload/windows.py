# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Offload feature for Windows."""

import logging
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_win_registry import WindowsRegistry

from .base import BaseFeatureOffload
from .data_structures import OFFLOAD_SETTINGS_MAP, RxTxOffloadSetting, OFFLOAD_DESCRIPTION_BOOL_MAP
from ..stats.data_structures import Protocol
from ...exceptions import OffloadFeatureException

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface
    from ..ip.data_structures import IPVersion


logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsOffload(BaseFeatureOffload):
    """Windows class for Offload feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Windows Offload feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._win_registry = WindowsRegistry(connection=self._connection)

    def get_offload(self, protocol: Protocol, ip_ver: "IPVersion") -> str:
        """
        Get checksum offloading status.

        :param protocol: Protocol to check offloading status
        :param ip_ver: IP Version to check, 'IPVersion.V4' or 'IPVersion.V6'
        :return: Status of checksum offload, e.g. "Rx & Tx Enabled" / "Disabled", "Tx Enabled", "Rx Enabled"
        :raises ValueError: When cannot match protocol and IP version with offload settings.

        """
        feature_key = self._get_offload_key(ip_ver, protocol)

        """
        get offload fields e.g.,
        {
        '0': 'Disabled',
        '1': 'Tx Enabled',
        '2': 'Rx Enabled',
        '3': 'Rx & Tx Enabled',
        'PSPath': 'Microsoft.PowerShell.Core\\Registry::...',
        'PSParentPath': 'Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\CurrentCon...',
        'PSChildName': 'Enum',
        'PSDrive': 'HKLM',
        'PSProvider': 'Microsoft.PowerShell.Core\\Registry'
        }
        """
        feature_enum = self._win_registry.get_feature_enum(self._interface().name, feature_key)
        # get offload set value
        feature_value = self._get_offload_feature_value(feature_key)
        # get string value from raw value
        feature_value_description = feature_enum.get(feature_value)
        if feature_value_description is None:
            raise OffloadFeatureException(
                f"{feature_key} description is not present for interface: {self._interface().name}"
            )
        return feature_value_description

    def _get_offload_feature_value(self, feature_key: str) -> str:
        """
        Get the value of offload set in the interface.

        :param feature_key: Offload feature key.
        :return: Raw value of offload.
        """
        feature_list_dict = self._win_registry.get_feature_list(self._interface().name)
        feature_value = feature_list_dict.get(feature_key)
        if feature_value is None:
            raise OffloadFeatureException(f"{feature_key} is not present for interface: {self._interface().name}")
        return feature_value

    def set_offload(self, protocol: Protocol, ip_ver: "IPVersion", value: str) -> None:
        """
        Set offload value.

        :param protocol: Protocol to check offloading status
        :param ip_ver: IP Version to check, 'IPVersion.V4' or 'IPVersion.V6'
        :param value: checksum offload value, e.g. "Rx & Tx Enabled" / "Disabled", "Tx Enabled", "Rx Enabled"
        """
        feature_key = self._get_offload_key(ip_ver, protocol)
        feature_enum = self._win_registry.get_feature_enum(self._interface().name, feature_key)
        feature_enum = {v: k for k, v in feature_enum.items()}  # swap dictionary, "1": 'Disabled', into 'Disabled': "1'
        if value not in feature_enum.keys():
            raise OffloadFeatureException(f"Invalid offload value: '{value}' for interface: {self._interface().name}")
        self._win_registry.set_feature(self._interface().name, feature_key, feature_enum[value])

    def _get_offload_key(self, ip_ver: "IPVersion", protocol: Protocol) -> str:
        """
        Verify the correctness of the offload parameters and get the offload feature key.

        :param protocol: Protocol to check offloading status
        :param ip_ver: IP Version to check, 'IPVersion.V4' or 'IPVersion.V6'
        :return: an Offload key.
        :raises ValueError: When cannot match protocol and IP version with offload settings.
        """
        data_tuple = (protocol, ip_ver)
        if data_tuple not in OFFLOAD_SETTINGS_MAP:
            raise ValueError(
                f"Cannot match protocol {protocol} and ip version {ip_ver.value} to available values",
            )
        return OFFLOAD_SETTINGS_MAP[data_tuple]

    def get_checksum_offload_settings(self, protocol: Protocol, ip_ver: "IPVersion") -> RxTxOffloadSetting:
        """
        Fetch checksum offload settings for RX and TX.

        :param protocol: Protocol to check offloading status
        :param ip_ver: IP Version to check, 'IPVersion.V4' or 'IPVersion.V6'
        :return: RxTxOffloadSetting dataclass with information about offload settings for RX and TX
        """
        return OFFLOAD_DESCRIPTION_BOOL_MAP[self.get_offload(protocol, ip_ver)]

    def set_checksum_offload_settings(
        self, rx_tx_settings: RxTxOffloadSetting, protocol: Protocol, ip_ver: "IPVersion"
    ) -> None:
        """
        Set checksum offload settings.

        :param rx_tx_settings: offloading enabled settings
        :param protocol: Protocol to check offloading status
        :param ip_ver: IP Version to check, 'IPVersion.V4' or 'IPVersion.V6'
        """
        offload_bool_description_map = {
            v: k for k, v in OFFLOAD_DESCRIPTION_BOOL_MAP.items()
        }  # swap dictionary, "Disabled": RxTxOffload...(False, False), into RxTxOffload...(False, False): "Disabled"

        self.set_offload(protocol, ip_ver, offload_bool_description_map[rx_tx_settings])
