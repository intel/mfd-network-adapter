# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from mfd_connect import RPyCConnection
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import WindowsInterfaceInfo
from mfd_win_registry import WindowsRegistry
from mfd_win_registry.constants import BuffersAttribute

from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface


class TestBuffers:
    @pytest.fixture()
    def interface(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.WINDOWS
        mocker.patch("mfd_win_registry.WindowsRegistry", return_value=mocker.Mock())
        mocker.create_autospec(WindowsRegistry)

        pci_address = PCIAddress(0, 0, 0, 0)
        interface = WindowsNetworkInterface(
            connection=conn, interface_info=WindowsInterfaceInfo(pci_address=pci_address, name="SLOT 5 Port 1")
        )
        return interface

    def test_get_rx_buffers(self, interface, mocker):
        interface.buffers._win_reg.get_rx_buffers = mocker.create_autospec(WindowsRegistry.get_rx_buffers)
        interface.buffers.get_rx_buffers()
        interface.buffers._win_reg.get_rx_buffers.assert_called_once_with("SLOT 5 Port 1", BuffersAttribute.NONE)

    def test_get_rx_buffers_with_attr(self, interface, mocker):
        interface.buffers._win_reg.get_rx_buffers = mocker.create_autospec(WindowsRegistry.get_rx_buffers)
        interface.buffers.get_rx_buffers(BuffersAttribute.MAX)
        interface.buffers._win_reg.get_rx_buffers.assert_called_once_with("SLOT 5 Port 1", BuffersAttribute.MAX)

    def test_get_tx_buffers(self, interface, mocker):
        interface.buffers._win_reg.get_tx_buffers = mocker.create_autospec(WindowsRegistry.get_tx_buffers)
        interface.buffers.get_tx_buffers()
        interface.buffers._win_reg.get_tx_buffers.assert_called_once_with("SLOT 5 Port 1", BuffersAttribute.NONE)

    def test_get_tx_buffers_with_attr(self, mocker, interface):
        interface.buffers._win_reg.get_tx_buffers = mocker.create_autospec(WindowsRegistry.get_tx_buffers)
        interface.buffers.get_tx_buffers(BuffersAttribute.MIN)
        interface.buffers._win_reg.get_tx_buffers.assert_called_once_with("SLOT 5 Port 1", BuffersAttribute.MIN)
