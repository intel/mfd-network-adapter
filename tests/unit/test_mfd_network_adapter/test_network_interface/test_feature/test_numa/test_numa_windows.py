# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
import time

from mfd_connect import RPyCConnection
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import WindowsInterfaceInfo
from mfd_win_registry import WindowsRegistry


from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface
from mfd_network_adapter.network_interface.feature.link.windows import WindowsLink


class TestWindowsNetworkInterface:
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

    def test_set_numa_node_id(self, mocker, interface):
        """Unit Test for modifying the NUMA Node ID for windows."""
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
        interface.numa.set_numa_node_id(node_id=100)
        interface.numa._win_registry.set_feature.assert_called_once_with(
            interface.numa._win_registry, interface="Ethernet", feature="*NumaNodeId", value=100
        )
