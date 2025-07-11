# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import re

import pytest
from mfd_connect import RPyCConnection
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import WindowsInterfaceInfo

from mfd_network_adapter.network_interface.exceptions import OffloadFeatureException
from mfd_network_adapter.network_interface.feature.ip.data_structures import IPVersion
from mfd_network_adapter.network_interface.feature.offload.consts import CHECKSUM_OFFLOAD_TCP_IPV4
from mfd_network_adapter.network_interface.feature.offload.data_structures import RxTxOffloadSetting
from mfd_network_adapter.network_interface.feature.stats.data_structures import Protocol
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface

feature_enum = {
    "0": "Disabled",
    "1": "Tx Enabled",
    "2": "Rx Enabled",
    "3": "Rx & Tx Enabled",
    "PSChildName": "Enum",
    "PSDrive": "HKLM",
    "PSProvider": "Microsoft.PowerShell.Core\\Registry",
}
feature_list = {
    "DriverDesc": "Intel(R)",
    "ProviderName": "Intel",
    "DriverDateData": "{0,",
    "DriverDate": "7-19-2022",
    "DriverVersion": "4.1.246.2",
    "InfPath": "oem21.inf",
    "InfSection": "S1563_DP",
    "IncludedInfs": "{pci.inf}",
    "MatchingDeviceId": "PCI\\VEN_8086&DEV_1563",
    "*FlowControl": "3",
    "MinHardwareOwnedPacketCount": "32",
    "LogLinkStateEvent": "51",
    "*LsoV1IPv4": "0",
    "*HeaderDataSplit": "0",
    "MulticastFilterType": "0",
    "VlanFiltering": "0",
    "UniversalInstall": "1",
    "NumRssQueuesPerVPort": "4",
    "VMQSupported": "1",
    "IntelANSVlanID": "{}",
    "*IPsecOffloadV2": "0",
    "CoInstallFlag": "2621448",
    "*IfType": "6",
    "*MediaType": "0",
    "*PhysicalMediaType": "14",
    "BusType": "5",
    "Characteristics": "132",
    "Port1FunctionNumber": "0",
    "*TransmitBuffers": "512",
    "*ReceiveBuffers": "512",
    "*TCPChecksumOffloadIPv4": "3",
    "*TCPChecksumOffloadIPv6": "3",
    "*UDPChecksumOffloadIPv4": "3",
    "*UDPChecksumOffloadIPv6": "3",
    "*IPChecksumOffloadIPv4": "3",
    "ITR": "65535",
    "*PriorityVLANTag": "3",
    "*InterruptModeration": "1",
    "*LsoV2IPv4": "1",
    "*LsoV2IPv6": "1",
    "*JumboPacket": "1514",
    "*NumRssQueues": "8",
    "*RSS": "1",
    "*EncapsulatedPacketTaskOffload": "1",
    "*EncapsulatedPacketTaskOffloadNvgre": "1",
    "*EncapsulatedPacketTaskOffloadVxlan": "1",
    "*VxlanUDPPortNumber": "4789",
    "*EncapOverhead": "0",
    "*RssOnHostVPorts": "1",
    "*RSSProfile": "1",
    "*RssBaseProcNumber": "0",
    "*NumaNodeId": "65535",
    "*MaxRssProcessors": "16",
    "*QOS": "0",
    "*VMQ": "1",
    "*SRIOV": "1",
    "VlanId": "0",
    "*SpeedDuplex": "0",
    "DMACoalescing": "0",
    "EnablePME": "0",
    "*WakeOnPattern": "1",
    "*WakeOnMagicPacket": "1",
    "WakeOnLink": "0",
    "*RSCIPv4": "1",
    "*RSCIPv6": "1",
    "IfTypePreStart": "6",
    "NetworkInterfaceInstallTimestamp": "133523895990223843",
    "InstallTimeStamp": "{232,",
    "DeviceInstanceID": "VMBUS\\{f8615163-df3e-46c5-913f-f2d2f965ed0e}\\{0dcc8d3e-07f6-4a71-a802-08389b63cfbb}",
    "ComponentId": "VMBUS\\{f8615163-df3e-46c5-913f-f2d2f965ed0e}",
    "NetCfgInstanceId": "{8E5A25A3-83A0-417A-B310-B1811C1658F7}",
    "NetLuidIndex": "32772",
    "PSChildName": "0001",
    "PSDrive": "HKLM",
    "PSProvider": "Microsoft.PowerShell.Core\\Registry",
}


