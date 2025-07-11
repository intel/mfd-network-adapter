# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
import time
from textwrap import dedent
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess

from mfd_network_adapter.api.basic.windows import get_logical_processors_count
from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.exceptions import RSSException, RSSExecutionError
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface
from mfd_network_adapter.network_interface.feature.link.windows import WindowsLink
from mfd_network_adapter.network_interface.feature.rss import WindowsRSS
from mfd_network_adapter.network_interface.feature.rss.data_structures import RSSProfileInfo
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import WindowsInterfaceInfo
from mfd_win_registry import WindowsRegistry


class TestWindowsNetworkInterface:
    adapter_info = {
        "Name": "SLOT 4 Port 2",
        "InterfaceDescription": "Intel(R) Ethernet Network Adapter E810-C-Q2 #2",
        "Enabled": "True",
        "NumberOfReceiveQueues": "16",
        "Profile": "NUMAStatic",
        "BaseProcessor": "0:0",
        "MaxProcessor": "1:34",
        "MaxProcessors": "32",
        "RssProcessorArray": (
            "1:0/0  1:2/0  1:4/0  1:6/0  1:8/0  1:10/0  1:12/0  1:14/0\t\t"
            "1:16/0  1:18/0  1:20/0  1:22/0  1:24/0  1:26/0  1:28/0  1:30/0\t\t1:32/0  1:34/0"
            "  0:0/2688  0:2/2688  0:4/2688  0:6/2688  0:8/2688  0:10/2688\t\t0:12/2688  0:14/2688"
            "  0:16/2688  0:18/2688  0:20/2688  0:22/2688  0:24/2688  0:26/2688\t\t"
            "0:28/2688  0:30/2688  0:32/2688  0:34/2688"
        ),
        "IndirectionTable": (
            "1:0\t1:2\t1:4\t1:6\t1:8\t1:10\t1:12\t1:14\t\t\t1:16\t1:18\t1:20\t1:22\t"
            "1:24\t1:26\t1:32\t1:34\t\t\t1:0\t1:2\t1:4\t1:6\t1:8\t1:10\t1:12\t1:14\t\t\t1:16\t1:18\t"
            "1:20\t1:22\t1:24\t1:26\t1:32\t1:34\t\t\t1:0\t1:2\t1:4\t1:6\t1:8\t1:10\t1:12\t1:14\t\t\t"
            "1:16\t1:18\t1:20\t1:22\t1:24\t1:26\t1:32\t1:34\t\t\t1:0\t1:2\t1:4\t1:6\t1:8\t1:10\t1:12\t"
            "1:14\t\t\t1:16\t1:18\t1:20\t1:22\t1:24\t1:26\t1:32\t1:34\t\t\t1:0\t1:2\t1:4\t1:6\t1:8\t1:10\t"
            "1:12\t1:14\t\t\t1:16\t1:18\t1:20\t1:22\t1:24\t1:26\t1:32\t1:34\t\t\t1:0\t1:2\t1:4\t1:6\t1:8\t"
            "1:10\t1:12\t1:14\t\t\t1:16\t1:18\t1:20\t1:22\t1:24\t1:26\t1:32\t1:34\t\t\t1:0\t1:2\t1:4\t1:6\t"
            "1:8\t1:10\t1:12\t1:14\t\t\t1:16\t1:18\t1:20\t1:22\t1:24\t1:26\t1:32\t1:34\t\t\t1:0\t1:2\t1:4\t"
            "1:6\t1:8\t1:10\t1:12\t1:14\t\t\t1:16\t1:18\t1:20\t1:22\t1:24\t1:26\t1:32\t1:34"
        ),
    }
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
        "*RssMaxProcNumber": "0",
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
        "Version": "43",
        "PSPath": "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\Current\
        ControlSet\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0005",
        "PSParentPath": "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\Current\
        ControlSet\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}",
        "PSChildName": "0005",
        "PSDrive": "HKLM",
        "PSProvider": "Microsoft.PowerShell.Core\\Registry",
    }
    feature_enum = {
        "1": "ClosestProcessor",
        "2": "ClosestProcessorStatic",
        "3": "NUMAScaling",
        "4": "NUMAScalingStatic",
        "5": "ConservativeScaling",
        "PSPath": (
            "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\CurrentControlSet\\control"
            "\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0005\\Ndi\\Params\\*RSSProfile\\Enum"
        ),
        "PSParentPath": (
            "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\CurrentControlSet"
            "\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0005\\Ndi\\Params\\*RSSProfile"
        ),
        "PSChildName": "Enum",
        "PSDrive": "HKLM",
        "PSProvider": "Microsoft.PowerShell.Core\\Registry",
    }

    @pytest.fixture()
    def winrss(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "SLOT 4 Port 2"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS
        branding_string = "Intel(R) Ethernet Network Adapter E810-C-Q2 #2"
        interface = WindowsNetworkInterface(
            connection=connection,
            interface_info=WindowsInterfaceInfo(name=name, pci_address=pci_address, branding_string=branding_string),
        )
        mocker.stopall()
        return interface

    def test_set_queues(self, winrss, mocker):
        return_val = None
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=return_val),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        winrss.rss.set_queues(queue_number=16)
        winrss.rss._win_registry.set_feature.assert_called_once_with(
            winrss.rss._win_registry, interface="SLOT 4 Port 2", feature="*NumRssQueues", value="16"
        )

    def test_set_rss_enabled(self, winrss, mocker):
        return_val = None
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=return_val),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        winrss.rss.set_rss(enabled=State.ENABLED)
        winrss.rss._win_registry.set_feature.assert_called_once_with(
            winrss.rss._win_registry, interface="SLOT 4 Port 2", feature="*RSS", value="1"
        )

    def test_set_rss_disabled(self, winrss, mocker):
        return_val = None
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=return_val),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        winrss.rss.set_rss(enabled=State.DISABLED)
        winrss.rss._win_registry.set_feature.assert_called_once_with(
            winrss.rss._win_registry, interface="SLOT 4 Port 2", feature="*RSS", value="0"
        )

    def test_set_max_processors(self, winrss, mocker):
        return_val = None
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=return_val),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        winrss.rss.set_max_processors(max_proc=32)
        winrss.rss._win_registry.set_feature.assert_called_once_with(
            winrss.rss._win_registry, interface="SLOT 4 Port 2", feature="*MaxRssProcessors", value="32"
        )

    def test_set_base_processors_number(self, winrss, mocker):
        return_val = None
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=return_val),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        winrss.rss.set_base_processor_num(base_proc_num=10)
        winrss.rss._win_registry.set_feature.assert_called_once_with(
            winrss.rss._win_registry, interface="SLOT 4 Port 2", feature="*RssBaseProcNumber", value="10"
        )

    def test_set_max_processors_number(self, winrss, mocker):
        return_val = None
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=return_val),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        winrss.rss.set_max_processor_num(max_proc_num=10)
        winrss.rss._win_registry.set_feature.assert_called_once_with(
            winrss.rss._win_registry, interface="SLOT 4 Port 2", feature="*RssMaxProcNumber", value="10"
        )

    def test_set_max_queues_vport(self, winrss, mocker):
        return_val = None
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=return_val),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        winrss.rss.set_max_queues_per_vport(max_queues_vport=8)
        winrss.rss._win_registry.set_feature.assert_called_once_with(
            winrss.rss._win_registry, interface="SLOT 4 Port 2", feature="MaxNumRssQueuesPerVPort", value="8"
        )

    def test_get_queues_feature_absent(self, winrss, mocker):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value={}),
        )
        winrss.rss._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        with pytest.raises(RSSException, match=r"Feature: \*NumRssQueues doesn't exists on interface: SLOT 4 Port 2"):
            winrss.rss.get_queues()

    def test_get_queues(self, winrss, mocker):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=self.feature_list),
        )
        winrss.rss._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        assert "16" == winrss.rss.get_queues()

    def test_get_max_processors(self, winrss, mocker):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=self.feature_list),
        )
        winrss.rss._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        assert "32" == winrss.rss.get_max_processors()

    def test_get_base_processor_num(self, winrss, mocker):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=self.feature_list),
        )
        winrss.rss._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        assert "0" == winrss.rss.get_base_processor_num()

    def test_get_max_processor_num(self, winrss, mocker):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=self.feature_list),
        )
        winrss.rss._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        assert "0" == winrss.rss.get_max_processor_num()

    def test_get_profile(self, winrss, mocker):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry._convert_interface_to_index",
            mocker.create_autospec(WindowsRegistry._convert_interface_to_index, return_value="5"),
        )
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_enum",
            mocker.create_autospec(WindowsRegistry.get_feature_enum, return_value=self.feature_enum),
        )
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=self.feature_list),
        )
        winrss.rss._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        assert "NUMAScalingStatic" == winrss.rss.get_profile()

    def test_get_max_channels(self, winrss, mocker):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=self.feature_list),
        )
        winrss.rss._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        assert "1" == winrss.rss.get_max_channels()

    def test_get_adapter_info(self, winrss):
        output = dedent(
            """
                Name                                            : SLOT 4 Port 2
                InterfaceDescription                            : Intel(R) Ethernet Network Adapter E810-C-Q2 #2
                Enabled                                         : True
                NumberOfReceiveQueues                           : 16
                Profile                                         : Conservative
                BaseProcessor: [Group:Number]                   : 0:0
                MaxProcessor: [Group:Number]                    : 1:34
                MaxProcessors                                   : 16
                RssProcessorArray: [Group:Number/NUMA Distance] :
                  1:0/0  1:2/0  1:4/0  1:6/0  1:8/0  1:10/0  1:12/0  1:14/0
                  1:16/0  1:18/0  1:20/0  1:22/0  1:24/0  1:26/0  1:28/0  1:30/0
                  1:32/0  1:34/0  0:0/2688  0:2/2688  0:4/2688  0:6/2688  0:8/2688  0:10/2688
                  0:12/2688  0:14/2688  0:16/2688  0:18/2688  0:20/2688  0:22/2688  0:24/2688  0:26/2688
                  0:28/2688  0:30/2688  0:32/2688  0:34/2688
                IndirectionTable: [Group:Number]                : 1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t
                                                                  1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t\n\n\n\n"""
        )
        expected = {
            "Name": "SLOT 4 Port 2",
            "InterfaceDescription": "Intel(R) Ethernet Network Adapter E810-C-Q2 #2",
            "Enabled": "True",
            "NumberOfReceiveQueues": "16",
            "Profile": "Conservative",
            "BaseProcessor": "0:0",
            "MaxProcessor": "1:34",
            "MaxProcessors": "16",
            "RssProcessorArray": (
                "1:0/0  1:2/0  1:4/0  1:6/0  1:8/0  1:10/0  1:12/0  1:14/0\t\t1:16/0  1:18/0  "
                "1:20/0  1:22/0  1:24/0  1:26/0  1:28/0  1:30/0\t\t1:32/0  1:34/0  0:0/2688  0:2/2688  0:4/2688  "
                "0:6/2688  0:8/2688  0:10/2688\t\t0:12/2688  0:14/2688  0:16/2688  0:18/2688  0:20/2688  0:22/2688  "
                "0:24/2688  0:26/2688\t\t0:28/2688  0:30/2688  0:32/2688  0:34/2688"
            ),
            "IndirectionTable": (
                "1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t\t\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2"
                "\t\t\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t\t\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t\t\t1:0\t"
                "1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t\t\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t\t\t1:0\t1:2\t1:0\t1:2"
                "\t1:0\t1:2\t1:0\t1:2\t\t\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t\t\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t"
                "1:0\t1:2\t\t\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t\t\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t\t\t"
                "1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t\t\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t\t\t1:0\t1:2\t"
                "1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t\t\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t1:0\t1:2\t\t\t1:0\t1:2\t1:0\t1:2\t"
                "1:0\t1:2\t1:0\t1:2"
            ),
        }
        winrss.rss._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr=""
        )
        assert expected == winrss.rss.get_adapter_info()

    def test_get_proc_info(self, winrss):
        output = dedent(
            """
            BaseProcessorGroup  : 0
            BaseProcessorNumber : 0
            MaxProcessorGroup   : 1
            MaxProcessorNumber  : 34
            MaxProcessors       : 16
            """
        )
        expected = {
            "BaseProcessorGroup": "0",
            "BaseProcessorNumber": "0",
            "MaxProcessorGroup": "1",
            "MaxProcessorNumber": "34",
            "MaxProcessors": "16",
        }
        winrss.rss._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr=""
        )
        assert expected == winrss.rss.get_proc_info()

    def test_get_max_available_processors(self, winrss):
        output = "32\n"
        expected = 32
        winrss.rss._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr=""
        )
        assert expected == winrss.rss.get_max_available_processors()

    def test_get_max_available_processors_empty(self, winrss):
        expected = 0
        winrss.rss._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        assert expected == winrss.rss.get_max_available_processors()

    def test_get_indirection_table_processor_numbers(self, winrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_adapter_info",
            mocker.create_autospec(WindowsRSS.get_adapter_info, return_value=self.adapter_info),
        )
        expected = [
            "36",
            "38",
            "40",
            "42",
            "44",
            "46",
            "48",
            "50",
            "52",
            "54",
            "56",
            "58",
            "60",
            "62",
            "68",
            "70",
            "36",
            "38",
            "40",
            "42",
            "44",
            "46",
            "48",
            "50",
            "52",
            "54",
            "56",
            "58",
            "60",
            "62",
            "68",
            "70",
            "36",
            "38",
            "40",
            "42",
            "44",
            "46",
            "48",
            "50",
            "52",
            "54",
            "56",
            "58",
            "60",
            "62",
            "68",
            "70",
            "36",
            "38",
            "40",
            "42",
            "44",
            "46",
            "48",
            "50",
            "52",
            "54",
            "56",
            "58",
            "60",
            "62",
            "68",
            "70",
            "36",
            "38",
            "40",
            "42",
            "44",
            "46",
            "48",
            "50",
            "52",
            "54",
            "56",
            "58",
            "60",
            "62",
            "68",
            "70",
            "36",
            "38",
            "40",
            "42",
            "44",
            "46",
            "48",
            "50",
            "52",
            "54",
            "56",
            "58",
            "60",
            "62",
            "68",
            "70",
            "36",
            "38",
            "40",
            "42",
            "44",
            "46",
            "48",
            "50",
            "52",
            "54",
            "56",
            "58",
            "60",
            "62",
            "68",
            "70",
            "36",
            "38",
            "40",
            "42",
            "44",
            "46",
            "48",
            "50",
            "52",
            "54",
            "56",
            "58",
            "60",
            "62",
            "68",
            "70",
        ]
        assert expected == winrss.rss.get_indirection_table_processor_numbers()

    def test_get_indirection_table_processor_numbers_empty(self, winrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_adapter_info",
            mocker.create_autospec(WindowsRSS.get_adapter_info, return_value={}),
        )
        assert [] == winrss.rss.get_indirection_table_processor_numbers()

    def test_get_numa_processor_array(self, winrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_adapter_info",
            mocker.create_autospec(WindowsRSS.get_adapter_info, return_value=self.adapter_info),
        )
        expected = [
            "36",
            "38",
            "40",
            "42",
            "44",
            "46",
            "48",
            "50",
            "52",
            "54",
            "56",
            "58",
            "60",
            "62",
            "64",
            "66",
            "68",
            "70",
        ]
        assert expected == winrss.rss.get_numa_processor_array()

    def test_get_numa_processor_array_empty(self, winrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_adapter_info",
            mocker.create_autospec(WindowsRSS.get_adapter_info, return_value={}),
        )
        assert [] == winrss.rss.get_numa_processor_array()

    def test_get_numa_processor_array_numa_distance(self, winrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_adapter_info",
            mocker.create_autospec(WindowsRSS.get_adapter_info, return_value=self.adapter_info),
        )
        assert [] == winrss.rss.get_numa_processor_array(numa_distance=1)

    def test_set_profile(self, winrss, mocker):
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
        winrss.rss.set_profile(RSSProfileInfo.CLOSESTPROCESSOR)
        winrss.rss._win_registry.set_feature.assert_called_once_with(
            winrss.rss._win_registry, interface="SLOT 4 Port 2", feature="*RSSProfile", value="1"
        )

    def test_set_profile_empty(self, winrss, mocker):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_enum",
            mocker.create_autospec(WindowsRegistry.get_feature_enum, return_value={}),
        )
        with pytest.raises(
            RSSException, match="ClosestProcessor enum value is not present on interface: SLOT 4 Port 2"
        ):
            winrss.rss.set_profile(RSSProfileInfo.CLOSESTPROCESSOR)

    def test_set_profile_command(self, winrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        cmd = "Set-NetAdapterRss -Name 'SLOT 4 Port 2' -Profile ClosestProcessor"
        winrss.rss.set_profile_command(RSSProfileInfo.CLOSESTPROCESSOR)
        winrss.rss._connection.execute_powershell.assert_called_with(cmd, custom_exception=RSSExecutionError)

    def test_set_numa_node(self, winrss, mocker):
        cmd = "Set-NetAdapterRss -Name 'SLOT 4 Port 2' -NumaNode 65535"
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        winrss.rss.set_numa_node_id(node_id=65535)
        winrss.rss._connection.execute_powershell.assert_called_with(cmd, custom_exception=RSSExecutionError)

    def test_enable(self, winrss, mocker):
        cmd = "Enable-NetAdapterRss -Name 'SLOT 4 Port 2'"
        winrss.rss.enable()
        winrss.rss._connection.execute_powershell.assert_called_with(cmd, custom_exception=RSSExecutionError)

    def test_disable(self, winrss, mocker):
        cmd = "Disable-NetAdapterRss -Name 'SLOT 4 Port 2'"
        winrss.rss.disable()
        winrss.rss._connection.execute_powershell.assert_called_with(cmd, custom_exception=RSSExecutionError)

    def test_get_max_queues(self, winrss, mocker):
        output = {
            "1": "1",
            "2": "2",
            "4": "4",
            "8": "8",
            "16": "16",
            "32": "32",
            "64": "64",
            "PSPath": (
                "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\CurrentControlSet\\"
                "control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0005\\Ndi\\Params\\*NumRssQueues\\Enum"
            ),
            "PSParentPath": (
                "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\CurrentControlSet\\"
                "control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0005\\Ndi\\Params\\*NumRssQueues"
            ),
            "PSChildName": "Enum",
            "PSDrive": "HKLM",
            "PSProvider": "Microsoft.PowerShell.Core\\Registry",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry._convert_interface_to_index",
            mocker.create_autospec(WindowsRegistry._convert_interface_to_index, return_value="5"),
        )
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_registry_path",
            mocker.create_autospec(WindowsRegistry.get_registry_path, return_value=output),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.get_logical_processors_count",
            mocker.create_autospec(get_logical_processors_count, return_value=72),
        )
        assert 64 == winrss.rss.get_max_queues()

    def test_get_max_queues_common_registry(self, winrss, mocker):
        output = {
            "ParamDesc": "Maximum",
            "default": "16",
            "type": "enum",
            "PSPath": (
                "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\CurrentControlSet\\"
                "control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0005\\Ndi\\Params\\*NumRssQueues"
            ),
            "PSParentPath": (
                "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\CurrentControlSet\\"
                "control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0005\\Ndi\\Params"
            ),
            "PSChildName": "*NumRssQueues",
            "PSDrive": "HKLM",
            "PSProvider": "Microsoft.PowerShell.Core\\Registry",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry._convert_interface_to_index",
            mocker.create_autospec(WindowsRegistry._convert_interface_to_index, return_value="5"),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.get_logical_processors_count",
            mocker.create_autospec(get_logical_processors_count, return_value=72),
        )
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_registry_path",
            mocker.create_autospec(WindowsRegistry.get_registry_path, side_effect=[None, output]),
        )
        assert 72 == winrss.rss.get_max_queues()

    def test_get_state(self, winrss, mocker):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=self.feature_list),
        )
        assert winrss.rss.get_state() is State.ENABLED

    def test_get_state_not_exists(self, winrss, mocker):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value={}),
        )
        with pytest.raises(RSSException, match=r"Feature: \*RSS doesn't exists on interface: SLOT 4 Port 2"):
            winrss.rss.get_state()

    def test_get_state_fail(self, winrss, mocker):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value={"*RSS": "0"}),
        )
        assert winrss.rss.get_state() is State.DISABLED

    def test_get_num_queues_used(self, winrss, mocker):
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        winrss.rss._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="4\n", stderr=""
        )
        assert 4 == winrss.rss.get_num_queues_used(traffic_duration=0.1)  # W/A for patching time logic

    def test_get_cpu_ids(self, winrss, mocker):
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        output = dedent(
            """InstanceName
            ------------
            23, intel(r) ethernet connection x722 for 10gbe sfp+ #4
            22, intel(r) ethernet connection x722 for 10gbe sfp+ #4
            21, intel(r) ethernet connection x722 for 10gbe sfp+ #4
            9, intel(r) ethernet connection x722 for 10gbe sfp+ #4
            """
        )
        expected = {"9", "23", "21", "22"}
        winrss.rss._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr=""
        )
        assert expected == winrss.rss.get_cpu_ids(traffic_duration=0.1)  # W/A for patching time logic

    def test_validate_statistics_max_queues(self, winrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_state",
            mocker.create_autospec(WindowsRSS.get_state, return_value=State.ENABLED),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_queues",
            mocker.create_autospec(WindowsRSS.get_queues, return_value=16),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_num_queues_used",
            mocker.create_autospec(WindowsRSS.get_num_queues_used, return_value=16),
        )
        winrss.rss.validate_statistics(traffic_duration=1)
        winrss.rss.get_state.assert_called_once()
        winrss.rss.get_queues.assert_called_once()
        winrss.rss.get_num_queues_used.assert_called_once()

    def test_validate_statistics_max_cpus(self, winrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_state",
            mocker.create_autospec(WindowsRSS.get_state, return_value=State.ENABLED),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_queues",
            mocker.create_autospec(WindowsRSS.get_queues, return_value=16),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_num_queues_used",
            mocker.create_autospec(WindowsRSS.get_num_queues_used, return_value=12),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_max_available_processors",
            mocker.create_autospec(WindowsRSS.get_max_available_processors, return_value=12),
        )
        winrss.rss.validate_statistics(traffic_duration=1)
        winrss.rss.get_state.assert_called_once()
        winrss.rss.get_queues.assert_called_once()
        winrss.rss.get_num_queues_used.assert_called_once()
        winrss.rss.get_max_available_processors.assert_called_once()

    def test_validate_statistics_10g_1_queue_less(self, winrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_state",
            mocker.create_autospec(WindowsRSS.get_state, return_value=State.ENABLED),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_queues",
            mocker.create_autospec(WindowsRSS.get_queues, return_value=16),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_num_queues_used",
            mocker.create_autospec(WindowsRSS.get_num_queues_used, return_value=15),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_max_available_processors",
            mocker.create_autospec(WindowsRSS.get_max_available_processors, return_value=32),
        )
        winrss.rss.validate_statistics(is_10g_adapter=True, traffic_duration=1)
        winrss.rss.get_state.assert_called_once()
        winrss.rss.get_queues.assert_called_once()
        winrss.rss.get_num_queues_used.assert_called_once()
        winrss.rss.get_max_available_processors.assert_called_once()

    def test_validate_statistics_fail_exceed_queues(self, winrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_state",
            mocker.create_autospec(WindowsRSS.get_state, return_value=State.ENABLED),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_queues",
            mocker.create_autospec(WindowsRSS.get_queues, return_value=16),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_num_queues_used",
            mocker.create_autospec(WindowsRSS.get_num_queues_used, return_value=17),
        )
        with pytest.raises(RSSException, match="More than maximum number of RSS queues: 16 but 17 were used"):
            winrss.rss.validate_statistics(traffic_duration=1)
            winrss.rss.get_state.assert_called_once()
            winrss.rss.get_queues.assert_called_once()
            winrss.rss.get_num_queues_used.assert_called_once()

    def test_validate_statistics_fail_max_cpus(self, winrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_state",
            mocker.create_autospec(WindowsRSS.get_state, return_value=State.ENABLED),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_queues",
            mocker.create_autospec(WindowsRSS.get_queues, return_value=16),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_num_queues_used",
            mocker.create_autospec(WindowsRSS.get_num_queues_used, return_value=15),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.windows.WindowsRSS.get_max_available_processors",
            mocker.create_autospec(WindowsRSS.get_max_available_processors, return_value=16),
        )
        with pytest.raises(
            RSSException,
            match="Not all maximum number of RSS queues were used. Max RSS queues: 16, Used RSS queues: 15",
        ):
            winrss.rss.validate_statistics(traffic_duration=1)
            winrss.rss.get_state.assert_called_once()
            winrss.rss.get_queues.assert_called_once()
            winrss.rss.get_num_queues_used.assert_called_once()
            winrss.rss.get_max_available_processors.assert_called_once()
