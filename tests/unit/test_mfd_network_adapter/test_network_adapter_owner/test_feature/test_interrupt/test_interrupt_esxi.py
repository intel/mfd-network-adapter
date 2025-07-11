# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test Interrupt ESXi."""

import pytest
import time
from textwrap import dedent

from mfd_connect import RPyCConnection
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import InterfaceInfo
from mfd_connect.base import ConnectionCompletedProcess


from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner
from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_network_adapter.network_interface.exceptions import InterruptFeatureException


class TestESXiInterrupt:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.ESXI
        host = ESXiNetworkAdapterOwner(connection=connection)
        yield host
        mocker.stopall()

    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "eth0"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.ESXI
        interface = ESXiNetworkInterface(
            connection=connection, owner=None, interface_info=InterfaceInfo(name=name, pci_address=pci_address)
        )
        mocker.stopall()
        return interface

    @pytest.fixture()
    def interface_1(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 1)
        name = "eth1"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.ESXI
        interface = ESXiNetworkInterface(
            connection=connection, owner=None, interface_info=InterfaceInfo(name=name, pci_address=pci_address)
        )
        mocker.stopall()
        return interface

    def test_set_interrupt_moderation_rate_ixgben(self, mocker, owner, interface, interface_1):
        output = dedent(
            """\
            Name    PCI          Driver      Link Speed      Duplex MAC Address       MTU    Description
vmnic0  0000:4b:00.0 ixgben      Up   40000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Controller XL710
vmnic1  0000:4b:00.1 ixgben      Up   40000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Controller XL710
vmnic2  0000:31:00.0 igbn        Up   1000Mbps   Full   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
vmnic3  0000:31:00.1 igbn        Down 0Mbps      Half   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
vmnic4  0000:31:00.2 igbn        Down 0Mbps      Half   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
vmnic5  0000:31:00.3 igbn        Down 0Mbps      Half   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
"""  # noqa E501
        )
        driver_name = "ixgben"
        owner.get_interfaces = mocker.Mock(return_value=[interface, interface, interface_1])
        interface.driver.get_driver_info = mocker.Mock()
        interface.driver.get_driver_info().driver_name = driver_name
        interface_1.driver.get_driver_info = mocker.Mock()
        interface_1.driver.get_driver_info().driver_name = "driver_name"
        owner.driver.prepare_multiple_param_options = mocker.Mock(return_value="VMDQ=1,2 RxITR=100,100 TxITR=100,100")
        owner.driver.unload_module = mocker.Mock()
        owner.driver.load_module = mocker.Mock()
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        owner._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="", stdout="", stderr=""),
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr=""),
        ]
        owner.interrupt.set_interrupt_moderation_rate(driver_name="ixgben", rxvalue=100, txvalue=100)
        owner.driver.unload_module.assert_called_with(module_name="ixgben")
        owner.driver.load_module.assert_called_with(module_name="ixgben", params="VMDQ=1,2 RxITR=100,100 TxITR=100,100")

    def test_set_interrupt_moderation_rate_i40en(self, mocker, owner, interface, interface_1):
        output = dedent(
            """\
Name    PCI          Driver      Link Speed      Duplex MAC Address       MTU    Description
vmnic0  0000:4b:00.0 i40en       Up   40000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Controller XL710
vmnic1  0000:4b:00.1 i40en       Up   40000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Controller XL710
vmnic2  0000:31:00.0 igbn        Up   1000Mbps   Full   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
vmnic3  0000:31:00.1 igbn        Down 0Mbps      Half   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
vmnic4  0000:31:00.2 igbn        Down 0Mbps      Half   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
vmnic5  0000:31:00.3 igbn        Down 0Mbps      Half   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
"""  # noqa E501
        )
        driver_name = "i40en"
        owner.get_interfaces = mocker.Mock(return_value=[interface, interface, interface_1])
        interface.driver.get_driver_info = mocker.Mock()
        interface.driver.get_driver_info().driver_name = driver_name
        interface_1.driver.get_driver_info = mocker.Mock()
        interface_1.driver.get_driver_info().driver_name = "driver_name"
        owner.driver.prepare_multiple_param_options = mocker.Mock(return_value="VMDQ=1,2 RxITR=100 TxITR=100")
        owner.driver.unload_module = mocker.Mock()
        owner.driver.load_module = mocker.Mock()
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        owner._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="", stdout="", stderr=""),
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr=""),
        ]
        owner.interrupt.set_interrupt_moderation_rate(driver_name="i40en", rxvalue=100, txvalue=100)
        owner.driver.unload_module.assert_called_with(module_name="i40en")
        owner.driver.load_module.assert_called_with(module_name="i40en", params="VMDQ=1,2 RxITR=100 TxITR=100")

    def test_set_interrupt_moderation_rate_error(self, mocker, owner, interface, interface_1):
        output = dedent(
            """\
Name    PCI          Driver      Link Speed      Duplex MAC Address       MTU    Description
vmnic0  0000:4b:00.0 ixgben      Up   40000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Controller XL710
vmnic1  0000:4b:00.1 ixgben      Up   40000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Controller XL710
vmnic2  0000:31:00.0 igbn        Up   1000Mbps   Full   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
vmnic3  0000:31:00.1 igbn        Down 0Mbps      Half   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
vmnic4  0000:31:00.2 igbn        Down 0Mbps      Half   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
vmnic5  0000:31:00.3 igbn        Down 0Mbps      Half   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
"""  # noqa E501
        )
        driver_name = "i40en"
        owner.get_interfaces = mocker.Mock(return_value=[interface, interface, interface_1])
        interface.driver.get_driver_info = mocker.Mock()
        interface.driver.get_driver_info().driver_name = driver_name
        interface_1.driver.get_driver_info = mocker.Mock()
        interface_1.driver.get_driver_info().driver_name = "driver_name"
        owner.driver.unload_module = mocker.Mock()
        owner.driver.load_module = mocker.Mock()
        owner.driver.prepare_multiple_param_options = mocker.Mock(return_value="VMDQ=1,2 RxITR=100 TxITR=100")
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        owner._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="", stdout="", stderr=""),
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr=""),
        ]
        with pytest.raises(InterruptFeatureException, match="Unable to load the module i40en"):
            owner.interrupt.set_interrupt_moderation_rate(driver_name="i40en", rxvalue=100, txvalue=100)

    def test_set_interrupt_moderation_rate_no_parameters(self, mocker, owner, interface):
        with pytest.raises(InterruptFeatureException, match="No parameters provided"):
            owner.interrupt.set_interrupt_moderation_rate(driver_name="i40en")
