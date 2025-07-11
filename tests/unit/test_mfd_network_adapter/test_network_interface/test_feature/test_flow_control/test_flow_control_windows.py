# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
import time
from dataclasses import fields
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_network_adapter.network_interface.exceptions import FlowControlException
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface
from mfd_network_adapter.network_interface.feature.link.windows import WindowsLink
from mfd_network_adapter.network_interface.feature.flow_control import WindowsFlowControl
from mfd_network_adapter.network_interface.feature.flow_control.data_structures import (
    FlowControlParams,
    FlowControlType,
    Watermark,
)
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import WindowsInterfaceInfo
from mfd_win_registry import WindowsRegistry


class TestWindowsNetworkInterface:
    feature_list = {
        "DriverDesc": "Intel(R) Ethernet Network Adapter E810-C-Q2",
        "ProviderName": "Intel",
        "DriverDateData": "{0, 64, 246, 183...}",
        "DriverDate": "4-18-2023",
        "DriverVersion": "1.13.236.0",
        "InfPath": "oem12.inf",
        "InfSection": "F1592",
        "IncludedInfs": "{pci.inf}",
        "MatchingDeviceId": "PCI\\VEN_8086&DEV_1592&SUBSYS_00028086",
        "LogLinkStateEvent": "51",
        "UniversalInstall": "1",
        "IceaInstallDir": "C:\\Windows\\System32\\DriverStore\\FileRepository\\icea68.inf_amd64_842fd73bafcfa6da",
        "VMQSupported": "1",
        "CoInstallFlag": "539492416",
        "*IfType": "6",
        "*MediaType": "0",
        "*PhysicalMediaType": "14",
        "BusType": "5",
        "Characteristics": "132",
        "Port1FunctionNumber": "0",
        "*FlowControl": "0",
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
        "LinkOnIntDown": "1",
        "AllowNoFECModulesInAuto": "0",
        "*NumRssQueues": "16",
        "MaxNumRssQueuesPerVPort": "4",
        "*RSSProfile": "4",
        "*RSS": "1",
        "*RssBaseProcNumber": "0",
        "*NumaNodeId": "65535",
        "*MaxRssProcessors": "32",
        "*NetworkDirect": "1",
        "*NetworkDirectTechnology": "1",
        "RdmaRoceFrameSize": "1024",
        "RdmaMaxVfsEnabled": "0",
        "RdmaVfPreferredResourceProfile": "0",
        "VlanId": "0",
        "*QOS": "1",
        "*SRIOV": "1",
        "MDDAutoResetVFs": "0",
        "*EncapsulatedPacketTaskOffload": "1",
        "*EncapsulatedPacketTaskOffloadNvgre": "1",
        "*EncapsulatedPacketTaskOffloadVxlan": "1",
        "*VxlanUDPPortNumber": "4789",
        "*EncapOverhead": "0",
        "*VMQ": "1",
        "*VMQVlanFiltering": "1",
        "*RssOnHostVPorts": "1",
        "*UsoIPv4": "1",
        "*UsoIPv6": "1",
        "*PtpHardwareTimestamp": "0",
        "*SoftwareTimestamp": "0",
        "*SpeedDuplex": "0",
        "FecMode": "2",
        "IfTypePreStart": "6",
        "NetworkInterfaceInstallTimestamp": "133268775009839512",
        "InstallTimeStamp": "{231, 7, 4, 0...}",
        "DeviceInstanceID": "PCI\\VEN_8086&DEV_1592&SUBSYS_00028086&REV_01\\000100FFFF00000001",
        "ComponentId": "PCI\\VEN_8086&DEV_1592&SUBSYS_00028086",
        "NetCfgInstanceId": "{81C379EE-5F3E-4BE8-B2CC-AF2D0023336D}",
        "NetLuidIndex": "32773",
        "Port": "1",
        "CoInstallFlagSet": "1",
        "IntelDCBxInstalled": "1",
        "PerformanceProfile": "7",
        "FlowControlHighWatermark": "200",
        "FlowControlLowWatermark": "100",
        "Version": "43",
    }
    feature_enum = {
        "0": "Disabled",
        "1": "Tx Enabled",
        "2": "Rx Enabled",
        "3": "Rx & Tx Enabled",
        "4": "Auto Negotiation",
    }

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
        return interface

    def test_get_flow_control(self, interface, mocker):
        fc_params = FlowControlParams(autonegotiate=None, tx="off", rx="off")
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.flow_control.WindowsFlowControl.get_flow_control_registry",
            mocker.create_autospec(WindowsFlowControl.get_flow_control_registry, return_value="Disabled"),
        )
        fc_params_get = interface.flow_control.get_flow_control()
        for f in fields(fc_params):
            if "tx" or "rx" in f.name:
                assert getattr(fc_params_get, f.name) == getattr(fc_params, f.name)

    def test_get_flow_control_err(self, interface, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.flow_control.WindowsFlowControl.get_flow_control_registry",
            mocker.create_autospec(WindowsFlowControl.get_flow_control_registry, return_value=""),
        )
        with pytest.raises(FlowControlException, match="Cannot match Flow Control setting from registry"):
            interface.flow_control.get_flow_control()

    def test_set_flow_control(self, interface, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.flow_control.WindowsFlowControl.get_flow_control_registry",
            mocker.create_autospec(WindowsFlowControl.get_flow_control_registry, return_value="Disabled"),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.flow_control.WindowsFlowControl.set_flow_control_registry",
            mocker.create_autospec(WindowsFlowControl.set_flow_control_registry, return_value=None),
        )
        interface.flow_control.set_flow_control(FlowControlParams(autonegotiate=None, tx="off", rx=None))
        interface.flow_control.set_flow_control_registry.assert_called_with(
            interface.flow_control, FlowControlType.DISABLED
        )

    def test_set_flow_control_err(self, interface, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.flow_control.WindowsFlowControl.get_flow_control_registry",
            mocker.create_autospec(WindowsFlowControl.get_flow_control_registry, return_value=""),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.flow_control.WindowsFlowControl.set_flow_control_registry",
            mocker.create_autospec(WindowsFlowControl.set_flow_control_registry, return_value=None),
        )
        with pytest.raises(FlowControlException, match="Cannot match flow control setting to available value"):
            interface.flow_control.set_flow_control(FlowControlParams(autonegotiate=None, tx="off", rx=None))

    def test_set_flow_control_registry(self, interface, mocker):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_enum",
            mocker.create_autospec(WindowsRegistry.get_feature_enum, return_value=self.feature_enum),
        )
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=None),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        interface.flow_control.set_flow_control_registry(setting=FlowControlType.DISABLED)
        interface.flow_control._win_registry.set_feature.assert_called_once_with(
            interface.flow_control._win_registry, interface="Ethernet", feature="*FlowControl", value="0"
        )

    def test_get_flow_control_registry(self, interface, mocker):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=self.feature_list),
        )
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_enum",
            mocker.create_autospec(WindowsRegistry.get_feature_enum, return_value=self.feature_enum),
        )
        interface.flow_control._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        assert "Disabled" == interface.flow_control.get_flow_control_registry()

    def test_get_flow_ctrl_watermark(self, mocker, interface):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=self.feature_list),
        )
        assert "200" == interface.flow_control.get_flow_ctrl_watermark(watermark=Watermark.HIGH)

    def test_get_flow_ctrl_watermark_err(self, mocker, interface):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value={}),
        )
        with pytest.raises(
            FlowControlException, match="Feature: FlowControlHighWatermark doesn't exists on interface: Ethernet"
        ):
            interface.flow_control.get_flow_ctrl_watermark(watermark=Watermark.HIGH)

    def test_set_flow_ctrl_watermark_high(self, mocker, interface):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=None),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        interface.flow_control.set_flow_ctrl_watermark(watermark=Watermark.HIGH, value="200")
        interface.flow_control._win_registry.set_feature.assert_called_once_with(
            interface.flow_control._win_registry, interface="Ethernet", feature="FlowControlHighWatermark", value="200"
        )

    def test_set_flow_ctrl_watermark_low(self, mocker, interface):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=None),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        interface.flow_control.set_flow_ctrl_watermark(watermark=Watermark.LOW, value="100")
        interface.flow_control._win_registry.set_feature.assert_called_once_with(
            interface.flow_control._win_registry, interface="Ethernet", feature="FlowControlLowWatermark", value="100"
        )

    def test_remove_flow_ctrl_watermark(self, mocker, interface):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.remove_feature",
            mocker.create_autospec(WindowsRegistry.remove_feature, return_value=None),
        )
        interface.flow_control.remove_flow_ctrl_watermark(watermark=Watermark.HIGH)
        interface.flow_control._win_registry.remove_feature.assert_called_once_with(
            interface.flow_control._win_registry, interface="Ethernet", feature="FlowControlHighWatermark"
        )

    def test_get_flow_ctrl_values(self, mocker, interface):
        expected_output = [
            "Disabled",
            "Tx Enabled",
            "Rx Enabled",
            "Rx & Tx Enabled",
            "Auto Negotiation",
        ]
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_enum",
            mocker.create_autospec(WindowsRegistry.get_feature_enum, return_value=self.feature_enum),
        )
        assert interface.flow_control.get_flow_ctrl_values()[0] == expected_output[0]
