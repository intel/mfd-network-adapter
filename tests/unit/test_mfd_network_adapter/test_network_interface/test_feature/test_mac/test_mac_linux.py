# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""MAC Feature unit tests."""

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_kernel_namespace import add_namespace_call_command
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_interface.exceptions import MACFeatureExecutionError
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface


class TestLinuxMAC:
    @pytest.fixture(params=[{"namespace": None}, {"namespace": "test_namespace"}])
    def interface(self, mocker, request):
        pci_address = PCIAddress(0, 0, 0, 0)
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.LINUX

        port = LinuxNetworkInterface(
            connection=_connection,
            interface_info=LinuxInterfaceInfo(
                name="eth0", pci_address=pci_address, namespace=request.param.get("namespace")
            ),
        )
        mocker.stopall()
        return port

    def test_get_multicast_mac_number_correct(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="5", return_code=0, stderr=""
        )

        interface.mac.get_multicast_mac_number()
        command = add_namespace_call_command(
            f"ip maddr show {interface.name} | grep link -c", namespace=interface.namespace
        )

        interface._connection.execute_command.assert_called_with(
            command, shell=True, custom_exception=MACFeatureExecutionError
        )
