# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import time

import pytest
from textwrap import dedent

from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import WindowsInterfaceInfo
from mfd_win_registry import WindowsRegistry


from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface
from mfd_network_adapter.network_interface.exceptions import QueueFeatureException
from mfd_network_adapter.network_interface.feature.link.windows import WindowsLink


class TestQueueWindows:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet"
        branding_string = "Intel(R) Ethernet Network Adapter E810-C-Q2 #8"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS
        interface = WindowsNetworkInterface(
            connection=connection,
            owner=None,
            interface_info=WindowsInterfaceInfo(name=name, pci_address=pci_address, branding_string=branding_string),
        )
        mocker.stopall()
        return interface

    def test_get_hw_queue_number(self, mocker, interface):
        """Test get hw queue number."""
        interface_id = "11"
        mocker.patch(
            "mfd_win_registry.WindowsRegistry._convert_interface_to_index",
            mocker.create_autospec(WindowsRegistry._convert_interface_to_index, return_value=interface_id),
        )
        get_registry_path_expected_output = {
            "DriverDesc": "Intel(R)",
            "ProviderName": "Intel",
            "DriverDateData": "{0,",
            "DriverDate": "4-18-2023",
            "DriverVersion": "1.13.236.0",
            "InfPath": "oem12.inf",
            "InfSection": "F1592",
            "IncludedInfs": "{pci.inf}",
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
            "*NumVPorts": "5",
            "*NumVFs": "4",
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
            "FecMode": "1",
            "IfTypePreStart": "6",
            "NetworkInterfaceInstallTimestamp": "133268775009839512",
            "InstallTimeStamp": "{231,",
            "DeviceInstanceID": "PCI\\VEN_8086&DEV_1592&SUBSYS_00028086&REV_01\\000100FFFF00000001",
            "ComponentId": "PCI\\VEN_8086&DEV_1592&SUBSYS_00028086",
            "NetCfgInstanceId": "{81C379EE-5F3E-4BE8-B2CC-AF2D0023336D}",
            "NetLuidIndex": "32773",
            "Port": "1",
            "CoInstallFlagSet": "1",
            "IntelDCBxInstalled": "1",
            "PerformanceProfile": "7",
            "PSPath": (
                "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system"
                "\\CurrentControlSet\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\%s\\NicSwitches\\0\\0005"
            ),
            "PSParentPath": (
                "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system"
                "\\CurrentControlSet\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\%s\\NicSwitches\\0"
            ),
            "PSChildName": "0005",
            "PSDrive": "HKLM",
            "PSProvider": "Microsoft.PowerShell.Core\\Registry",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_registry_path",
            mocker.create_autospec(WindowsRegistry.get_registry_path, return_value=get_registry_path_expected_output),
        )

        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        assert interface.queue.get_hw_queue_number() == 5

    def test_get_hw_queue_number_with_error(self, mocker, interface):
        """Test get hw queue number with error."""
        intf_index = "11"
        mocker.patch(
            "mfd_win_registry.WindowsRegistry._convert_interface_to_index",
            mocker.create_autospec(WindowsRegistry._convert_interface_to_index, return_value=intf_index),
        )
        get_registry_path_expected_output = {
            "DriverDesc": "Intel(R)",
            "ProviderName": "Intel",
            "DriverDateData": "{0,",
            "DriverDate": "4-18-2023",
            "DriverVersion": "1.13.236.0",
            "InfPath": "oem12.inf",
            "InfSection": "F1592",
            "IncludedInfs": "{pci.inf}",
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
            "*NumVFs": "5",
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
            "FecMode": "1",
            "IfTypePreStart": "6",
            "NetworkInterfaceInstallTimestamp": "133268775009839512",
            "InstallTimeStamp": "{231,",
            "DeviceInstanceID": "PCI\\VEN_8086&DEV_1592&SUBSYS_00028086&REV_01\\000100FFFF00000001",
            "ComponentId": "PCI\\VEN_8086&DEV_1592&SUBSYS_00028086",
            "NetCfgInstanceId": "{81C379EE-5F3E-4BE8-B2CC-AF2D0023336D}",
            "NetLuidIndex": "32773",
            "Port": "1",
            "CoInstallFlagSet": "1",
            "IntelDCBxInstalled": "1",
            "PerformanceProfile": "7",
            "PSPath": (
                "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system"
                "\\CurrentControlSet\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\%s\\NicSwitches\\0\\0005"
            ),
            "PSParentPath": (
                "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system"
                "\\CurrentControlSet\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\%s\\NicSwitches\\0"
            ),
            "PSChildName": "0005",
            "PSDrive": "HKLM",
            "PSProvider": "Microsoft.PowerShell.Core\\Registry",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_registry_path",
            mocker.create_autospec(WindowsRegistry.get_registry_path, return_value=get_registry_path_expected_output),
        )

        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        with pytest.raises(Exception):
            interface.queue.get_hw_queue_number()

    def test_set_sriov_queue_number(self, mocker, interface):
        """Test set sriov queue number."""
        interface_id = "11"
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.queue.windows.sleep",
            mocker.create_autospec(time.sleep),
        )
        mocker.patch(
            "mfd_win_registry.WindowsRegistry._convert_interface_to_index",
            mocker.create_autospec(WindowsRegistry._convert_interface_to_index, return_value=interface_id),
        )
        path = r"hklm:\system\CurrentControlSet\control\class\{4D36E972-E325-11CE-BFC1-08002BE10318}\0011\NicSwitches\0"
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=None),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        interface.queue.set_sriov_queue_number(value=1)
        interface.queue._win_registry.set_feature.assert_called_once_with(
            interface.queue._win_registry, interface="Ethernet", feature="*NumVFs", value=1, base_path=path
        )

    def test_split_hw_queues(self, interface, mocker) -> None:
        """Test split hw queues."""
        interface.queue.get_hw_queue_number = mocker.create_autospec(
            interface.queue.get_hw_queue_number, return_value=4
        )
        interface.queue.set_sriov_queue_number = mocker.create_autospec(interface.queue.set_sriov_queue_number)
        interface.queue.split_hw_queues()
        interface.queue.set_sriov_queue_number.assert_called_with(value=2)

    def test_get_vmq_queue(self, interface):
        """Test get vmq queue."""
        expected_output = dedent(
            """
            Name 		QueueID		MacAddress 	    VlanID Processor VmFriendlyName
            ----		-------		---------- 	    ------ --------- --------------
            VNIC		0		00-90-FA-30-30-AB	   0:0	     VMHost1
            VNIC		1		00-90-FA-30-30-AI	   0:0	     VMHost2
            """
        )
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            args="", stdout=expected_output, return_code=0, stderr=""
        )
        executed_output = interface.queue.get_vmq_queue()
        interface._connection.execute_powershell.assert_called_with(
            f"Get-NetAdapterVMQQueue -Name '{interface.name}'", custom_exception=QueueFeatureException
        )
        assert expected_output == executed_output

    def test_get_vmq_queue_with_error(self, interface):
        """Test get vmq queue with error."""
        interface._connection.execute_powershell.side_effect = QueueFeatureException(returncode=1, cmd="")
        with pytest.raises(QueueFeatureException):
            interface.queue.get_vmq_queue()

    def test_queues_in_use(self, interface, mocker):
        """Test queues in use."""
        output = "990.203041184617\n100\n200\n590.203041184617\n100.77\n"
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.queue.windows.sleep",
            mocker.create_autospec(time.sleep),
        )
        executed_output = interface.queue.get_queues_in_use(traffic_duration=0.1)  # W/A for time logic flow
        card_name = interface.branding_string
        ps_cmd = rf"(Get-Counter '\Per Processor Network Interface Card Activity(*{card_name})\Received Packets/sec')"
        cmd = rf"{ps_cmd}.CounterSamples.CookedValue"
        interface._connection.execute_powershell.assert_called_with(cmd, expected_return_codes={0})
        assert executed_output == 4

    def test_queues_in_use_negative(self, interface, mocker):
        """Test queues in use no values."""
        output = "0\n0\n0\n0\n0\n"
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.queue.windows.sleep",
            mocker.create_autospec(time.sleep),
        )
        executed_output = interface.queue.get_queues_in_use(traffic_duration=0.1)  # W/A for time logic flow
        card_name = interface.branding_string
        ps_cmd = rf"(Get-Counter '\Per Processor Network Interface Card Activity(*{card_name})\Received Packets/sec')"
        cmd = rf"{ps_cmd}.CounterSamples.CookedValue"
        interface._connection.execute_powershell.assert_called_with(cmd, expected_return_codes={0})
        assert executed_output == 0
