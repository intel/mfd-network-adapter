# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import time

import pytest

from mfd_connect import RPyCConnection
from mfd_typing import PCIAddress, OSName
from mfd_network_adapter.data_structures import State
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
            connection=connection, owner=None, interface_info=WindowsInterfaceInfo(name=name, pci_address=pci_address)
        )
        mocker.stopall()
        return interface

    def test_set_adaptive_ifs_enabled(self, mocker, interface):
        """Test for setting Adaptive IFs for windows to enabled."""
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.inter_frame.windows.sleep",
            mocker.create_autospec(time.sleep),
        )
        return_val = None
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=return_val),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        interface.inter_frame.set_adaptive_ifs(enabled=State.ENABLED)
        interface.inter_frame._win_registry.set_feature.assert_called_once_with(
            interface.inter_frame._win_registry, interface="Ethernet", feature="AdaptiveIFS", value="1"
        )

    def test_set_adaptive_ifs_disabled(self, mocker, interface):
        """Test for setting Adaptive IFs for windows to disabled."""
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.inter_frame.windows.sleep",
            mocker.create_autospec(time.sleep),
        )
        return_val = None
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=return_val),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        interface.inter_frame.set_adaptive_ifs(enabled=State.DISABLED)
        interface.inter_frame._win_registry.set_feature.assert_called_once_with(
            interface.inter_frame._win_registry, interface="Ethernet", feature="AdaptiveIFS", value="0"
        )

    def test_get_adaptive_ifs(self, mocker, interface):
        """Test for get Adaptive IFs for windows."""
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
            "AdaptiveIFS": "1",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=output_feature_list),
        )
        assert interface.inter_frame.get_adaptive_ifs() == output_feature_list["AdaptiveIFS"]
