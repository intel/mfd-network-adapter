# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import time
import pytest
from unittest.mock import call

from mfd_connect import RPyCConnection
from mfd_typing import PCIAddress, OSName, PCIDevice
from mfd_typing.network_interface import WindowsInterfaceInfo
from mfd_win_registry import WindowsRegistry
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing.network_interface import InterfaceType
from mfd_connect.util import rpc_copy_utils
from mfd_devcon import Devcon

from mfd_network_adapter.network_interface.feature.ip.data_structures import IPFlag
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface
from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.feature.link.windows import WindowsLink
from mfd_network_adapter.network_interface.exceptions import InterruptFeatureException
from mfd_network_adapter.network_interface.feature.interrupt import WindowsInterrupt
from mfd_network_adapter.network_interface.feature.stats.windows import WindowsStats
from mfd_network_adapter.network_interface.feature.interrupt.data_structures import (
    InterruptModerationRate,
    ITRValues,
    InterruptMode,
    StatusToQuery,
)
from mfd_devcon.parser import DevconResources


class TestWindowsNetworkInterface:
    @pytest.fixture()
    def interface(self, mocker):
        mocker.patch(
            "mfd_connect.util.rpc_copy_utils.copy",
            mocker.create_autospec(rpc_copy_utils.copy),
        )
        mocker.patch("mfd_devcon.Devcon.check_if_available", mocker.create_autospec(Devcon.check_if_available))
        mocker.patch("mfd_devcon.Devcon.get_version", mocker.create_autospec(Devcon.get_version, return_value="1.2"))
        mocker.patch(
            "mfd_devcon.Devcon._get_tool_exec_factory",
            mocker.create_autospec(Devcon._get_tool_exec_factory, return_value="devcon"),
        )
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet"
        pnp_device_id = "PCI\\VEN_8086&DEV_1592&SUBSYS_00028086&REV_01\\000100FFFF00000001"
        pci_device = PCIDevice(data="8086:1592")
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS
        branding_string = "Intel(R) Ethernet Network Adapter E810-C-Q2 #2"
        interface = WindowsNetworkInterface(
            connection=connection,
            owner=None,
            interface_info=WindowsInterfaceInfo(
                name=name,
                pci_address=pci_address,
                pci_device=pci_device,
                pnp_device_id=pnp_device_id,
                branding_string=branding_string,
            ),
        )
        yield interface
        mocker.stopall()

    @pytest.fixture()
    def interface_10g(self, mocker):
        mocker.patch(
            "mfd_connect.util.rpc_copy_utils.copy",
            mocker.create_autospec(rpc_copy_utils.copy),
        )
        mocker.patch("mfd_devcon.Devcon.check_if_available", mocker.create_autospec(Devcon.check_if_available))
        mocker.patch("mfd_devcon.Devcon.get_version", mocker.create_autospec(Devcon.get_version, return_value="1.2"))
        mocker.patch(
            "mfd_devcon.Devcon._get_tool_exec_factory",
            mocker.create_autospec(Devcon._get_tool_exec_factory, return_value="devcon"),
        )
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet"
        pci_device = PCIDevice(data="8086:1563")
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS
        interface = WindowsNetworkInterface(
            connection=connection,
            owner=None,
            interface_info=WindowsInterfaceInfo(name=name, pci_address=pci_address, pci_device=pci_device),
        )
        yield interface
        mocker.stopall()

    @pytest.fixture()
    def interface_cpk(self, mocker):
        mocker.patch(
            "mfd_connect.util.rpc_copy_utils.copy",
            mocker.create_autospec(rpc_copy_utils.copy),
        )
        mocker.patch("mfd_devcon.Devcon.check_if_available", mocker.create_autospec(Devcon.check_if_available))
        mocker.patch("mfd_devcon.Devcon.get_version", mocker.create_autospec(Devcon.get_version, return_value="1.2"))
        mocker.patch(
            "mfd_devcon.Devcon._get_tool_exec_factory",
            mocker.create_autospec(Devcon._get_tool_exec_factory, return_value="devcon"),
        )
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet"
        pnp_device_id = "PCI\\VEN_8086&DEV_1892&SUBSYS_00028086&REV_01\\000100FFFF00000001"
        pci_device = PCIDevice(data="8086:1892")
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS
        branding_string = "Intel(R) Ethernet Network Adapter E810-C-Q2 #2"
        interface = WindowsNetworkInterface(
            connection=connection,
            owner=None,
            interface_info=WindowsInterfaceInfo(
                name=name,
                pci_address=pci_address,
                pci_device=pci_device,
                pnp_device_id=pnp_device_id,
                branding_string=branding_string,
            ),
        )
        yield interface
        mocker.stopall()

    def test_set_interrupt_moderation(self, mocker, interface):
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
        interface.interrupt.set_interrupt_moderation(enabled=State.ENABLED)
        interface.interrupt._win_registry.set_feature.assert_called_once_with(
            interface.interrupt._win_registry, interface="Ethernet", feature="*InterruptModeration", value="1"
        )

    def test_get_interrupt_moderation(self, mocker, interface):
        output_feature_list = {
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
            "EnablePME": "1",
            "*InterruptModeration": "1",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=output_feature_list),
        )
        assert interface.interrupt.get_interrupt_moderation() == "1"

    def test_get_interrupt_moderation_error(self, mocker, interface):
        output_feature_list = {
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
            "EnablePME": "1",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=output_feature_list),
        )

        with pytest.raises(
            InterruptFeatureException, match="InterruptModeration is not present for interface: Ethernet"
        ):
            interface.interrupt.get_interrupt_moderation()

    def test_get_num_interrupt_vectors(self, mocker, interface):
        output = """1024"""
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.interrupt.get_num_interrupt_vectors() == 1024
        interface._connection.execute_powershell.assert_called_with(
            f"(Get-NetAdapterHardwareInfo -Name '{interface.name}').NumMsixTableEntries", expected_return_codes={0}
        )

    def test_get_num_interrupt_vectors_error(self, mocker, interface):
        output = ""
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        with pytest.raises(
            InterruptFeatureException, match="Couldn't find NumMsixTableEntries field for interface: Ethernet"
        ):
            interface.interrupt.get_num_interrupt_vectors()

    def test_get_interrupt_moderation_rate(self, mocker, interface):
        output_feature_list = {
            "DriverDesc": "Intel(R) Ethernet Network Adapter E810-C-Q2",
            "ProviderName": "Intel",
            "DriverDateData": "{0, 64, 246, 183...}",
            "DriverDate": "4-18-2023",
            "DriverVersion": "1.13.236.0",
            "LogLinkStateEvent": "51",
            "EnablePME": "1",
            "*InterruptModeration": "1",
            "ITR": "65535",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=output_feature_list),
        )
        assert interface.interrupt.get_interrupt_moderation_rate() == "65535"

    def test_get_interrupt_moderation_rate_error(self, mocker, interface):
        output_feature_list = {}
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=output_feature_list),
        )
        with pytest.raises(
            InterruptFeatureException, match="InterruptModerationRate is not present for interface: Ethernet"
        ):
            interface.interrupt.get_interrupt_moderation_rate()

    def test_set_interrupt_moderation_rate(self, mocker, interface):
        return_val = None
        feature_enum = {
            "65535": "Adaptive",
            "2000": "Extreme",
            "950": "High",
            "488": "Medium",
            "200": "Low",
            "0": "Off",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_enum",
            mocker.create_autospec(WindowsRegistry.get_feature_enum, return_value=feature_enum),
        )
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
        interface.interrupt.set_interrupt_moderation_rate(InterruptModerationRate.ADAPTIVE)
        interface.interrupt._win_registry.set_feature.assert_called_once_with(
            interface.interrupt._win_registry, interface="Ethernet", feature="ITR", value="65535"
        )

    def test_set_adaptive_interrupt_mode_on(self, mocker, interface):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.interrupt.WindowsInterrupt.set_interrupt_moderation_rate",
            mocker.create_autospec(WindowsInterrupt.set_interrupt_moderation_rate, return_value=None),
        )
        interface.interrupt.set_adaptive_interrupt_mode(State.ENABLED)
        interface.interrupt.set_interrupt_moderation_rate.assert_called_with(
            interface.interrupt, InterruptModerationRate.ADAPTIVE
        )

    def test_set_adaptive_interrupt_mode_off(self, mocker, interface):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.interrupt.WindowsInterrupt.set_interrupt_moderation_rate",
            mocker.create_autospec(WindowsInterrupt.set_interrupt_moderation_rate, return_value=None),
        )
        interface.interrupt.set_adaptive_interrupt_mode(State.DISABLED)
        interface.interrupt.set_interrupt_moderation_rate.assert_called_with(
            interface.interrupt, InterruptModerationRate.OFF
        )

    def test_get_interrupt_mode_legacy(self, mocker, interface):
        output_msi_supported = "0"
        output = "33"
        mocker.patch.object(
            interface._connection,
            "execute_powershell",
            side_effect=[
                ConnectionCompletedProcess(return_code=0, args="", stdout=output_msi_supported, stderr=""),
                ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr=""),
            ],
        )
        cmd = (
            r"(get-itemproperty -path 'hklm:\system\CurrentControlSet\enum"
            rf"\{interface.pnp_device_id}\Device"
            r" Parameters\Interrupt Management\MessageSignaledInterruptProperties')"
        )
        assert interface.interrupt.get_interrupt_mode() == ("legacy", None)
        interface._connection.execute_powershell.assert_has_calls(
            [
                call(f"{cmd}.MSISupported", expected_return_codes={0}),
                call(f"{cmd}.MessageNumberLimit", expected_return_codes={0}),
            ]
        )

    def test_get_interrupt_mode_msix_message_number_limit(self, mocker, interface):
        output_msi_supported = "1"
        output = "33"
        mocker.patch.object(
            interface._connection,
            "execute_powershell",
            side_effect=[
                ConnectionCompletedProcess(return_code=0, args="", stdout=output_msi_supported, stderr=""),
                ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr=""),
            ],
        )
        cmd = (
            r"(get-itemproperty -path 'hklm:\system\CurrentControlSet\enum"
            rf"\{interface.pnp_device_id}\Device"
            r" Parameters\Interrupt Management\MessageSignaledInterruptProperties')"
        )
        assert interface.interrupt.get_interrupt_mode() == ("msix", 33)
        interface._connection.execute_powershell.assert_has_calls(
            [
                call(f"{cmd}.MSISupported", expected_return_codes={0}),
                call(f"{cmd}.MessageNumberLimit", expected_return_codes={0}),
            ]
        )

    def test_get_interrupt_mode_msi(self, mocker, interface):
        output_msi_supported = "1"
        output = "1"
        mocker.patch.object(
            interface._connection,
            "execute_powershell",
            side_effect=[
                ConnectionCompletedProcess(return_code=0, args="", stdout=output_msi_supported, stderr=""),
                ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr=""),
            ],
        )
        cmd = (
            r"(get-itemproperty -path 'hklm:\system\CurrentControlSet\enum"
            rf"\{interface.pnp_device_id}\Device"
            r" Parameters\Interrupt Management\MessageSignaledInterruptProperties')"
        )
        assert interface.interrupt.get_interrupt_mode() == ("msi", None)
        interface._connection.execute_powershell.assert_has_calls(
            [
                call(f"{cmd}.MSISupported", expected_return_codes={0}),
                call(f"{cmd}.MessageNumberLimit", expected_return_codes={0}),
            ]
        )

    def test_get_interrupt_mode_msix(self, mocker, interface):
        output_msi_supported = "1"
        output = "0"
        mocker.patch.object(
            interface._connection,
            "execute_powershell",
            side_effect=[
                ConnectionCompletedProcess(return_code=0, args="", stdout=output_msi_supported, stderr=""),
                ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr=""),
            ],
        )
        cmd = (
            r"(get-itemproperty -path 'hklm:\system\CurrentControlSet\enum"
            rf"\{interface.pnp_device_id}\Device"
            r" Parameters\Interrupt Management\MessageSignaledInterruptProperties')"
        )
        assert interface.interrupt.get_interrupt_mode() == ("msix", None)
        interface._connection.execute_powershell.assert_has_calls(
            [
                call(f"{cmd}.MSISupported", expected_return_codes={0}),
                call(f"{cmd}.MessageNumberLimit", expected_return_codes={0}),
            ]
        )

    def test_get_expected_max_interrupts(self, mocker, interface):
        assert interface.interrupt.get_expected_max_interrupts(ITRValues.LOW) == 40000

    def test_get_expected_max_interrupts_default(self, mocker, interface):
        assert interface.interrupt.get_expected_max_interrupts(ITRValues.OFF) == 2000000

    def test_get_expected_max_interrupts_10g_lro_on(self, mocker, interface_10g):
        output_feature_list = {
            "DriverDesc": "Intel(R) Ethernet Network Adapter E810-C-Q2",
            "ProviderName": "Intel",
            "DriverDateData": "{0, 64, 246, 183...}",
            "DriverDate": "4-18-2023",
            "DriverVersion": "1.13.236.0",
            "LogLinkStateEvent": "51",
            "EnablePME": "1",
            "*InterruptModeration": "1",
            "ITR": "65535",
            "*RscIPv4": "1",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=output_feature_list),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.interrupt.WindowsInterrupt.get_rsc_operational_enabled",
            mocker.create_autospec(WindowsInterrupt.get_rsc_operational_enabled, return_value=False),
        )
        assert interface_10g.interrupt.get_expected_max_interrupts(ITRValues.OFF) == 166666

    def test_get_expected_max_interrupts_lro_on_rsc_enabled(self, mocker, interface_10g):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.interrupt.WindowsInterrupt.get_rsc_operational_enabled",
            mocker.create_autospec(WindowsInterrupt.get_rsc_operational_enabled, return_value=True),
        )
        assert interface_10g.interrupt.get_expected_max_interrupts(ITRValues.OFF) == 166666

    def test_get_rsc_operational_enabled(self, interface_10g):
        interface_10g._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            stdout="False", return_code=0, args=""
        )
        assert interface_10g.interrupt.get_rsc_operational_enabled(IPFlag.IPV4, StatusToQuery.OPERATIONALSTATE) is False

        interface_10g._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            stdout="True", return_code=0, args=""
        )
        assert interface_10g.interrupt.get_rsc_operational_enabled(IPFlag.IPV4, StatusToQuery.OPERATIONALSTATE) is True

    def test_get_expected_max_interrupts_10g(self, mocker, interface_10g):
        assert interface_10g.interrupt.get_expected_max_interrupts(ITRValues.OFF, virtual=True) == 488000

    def test_get_expected_max_interrupts_low_granularity_2_0(self, mocker, interface_10g):
        assert interface_10g.interrupt.get_expected_max_interrupts(ITRValues.LOW) == 20000

    def test_get_expected_max_interrupts_medium(self, mocker, interface_10g):
        assert interface_10g.interrupt.get_expected_max_interrupts(ITRValues.MEDIUM) == 8196

    def test_get_expected_max_interrupts_high(self, mocker, interface_10g):
        assert interface_10g.interrupt.get_expected_max_interrupts(ITRValues.HIGH) == 4237

    def test_get_expected_max_interrupts_balanced(self, mocker, interface_10g):
        assert interface_10g.interrupt.get_expected_max_interrupts(ITRValues.BALANCED) == 3012

    def test_get_expected_max_interrupts_extreme_granularity_2_0(self, mocker, interface_10g):
        assert interface_10g.interrupt.get_expected_max_interrupts(ITRValues.EXTREME) == 2000

    def test_get_expected_max_interrupts_extreme_granularity_1_0(self, mocker, interface):
        assert interface.interrupt.get_expected_max_interrupts(ITRValues.EXTREME) == 4000

    def test_check_itr_value_set(self, mocker, interface):
        stats_out = {"OID_INTEL_CURRENT_ITR": "1000"}
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.windows.WindowsStats.get_stats",
            mocker.create_autospec(WindowsStats.get_stats, return_value=stats_out),
        )
        assert interface.interrupt.check_itr_value_set(1000) is True

    def test_check_itr_value_set_error(self, mocker, interface):
        stats_out = {"OID_INTEL_CURRENT_ITR": "1000"}
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.windows.WindowsStats.get_stats",
            mocker.create_autospec(WindowsStats.get_stats, return_value=stats_out),
        )
        with pytest.raises(InterruptFeatureException, match="Expected value is not matching."):
            interface.interrupt.check_itr_value_set(100)

    def test_check_itr_value_set_generic_error(self, mocker, interface):
        interface._interface_info.interface_type = InterfaceType.VF
        with pytest.raises(
            InterruptFeatureException, match="OID_INTEL_CURRENT_ITR value is supported only on Generic Interface"
        ):
            interface.interrupt.check_itr_value_set(100)

    def test_get_per_queue_interrupts_per_sec(self, mocker, interface):
        output = """

Timestamp : 2/1/2024 11:08:30 AM
Readings  : \\\\b17-27878\\per processor network interface card activity(total, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            3.980376736019154
            \n            \\\\b17-27878\\per processor network interface card activity(71, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            0.01066112850166
            \n            \\\\b17-27878\\per processor network interface card activity(70, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            0.969527239507900
            \n            \\\\b17-27878\\per processor network interface card activity(69, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            2.01066112850165
            \n            \\\\b17-27878\\per processor network interface card activity(68, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            0.989527239507944
            \n            """
        expected_output = {
            "total, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 3.980376736019154,
            "68, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 0.989527239507944,
            "69, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 2.01066112850165,
            "70, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 0.969527239507900,
            "71, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 0.01066112850166,
        }
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.interrupt.get_per_queue_interrupts_per_sec(interval=1, samples=1) == expected_output
        interface.interrupt._connection.execute_powershell.assert_called_with(
            "Get-counter -Counter '\\Per Processor Network Interface Card Activity(*, Intel(R) Ethernet Network Adapter\
 E810-C-Q2 #2)\\Interrupts/sec' -MaxSamples 1 -SampleInterval 1 | Format-List",
            expected_return_codes={0},
        )

    def test__get_performance_collection(self, mocker, interface):
        output = """

Timestamp : 2/1/2024 11:08:30 AM
Readings  : \\\\b17-27878\\per processor network interface card activity(total, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            3.980376736019154
            \n            \\\\b17-27878\\per processor network interface card activity(71, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            0.01066112850166
            \n            \\\\b17-27878\\per processor network interface card activity(70, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            0.969527239507900
            \n            \\\\b17-27878\\per processor network interface card activity(69, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            2.01066112850165
            \n            \\\\b17-27878\\per processor network interface card activity(68, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            0.989527239507944
            \n            """
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        counter = "\\Per Processor Network Interface Card Activity(*, Intel(R) Ethernet Network Adapter\
 E810-C-Q2 #2)\\Interrupts/sec"
        interface.interrupt._get_performance_collection(counter=counter, interval=1, samples=1)
        interface.interrupt._connection.execute_powershell.assert_called_with(
            "Get-counter -Counter '\\Per Processor Network Interface Card Activity(*, Intel(R) Ethernet Network Adapter\
 E810-C-Q2 #2)\\Interrupts/sec' -MaxSamples 1 -SampleInterval 1 | Format-List",
            expected_return_codes={0},
        )

    def test__parse_performance_collection(self, mocker, interface):
        output = {
            " \\b17-27878\\per processor network interface card activity(total, intel(r) ethernet network adapter\
 e810-c-q2 #2)\\interrupts/sec": {"2/1/2024 11:08:30 AM": "3.980376736019154"},
            "\\b17-27878\\per processor network interface card activity(71, intel(r) ethernet network adapter e810-c-q2\
 #2)\\interrupts/sec": {"2/1/2024 11:08:30 AM": "0.01066112850166"},
            "\\b17-27878\\per processor network interface card activity(70, intel(r) ethernet network adapter e810-c-q2\
 #2)\\interrupts/sec": {"2/1/2024 11:08:30 AM": "0.969527239507900"},
            "\\b17-27878\\per processor network interface card activity(69, intel(r) ethernet network adapter e810-c-q2\
 #2)\\interrupts/sec": {"2/1/2024 11:08:30 AM": "2.01066112850165"},
            "\\b17-27878\\per processor network interface card activity(68, intel(r) ethernet network adapter e810-c-q2\
 #2)\\interrupts/sec": {"2/1/2024 11:08:30 AM": "0.989527239507944"},
        }
        expected_output = {
            "total, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 3.980376736019154,
            "68, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 0.989527239507944,
            "69, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 2.01066112850165,
            "70, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 0.9695272395079,
            "71, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 0.01066112850166,
        }

        assert interface.interrupt._parse_performance_collection(raw_perf_data=output) == expected_output

    def test__mean_data(self, mocker, interface):
        output = {"2/6/2024 9:20:03 AM": "3.01636771613808", "2/6/2024 9:20:04 AM": "1.91177721677737"}
        assert interface.interrupt._mean_data(time_data_dict=output) == 2.464072466457725

    def test_get_per_queue_interrupts_per_sec_mulitple_samples(self, mocker, interface):
        output = """

Timestamp : 2/1/2024 11:08:30 AM
Readings  : \\\\b17-27878\\per processor network interface card activity(total, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            3.980376736019154
            \n            \\\\b17-27878\\per processor network interface card activity(71, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            0.01066112850166
            \n            \\\\b17-27878\\per processor network interface card activity(70, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            0.969527239507900
            \n            \\\\b17-27878\\per processor network interface card activity(69, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            2.01066112850165
            \n            \\\\b17-27878\\per processor network interface card activity(68, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            0.989527239507944
            \n


Timestamp : 2/1/2024 11:08:32 AM
Readings  : \\\\b17-27878\\per processor network interface card activity(total, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            0
            \n            \\\\b17-27878\\per processor network interface card activity(71, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            0
            \n            \\\\b17-27878\\per processor network interface card activity(70, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            0
            \n            \\\\b17-27878\\per processor network interface card activity(69, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            0
            \n            \\\\b17-27878\\per processor network interface card activity(68, intel(r) ethernet network \
adapter e810-c-q2 #2)\\interrupts/sec :
            0
            \n            """
        expected_output = {
            "total, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 1.990188368009577,
            "68, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 0.494763619753972,
            "69, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 1.005330564250825,
            "70, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 0.48476361975395,
            "71, intel(r) ethernet network adapter e810-c-q2 #2_interrupts/sec": 0.00533056425083,
        }
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.interrupt.get_per_queue_interrupts_per_sec(interval=2, samples=2) == expected_output
        interface.interrupt._connection.execute_powershell.assert_called_with(
            "Get-counter -Counter '\\Per Processor Network Interface Card Activity(*, Intel(R) Ethernet Network Adapter\
 E810-C-Q2 #2)\\Interrupts/sec' -MaxSamples 2 -SampleInterval 2 | Format-List",
            expected_return_codes={0},
        )

    def test_set_interrupt_mode(self, mocker, interface):
        output = [
            DevconResources(
                device_pnp="PCI\\VEN_8086&DEV_1592&SUBSYS_00028086&REV_01\\000100FFFF00000001",
                name="Intel(R) Ethernet Network Adapter E810-C-Q2 #2",
                resources=["IRQ : 4294966818"],
            )
        ]
        mocker.patch(
            "mfd_devcon.Devcon.get_resources",
            mocker.create_autospec(Devcon.get_resources, return_value=output),
        )
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_itemproperty",
            mocker.create_autospec(WindowsRegistry.set_itemproperty, side_effect=[None, None]),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        path = (
            rf"hklm:\system\CurrentControlSet\enum\{interface.pnp_device_id}\Device "
            r"Parameters\Interrupt Management\MessageSignaledInterruptProperties"
        )
        interface.interrupt.set_interrupt_mode(InterruptMode.MSI)
        interface.interrupt._win_registry.set_itemproperty.assert_has_calls(
            [
                call(interface.interrupt._win_registry, path=path, name="MessageNumberLimit", value="1"),
                call(interface.interrupt._win_registry, path=path, name="MSISupported", value="1"),
            ]
        )

    def test_set_interrupt_mode_error(self, mocker, interface):
        output = [
            DevconResources(
                device_pnp="PCI\\VEN_8086&DEV_1592&SUBSYS_00028086&REV_01\\000100FFFF00000001",
                name="Intel(R) Ethernet Network Adapter E810-C-Q2 #2",
                resources=[],
            )
        ]
        mocker.patch(
            "mfd_devcon.Devcon.get_resources",
            mocker.create_autospec(Devcon.get_resources, return_value=output),
        )
        with pytest.raises(InterruptFeatureException, match="Number of IRQs assigned mismatch"):
            interface.interrupt.set_interrupt_mode(InterruptMode.MSI)

    def test_set_interrupt_mode_not_supported(self, mocker, interface_cpk):
        output = [
            DevconResources(
                device_pnp="PCI\\VEN_8086&DEV_1592&SUBSYS_00028086&REV_01\\000100FFFF00000001",
                name="Intel(R) Ethernet Network Adapter E810-C-Q2 #2",
                resources=[],
            )
        ]
        mocker.patch(
            "mfd_devcon.Devcon.get_resources",
            mocker.create_autospec(Devcon.get_resources, return_value=output),
        )
        with pytest.raises(InterruptFeatureException, match="Not supported interrupt mode"):
            interface_cpk.interrupt.set_interrupt_mode(InterruptMode.LEGACY)

    def test_set_interrupt_mode_mulitple_irqs(self, mocker, interface):
        output = [
            DevconResources(
                device_pnp="PCI\\VEN_8086&DEV_1592&SUBSYS_00028086&REV_01\\000100FFFF00000001",
                name="Intel(R) Ethernet Network Adapter E810-C-Q2 #2",
                resources=[
                    "IRQ : 4294966818",
                    "IRQ : 4294966817",
                    "IRQ : 4294966816",
                    "IRQ : 4294966815",
                    "IRQ : 4294966814",
                    "IRQ : 4294966813",
                    "IRQ : 4294966812",
                    "IRQ : 4294966811",
                    "IRQ : 4294966810",
                    "IRQ : 4294966809",
                    "IRQ : 4294966808",
                    "IRQ : 4294966807",
                    "IRQ : 4294966806",
                    "IRQ : 4294966805",
                    "IRQ : 4294966804",
                    "IRQ : 4294966803",
                    "IRQ : 4294966802",
                    "IRQ : 4294966801",
                    "IRQ : 4294966800",
                    "IRQ : 4294966799",
                    "IRQ : 4294966798",
                    "IRQ : 4294966797",
                    "IRQ : 4294966796",
                    "IRQ : 4294966795",
                    "IRQ : 4294966794",
                    "IRQ : 4294966793",
                    "IRQ : 4294966792",
                    "IRQ : 4294966791",
                    "IRQ : 4294966790",
                    "IRQ : 4294966789",
                    "IRQ : 4294966788",
                    "IRQ : 4294966787",
                    "IRQ : 4294966786",
                    "IRQ : 4294966785",
                    "IRQ : 4294966784",
                    "IRQ : 4294966783",
                    "IRQ : 4294966782",
                    "IRQ : 4294966781",
                    "IRQ : 4294966780",
                    "IRQ : 4294966779",
                    "IRQ : 4294966778",
                    "IRQ : 4294966777",
                    "IRQ : 4294966776",
                    "IRQ : 4294966775",
                    "IRQ : 4294966774",
                    "IRQ : 4294966773",
                    "IRQ : 4294966772",
                    "IRQ : 4294966771",
                    "IRQ : 4294966770",
                    "IRQ : 4294966769",
                    "IRQ : 4294966768",
                    "IRQ : 4294966767",
                    "IRQ : 4294966766",
                ],
            )
        ]
        mocker.patch(
            "mfd_devcon.Devcon.get_resources",
            mocker.create_autospec(Devcon.get_resources, return_value=output),
        )
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_itemproperty",
            mocker.create_autospec(WindowsRegistry.set_itemproperty, side_effect=[None, None]),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        path = (
            rf"hklm:\system\CurrentControlSet\enum\{interface.pnp_device_id}\Device "
            r"Parameters\Interrupt Management\MessageSignaledInterruptProperties"
        )
        interface.interrupt.set_interrupt_mode(InterruptMode.MSIX)
        interface.interrupt._win_registry.set_itemproperty.assert_has_calls(
            [
                call(interface.interrupt._win_registry, path=path, name="MessageNumberLimit", value="33"),
                call(interface.interrupt._win_registry, path=path, name="MSISupported", value="1"),
            ]
        )

    def test__get_supported_interrupt_modes(self, mocker, interface):
        assert interface.interrupt._get_supported_interrupt_modes() == [
            InterruptMode.MSIX,
            InterruptMode.MSI,
            InterruptMode.LEGACY,
        ]

    def test_set_interrupt_mode_not_set(self, mocker, interface):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_itemproperty",
            mocker.create_autospec(WindowsRegistry.set_itemproperty, side_effect=[None]),
        )
        with pytest.raises(InterruptFeatureException, match="Can't set interrupt mode"):
            interface.interrupt.set_interrupt_mode(InterruptMode.MSI)

    def test_set_interrupt_mode_no_irqs_assigned(self, mocker, interface):
        mocker.patch(
            "mfd_devcon.Devcon.get_resources",
            mocker.create_autospec(Devcon.get_resources, return_value=""),
        )
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_itemproperty",
            mocker.create_autospec(WindowsRegistry.set_itemproperty, side_effect=[None, None]),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        with pytest.raises(InterruptFeatureException, match="No IRQs assigned to the interface"):
            interface.interrupt.set_interrupt_mode(InterruptMode.MSI)
