# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from mfd_connect import SSHConnection
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import InterfaceInfo
from mfd_typing.driver_info import DriverInfo
from mfd_connect.base import ConnectionCompletedProcess

from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_network_adapter.network_interface.feature.buffers.data_structures import RingSize
from mfd_network_adapter.network_interface.feature.driver.esxi import EsxiDriver
from mfd_network_adapter.network_interface.feature.ens.esxi import ESXiFeatureENS
from mfd_network_adapter.network_interface.exceptions import RingSizeParametersException


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

    def test_set_ring_size(self, mocker, interface):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.driver.esxi.EsxiDriver.get_driver_info",
            mocker.create_autospec(
                EsxiDriver.get_driver_info, return_value=DriverInfo(driver_name="i40en", driver_version="2.5.0.28")
            ),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ens.esxi.ESXiFeatureENS.is_ens_enabled",
            mocker.create_autospec(ESXiFeatureENS.is_ens_enabled, return_value=False),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.buffers.set_ring_size(rx_ring_size=1024, tx_ring_size=1024)
        interface.buffers._connection.execute_command.assert_called_with(
            "esxcli network nic ring current set  -r 1024 -t 1024 -n vmnic1", expected_return_codes=[0]
        )

    def test_set_ring_size_ens(self, mocker, interface):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.driver.esxi.EsxiDriver.get_driver_info",
            mocker.create_autospec(
                EsxiDriver.get_driver_info, return_value=DriverInfo(driver_name="i40en_ens", driver_version="2.5.0.28")
            ),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ens.esxi.ESXiFeatureENS.is_ens_enabled",
            mocker.create_autospec(ESXiFeatureENS.is_ens_enabled, return_value=True),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.buffers.set_ring_size(rx_ring_size=1024, tx_ring_size=1024)
        interface.buffers._connection.execute_command.assert_called_with(
            "nsxdp-cli ens uplink ring set  -r 1024 -t 1024 -n vmnic1", expected_return_codes=[0]
        )

    def test_set_ring_size_no_parameters(self, mocker, interface):
        with pytest.raises(RingSizeParametersException, match="No parameters found"):
            interface.buffers.set_ring_size()

    def test_get_ring_size_current(self, mocker, interface):
        output = "   RX: 1024\n   RX Mini: 0\n   RX Jumbo: 0\n   TX: 1024\n"
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.driver.esxi.EsxiDriver.get_driver_info",
            mocker.create_autospec(
                EsxiDriver.get_driver_info, return_value=DriverInfo(driver_name="i40en", driver_version="2.5.0.28")
            ),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ens.esxi.ESXiFeatureENS.is_ens_enabled",
            mocker.create_autospec(ESXiFeatureENS.is_ens_enabled, return_value=False),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.buffers.get_ring_size(preset=False) == RingSize(tx_ring_size=1024, rx_ring_size=1024)
        interface.buffers._connection.execute_command.assert_called_with(
            "esxcli network nic ring current get -n vmnic1", expected_return_codes=[0]
        )

    def test_get_ring_size_preset(self, mocker, interface):
        output = "   Max RX: 4096\n   Max RX Mini: 0\n   Max RX Jumbo: 0\n   Max TX: 4096\n"
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.driver.esxi.EsxiDriver.get_driver_info",
            mocker.create_autospec(
                EsxiDriver.get_driver_info, return_value=DriverInfo(driver_name="i40en", driver_version="2.5.0.28")
            ),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ens.esxi.ESXiFeatureENS.is_ens_enabled",
            mocker.create_autospec(ESXiFeatureENS.is_ens_enabled, return_value=False),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.buffers.get_ring_size(preset=True) == RingSize(tx_ring_size=4096, rx_ring_size=4096)
        interface.buffers._connection.execute_command.assert_called_with(
            "esxcli network nic ring preset get -n vmnic1", expected_return_codes=[0]
        )

    def test_get_ring_size_ens(self, mocker, interface):
        output = "Tx Ring Size: 2048\nRx Ring Size: 1024\n"
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.driver.esxi.EsxiDriver.get_driver_info",
            mocker.create_autospec(
                EsxiDriver.get_driver_info, return_value=DriverInfo(driver_name="icen_ens", driver_version="2.5.0.28")
            ),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ens.esxi.ESXiFeatureENS.is_ens_enabled",
            mocker.create_autospec(ESXiFeatureENS.is_ens_enabled, return_value=True),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.buffers.get_ring_size(preset=True) == RingSize(tx_ring_size=2048, rx_ring_size=1024)
        interface.buffers._connection.execute_command.assert_called_with(
            "nsxdp-cli ens uplink ring get -n vmnic1", expected_return_codes=[0]
        )