class TestWindowsNetworkInterfaceOffload:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS
        interface = WindowsNetworkInterface(
            connection=connection, interface_info=WindowsInterfaceInfo(name=name, pci_address=pci_address)
        )
        mocker.stopall()
        yield interface

    @pytest.fixture()
    def offload(self, interface):
        yield interface.offload

    def test__get_offload_feature_value(self, offload, mocker):
        offload._win_registry.get_feature_list = mocker.create_autospec(offload._win_registry.get_feature_list)
        offload._win_registry.get_feature_list.return_value = feature_list
        assert offload._get_offload_feature_value("*TCPChecksumOffloadIPv4") == "3"

    def test__get_offload_feature_value_missing_key(self, offload, mocker):
        offload._win_registry.get_feature_list = mocker.create_autospec(offload._win_registry.get_feature_list)
        offload._win_registry.get_feature_list.return_value = feature_list
        with pytest.raises(OffloadFeatureException, match=re.escape("*TCPChec is not present for interface: Ethernet")):
            offload._get_offload_feature_value("*TCPChec")

    def test__get_offload_key(self, offload):
        assert offload._get_offload_key(ip_ver=IPVersion.V4, protocol=Protocol.TCP) == CHECKSUM_OFFLOAD_TCP_IPV4
        with pytest.raises(
            ValueError,
            match="Cannot match protocol Protocol.SCTP and ip version 4 to available values",
        ):
            offload._get_offload_key(ip_ver=IPVersion.V4, protocol=Protocol.SCTP)

    def test_get_offload(self, offload, mocker):
        protocol = Protocol.TCP
        ip_ver = IPVersion.V4
        offload._get_offload_key = mocker.create_autospec(offload._get_offload_key)
        offload._win_registry.get_feature_enum = mocker.create_autospec(offload._win_registry.get_feature_enum)
        offload._get_offload_feature_value = mocker.create_autospec(offload._get_offload_feature_value)

        offload._win_registry.get_feature_enum.return_value = feature_enum
        offload._get_offload_feature_value.return_value = "3"
        offload._get_offload_key.return_value = CHECKSUM_OFFLOAD_TCP_IPV4
        assert offload.get_offload(protocol, ip_ver) == "Rx & Tx Enabled"
        offload._get_offload_key.assert_called_once_with(ip_ver, protocol)
        offload._get_offload_feature_value.assert_called_once_with(CHECKSUM_OFFLOAD_TCP_IPV4)

    def test_get_offload_missing_description(self, offload, mocker):
        protocol = Protocol.TCP
        ip_ver = "4"
        offload._get_offload_key = mocker.create_autospec(offload._get_offload_key)
        offload._win_registry.get_feature_enum = mocker.create_autospec(offload._win_registry.get_feature_enum)
        offload._get_offload_feature_value = mocker.create_autospec(offload._get_offload_feature_value)
        offload._win_registry.get_feature_enum.return_value = feature_enum
        offload._get_offload_feature_value.return_value = "4"
        offload._get_offload_key.return_value = CHECKSUM_OFFLOAD_TCP_IPV4
        with pytest.raises(
            OffloadFeatureException,
            match=re.escape("*TCPChecksumOffloadIPv4 description is not present for interface: Ethernet"),
        ):
            offload.get_offload(protocol, ip_ver)

    def test_set_offload(self, offload, mocker):
        protocol = Protocol.TCP
        ip_ver = IPVersion.V4
        value = "Rx & Tx Enabled"
        offload._get_offload_key = mocker.create_autospec(offload._get_offload_key)
        offload._win_registry.get_feature_enum = mocker.create_autospec(offload._win_registry.get_feature_enum)
        offload._win_registry.set_feature = mocker.create_autospec(offload._win_registry.set_feature)

        offload._get_offload_key.return_value = CHECKSUM_OFFLOAD_TCP_IPV4
        offload._win_registry.get_feature_enum.return_value = feature_enum

        offload.set_offload(protocol, ip_ver, value)

        offload._win_registry.set_feature.assert_called_once_with("Ethernet", "*TCPChecksumOffloadIPv4", "3")

    def test_set_offload_missing_value(self, offload, mocker):
        protocol = Protocol.TCP
        ip_ver = IPVersion.V4
        value = "Rx & Tx"
        offload._get_offload_key = mocker.create_autospec(offload._get_offload_key)
        offload._win_registry.get_feature_enum = mocker.create_autospec(offload._win_registry.get_feature_enum)
        offload._win_registry.set_feature = mocker.create_autospec(offload._win_registry.set_feature)

        offload._get_offload_key.return_value = CHECKSUM_OFFLOAD_TCP_IPV4
        offload._win_registry.get_feature_enum.return_value = feature_enum

        with pytest.raises(OffloadFeatureException, match="Invalid offload value: 'Rx & Tx' for interface: Ethernet"):
            offload.set_offload(protocol, ip_ver, value)

    def test_get_checksum_offload_settings(self, offload, mocker):
        offload.get_offload = mocker.create_autospec(offload.get_offload)
        offload.get_offload.return_value = "Rx & Tx Enabled"
        assert offload.get_checksum_offload_settings(Protocol.TCP, IPVersion.V4) == RxTxOffloadSetting(True, True)
        offload.get_offload.assert_called_once_with(Protocol.TCP, IPVersion.V4)

    def test_set_checksum_offload_settings(self, offload, mocker):
        offload.set_offload = mocker.create_autospec(offload.set_offload)
        offload.set_checksum_offload_settings(RxTxOffloadSetting(True, True), Protocol.TCP, IPVersion.V4)
        offload.set_offload.assert_called_once_with(Protocol.TCP, IPVersion.V4, "Rx & Tx Enabled")
