# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import re

import pytest
from mfd_connect import RPyCConnection
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import WindowsInterfaceInfo
from mfd_win_registry import WindowsRegistry
from mfd_win_registry.exceptions import WindowsRegistryException

from mfd_network_adapter.network_interface.feature.mtu import MtuSize
from mfd_network_adapter.network_interface.feature.mtu.data_structures import JumboFramesWindowsInfo
from mfd_network_adapter.network_interface.feature.mtu.exceptions import WindowsMTUException
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface


class TestWindowsMTU:
    @pytest.fixture()
    def port(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.WINDOWS
        name = "Ethernet 3"
        port = WindowsNetworkInterface(
            connection=_connection, interface_info=WindowsInterfaceInfo(name=name, pci_address=pci_address)
        )
        return port

    def test_set_mtu_mtu_set_correctly(self, mocker, port):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=None),
        )
        port.mtu.set_mtu(MtuSize.MTU_4K)
        port.mtu._win_registry.set_feature.assert_called_with(
            port.mtu._win_registry,
            interface="Ethernet 3",
            feature=JumboFramesWindowsInfo.JUMBO_PACKET,
            value=str(MtuSize.MTU_4K),
        )

    def test_set_mtu_error_occurred(self, mocker, port):
        error = "error"
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(
                WindowsRegistry.set_feature,
                side_effect=[WindowsRegistryException(error), WindowsRegistryException(error)],
            ),
        )
        with pytest.raises(
            WindowsMTUException,
            match=re.escape(f"Cannot set any of {port.mtu._mtu_registry_keys}, error occurred: {error}."),
        ):
            port.mtu.set_mtu(MtuSize.MTU_4K)

    def test_get_mtu_correct_mtu_found(self, mocker, port):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(
                WindowsRegistry.get_feature_list, return_value={JumboFramesWindowsInfo.JUMBO_PACKET: MtuSize.MTU_4K}
            ),
        )
        actual_mtu = port.mtu.get_mtu()
        port.mtu._win_registry.get_feature_list.assert_called_with(port.mtu._win_registry, interface="Ethernet 3")

        assert actual_mtu == MtuSize.MTU_4K

    def test_get_mtu_mtu_key_not_found(self, mocker, port):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value={}),
        )
        with pytest.raises(
            WindowsMTUException,
            match=re.escape(
                f"None of the searching registry keys: {port.mtu._mtu_registry_keys} "
                f"are not found for interface {port.name}."
            ),
        ):
            port.mtu.get_mtu()
