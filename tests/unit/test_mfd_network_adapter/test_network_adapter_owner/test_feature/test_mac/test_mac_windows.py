# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Windows MAC Feature of Network Adapter Owner Unit Tests."""

import pytest
from mfd_connect import RPyCConnection
from mfd_typing import OSName, MACAddress
from mfd_win_registry import WindowsRegistry, PropertyType
from mfd_win_registry.exceptions import WindowsRegistryException

from mfd_network_adapter.network_adapter_owner.exceptions import MACFeatureError
from mfd_network_adapter.network_adapter_owner.feature.mac.windows import LOCALLY_ADMINISTERED_ADDRESS
from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner


class TestWindowsMAC:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS
        host = WindowsNetworkAdapterOwner(connection=connection)
        yield host
        mocker.stopall()

    def test_set_mac_successfull(self, owner, mocker):
        interface_name = "Ethernet 2"
        mac_address = MACAddress("00:00:00:00:00:00")

        owner.mac._win_registry = mocker.create_autospec(WindowsRegistry)
        owner.mac.set_mac(interface_name=interface_name, mac=mac_address)
        owner.mac._win_registry.set_feature.assert_called_once_with(
            interface=interface_name,
            feature=LOCALLY_ADMINISTERED_ADDRESS,
            value=str(mac_address),
            prop_type=PropertyType.STRING,
        )

    def test_set_mac_failure_due_to_registry_exception(self, owner, mocker):
        owner.mac._win_registry = mocker.create_autospec(WindowsRegistry)
        owner.mac._win_registry.set_feature.side_effect = WindowsRegistryException
        with pytest.raises(MACFeatureError):
            owner.mac.set_mac(interface_name="Ethernet 2", mac=MACAddress("00:00:00:00:00:00"))
