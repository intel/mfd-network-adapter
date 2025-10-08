# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test Virtualization Linux."""

from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import PCIAddress, OSName, MACAddress
from mfd_typing.mac_address import get_random_mac
from mfd_typing.network_interface import LinuxInterfaceInfo, InterfaceType, InterfaceInfo

from mfd_network_adapter.data_structures import State
from mfd_network_adapter.exceptions import (
    VirtualFunctionNotFoundException,
    NetworkAdapterConfigurationException,
    NetworkInterfaceNotSupported,
)
from mfd_network_adapter.network_interface.data_structures import VFDetail, LinkState, VlanProto
from mfd_network_adapter.network_interface.exceptions import (
    VirtualizationFeatureException,
    VirtualizationWrongInterfaceException,
)
from mfd_network_adapter.network_interface.feature.virtualization.data_structures import MethodType
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface


class TestVirtualizationLinux:
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

    @pytest.fixture()
    def interfaces_with_vf(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        interfaces = []
        interfaces.append(
            LinuxNetworkInterface(
                connection=connection,
                owner=None,
                interface_info=InterfaceInfo(name="eth0", pci_address=PCIAddress(data="0000:18:00.0")),
                interface_type=InterfaceType.PF,
            )
        )
        interfaces.append(
            LinuxNetworkInterface(
                connection=connection,
                owner=None,
                interface_info=InterfaceInfo(name="eth1", pci_address=PCIAddress(data="0000:10:00.0")),
                interface_type=InterfaceType.VF,
            )
        )
        yield interfaces
        mocker.stopall()

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

    @pytest.mark.parametrize(
        "stdout,expected_vf_id",
        [
            (
                "root 0 Jan  1 00:00 /sys/bus/pci/devices/0000:18:00.0/virtfn3 -> ../../../0000:10:00.0\n",
                3,
            ),
            (
                "root root 0 Jan  1 00:00 /sys/bus/pci/devices/0000:18:00.0/virtfn7 -> ../../../0000:10:00.0\n",
                7,
            ),
        ],
    )
    def test_retrieves_correct_vf_id_for_matching_pci_address(self, interfaces_with_vf, stdout, expected_vf_id):
        pf, vf = interfaces_with_vf
        pf._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="ls", stdout=stdout, stderr=""
        )
        assert pf.virtualization.get_vf_id_by_pci(vf.pci_address) == expected_vf_id

    def test_raises_exception_when_no_matching_vf_found(self, interfaces_with_vf):
        pf, vf = interfaces_with_vf
        stdout = "root 0 Jan  1 00:00 /sys/bus/pci/devices/0000:00:00.0/virtfn3 -> ../../../0000:de:ad:be.ef\n"
        pf._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="ls", stdout=stdout, stderr=""
        )
        with pytest.raises(
            VirtualFunctionNotFoundException,
            match=f"0 matched VFs for PF PCI Address {pf.pci_address}",
        ):
            pf.virtualization.get_vf_id_by_pci(vf.pci_address)

    def test_raises_exception_when_command_fails(self, interfaces_with_vf):
        pf, vf = interfaces_with_vf
        pf._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="ls", stdout="", stderr="Error"
        )
        with pytest.raises(VirtualFunctionNotFoundException):
            pf.virtualization.get_vf_id_by_pci(vf.pci_address)

    @pytest.mark.parametrize(
        "stdout, expected",
        [("resource pci/0000:00:00.0:\n  name msix_vf size 128 occ 0 unit entry\n", 128)],
    )
    def test_get_msix_vectors_count_devlink_success(self, interface, stdout, expected):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="devlink", stdout=stdout, stderr=""
        )
        assert interface.virtualization.get_msix_vectors_count(method=MethodType.DEVLINK) == expected
        called_cmd = (
            interface._connection.execute_command.call_args.kwargs.get("command")
            or interface._connection.execute_command.call_args.args[0]
        )
        assert f"devlink resource show pci/{interface.pci_address}" in called_cmd

    @pytest.mark.parametrize(
        "stdout",
        ["resource pci/0000:00:00.0:\n  name something_else size 64 occ 0\n"],
    )
    def test_get_msix_vectors_count_devlink_failed(self, interface, stdout):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="devlink", stdout=stdout, stderr=""
        )
        with pytest.raises(
            NetworkAdapterConfigurationException,
            match=f"Could not find MSI-X vectors count for interface {interface.name}",
        ):
            interface.virtualization.get_msix_vectors_count(method=MethodType.DEVLINK)

    @pytest.mark.parametrize(
        "stdout,expected",
        [("256\n", 256)],
    )
    def test_get_msix_vectors_count_sysfs(self, interface, stdout, expected):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="cat", stdout=stdout, stderr=""
        )
        assert interface.virtualization.get_msix_vectors_count(method=MethodType.SYSFS) == expected
        called_cmd = (
            interface._connection.execute_command.call_args.kwargs.get("command")
            or interface._connection.execute_command.call_args.args[0]
        )
        assert f"/sys/bus/pci/devices/{interface.pci_address}/sriov_vf_msix_count" in called_cmd

    @pytest.mark.parametrize(
        "stdout",
        [("")],
    )
    def test_get_msix_vectors_count_sysfs_failed(self, interface, stdout):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="devlink", stdout=stdout, stderr=""
        )
        with pytest.raises(
            NetworkAdapterConfigurationException,
            match=f"Could not find MSI-X vectors count for interface {interface.name}",
        ):
            interface.virtualization.get_msix_vectors_count(method=MethodType.SYSFS)

    def test_get_msix_vectors_count_invalid_method(self, interface):
        with pytest.raises(ValueError, match="Unknown method"):
            interface.virtualization.get_msix_vectors_count(method="invalid")

    def test_get_msix_vectors_count_exception(self, interfaces_with_vf):
        with pytest.raises(
            NetworkInterfaceNotSupported,
            match="Getting MSI-X vector count is only supported on PF interface.",
        ):
            interfaces_with_vf[1].virtualization.get_msix_vectors_count()

    @pytest.mark.parametrize("rc", [0, 1])
    def test_set_msix_vectors_count_devlink(self, interface, rc):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=rc, args="devlink", stdout="", stderr=""
        )
        interface.virtualization.set_msix_vectors_count(256, method=MethodType.DEVLINK)
        interface._connection.execute_command.assert_called_once_with(
            f"devlink resource set pci/{interface.pci_address} path /msix/msix_vf/ size 256",
            custom_exception=NetworkAdapterConfigurationException,
        )

    @pytest.mark.parametrize("rc", [0, 1])
    def test_set_msix_vectors_count_sysfs(self, interface, rc):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=rc, args="echo", stdout="", stderr=""
        )
        interface.virtualization.set_msix_vectors_count(128, method=MethodType.SYSFS)
        interface._connection.execute_command.assert_called_once_with(
            f"echo 128 > /sys/bus/pci/devices/{interface.pci_address}/sriov_vf_msix_count",
            custom_exception=NetworkAdapterConfigurationException,
        )

    def test_set_msix_vectors_count_invalid_method(self, interface):
        with pytest.raises(ValueError, match="Unknown method"):
            interface.virtualization.set_msix_vectors_count(64, method="bad_method")

    def test_set_msix_vectors_count_exception(self, interfaces_with_vf):
        with pytest.raises(
            NetworkInterfaceNotSupported,
            match="Setting MSI-X vector count on VF is only supported through PF interface.",
        ):
            interfaces_with_vf[1].virtualization.set_msix_vectors_count(32)
