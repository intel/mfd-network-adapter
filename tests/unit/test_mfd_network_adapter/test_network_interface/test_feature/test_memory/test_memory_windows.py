# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from pathlib import Path

import pytest
from mfd_connect import RPyCConnection
from mfd_typing import PCIAddress, OSName, PCIDevice
from mfd_typing.network_interface import WindowsInterfaceInfo

from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface


class TestWindowsNetworkInterface:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet"
        pnp_device_id = "PCI\\VEN_8086&DEV_1592&SUBSYS_00028086&REV_01\\000100FFFF00000001"
        pci_device = PCIDevice(data="8086:1592")
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS
        branding_string = "Intel(R) Ethernet Network Adapter E810-C-Q2 #2"
        interface = WindowsNetworkInterface(
            connection=connection,
            owner=None,
            interface_info=WindowsInterfaceInfo(
                name=name,
                pci_address=pci_address,
                pci_device=pci_device,
                pnp_device_id=pnp_device_id,
                branding_string=branding_string,
            ),
        )
        mocker.stopall()
        return interface

    def test_get_memory_values(self, mocker, interface):
        poolmon_dir_path = "/path/to/poolmon"
        poolmon = mocker.MagicMock()
        interface.memory.poolmon = poolmon
        poolmon.get_tag_for_interface.return_value = "tag"
        log_path = mocker.create_autospec(Path)
        poolmon.pool_snapshot.return_value = log_path
        poolmon.get_values_from_snapshot.return_value = {"Nonp": 4096, "Bytes": 16384, "Tag": "tag"}

        log_path.read_text.return_value = "log content"

        assert interface.memory.get_memory_values(poolmon_dir_path) == {"Nonp": 4096, "Bytes": 16384, "Tag": "tag"}
        poolmon.get_tag_for_interface.assert_called_once_with(interface.service_name)
        poolmon.pool_snapshot.assert_called_once()
        poolmon.get_values_from_snapshot.assert_called_once_with("tag", "log content")
        log_path.unlink.assert_called_once()

    def test_get_memory_values_no_cleanup(self, mocker, interface):
        poolmon_dir_path = "/path/to/poolmon"
        poolmon = mocker.MagicMock()
        interface.memory.poolmon = poolmon
        poolmon.get_tag_for_interface.return_value = "tag"
        log_path = mocker.create_autospec(Path)
        poolmon.pool_snapshot.return_value = log_path
        poolmon.get_values_from_snapshot.return_value = {"Nonp": 4096, "Bytes": 16384, "Tag": "tag"}

        log_path.read_text.return_value = "log content"

        assert interface.memory.get_memory_values(poolmon_dir_path, cleanup_logs=False) == {
            "Nonp": 4096,
            "Bytes": 16384,
            "Tag": "tag",
        }
        poolmon.get_tag_for_interface.assert_called_once_with(interface.service_name)
        poolmon.pool_snapshot.assert_called_once()
        poolmon.get_values_from_snapshot.assert_called_once_with("tag", "log content")
        log_path.unlink.assert_not_called()

    def test_get_memory_values_no_poolmon(self, mocker, interface):
        poolmon_dir_path = "/path/to/poolmon"
        poolmon = mocker.MagicMock()
        poolmon_mock = mocker.patch(
            "mfd_network_adapter.network_interface.feature.memory.windows.Poolmon", return_value=poolmon
        )
        poolmon.get_tag_for_interface.return_value = "tag"
        log_path = mocker.create_autospec(Path)
        poolmon.pool_snapshot.return_value = log_path
        poolmon.get_values_from_snapshot.return_value = {"Nonp": 4096, "Bytes": 16384, "Tag": "tag"}

        log_path.read_text.return_value = "log content"

        assert interface.memory.get_memory_values(poolmon_dir_path) == {"Nonp": 4096, "Bytes": 16384, "Tag": "tag"}
        poolmon_mock.assert_called_once_with(
            connection=interface._connection, absolute_path_to_binary_dir=poolmon_dir_path
        )
        poolmon.get_tag_for_interface.assert_called_once_with(interface.service_name)
        poolmon.pool_snapshot.assert_called_once()
        poolmon.get_values_from_snapshot.assert_called_once_with("tag", "log content")
        log_path.unlink.assert_called_once()
