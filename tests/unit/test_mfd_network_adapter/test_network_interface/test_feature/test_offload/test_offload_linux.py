# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Offload Feature Linux Unit Tests."""

from dataclasses import dataclass

import pytest
from mfd_connect import RPyCConnection
from mfd_ethtool import Ethtool
from mfd_typing import PCIAddress, OSName, OSBitness
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_interface.exceptions import OffloadFeatureException
from mfd_network_adapter.network_interface.feature.offload.data_structures import OffloadSetting, RxTxOffloadSetting
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface


@dataclass
class EthtoolFeatures:
    rx_checksumming: list[str]
    tx_checksumming: list[str]
    tx_checksum_ipv4: list[str]
    tx_checksum_ip_generic: list[str]
    tx_checksum_ipv6: list[str]
    tx_checksum_fcoe_crc: list[str]
    tx_checksum_sctp: list[str]
    scatter_gather: list[str]
    tx_scatter_gather: list[str]
    tx_scatter_gather_fraglist: list[str]
    tcp_segmentation_offload: list[str]
    tx_tcp_segmentation: list[str]
    tx_tcp_ecn_segmentation: list[str]
    tx_tcp_mangleid_segmentation: list[str]
    tx_tcp6_segmentation: list[str]
    generic_segmentation_offload: list[str]
    generic_receive_offload: list[str]
    large_receive_offload: list[str]
    rx_vlan_offload: list[str]
    tx_vlan_offload: list[str]
    ntuple_filters: list[str]
    receive_hashing: list[str]
    highdma: list[str]
    rx_vlan_filter: list[str]
    vlan_challenged: list[str]
    tx_lockless: list[str]
    netns_local: list[str]
    tx_gso_robust: list[str]
    tx_fcoe_segmentation: list[str]
    tx_gre_segmentation: list[str]
    tx_gre_csum_segmentation: list[str]
    tx_ipxip4_segmentation: list[str]
    tx_ipxip6_segmentation: list[str]
    tx_udp_tnl_segmentation: list[str]
    tx_udp_tnl_csum_segmentation: list[str]
    tx_gso_partial: list[str]
    tx_tunnel_remcsum_segmentation: list[str]
    tx_sctp_segmentation: list[str]
    tx_esp_segmentation: list[str]
    tx_udp_segmentation: list[str]
    tx_gso_list: list[str]
    rx_udp_gro_forwarding: list[str]
    rx_gro_list: list[str]
    tls_hw_rx_offload: list[str]
    fcoe_mtu: list[str]
    tx_nocache_copy: list[str]
    loopback: list[str]
    rx_fcs: list[str]
    rx_all: list[str]
    tx_vlan_stag_hw_insert: list[str]
    rx_vlan_stag_hw_parse: list[str]
    rx_vlan_stag_filter: list[str]
    l2_fwd_offload: list[str]
    hw_tc_offload: list[str]
    esp_hw_offload: list[str]
    esp_tx_csum_hw_offload: list[str]
    rx_udp_tunnel_port_offload: list[str]
    tls_hw_tx_offload: list[str]
    rx_gro_hw: list[str]
    tls_hw_record: list[str]


ETHTOOL_FEATURES = EthtoolFeatures(
    rx_checksumming=["on"],
    tx_checksumming=["on"],
    tx_checksum_ipv4=["on"],
    tx_checksum_ip_generic=["off [fixed]"],
    tx_checksum_ipv6=["on"],
    tx_checksum_fcoe_crc=["off [fixed]"],
    tx_checksum_sctp=["on"],
    scatter_gather=["on"],
    tx_scatter_gather=["on"],
    tx_scatter_gather_fraglist=["off [fixed]"],
    tcp_segmentation_offload=["on"],
    tx_tcp_segmentation=["on"],
    tx_tcp_ecn_segmentation=["on"],
    tx_tcp_mangleid_segmentation=["on"],
    tx_tcp6_segmentation=["on"],
    generic_segmentation_offload=["on"],
    generic_receive_offload=["on"],
    large_receive_offload=["off [fixed]"],
    rx_vlan_offload=["on"],
    tx_vlan_offload=["on"],
    ntuple_filters=["on"],
    receive_hashing=["on"],
    highdma=["on"],
    rx_vlan_filter=["on"],
    vlan_challenged=["off [fixed]"],
    tx_lockless=["off [fixed]"],
    netns_local=["off [fixed]"],
    tx_gso_robust=["off [fixed]"],
    tx_fcoe_segmentation=["off [fixed]"],
    tx_gre_segmentation=["on"],
    tx_gre_csum_segmentation=["on"],
    tx_ipxip4_segmentation=["on"],
    tx_ipxip6_segmentation=["on"],
    tx_udp_tnl_segmentation=["on"],
    tx_udp_tnl_csum_segmentation=["on"],
    tx_gso_partial=["on"],
    tx_tunnel_remcsum_segmentation=["off [fixed]"],
    tx_sctp_segmentation=["off [fixed]"],
    tx_esp_segmentation=["off [fixed]"],
    tx_udp_segmentation=["on"],
    tx_gso_list=["off [fixed]"],
    rx_udp_gro_forwarding=["off"],
    rx_gro_list=["off"],
    tls_hw_rx_offload=["off [fixed]"],
    fcoe_mtu=["off [fixed]"],
    tx_nocache_copy=["off"],
    loopback=["off [fixed]"],
    rx_fcs=["off [fixed]"],
    rx_all=["off [fixed]"],
    tx_vlan_stag_hw_insert=["off"],
    rx_vlan_stag_hw_parse=["off"],
    rx_vlan_stag_filter=["on"],
    l2_fwd_offload=["off [fixed]"],
    hw_tc_offload=["off"],
    esp_hw_offload=["off [fixed]"],
    esp_tx_csum_hw_offload=["off [fixed]"],
    rx_udp_tunnel_port_offload=["on"],
    tls_hw_tx_offload=["off [fixed]"],
    rx_gro_hw=["off [fixed]"],
    tls_hw_record=["off [fixed]"],
)


