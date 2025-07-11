# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Offload Feature ESXi Unit Tests."""

import pytest
from mfd_connect import RPyCConnection
from mfd_common_libs import log_levels
from mfd_typing import PCIAddress, OSName, OSBitness
from mfd_typing.network_interface import InterfaceInfo
from mfd_connect.base import ConnectionCompletedProcess

from mfd_network_adapter.network_interface.exceptions import OffloadFeatureException
from mfd_network_adapter.network_interface.feature.driver.esxi import EsxiDriver
from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_network_adapter.data_structures import State


class TestESXiNetworkInterfaceOffload:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "vmnic4"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.ESXI
        connection.get_os_bitness.return_value = OSBitness.OS_64BIT

        interface = ESXiNetworkInterface(
            connection=connection,
            interface_info=InterfaceInfo(name=name, pci_address=pci_address),
        )

        interface._driver = mocker.create_autospec(EsxiDriver)
        interface._driver.get_driver_info.return_value.driver_name = "ixgben"
        mocker.stopall()
        yield interface

    def test_get_offload_name_for_tools_successfully(self, interface):
        offload_name = interface.offload.get_offload_name_for_tools("tso")
        assert offload_name == {"esxcli": "ipv4tso", "vsish": "CAP_TSO"}

    def test_get_offload_name_for_tools_raises_for_unsupported_offload(self, interface):
        with pytest.raises(OffloadFeatureException):
            interface.offload.get_offload_name_for_tools("unsupported")

    def test_change_offload_setting_successfully_for_supported_offload(self, interface, mocker):
        mock_logger = mocker.patch("mfd_network_adapter.network_interface.feature.offload.esxi.logger")

        interface.offload.change_offload_setting("tso", enable=State.ENABLED)

        interface._connection.execute_command.assert_called_once()
        mock_logger.log.assert_any_call(level=log_levels.MODULE_DEBUG, msg="Changing tso offload setting to True")
        mock_logger.log.assert_any_call(level=log_levels.MODULE_DEBUG, msg="tso offload setting changed successfully.")

    def test_change_offload_setting_raises_for_unsupported_offload(self, interface):
        with pytest.raises(OffloadFeatureException):
            interface.offload.change_offload_setting("unsupported", enable=State.ENABLED)

    def test_change_offload_setting_geneve_for_icen_driver(self, interface, mocker):
        interface._driver.get_driver_info.return_value.driver_name = "icen"
        interface.offload.change_offload_setting("geneve", enable=State.ENABLED)
        interface._connection.execute_command.assert_any_call(
            command="esxcli network nic software set -n vmnic4 --geneveoffload=false"
        )

    def test_change_offload_setting_geneve_for_ixgben_driver(self, interface):
        interface.offload.change_offload_setting("geneve", enable=State.DISABLED)
        interface._connection.execute_command.assert_any_call(
            command="esxcli network nic software set -n vmnic4 --obo=true"
        )

    def test_change_offload_setting_tso256k(self, interface, mocker):
        interface.offload.set_hw_capabilities = mocker.patch.object(
            interface.offload, "set_hw_capabilities", return_value=None
        )
        interface.offload.change_offload_setting("tso256k", enable=State.ENABLED)
        interface.offload.set_hw_capabilities.assert_called_once_with("tso256k", State.ENABLED)

    def test_check_offload_setting_returns_true_for_enabled(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="1"
        )
        result = interface.offload.check_offload_setting("tso")
        assert result is True

    def test_check_offload_setting_returns_false_for_disabled(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="0"
        )
        result = interface.offload.check_offload_setting("tso")
        assert result is False

    def test_check_offload_setting_raises_for_unsupported_offload(self, interface):
        with pytest.raises(OffloadFeatureException):
            interface.offload.check_offload_setting("unsupported")

    def test_set_hw_capabilities_enables_capability(self, interface):
        interface.offload.set_hw_capabilities("tso256k", State.ENABLED)
        interface._connection.execute_command.assert_called_once_with(
            command="vsish -e set /net/pNics/vmnic4/hwCapabilities/CAP_TSO256k 1", expected_return_codes={0, 2}
        )

    def test_set_hw_capabilities_disables_capability(self, interface):
        interface.offload.set_hw_capabilities("tso256k", State.DISABLED)
        interface._connection.execute_command.assert_called_once_with(
            command="vsish -e set /net/pNics/vmnic4/hwCapabilities/CAP_TSO256k 0", expected_return_codes={0, 2}
        )

    def test_set_hw_capabilities_raises_on_invalid_capability(self, interface):
        with pytest.raises(OffloadFeatureException):
            interface.offload.set_hw_capabilities("INVALID_CAP", State.ENABLED)

    def test_get_hw_capabilities_returns_enabled(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="1"
        )
        result = interface.offload._get_hw_capabilities("tso")
        assert result == "1"

    def test_get_hw_capabilities_returns_disabled(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="0"
        )
        result = interface.offload._get_hw_capabilities("tso")
        assert result == "0"

    def test_get_hw_capabilities_calls_execute_command_with_correct_args(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="1"
        )
        interface.offload._get_hw_capabilities("tso")
        interface._connection.execute_command.assert_called_once_with(
            command="vsish -e get /net/pNics/vmnic4/hwCapabilities/CAP_TSO", expected_return_codes={0}
        )
