# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
from mfd_common_libs import log_levels
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_const import Speed, Family
from mfd_typing import OSName, PCIDevice
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_interface.feature.utils.data_structures import EepromOption
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface


class TestIPLinux:
    @pytest.fixture
    def interface(self, mocker):
        pci_device = PCIDevice(data="8086:1590")  # Family.CVL, Speed.G100
        name = "eth0"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.LINUX

        interface = LinuxNetworkInterface(
            connection=_connection, interface_info=LinuxInterfaceInfo(pci_device=pci_device, name=name)
        )
        yield interface
        mocker.stopall()

    @pytest.fixture
    def utils(self, interface, mocker):
        mocker.patch("mfd_ethtool.Ethtool")
        yield interface.utils

    def test_is_speed_eq(self, interface):
        assert interface.utils.is_speed_eq(Speed.G100)
        assert not interface.utils.is_speed_eq(Speed.G10)
        assert not interface.utils.is_speed_eq(Speed.G40)

    def test_is_speed_eq_or_higher(self, interface):
        assert interface.utils.is_speed_eq_or_higher(Speed.G100)
        assert interface.utils.is_speed_eq_or_higher(Speed.G10)
        assert interface.utils.is_speed_eq_or_higher(Speed.G40)
        assert not interface.utils.is_speed_eq_or_higher(Speed.G200)

    def test_is_family_eq(self, interface):
        assert interface.utils.is_family_eq(Family.CVL)
        assert not interface.utils.is_family_eq(Family.NNT)
        assert not interface.utils.is_family_eq(Family.FVL)

    def test_set_all_multicast(self, interface, caplog):
        caplog.set_level(log_levels.MODULE_DEBUG)
        # Test when turned_on is True
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.utils.set_all_multicast(True)
        interface._connection.execute_command.assert_called_once_with(
            "ifconfig eth0 allmulti", expected_return_codes={0}
        )
        assert "All-multicast mode enabled on eth0" in caplog.text

        interface._connection.execute_command.reset_mock()

        # Test when turned_on is False
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.utils.set_all_multicast(False)
        interface._connection.execute_command.assert_called_once_with(
            "ifconfig eth0 -allmulti", expected_return_codes={0}
        )
        assert "All-multicast mode disabled on eth0" in caplog.text

    def test_get_coalescing_information(self, utils, interface):
        utils.ethtool.get_coalesce_options.return_value = "coalesce_options"
        result = utils.get_coalescing_information()
        assert result == "coalesce_options"
        utils.ethtool.get_coalesce_options.assert_called_once_with(
            device_name=utils._interface().name, namespace=utils._interface().namespace
        )

    def test_set_coalescing_information(self, utils):
        utils.ethtool.set_coalesce_options.return_value = "set_coalesce_options"
        result = utils.set_coalescing_information("option", "value")
        assert result == "set_coalesce_options"
        utils.ethtool.set_coalesce_options.assert_called_once_with(
            device_name=utils._interface().name,
            namespace=utils._interface().namespace,
            param_name="option",
            param_value="value",
            expected_codes=frozenset([0, 80]),
        )

    def test_change_eeprom(self, utils):
        utils.ethtool.change_eeprom_settings.return_value = "change_eeprom_settings"
        result = utils.change_eeprom(EepromOption.MAGIC, "value")
        assert result == "change_eeprom_settings"
        utils.ethtool.change_eeprom_settings.assert_called_once_with(
            params="magic value", device_name=utils._interface().name, namespace=utils._interface().namespace
        )

    def test_change_eeprom_valid(self, utils):
        utils.ethtool.change_eeprom_settings.return_value = "change_eeprom_settings"
        with pytest.raises(ValueError, match="Invalid EEPROM option: magic"):
            utils.change_eeprom("magic", "value")

    def test_blink(self, utils):
        utils.ethtool.show_visible_port_identification.return_value = "show_visible_port_identification"
        result = utils.blink(3)
        assert result == "show_visible_port_identification"
        utils.ethtool.show_visible_port_identification.assert_called_once_with(
            duration=3, device_name=utils._interface().name, namespace=utils._interface().namespace
        )
