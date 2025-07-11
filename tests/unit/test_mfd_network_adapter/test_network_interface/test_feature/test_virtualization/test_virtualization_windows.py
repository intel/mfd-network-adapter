# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test Virtualization Windows."""

from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import WindowsInterfaceInfo, InterfaceType

from mfd_network_adapter.network_interface.exceptions import VirtualizationFeatureNotFoundError
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface


class TestVirtualizationWindows:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet 4"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.WINDOWS

        interface = WindowsNetworkInterface(
            connection=_connection,
            interface_info=WindowsInterfaceInfo(pci_address=pci_address, name=name, interface_type=InterfaceType.PF),
        )
        mocker.stopall()
        return interface

    def test_set_sriov(self, mocker, interface):
        arg_pairs = [(False, False), (False, True), (True, False), (True, True)]
        expected_commands = [
            'Disable-NetAdapterSriov -Name "Ethernet 4"',
            'Disable-NetAdapterSriov -Name "Ethernet 4" -NoRestart',
            'Enable-NetAdapterSriov -Name "Ethernet 4"',
            'Enable-NetAdapterSriov -Name "Ethernet 4" -NoRestart',
        ]

        calls = []
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )

        for pair in zip(arg_pairs, expected_commands):
            args, command = pair
            enable, no_restart = args

            interface.virtualization.set_sriov(enable, no_restart)
            calls.append(mocker.call(command))

        interface._connection.execute_powershell.assert_has_calls(calls)

    def test_set_vmq(self, mocker, interface):
        arg_pairs = [(False, False), (False, True), (True, False), (True, True)]
        expected_commands = [
            'Disable-NetAdapterVmq -Name "Ethernet 4"',
            'Disable-NetAdapterVmq -Name "Ethernet 4" -NoRestart',
            'Enable-NetAdapterVmq -Name "Ethernet 4"',
            'Enable-NetAdapterVmq -Name "Ethernet 4" -NoRestart',
        ]

        calls = []
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )

        for pair in zip(arg_pairs, expected_commands):
            args, command = pair
            enable, no_restart = args

            interface.virtualization.set_vmq(enable, no_restart)
            calls.append(mocker.call(command))

        interface._connection.execute_powershell.assert_has_calls(calls)

    def test_is_vmq_enabled_false(self, interface):
        output = dedent(
            """\
        False
        """
        )
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert False is interface.virtualization.is_vmq_enabled()

    def test_is_sriov_enabled_true(self, interface):
        output = dedent(
            """\
        True
        """
        )
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert True is interface.virtualization.is_sriov_enabled()
        interface._connection.execute_powershell.assert_called_with(
            f"(Get-NetAdapterSriov -Name '{interface.name}').Enabled", expected_return_codes={0}
        )

    def test_is_sriov_enabled_no_match(self, interface):
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        with pytest.raises(
            VirtualizationFeatureNotFoundError,
            match="Could not find looking for field for verifying that SRIOV is enabled.",
        ):
            interface.virtualization.is_sriov_enabled()

    def test_is_sriov_supported_supported(self, interface):
        output = dedent(
            """\
        Supported
        """
        )
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert True is interface.virtualization.is_sriov_supported()

    def test_is_sriov_supported_not_supported(self, interface):
        output = dedent(
            """\
        NotSupported
        """
        )
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert False is interface.virtualization.is_sriov_supported()

    def test_enable_pf_npcap_binding_pass(self, interface):
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.virtualization.enable_pf_npcap_binding()
        interface._connection.execute_powershell.assert_called_with(
            command="Enable-NetAdapterBinding -Name 'Ethernet 4' -DisplayName 'Npcap Packet Driver (NPCAP)'",
            expected_return_codes={0},
        )
