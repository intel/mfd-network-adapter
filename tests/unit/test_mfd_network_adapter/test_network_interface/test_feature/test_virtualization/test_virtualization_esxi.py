# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test Virtualization ESXi."""

from textwrap import dedent
from unittest.mock import MagicMock

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import InterfaceInfo
from mfd_network_adapter.network_interface.exceptions import VirtualizationFeatureError, VirtualizationFeatureException
from mfd_network_adapter.network_interface.feature.virtualization.data_structures import VFInfo

from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface


class TestVirtualizationESXi:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 1, 0, 1)
        name = "vmnic1"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.ESXI

        interface = ESXiNetworkInterface(
            connection=_connection, interface_info=InterfaceInfo(pci_address=pci_address, name=name)
        )
        mocker.stopall()
        return interface

    def test_get_enabled_vfs(self, interface):
        eth = "vmnic6"
        output = dedent(
            """VF ID  Active  PCI Address     Owner World ID
            ----  ------  --------------  --------------
            0   false  00000:134:02.0   -
            1   false  00000:134:02.1   -
            """
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        vfs = interface.virtualization.get_enabled_vfs(eth)
        assert vfs == 2

    def test_get_enabled_vfs_error(self, interface):
        eth = "vmnic6"
        output = "There is no SRIOV Nic with name vmnic6"
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        vfs = interface.virtualization.get_enabled_vfs(eth)
        assert vfs == 0

    def test_get_intnet_sriovnic_options_old_intnet(self, interface):
        eth = "vmnic4"
        output = """
        VF ID           Trusted         Spoof Check
        -----           -------         -----------
        0               false           true
        """
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        vf_settings = interface.virtualization.get_intnet_sriovnic_options(vf_id=0, interface=eth)
        assert vf_settings == {"trusted": False, "spoof": True, "floating_veb": None}

    def test_get_intnet_sriovnic_options_new_intnet(self, interface):
        eth = "vmnic4"
        output = """
        VF ID           Trusted         Spoof Check     Floating VEB
        -----           -------         -----------     ------------
        0               false           true            false
        """
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        vf_settings = interface.virtualization.get_intnet_sriovnic_options(vf_id=0, interface=eth)
        assert vf_settings == {"trusted": False, "spoof": True, "floating_veb": False}

    def test_get_intnet_sriovnic_options_wrong_vf_id(self, interface):
        eth = "vmnic4"
        output = """
        Invalid VF ID 8. VF ID should be in range 0 to 7
        """
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        with pytest.raises(VirtualizationFeatureError):
            interface.virtualization.get_intnet_sriovnic_options(vf_id=8, interface=eth)

    def test_get_possible_options_intnet_sriovnic_vf_set(self, interface):
        output = """
        Error: Missing required parameter -t|--trusted
               Missing required parameter -v|--vfid
               Missing required parameter -n|--vmnic

        Usage: esxcli intnet sriovnic vf set [cmd options]

        Description:
          set                   Set SR-IOV virtual function for a NIC

        Cmd options:
          -f|--floating=<bool>  Set floating VEB to true or false. (optional)
          -s|--spoofchk=<bool>  Set mac/vlan spoof check to true or false. (optional)
          -t|--trusted=<bool>   Set trusted mode to true or false. (required)
          -v|--vfid=<long>      Specifies the VF id for the virtual function. (required)
          -n|--vmnic=<str>      Specifies the name for the SRIOV NIC. (required)
        """
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        expected = ["floating", "spoofchk", "trusted"]
        assert interface.virtualization.get_possible_intnet_sriovnic_options() == expected

    def test_set_intnet_sriovnic_options(self, interface, mocker):
        eth = "vmnic4"
        output = """
        Trusted mode is set to false, spoof check is set to true and floating VEB is set to true
        """
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert (
            interface.virtualization.set_intnet_sriovnic_options(vf_id=0, interface=eth, spoofchk=False, floating=True)
            is None
        )

    def test_set_intnet_sriovnic_options_missing_param(self, interface, mocker):
        eth = "vmnic4"
        output = """
        Error: Missing required parameter -t|--trusted
        """
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="command", stdout=output, stderr="stderr"
        )
        with pytest.raises(VirtualizationFeatureError):
            interface.virtualization.set_intnet_sriovnic_options(vf_id=0, interface=eth)

    def test_set_intnet_sriovnic_options_invalid_vf(self, interface, mocker):
        eth = "vmnic4"
        output = """
        Invalid VF ID 8. VF ID should be in range 0 to 7
        """
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="command", stdout=output, stderr="stderr"
        )
        with pytest.raises(VirtualizationFeatureError):
            interface.virtualization.set_intnet_sriovnic_options(vf_id=8, interface=eth)

    def test_set_intnet_sriovnic_options_invalid_option(self, interface, mocker):
        eth = "vmnic4"
        output = """
        Error: Invalid option --test
        """
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="command", stdout=output, stderr="stderr"
        )
        with pytest.raises(VirtualizationFeatureError):
            interface.virtualization.set_intnet_sriovnic_options(vf_id=8, interface=eth, test=True)

    def test_set_intnet_sriovnic_options_invalid_vmnic(self, interface, mocker):
        eth = "vmnic4"
        output = """
        ERROR: Vmnic specified doesn't exist or is unsupported
        """
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="command", stdout=output, stderr="stderr"
        )
        with pytest.raises(VirtualizationFeatureError):
            interface.virtualization.set_intnet_sriovnic_options(vf_id=8, interface=eth, test=True)

    def test_set_intnet_vmdq_loopback(self, interface, mocker):
        eth = "vmnic4"
        output = """
        Loopback traffic on the VMDQ VSIs successfully disabled.
        """
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert interface.virtualization.set_intnet_vmdq_loopback(interface=eth, loopback="false") is None

    def test_set_intnet_vmdq_loopback_invalid_vmnic(self, interface, mocker):
        eth = "vmnic4"
        output = """
        ERROR: Vmnic specified doesn't exist or is unsupported
        """
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="command", stdout=output, stderr="stderr"
        )
        with pytest.raises(VirtualizationFeatureError):
            interface.virtualization.set_intnet_vmdq_loopback(interface=eth, loopback=True)

    def test_set_intnet_vmdq_loopback_vmnic_unsupported(self, interface, mocker):
        eth = "vmnic4"
        output = """
        ERROR: Device is not supported!
        """
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="command", stdout=output, stderr="stderr"
        )
        with pytest.raises(VirtualizationFeatureError):
            interface.virtualization.set_intnet_vmdq_loopback(interface=eth, loopback=True)

    def test_set_intnet_vmdq_loopback_unable_to_change(self, interface, mocker):
        eth = "vmnic4"
        output = """
        ERROR: Unable to update the VMDQ VSIs loopback, status = 16
        """
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="command", stdout=output, stderr="stderr"
        )
        with pytest.raises(VirtualizationFeatureError):
            interface.virtualization.set_intnet_vmdq_loopback(interface=eth, loopback=True)

    def test_set_intnet_vmdq_loopback_invalid_loopback_value(self, interface, mocker):
        eth = "vmnic4"
        output = """Error: While processing '-l'. Argument type mismatch. Expecting one of {0, 1, n[o], y[es], f[alse], t[rue], off, on}. Got 'Falsefff'

Usage: esxcli intnet misc vmdqlb set [cmd options]

Description:
  set                   Allow VMDQ VSIs to send loopback traffic on the given PF.

Cmd options:
  -l|--loopback=<bool>  enable/disable the VMDQ VSIs loopback (1 - enable (default), 0 - disable) (required)
  -n|--vmnic=<str>      Vmnic name to operate on (required)
"""  # noqa: E501
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="command", stdout=output, stderr="stderr"
        )
        with pytest.raises(VirtualizationFeatureError):
            interface.virtualization.set_intnet_vmdq_loopback(interface=eth, loopback="fff")

    def test_get_intnet_vmdq_loopback_enabled(self, interface):
        eth = "vmnic4"
        output = """VMDQ VSIs loopback is set to true"""
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert interface.virtualization.get_intnet_vmdq_loopback(interface=eth)

    def test_get_intnet_vmdq_loopback_disabled(self, interface):
        eth = "vmnic4"
        output = """VMDQ VSIs loopback is set to false"""
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert not interface.virtualization.get_intnet_vmdq_loopback(interface=eth)

    def test_get_connected_vfs_info(self, interface):
        output = "    0    true  00000:075:17.0  2101956\n    1    true  00000:075:17.1  2102557\n"
        expected_result = [
            VFInfo(vf_id="0", pci_address=PCIAddress(domain=0, bus=75, slot=17, func=0), owner_world_id="2101956"),
            VFInfo(vf_id="1", pci_address=PCIAddress(domain=0, bus=75, slot=17, func=1), owner_world_id="2102557"),
        ]
        interface._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr=""),
        ]
        interface._connection.get_system_info.return_value = MagicMock(kernel_version="7.0.3")
        assert interface.virtualization.get_connected_vfs_info() == expected_result

    def test_get_connected_vfs_info_other_version(self, interface):
        output = "    0    true  0000:4b:11.0     2106440\n    1    true  0000:4b:11.1     2106876\n"
        expected_result = [
            VFInfo(vf_id="0", pci_address=PCIAddress(domain=0, bus=75, slot=17, func=0), owner_world_id="2106440"),
            VFInfo(vf_id="1", pci_address=PCIAddress(domain=0, bus=75, slot=17, func=1), owner_world_id="2106876"),
        ]
        interface._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr=""),
        ]
        interface._connection.get_system_info.return_value = MagicMock(kernel_version="8.0.3")
        assert interface.virtualization.get_connected_vfs_info() == expected_result

    def test_get_connected_vfs_info_error(self, interface):
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(
            cmd="esxcli network sriovnic vf list -n vmnic1 | grep true", returncode=1, stderr=""
        )
        interface._connection.get_system_info.return_value = MagicMock(kernel_version="7.0.3")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization.get_connected_vfs_info()