class TestLinuxNetworkInterfaceOffload:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        connection.get_os_bitness.return_value = OSBitness.OS_64BIT
        mocker.patch("mfd_ethtool.Ethtool.__init__", return_value=None)
        interface = LinuxNetworkInterface(
            connection=connection, interface_info=LinuxInterfaceInfo(name=name, pci_address=pci_address)
        )
        interface.offload._ethtool = mocker.create_autospec(Ethtool)
        interface.offload._ethtool.get_protocol_offload_and_feature_state.return_value = ETHTOOL_FEATURES

        mocker.stopall()
        yield interface

    def test_convert_offload_setting_ok(self, interface):
        result = interface.offload._convert_offload_setting(["on"])
        assert result == OffloadSetting.ON, "Expected ON when 'on' is in the list"

        result = interface.offload._convert_offload_setting(["off"])
        assert result == OffloadSetting.OFF, "Expected OFF when 'on' is not in the list"

        result = interface.offload._convert_offload_setting(["off [fixed]"])
        assert result == OffloadSetting.OFF, "Expected OFF when 'on' is not in the list"

    def test_convert_offload_setting_error(self, interface):
        with pytest.raises(OffloadFeatureException):
            interface.offload._convert_offload_setting(["invalid"])

        with pytest.raises(OffloadFeatureException):
            interface.offload._convert_offload_setting(None)

    def test_get_lso_success(self, interface):
        ETHTOOL_FEATURES.tcp_segmentation_offload = ["on"]
        assert interface.offload.get_lso() == OffloadSetting.ON
        ETHTOOL_FEATURES.tcp_segmentation_offload = ["off"]
        assert interface.offload.get_lso() == OffloadSetting.OFF

    def test_get_lso_failure(self, interface):
        interface.offload._ethtool.get_protocol_offload_and_feature_state.return_value = None
        with pytest.raises(OffloadFeatureException):
            interface.offload.get_lso()

    def test_get_lro_success(self, interface):
        ETHTOOL_FEATURES.large_receive_offload = ["on"]
        assert interface.offload.get_lro() == OffloadSetting.ON
        ETHTOOL_FEATURES.large_receive_offload = ["off"]
        assert interface.offload.get_lro() == OffloadSetting.OFF

    def test_get_lro_failure(self, interface):
        interface.offload._ethtool.get_protocol_offload_and_feature_state.return_value = None
        with pytest.raises(OffloadFeatureException):
            interface.offload.get_lro()

    def test_set_lso_success(self, interface, mocker):
        interface.offload.set_lso(OffloadSetting.ON)
        interface.offload._ethtool.set_protocol_offload_and_feature_state.assert_called_once_with(
            device_name=interface.name, param_name="tso", param_value="on", namespace=interface.namespace
        )

    def test_set_lro_success(self, interface):
        interface.offload.set_lro(OffloadSetting.ON)
        interface.offload._ethtool.set_protocol_offload_and_feature_state.assert_called_once_with(
            device_name=interface.name, param_name="lro", param_value="on", namespace=interface.namespace
        )

    def test_get_rx_checksumming_success(self, interface):
        ETHTOOL_FEATURES.rx_checksumming = ["on"]
        assert interface.offload.get_rx_checksumming() == OffloadSetting.ON
        ETHTOOL_FEATURES.rx_checksumming = ["off"]
        assert interface.offload.get_rx_checksumming() == OffloadSetting.OFF

    def test_get_rx_checksumming_failure(self, interface):
        interface.offload._ethtool.get_protocol_offload_and_feature_state.return_value = None
        with pytest.raises(OffloadFeatureException):
            interface.offload.get_rx_checksumming()

    def test_set_rx_checksumming_success(self, interface):
        interface.offload.set_rx_checksumming(OffloadSetting.ON)
        interface.offload._ethtool.set_protocol_offload_and_feature_state.assert_called_once_with(
            device_name=interface.name, param_name="rx", param_value="on", namespace=interface.namespace
        )

    def test_get_tx_checksumming_success(self, interface):
        ETHTOOL_FEATURES.tx_checksumming = ["on"]
        assert interface.offload.get_tx_checksumming() == OffloadSetting.ON
        ETHTOOL_FEATURES.tx_checksumming = ["off"]
        assert interface.offload.get_tx_checksumming() == OffloadSetting.OFF

    def test_get_tx_checksumming_failure(self, interface):
        interface.offload._ethtool.get_protocol_offload_and_feature_state.return_value = None
        with pytest.raises(OffloadFeatureException):
            interface.offload.get_tx_checksumming()

    def test_set_tx_checksumming_success(self, interface):
        interface.offload.set_tx_checksumming(OffloadSetting.ON)
        interface.offload._ethtool.set_protocol_offload_and_feature_state.assert_called_once_with(
            device_name=interface.name, param_name="tx", param_value="on", namespace=interface.namespace
        )

    def test_get_rx_vlan_offload_success(self, interface):
        ETHTOOL_FEATURES.rx_vlan_offload = ["on"]
        assert interface.offload.get_rx_vlan_offload() == OffloadSetting.ON
        ETHTOOL_FEATURES.rx_vlan_offload = ["off"]
        assert interface.offload.get_rx_vlan_offload() == OffloadSetting.OFF

    def test_get_rx_vlan_offload_failure(self, interface):
        interface.offload._ethtool.get_protocol_offload_and_feature_state.return_value = None
        with pytest.raises(OffloadFeatureException):
            interface.offload.get_rx_vlan_offload()

    def test_set_rx_vlan_offload_success(self, interface):
        interface.offload.set_rx_vlan_offload(OffloadSetting.ON)
        interface.offload._ethtool.set_protocol_offload_and_feature_state.assert_called_once_with(
            device_name=interface.name, param_name="rxvlan", param_value="on", namespace=interface.namespace
        )

    def test_get_tx_vlan_offload_success(self, interface):
        ETHTOOL_FEATURES.tx_vlan_offload = ["on"]
        assert interface.offload.get_tx_vlan_offload() == OffloadSetting.ON
        ETHTOOL_FEATURES.tx_vlan_offload = ["off"]
        assert interface.offload.get_tx_vlan_offload() == OffloadSetting.OFF

    def test_get_tx_vlan_offload_failure(self, interface):
        interface.offload._ethtool.get_protocol_offload_and_feature_state.return_value = None
        with pytest.raises(OffloadFeatureException):
            interface.offload.get_tx_vlan_offload()

    def test_set_tx_vlan_offload_success(self, interface):
        interface.offload.set_tx_vlan_offload(OffloadSetting.ON)
        interface.offload._ethtool.set_protocol_offload_and_feature_state.assert_called_once_with(
            device_name=interface.name, param_name="txvlan", param_value="on", namespace=interface.namespace
        )

    def test_get_checksum_offload_settings_success(self, interface, mocker):
        interface.offload.get_rx_checksumming = mocker.Mock(return_value=OffloadSetting.ON)
        interface.offload.get_tx_checksumming = mocker.Mock(return_value=OffloadSetting.ON)
        result = interface.offload.get_checksum_offload_settings()
        assert result.rx_enabled is True
        assert result.tx_enabled is True
        interface.offload.get_rx_checksumming = mocker.Mock(return_value=OffloadSetting.OFF)
        interface.offload.get_tx_checksumming = mocker.Mock(return_value=OffloadSetting.OFF)
        result = interface.offload.get_checksum_offload_settings()
        assert result.rx_enabled is False
        assert result.tx_enabled is False

    def test_get_checksum_offload_settings_failure(self, interface):
        interface.offload._ethtool.get_protocol_offload_and_feature_state.return_value = None
        with pytest.raises(OffloadFeatureException):
            interface.offload.get_checksum_offload_settings()

    def test_set_checksum_offload_settings_success(self, interface, mocker):
        interface.offload.set_checksum_offload_settings(RxTxOffloadSetting(True, True))

        interface.offload._ethtool.set_protocol_offload_and_feature_state.assert_has_calls(
            [
                mocker.call(device_name="Ethernet", param_name="rx", param_value="on", namespace=None),
                mocker.call(device_name="Ethernet", param_name="tx", param_value="on", namespace=None),
            ]
        )
