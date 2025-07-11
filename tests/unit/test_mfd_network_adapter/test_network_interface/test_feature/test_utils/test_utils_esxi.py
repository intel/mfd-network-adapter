# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName, PCIDevice
from mfd_typing.network_interface import InterfaceInfo

from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_network_adapter.network_interface.exceptions import UtilsException


class TestUtilsESXi:
    @pytest.fixture
    def interface(self, mocker):
        pci_device = PCIDevice(data="8086:1590")  # Family.CVL, Speed.G100
        name = "vmnic0"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.ESXI

        interface = ESXiNetworkInterface(
            connection=_connection, interface_info=InterfaceInfo(pci_device=pci_device, name=name)
        )
        yield interface
        mocker.stopall()

    def test_get_param(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="   Pause RX: true", stderr=""
        )
        assert interface.utils.get_param(param="Pause RX") == "true"

        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        with pytest.raises(UtilsException):
            interface.utils.get_param(param="Pause RX")
