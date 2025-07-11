# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""FreeBSD MAC Feature of Network Adapter Owner Unit Tests."""

import pytest
from mfd_connect import RPyCConnection
from mfd_typing import OSName, MACAddress

from mfd_network_adapter.network_adapter_owner.exceptions import MACFeatureExecutionError
from mfd_network_adapter.network_adapter_owner.freebsd import FreeBSDNetworkAdapterOwner


class TestFreeBSDMAC:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.FREEBSD
        host = FreeBSDNetworkAdapterOwner(connection=connection)
        yield host
        mocker.stopall()

    def test_set_mac_successfull(self, owner):
        interface_name = "em0"
        mac_address = MACAddress("00:00:00:00:00:00")

        owner.mac.set_mac(interface_name=interface_name, mac=mac_address)
        owner._connection.execute_command.assert_called_once_with(
            f"ifconfig {interface_name} ether {mac_address}", custom_exception=MACFeatureExecutionError
        )

    def test_set_mac_failure(self, owner):
        interface_name = "em0"
        mac_address = MACAddress("00:00:00:00:00:00")

        owner._connection.execute_command.side_effect = MACFeatureExecutionError(returncode=1, cmd="Error")
        with pytest.raises(MACFeatureExecutionError):
            owner.mac.set_mac(interface_name=interface_name, mac=mac_address)
