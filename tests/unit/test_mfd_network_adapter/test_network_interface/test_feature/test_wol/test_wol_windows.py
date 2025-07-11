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
from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.exceptions import WolFeatureException


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

    def test_set_wol_option_enabled(self, mocker, interface):
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
        interface.wol.set_wol_option(state=State.ENABLED)
        interface.wol._win_registry.set_feature.assert_called_once_with(
            interface.wol._win_registry, interface="Ethernet", feature="EnablePME", value="1"
        )

    def test_set_wol_option_disabled(self, mocker, interface):
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
        interface.wol.set_wol_option(state=State.DISABLED)
        interface.wol._win_registry.set_feature.assert_called_once_with(
            interface.wol._win_registry, interface="Ethernet", feature="EnablePME", value="0"
        )

    def test_get_wol_option(self, mocker, interface):
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
        assert interface.wol.get_wol_option() is State.ENABLED

    def test_get_wol_option_error(self, mocker, interface):
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
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=output_feature_list),
        )

        with pytest.raises(WolFeatureException, match="EnablePME is not present for interface: Ethernet"):
            interface.wol.get_wol_option()
