# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test Virtualization Linux."""

import pytest
from uuid import uuid4
from unittest.mock import call

from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_ethtool import Ethtool
from mfd_typing import OSName, PCIAddress
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner
from mfd_network_adapter.network_adapter_owner.exceptions import (
    VirtualizationFeatureCalledError,
    VirtualizationFeatureException,
)

mdev_uuid = uuid4()


class TestLinuxVirtualization:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        host = LinuxNetworkAdapterOwner(connection=connection)
        yield host
        mocker.stopall()

    def test_create_mdev(self, owner):
        pci_address = PCIAddress(domain=0, bus=0, slot=1, func=0)
        driver_name = "idpf-vdcm"
        owner.virtualization.create_mdev(mdev_uuid, pci_address, driver_name)
        owner._connection.execute_command.assert_called_once_with(
            f"echo {mdev_uuid} | tee /sys/bus/pci/devices/0000\\:00\\:01.0/mdev_supported_types/idpf-vdcm/create",
            custom_exception=VirtualizationFeatureCalledError,
        )

    def test_remove_mdev(self, owner):
        owner.virtualization.remove_mdev(mdev_uuid)
        owner._connection.execute_command.assert_called_once_with(
            f"echo 1 > /sys/bus/mdev/devices/{mdev_uuid}/remove",
            custom_exception=VirtualizationFeatureCalledError,
        )

    def test_enable_mdev(self, owner):
        owner.virtualization.enable_mdev(mdev_uuid)
        owner._connection.execute_command.assert_called_once_with(
            f"echo 1 > /sys/bus/mdev/devices/{mdev_uuid}/enable",
            custom_exception=VirtualizationFeatureCalledError,
        )

    def test_disable_mdev(self, owner):
        owner.virtualization.disable_mdev(mdev_uuid)
        owner._connection.execute_command.assert_called_once_with(
            f"echo 0 > /sys/bus/mdev/devices/{mdev_uuid}/enable",
            custom_exception=VirtualizationFeatureCalledError,
        )

    def test_get_all_mdev_uuids(self, owner):
        output = """
        17fdd872-13a5-439a-8b8b-22df82a4e8db  d058edb3-0f64-4d30-a309-b842687a145b  d816578d-cd6f-4fd2-a8e3-d094b11f7967
        """
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert owner.virtualization.get_all_mdev_uuids() == [
            "17fdd872-13a5-439a-8b8b-22df82a4e8db",
            "d058edb3-0f64-4d30-a309-b842687a145b",
            "d816578d-cd6f-4fd2-a8e3-d094b11f7967",
        ]

    def test_get_all_mdev_uuids_missing(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        with pytest.raises(expected_exception=VirtualizationFeatureException):
            owner.virtualization.get_all_mdev_uuids()

    def test_get_pci_address_of_mdev_pf(self, owner):
        output = "0000:00:01.0\n"
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert owner.virtualization.get_pci_address_of_mdev_pf(mdev_uuid=mdev_uuid) == PCIAddress(
            domain=0, bus=0, slot=1, func=0
        )

    def test_get_pci_address_of_mdev_pf_missing(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        with pytest.raises(expected_exception=VirtualizationFeatureException):
            owner.virtualization.get_pci_address_of_mdev_pf(mdev_uuid=mdev_uuid)

    def test_assign_queue_pairs(self, owner):
        qp = {"dma_queue_pairs": 2, "cy_queue_pairs": 4, "dc_queue_pairs": 16}
        owner.virtualization.assign_queue_pairs(mdev_uuid=mdev_uuid, queue_pairs=qp)
        call1 = call(
            f"echo 2 | tee /sys/bus/mdev/devices/{mdev_uuid}/dma_queue_pairs",
            custom_exception=VirtualizationFeatureCalledError,
        )
        call2 = call(
            f"echo 4 | tee /sys/bus/mdev/devices/{mdev_uuid}/cy_queue_pairs",
            custom_exception=VirtualizationFeatureCalledError,
        )
        call3 = call(
            f"echo 16 | tee /sys/bus/mdev/devices/{mdev_uuid}/dc_queue_pairs",
            custom_exception=VirtualizationFeatureCalledError,
        )
        owner._connection.execute_command.assert_has_calls([call1, call2, call3])

    def test_set_vmdq_pass(self, owner, mocker):
        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )

        owner.driver.reload_module = mocker.Mock()
        driver_name = "igb"
        value = 2
        reload_time = 5

        owner.virtualization.set_vmdq(driver_name=driver_name, value=value, reload_time=reload_time)

        owner.driver.reload_module.assert_called_once_with(
            driver_name=driver_name,
            reload_time=reload_time,
            params={"VMDQ": value},
        )
