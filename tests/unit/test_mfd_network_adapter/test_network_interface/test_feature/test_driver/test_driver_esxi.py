# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName
from mfd_typing.driver_info import DriverInfo

from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner
from tests.unit.test_mfd_network_adapter.test_network_adapter_owner.test_esxi_network_owner import TestESXiNetworkOwner


class TestESXiDriverFeature:
    output_esxcli = dedent(
        """   Advertised Auto Negotiation: true
       Advertised Link Modes: Auto, 40000BaseCR4/Full
       Auto Negotiation: true
       Backing DPUId: N/A
       Cable Type: DA
       Current Message Level: 0
       Driver Info:
             Bus Info: 0000:4b:00:0
             Driver: i40en
             Firmware Version: 8.15 0x80009621 1.2829.0
             Version: 2.5.0.28
       Link Detected: true
       Link Status: Up
       Name: vmnic0
       PHYAddress: 0
       Pause Autonegotiate: false
       Pause RX: false
       Pause TX: false
       Supported Ports: DA
       Supports Auto Negotiation: true
       Supports Pause: true
       Supports Wakeon: false
       Transceiver:
       Virtual Address: 00:00:00:00:00:00
       Wakeon: None
    """
    )

    @pytest.fixture()
    def owner(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.ESXI
        host = ESXiNetworkAdapterOwner(connection=conn)
        return host

    @pytest.fixture()
    def interface(self, owner):
        owner._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(
                return_code=0, args="command", stdout=TestESXiNetworkOwner.output_lspci_n, stderr="stderr"
            ),
            ConnectionCompletedProcess(
                return_code=0, args="command", stdout=TestESXiNetworkOwner.output_lspci_p, stderr="stderr"
            ),
            ConnectionCompletedProcess(
                return_code=0, args="command", stdout=TestESXiNetworkOwner.output_esxcfg_nics, stderr="stderr"
            ),
        ]
        interface = owner.get_interface()
        interface._connection.execute_command.side_effect = None
        return interface

    def test_get_firmware_version(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=self.output_esxcli, stderr="stderr"
        )
        assert interface.get_firmware_version() == "8.15 0x80009621 1.2829.0"

    def test_get_driver_info(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=self.output_esxcli, stderr="stderr"
        )
        assert interface.get_driver_info() == DriverInfo(driver_name="i40en", driver_version="2.5.0.28")
