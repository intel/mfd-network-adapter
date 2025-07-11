# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Unit tests of NetworkInterface base class."""

import pytest
from mfd_connect import RPyCConnection
from mfd_typing import PCIAddress, OSName, OSBitness
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_interface.data_structures import SwitchInfo
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface
from mfd_network_adapter.stat_checker.linux import LinuxStatChecker


class TestNetworkInterface:
    """Test cases for NetworkInterface class."""

    @pytest.fixture(params=[{"namespace": None}])
    def interface(self, mocker, request):
        pci_address = PCIAddress(0, 0, 0, 0)
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.LINUX
        _connection.get_os_bitness.return_value = OSBitness.OS_64BIT

        interface_info = LinuxInterfaceInfo(
            name="eth0", pci_address=pci_address, namespace=request.param.get("namespace")
        )

        interface = LinuxNetworkInterface(connection=_connection, interface_info=interface_info)
        interface.stat_checker = mocker.create_autospec(LinuxStatChecker)
        mocker.stopall()
        return interface

    def test_switch_info_is_added(self, interface, mocker):
        switch = mocker.Mock()
        switch_port = "Eth 1/1"
        switch_info = SwitchInfo(switch=switch, port=switch_port)

        interface.switch_info = switch_info
        assert interface.switch_info == switch_info

    def test_switch_info_is_none_when_not_provided(self, interface):
        assert interface.switch_info is None
