# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test Virtualization Linux."""

from textwrap import dedent

import pytest

from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import PCIAddress, OSName, MACAddress
from mfd_typing.network_interface import LinuxInterfaceInfo, InterfaceType

from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.data_structures import VFDetail, LinkState, VlanProto
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface
from mfd_network_adapter.network_interface.exceptions import (
    VirtualizationFeatureException,
    VirtualizationWrongInterfaceException,
)
from mfd_typing.mac_address import get_random_mac


class TestQueueLinux:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "eth1"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        interface = LinuxNetworkInterface(
            connection=connection,
            owner=None,
            interface_info=LinuxInterfaceInfo(name=name, pci_address=pci_address, interface_type=InterfaceType.PF),
        )
        mocker.stopall()
        return interface

    def test_set_max_tx_rate(self, interface, mocker):
        """Test set max tx rate."""
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface.virtualization.set_max_tx_rate(vf_id=2, value=200)
        interface._connection.execute_command.assert_called_once_with(
            f"ip link set dev {interface._interface_info.name} vf 2 max_tx_rate 200",
            custom_exception=VirtualizationFeatureException,
        )

    def test_set_max_tx_rate_with_error(self, interface, mocker):
        """Test set max tx rate."""
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(returncode=1, cmd="")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization.set_max_tx_rate(vf_id=2, value=200)

    def test_set_min_tx_rate(self, interface, mocker):
        """Test set max tx rate."""
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface.virtualization.set_min_tx_rate(vf_id=2, value=100)
        interface._connection.execute_command.assert_called_once_with(
            f"ip link set dev {interface._interface_info.name} vf 2 min_tx_rate 100",
            custom_exception=VirtualizationFeatureException,
        )

    def test_set_min_tx_rate_with_error(self, interface, mocker):
        """Test set min tx rate."""
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(returncode=1, cmd="")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization.set_min_tx_rate(vf_id=2, value=100)

    def test_set_trust_on(self, interface, mocker):
        """Test set trust."""
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface.virtualization.set_trust(vf_id=2, state=State.ENABLED)
        interface._connection.execute_command.assert_called_once_with(
            command=f"ip link set {interface._interface_info.name} vf 2 trust on",
            custom_exception=VirtualizationFeatureException,
        )

    def test_set_trust_off(self, interface, mocker):
        """Test set trust."""
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface.virtualization.set_trust(vf_id=2, state=State.DISABLED)
        interface._connection.execute_command.assert_called_once_with(
            command=f"ip link set {interface._interface_info.name} vf 2 trust off",
            custom_exception=VirtualizationFeatureException,
        )

    def test_set_trust_with_error(self, interface, mocker):
        """Test set trust with error."""
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(returncode=1, cmd="")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization.set_trust(vf_id=2, state=State.ENABLED)

    def test_set_spoofchk_on(self, interface, mocker):
        """Test set spoofchk."""
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface.virtualization.set_spoofchk(vf_id=2, state=State.ENABLED)
        interface._connection.execute_command.assert_called_once_with(
            command=f"ip link set {interface._interface_info.name} vf 2 spoofchk on",
            custom_exception=VirtualizationFeatureException,
        )

    def test_set_spoofchk_off(self, interface, mocker):
        """Test set spoofchk."""
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface.virtualization.set_spoofchk(vf_id=2, state=State.DISABLED)
        interface._connection.execute_command.assert_called_once_with(
            command=f"ip link set {interface._interface_info.name} vf 2 spoofchk off",
            custom_exception=VirtualizationFeatureException,
        )

    def test_set_spoofchk_with_error(self, interface, mocker):
        """Test set spoofchk with error."""
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(returncode=1, cmd="")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization.set_min_tx_rate(vf_id=2, value=100)

    def test__raise_error_if_not_pf_raises(self, interface):
        interface._interface_info.interface_type = InterfaceType.VF
        with pytest.raises(VirtualizationWrongInterfaceException):
            interface.virtualization._raise_error_if_not_supported_type()

    def test__raise_error_if_not_pf_passes(self, interface):
        interface._interface_info.interface_type = InterfaceType.PF
        assert interface.virtualization._raise_error_if_not_supported_type() is None

    def test__raise_error_if_not_pf_passes_bts(self, interface):
        interface._interface_info.interface_type = InterfaceType.BTS
        assert interface.virtualization._raise_error_if_not_supported_type() is None

    def test_set_link_for_vf_pass(self, interface, mocker):
        interface._interface_info.name = "foo"
        vf_id = 2
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface.virtualization.set_link_for_vf(vf_id=vf_id, link_state=LinkState.AUTO)
        interface._connection.execute_command.assert_called_once_with(
            command=f"ip link set {interface._interface_info.name} vf {vf_id} state auto",
            custom_exception=VirtualizationFeatureException,
        )

    def test_set_link_for_vf_error(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(returncode=1, cmd="")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization.set_link_for_vf(vf_id=2, link_state=LinkState.AUTO)

    def test_set_vlan_for_vf_pass_proto(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        vf_id = 2
        vlan_id = 100
        interface.virtualization.set_vlan_for_vf(vf_id=vf_id, vlan_id=vlan_id, proto=VlanProto.Dot1q)
        interface._connection.execute_command.assert_called_once_with(
            command=f"ip link set {interface._interface_info.name} vf {vf_id} vlan {vlan_id} proto 802.1Q",
            custom_exception=VirtualizationFeatureException,
        )

    def test_set_vlan_for_vf_pass_non_proto(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        vf_id = 2
        vlan_id = 100
        interface.virtualization.set_vlan_for_vf(vf_id=vf_id, vlan_id=vlan_id)
        interface._connection.execute_command.assert_called_once_with(
            command=f"ip link set {interface._interface_info.name} vf {vf_id} vlan {vlan_id}",
            custom_exception=VirtualizationFeatureException,
        )

    def test_set_vlan_for_vf_error(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(returncode=1, cmd="")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization.set_vlan_for_vf(vf_id=2, vlan_id=100)

    def test_set_mac_for_vf_pass(self, interface, mocker):
        vf_id = 0
        mac = MACAddress(get_random_mac())
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface.virtualization.set_mac_for_vf(vf_id=vf_id, mac=mac)
        interface._connection.execute_command.assert_called_once_with(
            command=f"ip link set {interface._interface_info.name} vf {vf_id} mac {mac}",
            custom_exception=VirtualizationFeatureException,
        )

    def test_set_mac_for_vf_error(self, interface, mocker):
        vf_id = 0
        mac = MACAddress(get_random_mac())
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(returncode=1, cmd="")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization.set_mac_for_vf(vf_id=vf_id, mac=mac)

    def test__get_vfs_details_pass(self, interface, mocker):
        interface._interface_info.name = "eth1"
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        expected_command = f"ip link show dev {interface._interface_info.name}"
        output = dedent(
            """
        3: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP mode DEFAULT group default qlen 1000
        link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
        vf 0     link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00, spoof checking on, link-state auto, trust off
        vf 1     link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00, spoof checking on, link-state enable, trust off
        vf 9     link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00, spoof checking on, link-state auto, trust off`
        """
        )

        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0
        )

        expected_details = [
            VFDetail(
                id=0,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.ENABLED,
                link_state=LinkState.AUTO,
                trust=State.DISABLED,
            ),
            VFDetail(
                id=1,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.ENABLED,
                link_state=LinkState.ENABLE,
                trust=State.DISABLED,
            ),
            VFDetail(
                id=9,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.ENABLED,
                link_state=LinkState.AUTO,
                trust=State.DISABLED,
            ),
        ]

        assert interface.virtualization._get_vfs_details() == expected_details
        interface._connection.execute_command.assert_called_with(
            command=expected_command, custom_exception=VirtualizationFeatureException
        )

    def test__get_vfs_details_error(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(1, "", "", "")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization._get_vfs_details()

    def test_get_spoofchk_pass(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        returned_details = [
            VFDetail(
                id=0,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.ENABLED,
                link_state=LinkState.AUTO,
                trust=State.DISABLED,
            ),
            VFDetail(
                id=1,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.DISABLED,
                link_state=LinkState.AUTO,
                trust=State.DISABLED,
            ),
            VFDetail(
                id=9,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.ENABLED,
                link_state=LinkState.AUTO,
                trust=State.DISABLED,
            ),
        ]
        interface.virtualization._get_vfs_details = mocker.Mock(return_value=returned_details)
        assert interface.virtualization.get_spoofchk(vf_id=0) == State.ENABLED
        assert interface.virtualization.get_spoofchk(vf_id=1) == State.DISABLED
        assert interface.virtualization.get_spoofchk(vf_id=9) == State.ENABLED

    def test_get_spoofchk_error(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(1, "", "", "")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization.get_spoofchk(vf_id=0)

    def test_get_trust_pass(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        returned_details = [
            VFDetail(
                id=0,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.ENABLED,
                link_state=LinkState.AUTO,
                trust=State.DISABLED,
            ),
            VFDetail(
                id=1,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.DISABLED,
                link_state=LinkState.AUTO,
                trust=State.DISABLED,
            ),
            VFDetail(
                id=9,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.ENABLED,
                link_state=LinkState.AUTO,
                trust=State.ENABLED,
            ),
        ]
        interface.virtualization._get_vfs_details = mocker.Mock(return_value=returned_details)
        assert interface.virtualization.get_trust(vf_id=0) == State.DISABLED
        assert interface.virtualization.get_trust(vf_id=1) == State.DISABLED
        assert interface.virtualization.get_trust(vf_id=9) == State.ENABLED

    def test_get_trust_error(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(1, "", "", "")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization.get_trust(vf_id=0)

    def test_get_link_state_pass(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        returned_details = [
            VFDetail(
                id=0,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.ENABLED,
                link_state=LinkState.AUTO,
                trust=State.DISABLED,
            ),
            VFDetail(
                id=1,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.DISABLED,
                link_state=LinkState.ENABLE,
                trust=State.DISABLED,
            ),
            VFDetail(
                id=9,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.ENABLED,
                link_state=LinkState.DISABLE,
                trust=State.DISABLED,
            ),
        ]
        interface.virtualization._get_vfs_details = mocker.Mock(return_value=returned_details)
        assert interface.virtualization.get_link_state(vf_id=0) == LinkState.AUTO
        assert interface.virtualization.get_link_state(vf_id=1) == LinkState.ENABLE
        assert interface.virtualization.get_link_state(vf_id=9) == LinkState.DISABLE

    def test_get_link_state_error(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(1, "", "", "")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization.get_link_state(vf_id=0)

    def test_get_mac_address_pass(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        returned_details = [
            VFDetail(
                id=0,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.ENABLED,
                link_state=LinkState.AUTO,
                trust=State.DISABLED,
            ),
            VFDetail(
                id=1,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.DISABLED,
                link_state=LinkState.AUTO,
                trust=State.DISABLED,
            ),
            VFDetail(
                id=9,
                mac_address=MACAddress("00:00:00:00:00:00"),
                spoofchk=State.ENABLED,
                link_state=LinkState.AUTO,
                trust=State.DISABLED,
            ),
        ]
        interface.virtualization._get_vfs_details = mocker.Mock(return_value=returned_details)

        assert interface.virtualization.get_mac_address(vf_id=0) == MACAddress("00:00:00:00:00:00")
        assert interface.virtualization.get_mac_address(vf_id=1) == MACAddress("00:00:00:00:00:00")
        assert interface.virtualization.get_mac_address(vf_id=9) == MACAddress("00:00:00:00:00:00")

    def test_get_mac_address_error(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(1, "", "", "")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization.get_mac_address(vf_id=0)

    def test__get_max_vfs_by_name_pass(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(args="", return_code=0, stdout="   128  ")
        )

        assert interface.virtualization._get_max_vfs_by_name() == 128
        interface._connection.execute_command.assert_called_once_with(
            command=f"cat /sys/class/net/{interface._interface_info.name}/device/sriov_totalvfs",
            custom_exception=VirtualizationFeatureException,
        )

    def test__get_max_vfs_by_name_error(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(returncode=1, cmd="")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization._get_max_vfs_by_name()

    def test__get_max_vfs_by_pci_address_pass(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(args="", return_code=0, stdout="   128  ")
        )

        assert interface.virtualization._get_max_vfs_by_pci_address() == 128
        interface._connection.execute_command.assert_called_once_with(
            command=f"cat /sys/bus/pci/devices/{interface.pci_address}/sriov_totalvfs",
            custom_exception=VirtualizationFeatureException,
        )

    def test__get_max_vfs_by_pci_address_error(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(returncode=1, cmd="")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization._get_max_vfs_by_pci_address()

    def test__get_current_vfs_by_name_pass(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()

        interface._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(args="", return_code=0, stdout="5  ")
        )

        assert interface.virtualization._get_current_vfs_by_name() == 5
        interface._connection.execute_command.assert_called_once_with(
            command=f"cat /sys/class/net/{interface._interface_info.name}/device/sriov_numvfs",
            custom_exception=VirtualizationFeatureException,
        )

    def test__get_current_vfs_by_name_error(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(returncode=1, cmd="")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization._get_current_vfs_by_name()

    def test__get_current_vfs_by_pci_address_pass(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()

        interface._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(args="", return_code=0, stdout="5  ")
        )

        assert interface.virtualization._get_current_vfs_by_pci_address() == 5
        interface._connection.execute_command.assert_called_once_with(
            command=f"cat /sys/bus/pci/devices/{interface.pci_address}/sriov_numvfs",
            custom_exception=VirtualizationFeatureException,
        )

    def test__get_current_vfs_by_pci_address_error(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface._connection.execute_command.side_effect = VirtualizationFeatureException(returncode=1, cmd="")
        with pytest.raises(VirtualizationFeatureException):
            interface.virtualization._get_current_vfs_by_pci_address()

    def test_get_max_vfs_name_set(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface.virtualization._get_max_vfs_by_name = mocker.Mock()
        interface.virtualization.get_max_vfs()

        interface.virtualization._get_max_vfs_by_name.assert_called_once()

    def test_get_max_vfs_name_unset(self, interface, mocker):
        interface._interface_info.name = None
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface.virtualization._get_max_vfs_by_pci_address = mocker.Mock()
        interface.virtualization.get_max_vfs()
        interface.virtualization._get_max_vfs_by_pci_address.assert_called_once()

    def test_get_current_vfs_name_set(self, interface, mocker):
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface.virtualization._get_current_vfs_by_name = mocker.Mock()
        interface.virtualization.get_current_vfs()

        interface.virtualization._get_current_vfs_by_name.assert_called_once()

    def test_get_current_vfs_name_unset(self, interface, mocker):
        interface._interface_info.name = None
        interface.virtualization._raise_error_if_not_supported_type = mocker.Mock()
        interface.virtualization._get_current_vfs_by_pci_address = mocker.Mock()
        interface.virtualization.get_current_vfs()
        interface.virtualization._get_current_vfs_by_pci_address.assert_called_once()
