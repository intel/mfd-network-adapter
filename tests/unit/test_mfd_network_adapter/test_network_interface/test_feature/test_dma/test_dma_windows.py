# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import time
from unittest.mock import call

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.exceptions import ConnectionCalledProcessError
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import WindowsInterfaceInfo
from mfd_win_registry import WindowsRegistry

from mfd_network_adapter.network_interface.exceptions import DmaFeatureException
from mfd_network_adapter.network_interface.feature.dma.windows import WindowsDma
from mfd_network_adapter.network_interface.feature.utils.windows import WindowsUtils
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface


class TestDma:
    @pytest.fixture()
    def dma(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.WINDOWS
        mocker.patch("mfd_win_registry.WindowsRegistry", return_value=mocker.Mock())
        mocker.create_autospec(WindowsRegistry)

        name = "eth0"
        pci_address = PCIAddress(0, 0, 0, 0)
        interface = WindowsNetworkInterface(
            connection=conn, interface_info=WindowsInterfaceInfo(name=name, pci_address=pci_address)
        )
        dma_obj = WindowsDma(connection=conn, interface=interface)
        mocker.stopall()
        return dma_obj

    @pytest.fixture()
    def interface(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.WINDOWS
        name = "eth0"
        pci_address = PCIAddress(0, 0, 0, 0)
        interface = WindowsNetworkInterface(
            connection=conn, interface_info=WindowsInterfaceInfo(name=name, pci_address=pci_address)
        )
        return interface

    def test_set_dma_coalescing(self, mocker, dma, interface):
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        interface.dma._win_reg.set_feature = mocker.create_autospec(dma._win_reg.set_feature)
        interface.dma.set_dma_coalescing(value=10)
        interface.dma._win_reg.set_feature.assert_called_once_with("eth0", "DMACoalescing", "10")

    def test_set_dma_coalescing_powershell_method(self, mocker, dma, interface):
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        output = {
            "DriverDesc": "Intel(R)",
            "ProviderName": "Intel",
            "DriverDateData": "{0,",
            "DriverDate": "1-31-2022",
            "DriverVersion": "13.0.13.0",
            "InfPath": "oem18.inf",
            "InfSection": "E1521PM.19H1",
            "IncludedInfs": "{pci.inf}",
            "MatchingDeviceId": "PCI\\VEN_8086&DEV_1521&SUBSYS_00018086",
            "LogLinkStateEvent": "51",
            "ITR": "65535",
            "PciScanMethod": "3",
            "TxIntDelay": "28",
            "MulticastFilterType": "0",
            "VlanFiltering": "0",
            "UniversalInstall": "1",
            "*LsoV1IPv4": "0",
            "EnableWakeOnManagmentOnTCO": "0",
            "WakeOnSlot": "0",
            "WakeOnPort": "0",
            "EnableDca": "1",
            "EnableLLI": "0",
            "LLIPorts": "{}",
            "VMQSupported": "1",
            "*RSSProfile": "4",
            "ReduceSpeedOnPowerDown": "1",
            "CoInstallFlag": "2150110273",
            "*IfType": "6",
            "*MediaType": "0",
            "*PhysicalMediaType": "14",
            "BusType": "5",
            "Characteristics": "132",
            "Port1FunctionNumber": "0",
            "*FlowControl": "0",
            "*TransmitBuffers": "512",
            "*ReceiveBuffers": "256",
            "*TCPChecksumOffloadIPv4": "3",
            "*TCPChecksumOffloadIPv6": "3",
            "*UDPChecksumOffloadIPv4": "3",
            "*UDPChecksumOffloadIPv6": "3",
            "*IPChecksumOffloadIPv4": "3",
            "WaitAutoNegComplete": "2",
            "*InterruptModeration": "1",
            "*PriorityVLANTag": "3",
            "EnablePME": "0",
            "*LsoV2IPv4": "1",
            "*LsoV2IPv6": "1",
            "*JumboPacket": "1514",
            "*SpeedDuplex": "0",
            "PrimarySecondary": "0",
            "*WakeOnPattern": "1",
            "*WakeOnMagicPacket": "1",
            "WakeOnLink": "0",
            "*VMQ": "1",
            "*SRIOV": "1",
            "*RSS": "1",
            "*NumRssQueues": "4",
            "*MaxRssProcessors": "8",
            "*RssBaseProcNumber": "0",
            "*NumaNodeId": "65535",
            "VlanId": "0",
            "EEELinkAdvertisement": "1",
            "DMACoalescing": "10",
            "*PMARPOffload": "1",
            "*PMNSOffload": "1",
            "IfTypePreStart": "6",
            "NetworkInterfaceInstallTimestamp": "133389706821712106",
            "InstallTimeStamp": "{231,",
            "DeviceInstanceID": "PCI\\VEN_8086&DEV_1521&SUBSYS_00018086&REV_01\\507C6FFFFF01FB9000",
            "ComponentId": "PCI\\VEN_8086&DEV_1521&SUBSYS_00018086",
            "NetCfgInstanceId": "{0A64157A-2FA3-40D2-A1F0-521464F0018A}",
            "NetLuidIndex": "32774",
            "PSPath": "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\"
            "CurrentControlSet\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0003",
            "PSParentPath": "Microsoft.PowerShell.Core\\Registry::"
            "HKEY_LOCAL_MACHINE\\system\\CurrentControlSet\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}",
            "PSChildName": "0003",
            "PSDrive": "HKLM",
            "PSProvider": "Microsoft.PowerShell.Core\\Registry",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=output),
        )
        interface.dma.set_dma_coalescing(value=250, method_registry=False)

        calls = [call('Set-NetAdapterAdvancedProperty -Name "eth0" -RegistryKeyword DMACoalescing -RegistryValue 250')]
        interface.dma._connection.execute_powershell.assert_has_calls(calls, any_order=True)

    def test_set_dma_coalescing_powershell_method_invalid_input_value(self, mocker, dma, interface):
        output = {
            "DriverDesc": "Intel(R)",
            "ProviderName": "Intel",
            "DriverDateData": "{0,",
            "DriverDate": "1-31-2022",
            "DriverVersion": "13.0.13.0",
            "InfPath": "oem18.inf",
            "InfSection": "E1521PM.19H1",
            "IncludedInfs": "{pci.inf}",
            "MatchingDeviceId": "PCI\\VEN_8086&DEV_1521&SUBSYS_00018086",
            "LogLinkStateEvent": "51",
            "ITR": "65535",
            "PciScanMethod": "3",
            "TxIntDelay": "28",
            "MulticastFilterType": "0",
            "VlanFiltering": "0",
            "UniversalInstall": "1",
            "*LsoV1IPv4": "0",
            "EnableWakeOnManagmentOnTCO": "0",
            "WakeOnSlot": "0",
            "WakeOnPort": "0",
            "EnableDca": "1",
            "EnableLLI": "0",
            "LLIPorts": "{}",
            "VMQSupported": "1",
            "*RSSProfile": "4",
            "ReduceSpeedOnPowerDown": "1",
            "CoInstallFlag": "2150110273",
            "*IfType": "6",
            "*MediaType": "0",
            "*PhysicalMediaType": "14",
            "BusType": "5",
            "Characteristics": "132",
            "Port1FunctionNumber": "0",
            "*FlowControl": "0",
            "*TransmitBuffers": "512",
            "*ReceiveBuffers": "256",
            "*TCPChecksumOffloadIPv4": "3",
            "*TCPChecksumOffloadIPv6": "3",
            "*UDPChecksumOffloadIPv4": "3",
            "*UDPChecksumOffloadIPv6": "3",
            "*IPChecksumOffloadIPv4": "3",
            "WaitAutoNegComplete": "2",
            "*InterruptModeration": "1",
            "*PriorityVLANTag": "3",
            "EnablePME": "0",
            "*LsoV2IPv4": "1",
            "*LsoV2IPv6": "1",
            "*JumboPacket": "1514",
            "*SpeedDuplex": "0",
            "PrimarySecondary": "0",
            "*WakeOnPattern": "1",
            "*WakeOnMagicPacket": "1",
            "WakeOnLink": "0",
            "*VMQ": "1",
            "*SRIOV": "1",
            "*RSS": "1",
            "*NumRssQueues": "4",
            "*MaxRssProcessors": "8",
            "*RssBaseProcNumber": "0",
            "*NumaNodeId": "65535",
            "VlanId": "0",
            "EEELinkAdvertisement": "1",
            "DMACoalescing": "10",
            "*PMARPOffload": "1",
            "*PMNSOffload": "1",
            "IfTypePreStart": "6",
            "NetworkInterfaceInstallTimestamp": "133389706821712106",
            "InstallTimeStamp": "{231,",
            "DeviceInstanceID": "PCI\\VEN_8086&DEV_1521&SUBSYS_00018086&REV_01\\507C6FFFFF01FB9000",
            "ComponentId": "PCI\\VEN_8086&DEV_1521&SUBSYS_00018086",
            "NetCfgInstanceId": "{0A64157A-2FA3-40D2-A1F0-521464F0018A}",
            "NetLuidIndex": "32774",
            "PSPath": "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\"
            "CurrentControlSet\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0003",
            "PSParentPath": "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\"
            "CurrentControlSet\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}",
            "PSChildName": "0003",
            "PSDrive": "HKLM",
            "PSProvider": "Microsoft.PowerShell.Core\\Registry",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=output),
        )
        command = 'Set-NetAdapterAdvancedProperty -Name "eth0" -RegistryKeyword DMACoalescing -RegistryValue 100"'
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.utils.windows.WindowsUtils.set_advanced_property",
            mocker.create_autospec(
                WindowsUtils.set_advanced_property, side_effect=ConnectionCalledProcessError(returncode=1, cmd=command)
            ),
        )
        with pytest.raises(DmaFeatureException):
            interface.dma.set_dma_coalescing(value=20, method_registry=False)

    def test_get_dma_coalescing(self, mocker, dma, interface):
        output = {
            "DriverDesc": "Intel(R)",
            "ProviderName": "Intel",
            "DriverDateData": "{0,",
            "DriverDate": "1-31-2022",
            "DriverVersion": "13.0.13.0",
            "InfPath": "oem18.inf",
            "InfSection": "E1521PM.19H1",
            "IncludedInfs": "{pci.inf}",
            "MatchingDeviceId": "PCI\\VEN_8086&DEV_1521&SUBSYS_00018086",
            "LogLinkStateEvent": "51",
            "ITR": "65535",
            "PciScanMethod": "3",
            "TxIntDelay": "28",
            "MulticastFilterType": "0",
            "VlanFiltering": "0",
            "UniversalInstall": "1",
            "*LsoV1IPv4": "0",
            "EnableWakeOnManagmentOnTCO": "0",
            "WakeOnSlot": "0",
            "WakeOnPort": "0",
            "EnableDca": "1",
            "EnableLLI": "0",
            "LLIPorts": "{}",
            "VMQSupported": "1",
            "*RSSProfile": "4",
            "ReduceSpeedOnPowerDown": "1",
            "CoInstallFlag": "2150110273",
            "*IfType": "6",
            "*MediaType": "0",
            "*PhysicalMediaType": "14",
            "BusType": "5",
            "Characteristics": "132",
            "Port1FunctionNumber": "0",
            "*FlowControl": "0",
            "*TransmitBuffers": "512",
            "*ReceiveBuffers": "256",
            "*TCPChecksumOffloadIPv4": "3",
            "*TCPChecksumOffloadIPv6": "3",
            "*UDPChecksumOffloadIPv4": "3",
            "*UDPChecksumOffloadIPv6": "3",
            "*IPChecksumOffloadIPv4": "3",
            "WaitAutoNegComplete": "2",
            "*InterruptModeration": "1",
            "*PriorityVLANTag": "3",
            "EnablePME": "0",
            "*LsoV2IPv4": "1",
            "*LsoV2IPv6": "1",
            "*JumboPacket": "1514",
            "*SpeedDuplex": "0",
            "PrimarySecondary": "0",
            "*WakeOnPattern": "1",
            "*WakeOnMagicPacket": "1",
            "WakeOnLink": "0",
            "*VMQ": "1",
            "*SRIOV": "1",
            "*RSS": "1",
            "*NumRssQueues": "4",
            "*MaxRssProcessors": "8",
            "*RssBaseProcNumber": "0",
            "*NumaNodeId": "65535",
            "VlanId": "0",
            "EEELinkAdvertisement": "1",
            "DMACoalescing": "10",
            "*PMARPOffload": "1",
            "*PMNSOffload": "1",
            "IfTypePreStart": "6",
            "NetworkInterfaceInstallTimestamp": "133389706821712106",
            "InstallTimeStamp": "{231,",
            "DeviceInstanceID": "PCI\\VEN_8086&DEV_1521&SUBSYS_00018086&REV_01\\507C6FFFFF01FB9000",
            "ComponentId": "PCI\\VEN_8086&DEV_1521&SUBSYS_00018086",
            "NetCfgInstanceId": "{0A64157A-2FA3-40D2-A1F0-521464F0018A}",
            "NetLuidIndex": "32774",
            "PSPath": "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\"
            "CurrentControlSet\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0003",
            "PSParentPath": "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\"
            "CurrentControlSet\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}",
            "PSChildName": "0003",
            "PSDrive": "HKLM",
            "PSProvider": "Microsoft.PowerShell.Core\\Registry",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=output),
        )
        assert interface.dma.get_dma_coalescing() == 10

    def test_get_dma_coalescing_feature_not_found(self, mocker, dma, interface):
        output = {
            "DriverDesc": "Intel(R)",
            "ProviderName": "Intel",
            "DriverDateData": "{0,",
            "DriverDate": "1-31-2022",
            "DriverVersion": "13.0.13.0",
            "InfPath": "oem18.inf",
            "InfSection": "E1521PM.19H1",
            "IncludedInfs": "{pci.inf}",
            "MatchingDeviceId": "PCI\\VEN_8086&DEV_1521&SUBSYS_00018086",
            "LogLinkStateEvent": "51",
            "ITR": "65535",
            "PciScanMethod": "3",
            "TxIntDelay": "28",
            "MulticastFilterType": "0",
            "VlanFiltering": "0",
            "UniversalInstall": "1",
            "*LsoV1IPv4": "0",
            "EnableWakeOnManagmentOnTCO": "0",
            "WakeOnSlot": "0",
            "WakeOnPort": "0",
            "EnableDca": "1",
            "EnableLLI": "0",
            "LLIPorts": "{}",
            "VMQSupported": "1",
            "*RSSProfile": "4",
            "ReduceSpeedOnPowerDown": "1",
            "CoInstallFlag": "2150110273",
            "*IfType": "6",
            "*MediaType": "0",
            "*PhysicalMediaType": "14",
            "BusType": "5",
            "Characteristics": "132",
            "Port1FunctionNumber": "0",
            "*FlowControl": "0",
            "*TransmitBuffers": "512",
            "*ReceiveBuffers": "256",
            "*TCPChecksumOffloadIPv4": "3",
            "*TCPChecksumOffloadIPv6": "3",
            "*UDPChecksumOffloadIPv4": "3",
            "*UDPChecksumOffloadIPv6": "3",
            "*IPChecksumOffloadIPv4": "3",
            "WaitAutoNegComplete": "2",
            "*InterruptModeration": "1",
            "*PriorityVLANTag": "3",
            "EnablePME": "0",
            "*LsoV2IPv4": "1",
            "*LsoV2IPv6": "1",
            "*JumboPacket": "1514",
            "*SpeedDuplex": "0",
            "PrimarySecondary": "0",
            "*WakeOnPattern": "1",
            "*WakeOnMagicPacket": "1",
            "WakeOnLink": "0",
            "*VMQ": "1",
            "*SRIOV": "1",
            "*RSS": "1",
            "*NumRssQueues": "4",
            "*MaxRssProcessors": "8",
            "*RssBaseProcNumber": "0",
            "*NumaNodeId": "65535",
            "VlanId": "0",
            "EEELinkAdvertisement": "1",
            "*PMARPOffload": "1",
            "*PMNSOffload": "1",
            "IfTypePreStart": "6",
            "NetworkInterfaceInstallTimestamp": "133389706821712106",
            "InstallTimeStamp": "{231,",
            "DeviceInstanceID": "PCI\\VEN_8086&DEV_1521&SUBSYS_00018086&REV_01\\507C6FFFFF01FB9000",
            "ComponentId": "PCI\\VEN_8086&DEV_1521&SUBSYS_00018086",
            "NetCfgInstanceId": "{0A64157A-2FA3-40D2-A1F0-521464F0018A}",
            "NetLuidIndex": "32774",
            "PSPath": "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\"
            "CurrentControlSet\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0003",
            "PSParentPath": "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\"
            "CurrentControlSet\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}",
            "PSChildName": "0003",
            "PSDrive": "HKLM",
            "PSProvider": "Microsoft.PowerShell.Core\\Registry",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=output),
        )
        assert interface.dma.get_dma_coalescing() is None
