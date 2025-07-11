# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test Driver ESXi."""

import pytest

from mfd_connect import RPyCConnection
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import InterfaceInfo

from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner
from mfd_network_adapter.network_adapter_owner.exceptions import ESXiDriverLinkTimeout
from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_network_adapter.network_interface.feature.link import LinkState


class TestESXiDriver:
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
        yield interface
        mocker.stopall()

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

    @pytest.fixture()
    def interface_2(self, mocker):
        pci_address = PCIAddress(0, 2, 0, 0)
        name = "eth2"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.ESXI
        interface = ESXiNetworkInterface(
            connection=connection, owner=None, interface_info=InterfaceInfo(name=name, pci_address=pci_address)
        )
        mocker.stopall()
        return interface

    def test_prepare_values_sharing_same_driver(self, owner, interface, interface_2, mocker):
        driver_name = "ixgben"
        owner.get_interfaces = mocker.Mock(return_value=[interface, interface, interface_2])
        interface.driver.get_driver_info = mocker.Mock()
        interface.driver.get_driver_info().driver_name = driver_name
        interface_2.driver.get_driver_info = mocker.Mock()
        interface_2.driver.get_driver_info().driver_name = "driver_name"
        owner.driver.get_module_params_as_dict = mocker.Mock(return_value={"vmdq": "4,4"})
        res = "vmdq=4,4"
        assert res == owner.driver.prepare_values_sharing_same_driver(driver_name=driver_name, param="vmdq", value=4)

    def test_prepare_module_param_options_pass(self, owner, mocker):
        owner.driver.get_module_params_as_dict = mocker.Mock(return_value={"vmdq": "1,2,3,4", "sriov": "0,0,1,1"})
        assert "vmdq=4,3,2,1 sriov=0,0,1,1" == owner.driver.prepare_module_param_options(
            module_name="igben", param="vmdq", values=["4", "3", "2", "1"]
        )

    def test_prepare_module_param_options_empty_module_params(self, owner, mocker):
        owner.driver.get_module_params_as_dict = mocker.Mock(return_value={})
        assert "vmdq=4,3,2,1" == owner.driver.prepare_module_param_options(
            module_name="igben", param="vmdq", values=["4", "3", "2", "1"]
        )

    def test_prepare_multiple_param_options_pass(self, owner, mocker):
        owner.driver.get_module_params_as_dict = mocker.Mock(return_value={"VMDQ": "1,2", "DRSS": "0,1"})
        assert "VMDQ=1,2 DRSS=0,1 RxITR=100" == owner.driver.prepare_multiple_param_options(
            module_name="i40en", param_dict={"RxITR": "100"}
        )

    def test_prepare_multiple_param_options_empty_params(self, owner, mocker):
        owner.driver.get_module_params_as_dict = mocker.Mock(return_value={})
        assert "RxITR=100" == owner.driver.prepare_multiple_param_options(
            module_name="i40en", param_dict={"RxITR": "100"}
        )

    def test_wait_for_all_interfaces_load(self, mocker, owner, interface):
        mock_timeout_counter = mocker.patch(
            "mfd_network_adapter.network_adapter_owner.feature.driver.esxi.TimeoutCounter"
        )
        mock_timeout_counter.return_value.__bool__.side_effect = [False, False, False, False, True]
        mocker.patch("mfd_network_adapter.network_adapter_owner.feature.driver.esxi.sleep")
        interface.driver.get_driver_info = mocker.Mock(return_value=mocker.Mock(driver_name="test_driver"))
        owner._get_esxcfg_nics = mocker.Mock(
            return_value={
                PCIAddress(0, 0, 0, 0): {
                    "name": "name",
                    "mac": "mac",
                    "branding_string": "branding_string",
                    "driver": "test_driver",
                    "link": LinkState.UP,
                    "speed": "speed",
                    "duplex": "duplex",
                    "mtu": "mtu",
                }
            }
        )
        owner.driver.wait_for_all_interfaces_load("test_driver")

        owner._get_esxcfg_nics.assert_called()

    def test_wait_for_all_interfaces_load_timeout(self, owner, interface, mocker):
        mock_timeout_counter = mocker.patch(
            "mfd_network_adapter.network_adapter_owner.feature.driver.esxi.TimeoutCounter"
        )
        mock_timeout_counter.return_value.__bool__.side_effect = [False, False, False, False, True]
        mocker.patch("mfd_network_adapter.network_adapter_owner.feature.driver.esxi.sleep")
        interface.driver.get_driver_info = mocker.Mock(return_value=mocker.Mock(driver_name="test_driver"))
        owner._get_esxcfg_nics = mocker.Mock(
            return_value={
                PCIAddress(0, 0, 0, 0): {
                    "name": "name",
                    "mac": "mac",
                    "branding_string": "branding_string",
                    "driver": "driver",
                    "link": LinkState.DOWN,
                    "speed": "speed",
                    "duplex": "duplex",
                    "mtu": "mtu",
                }
            }
        )
        with pytest.raises(ESXiDriverLinkTimeout):
            owner.driver.wait_for_all_interfaces_load("test_driver")

        owner._get_esxcfg_nics.assert_called()
