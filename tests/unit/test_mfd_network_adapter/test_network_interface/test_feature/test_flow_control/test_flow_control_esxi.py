# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import time
from unittest.mock import call

import pytest
from mfd_connect import SSHConnection
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import InterfaceInfo
from mfd_connect.base import ConnectionCompletedProcess

from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_network_adapter.network_interface.feature.flow_control.data_structures import PauseParams
from mfd_network_adapter.network_interface.exceptions import FlowControlException, FlowControlExecutionError
from mfd_network_adapter.network_interface.feature.utils.esxi import EsxiUtils


class TestEsxiNetworkInterface:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 75, 0, 1)
        name = "vmnic1"
        _connection = mocker.create_autospec(SSHConnection)
        _connection.get_os_name.return_value = OSName.ESXI

        interface = ESXiNetworkInterface(
            connection=_connection, interface_info=InterfaceInfo(pci_address=pci_address, name=name)
        )
        yield interface
        mocker.stopall()

    def test_set_flow_control_settings(self, mocker, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="", return_code=1, stderr=""
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        interface.flow_control.set_flow_control_settings(rx_pause=True, tx_pause=True, autoneg=False)
        interface.flow_control._connection.execute_command.assert_called_with(
            "esxcli network nic pauseParams set -n vmnic1 -r True -t True -a False",
            custom_exception=FlowControlExecutionError,
            shell=True,
        )

    def test_set_flow_control_settings_error(self, mocker, interface):
        with pytest.raises(FlowControlException, match="No parameters provided"):
            interface.flow_control.set_flow_control_settings()

    def test_get_flow_control_settings(self, mocker, interface):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.utils.esxi.EsxiUtils.get_param",
            mocker.create_autospec(EsxiUtils.get_param, side_effect=["true", "true", "true"]),
        )
        assert interface.flow_control.get_flow_control_settings() == PauseParams(
            Pause_Autonegotiate=True, Pause_RX=True, Pause_TX=True
        )
        EsxiUtils.get_param.assert_has_calls(
            [
                call(interface.flow_control, param="Pause Autonegotiate"),
                call(interface.flow_control, param="Pause RX"),
                call(interface.flow_control, param="Pause TX"),
            ]
        )
