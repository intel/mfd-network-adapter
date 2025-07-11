# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Offload feature for Linux."""

import logging

from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_ethtool import Ethtool
from mfd_ethtool.exceptions import EthtoolExecutionError

from .base import BaseFeatureOffload
from .data_structures import OffloadSetting, RxTxOffloadSetting
from ...exceptions import OffloadFeatureException

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxOffload(BaseFeatureOffload):
    """Linux class for Offload feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize Linux Offload.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._ethtool = Ethtool(connection=connection)

    @staticmethod
    def _convert_offload_setting(value: list[str]) -> OffloadSetting:
        """
        Convert offload setting list of strings to OffloadSetting object.

        :param value: Offload setting
        :return: OffloadSetting object
        :raises OffloadFeatureException: When cannot convert offload setting or value is None
        """
        if value is None:
            raise OffloadFeatureException("The input value cannot be None.")
        if len(value) != 1 or not any(v in value[0] for v in ["on", "off"]):
            raise OffloadFeatureException(f"Cannot convert offload setting - {value}")
        return OffloadSetting.ON if "on" in value[0] else OffloadSetting.OFF

    def get_lso(self) -> OffloadSetting:
        """
        Get LSO value.

        :return: LSO value
        :raises OffloadFeatureException: When cannot get LSO value
        """
        ethtool_features = self._ethtool.get_protocol_offload_and_feature_state(
            device_name=self._interface().name, namespace=self._interface().namespace
        )
        try:
            return self._convert_offload_setting(ethtool_features.tcp_segmentation_offload)
        except AttributeError:
            raise OffloadFeatureException("Cannot get LSO value.")

    def set_lso(self, value: OffloadSetting) -> None:
        """
        Set LSO value.

        :param value: OffloadSetting.ON or OffloadSetting.OFF
        """
        self._ethtool.set_protocol_offload_and_feature_state(
            device_name=self._interface().name,
            param_name="tso",
            param_value=value.value,
            namespace=self._interface().namespace,
        )

    def set_lro(
        self,
        value: OffloadSetting,
    ) -> None:
        """
        Set LRO value.

        :param value: OffloadSetting.ON or OffloadSetting.OFF
        """
        self._ethtool.set_protocol_offload_and_feature_state(
            device_name=self._interface().name,
            param_name="lro",
            param_value=value.value,
            namespace=self._interface().namespace,
        )

    def get_lro(self) -> OffloadSetting:
        """
        Get LRO value.

        :return: LRO value
        :raises OffloadFeatureException: When cannot get LRO value
        """
        ethtool_features = self._ethtool.get_protocol_offload_and_feature_state(
            device_name=self._interface().name, namespace=self._interface().namespace
        )
        try:
            return self._convert_offload_setting(ethtool_features.large_receive_offload)
        except AttributeError:
            raise OffloadFeatureException("Cannot get LRO value.")

    def get_rx_checksumming(self) -> OffloadSetting:
        """
        Get RX checksumming value.

        :return: RX checksumming value
        :raises OffloadFeatureException: When cannot get RX checksumming value
        """
        ethtool_features = self._ethtool.get_protocol_offload_and_feature_state(
            device_name=self._interface().name, namespace=self._interface().namespace
        )
        try:
            return self._convert_offload_setting(ethtool_features.rx_checksumming)
        except AttributeError:
            raise OffloadFeatureException("Cannot get RX checksumming value.")

    def get_tx_checksumming(self) -> OffloadSetting:
        """
        Get TX checksumming value.

        :return: TX checksumming value
        :raises OffloadFeatureException: When cannot get TX checksumming value
        """
        ethtool_features = self._ethtool.get_protocol_offload_and_feature_state(
            device_name=self._interface().name, namespace=self._interface().namespace
        )
        try:
            return self._convert_offload_setting(ethtool_features.tx_checksumming)
        except AttributeError:
            raise OffloadFeatureException("Cannot get TX checksumming value.")

    def set_tx_checksumming(self, value: OffloadSetting) -> None:
        """
        Set TX checksumming value.

        :param value: OffloadSetting.ON or OffloadSetting.OFF
        """
        self._ethtool.set_protocol_offload_and_feature_state(
            device_name=self._interface().name,
            param_name="tx",
            param_value=value.value,
            namespace=self._interface().namespace,
        )

    def set_rx_checksumming(self, value: OffloadSetting) -> None:
        """
        Set RX checksumming value.

        :param value: OffloadSetting.ON or OffloadSetting.OFF
        """
        self._ethtool.set_protocol_offload_and_feature_state(
            device_name=self._interface().name,
            param_name="rx",
            param_value=value.value,
            namespace=self._interface().namespace,
        )

    def get_rx_vlan_offload(self) -> OffloadSetting:
        """
        Get RX VLAN offload value.

        :return: RX VLAN offload value
        :raises OffloadFeatureException: When cannot get RX VLAN offload value
        """
        ethtool_features = self._ethtool.get_protocol_offload_and_feature_state(
            device_name=self._interface().name, namespace=self._interface().namespace
        )
        try:
            return self._convert_offload_setting(ethtool_features.rx_vlan_offload)
        except AttributeError:
            raise OffloadFeatureException("Cannot get RX VLAN offload value.")

    def set_rx_vlan_offload(self, value: OffloadSetting) -> None:
        """
        Set RX VLAN offload value.

        :param value: OffloadSetting.ON or OffloadSetting.OFF
        """
        self._ethtool.set_protocol_offload_and_feature_state(
            device_name=self._interface().name,
            param_name="rxvlan",
            param_value=value.value,
            namespace=self._interface().namespace,
        )

    def get_tx_vlan_offload(self) -> OffloadSetting:
        """
        Get TX VLAN offload value.

        :return: TX VLAN offload value
        :raises OffloadFeatureException: When cannot get TX VLAN offload value
        """
        ethtool_features = self._ethtool.get_protocol_offload_and_feature_state(
            device_name=self._interface().name, namespace=self._interface().namespace
        )
        try:
            return self._convert_offload_setting(ethtool_features.tx_vlan_offload)
        except AttributeError:
            raise OffloadFeatureException("Cannot get TX VLAN offload value.")

    def set_tx_vlan_offload(self, value: OffloadSetting) -> None:
        """
        Set TX VLAN offload value.

        :param value: OffloadSetting.ON or OffloadSetting.OFF
        """
        self._ethtool.set_protocol_offload_and_feature_state(
            device_name=self._interface().name,
            param_name="txvlan",
            param_value=value.value,
            namespace=self._interface().namespace,
        )

    def get_checksum_offload_settings(self) -> RxTxOffloadSetting:
        """
        Get checksum offload settings.

        :return: RxTxOffloadSetting dataclass with information about offload settings for RX and TX
        :raises OffloadFeatureException: When cannot get checksum offload settings
        """
        rx = self.get_rx_checksumming() == OffloadSetting.ON
        tx = self.get_tx_checksumming() == OffloadSetting.ON

        return RxTxOffloadSetting(rx_enabled=rx, tx_enabled=tx)

    def set_checksum_offload_settings(self, rx_tx_settings: RxTxOffloadSetting) -> None:
        """
        Set checksum offload settings.

        :param rx_tx_settings: Checksum offload settings
        :raises OffloadFeatureException: When cannot set checksum offload settings
        """
        rx = OffloadSetting.ON if rx_tx_settings.rx_enabled else OffloadSetting.OFF
        tx = OffloadSetting.ON if rx_tx_settings.tx_enabled else OffloadSetting.OFF
        try:
            self.set_rx_checksumming(value=rx)
            self.set_tx_checksumming(value=tx)
        except EthtoolExecutionError:
            raise OffloadFeatureException("Cannot set checksum offload settings.")
