# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test Virtualization ESXi."""

import pytest

from textwrap import dedent

from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import InterfaceInfo

from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner
from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_network_adapter.network_interface.exceptions import VirtualizationFeatureError


class TestESXiVirtualization:
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

    def test_verify_vmdq_when_equal_desired_value(self, owner, interface, mocker):
        desired_value = 10
        interface.queue.get_queues_info = mocker.Mock(return_value={"maxQueues": 10})
        owner.virtualization.verify_vmdq(interface, desired_value)
        interface.queue.get_queues_info.assert_called_with("rx")

    def test_verify_vmdq_when_not_equal_desired_value(self, owner, interface, mocker):
        desired_value = 10
        interface.queue.get_queues_info = mocker.Mock(return_value={"maxQueues": 8})
        with pytest.raises(
            VirtualizationFeatureError, match=f"VMDQ value: 8 is different than expected: {desired_value}."
        ):
            owner.virtualization.verify_vmdq(interface, desired_value)

    def test_set_vmdq(self, owner, interface, interface_2, mocker):
        driver_name = "ixgben"
        reload_time = 15
        owner.get_interfaces = mocker.Mock(return_value=[interface, interface, interface_2])
        interface.driver.get_driver_info = mocker.Mock()
        interface.driver.get_driver_info().driver_name = driver_name
        interface_2.driver.get_driver_info = mocker.Mock()
        interface_2.driver.get_driver_info().driver_name = "driver_name"
        owner.driver.prepare_values_sharing_same_driver = mocker.Mock(return_value="vmdq=8,8 sriov=0,0")
        owner.driver.reload_module = mocker.Mock()
        owner.virtualization.set_vmdq(driver_name="ixgben", value=8, reload_time=reload_time)
        owner.driver.reload_module.assert_called_with(
            module_name=driver_name, reload_time=reload_time, params="vmdq=8,8 sriov=0,0"
        )

    def test_set_num_queue_pairs_per_vf(self, owner, interface, interface_2, mocker):
        driver_name = "ixgben"
        reload_time = 15
        owner.get_interfaces = mocker.Mock(return_value=[interface, interface, interface_2])
        interface.driver.get_driver_info = mocker.Mock()
        interface.driver.get_driver_info().driver_name = driver_name
        interface_2.driver.get_driver_info = mocker.Mock()
        interface_2.driver.get_driver_info().driver_name = "driver_name"
        owner.driver.prepare_values_sharing_same_driver = mocker.Mock(return_value="NumQPsPerVF=20,20 sriov=0,0")
        owner.driver.reload_module = mocker.Mock()
        owner.virtualization.set_num_queue_pairs_per_vf(driver_name="ixgben", value=20, reload_time=reload_time)
        owner.driver.reload_module.assert_called_with(
            module_name=driver_name, reload_time=reload_time, params="NumQPsPerVF=20,20 sriov=0,0"
        )

    def test__prepare_vmdq_values_for_interface_two_cards(self, mocker, owner, interface, interface_1, interface_2):
        driver_name = "ixgben"
        owner.get_interfaces = mocker.Mock(return_value=[interface, interface_1, interface_2])
        module_params = {"vmdq": "4,4,0", "sriov": "0,0,0"}
        owner.driver.get_module_params_as_dict = mocker.Mock(return_value=module_params)
        interface.driver.get_driver_info = interface_1.driver.get_driver_info = mocker.Mock()
        interface.driver.get_driver_info().driver_name = interface_1.driver.get_driver_info().driver_name = driver_name

        interface_2.driver.get_driver_info = mocker.Mock()
        interface_2.driver.get_driver_info().driver_name = driver_name
        interface_2.queue.get_queues_info = mocker.Mock(return_value={"maxQueues": 0})
        assert "vmdq=4,4,0 sriov=0,0,0" == owner.virtualization._prepare_vmdq_values_for_interface(
            interface=interface, value=4
        )

    def test_set_vmdq_on_interface_two_cards(self, owner, interface, interface_1, interface_2, mocker):
        driver_name = "ixgben"
        reload_time = 15
        owner.get_interfaces = mocker.Mock(return_value=[interface, interface_1, interface_2])
        interface.driver.get_driver_info = interface_1.driver.get_driver_info = mocker.Mock()
        interface.driver.get_driver_info().driver_name = interface_1.driver.get_driver_info().driver_name = driver_name

        interface_2.driver.get_driver_info = mocker.Mock()
        interface_2.driver.get_driver_info().driver_name = driver_name
        interface_2.queue.get_queues_info = mocker.Mock(return_value={"maxQueues": 8})

        module_params = {"vmdq": "1,1,8"}
        owner.driver.get_module_params_as_dict = mocker.Mock(return_value=module_params)
        owner.driver.reload_module = mocker.Mock()
        owner.virtualization.set_vmdq_on_interface(interface=interface, value=1, reload_time=reload_time)
        owner.driver.reload_module.assert_called_with(
            module_name=driver_name, reload_time=reload_time, params="vmdq=1,1,8"
        )

    def test_get_vm_vf_id(self, owner, interface):
        output1 = dedent(
            """\
        FR-9-Sophia
           World ID: 2104268
           Process ID: 0
           VMX Cartel ID: 2104267
           UUID: 56 4d 67 fa b9 f2 da 11-aa 79 47 50 07 db 8b 71
           Display Name: FR-9-Sophia
           Config File: /vmfs/volumes/60403711-c7bb0e92-7219-a4bf01645e6b/zoe/zoe.vmx

        FR-cli7-monica
           World ID: 2381189
           Process ID: 0
           VMX Cartel ID: 2381188
           UUID: 56 4d 6e 28 c8 5b fe b1-76 37 43 c0 fc 09 36 e4
           Display Name: FR-cli7-monica
           Config File: /vmfs/volumes/60403711-c7bb0e92-7219-a4bf01645e6b/FR-cli7-monica/FR-cli7-monica.vmx
        """
        )

        output2 = dedent(
            """\
            VF ID  Active  PCI Address     Owner World ID
            -----  ------  --------------  --------------
            0      true    0000:03:00.0    2103475
            1      true    0000:03:00.1    2104268
            2      false   0000:03:00.2    -
            3      true    0000:03:00.3    2381189
            4      false   0000:03:00.4    -
            5      true    0000:03:00.5    2103475
            6      false   0000:03:00.6    -
            7      true    0000:03:00.7    2381189
            """
        )

        owner._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="", stdout=output1),
            ConnectionCompletedProcess(return_code=0, args="", stdout=output2),
        ]
        assert owner.virtualization.get_vm_vf_ids("FR-cli7-monica", interface) == [3, 7]

    def test_get_vm_vf_id_no_vm(self, owner, interface):
        output = ""
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output
        )
        with pytest.raises(VirtualizationFeatureError, match="Cannot find the World ID of VM ABCDEF."):
            owner.virtualization.get_vm_vf_ids("ABCDEF", interface)

    def test_get_vm_vf_id_no_vf(self, owner, interface):
        output1 = dedent(
            """\
        FR-9-Sophia
           World ID: 2104268
           Process ID: 0
           VMX Cartel ID: 2104267
           UUID: 56 4d 67 fa b9 f2 da 11-aa 79 47 50 07 db 8b 71
           Display Name: FR-9-Sophia
           Config File: /vmfs/volumes/60403711-c7bb0e92-7219-a4bf01645e6b/zoe/zoe.vmx

        FR-cli7-monica
           World ID: 2381189
           Process ID: 0
           VMX Cartel ID: 2381188
           UUID: 56 4d 6e 28 c8 5b fe b1-76 37 43 c0 fc 09 36 e4
           Display Name: FR-cli7-monica
           Config File: /vmfs/volumes/60403711-c7bb0e92-7219-a4bf01645e6b/FR-cli7-monica/FR-cli7-monica.vmx
        """
        )
        output2 = ""

        owner._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="", stdout=output1),
            ConnectionCompletedProcess(return_code=0, args="", stdout=output2),
        ]

        with pytest.raises(VirtualizationFeatureError, match="No VF used by FR-cli7-monica VM."):
            owner.virtualization.get_vm_vf_ids("FR-cli7-monica", interface)
