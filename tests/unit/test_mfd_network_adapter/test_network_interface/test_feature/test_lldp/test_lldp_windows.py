# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
import time
from unittest.mock import call

from mfd_connect import RPyCConnection
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import WindowsInterfaceInfo
from mfd_win_registry import WindowsRegistry, PropertyType


from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface
from mfd_network_adapter.network_interface.feature.link.windows import WindowsLink
from mfd_network_adapter.data_structures import State


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

    def test_set_fwlldp(self, mocker, interface):
        """Unit Test for Setting FW LLDP for windows."""
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
        interface.lldp.set_fwlldp(enabled=State.ENABLED)
        interface.lldp._win_registry.set_feature.assert_has_calls(
            [
                call(
                    interface.lldp._win_registry,
                    interface="Ethernet",
                    feature="*QOS",
                    value="0",
                    prop_type=PropertyType.STRING,
                ),
                call(
                    interface.lldp._win_registry,
                    interface="Ethernet",
                    feature="DisableLLDP",
                    value="1",
                    prop_type=PropertyType.STRING,
                ),
            ]
        )
