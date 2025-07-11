# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_interface.exceptions import MTUException
from mfd_network_adapter.network_interface.feature.mtu import MtuSize
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface


class TestLinuxMTU:
    @pytest.fixture(params=[{"namespace": None}])
    def port(self, mocker, request):
        pci_address = PCIAddress(0, 0, 0, 0)
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.LINUX

        port = LinuxNetworkInterface(
            connection=_connection,
            interface_info=LinuxInterfaceInfo(
                name="eth0", pci_address=pci_address, namespace=request.param.get("namespace")
            ),
        )
        mocker.stopall()
        return port

    def test_get_mtu_default(self, port):
        output_mtu = dedent(
            """\
        2: eth0: <BROADCAST,MULT,UP,LOWER_UP> mtu 1500 qdisc mq master br0 state UP mode DEFAULT group default qlen 1000
        link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00"""
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_mtu, stderr=""
        )

        assert port.mtu.get_mtu() == MtuSize.MTU_DEFAULT

    def test_get_mtu_custom(self, port):
        output_mtu = dedent(
            """\
        2: eth0: <BROADCAST,MULT,UP,LOWER_UP> mtu 1501 qdisc mq master br0 state UP mode DEFAULT group default qlen 1000
        link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00"""
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_mtu, stderr=""
        )

        assert port.mtu.get_mtu() == MtuSize.MTU_CUSTOM

    def test_get_mtu_corrupted_output(self, port):
        output_mtu = dedent(
            """\
        2: eth0: <BROADCAST,MULT,UP,LOWER_UP>  mq master br0 state UP mode DEFAULT group default qlen 1000
        link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00"""
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_mtu, stderr=""
        )

        with pytest.raises(Exception, match=f"MTU not found\n {output_mtu}"):
            port.mtu.get_mtu()

    def test_set_mtu(self, port):
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )

        port.mtu.set_mtu(MtuSize.MTU_4K)
        port._connection.execute_command.assert_called_once_with(
            "ip link set mtu 4074 dev eth0", custom_exception=MTUException
        )

    def test_is_mtu_set(self, port):
        output_mtu = dedent(
            """\
        2: eth0: <BROADCAST,MULT,UP,LOWER_UP> mtu 1500 qdisc mq master br0 state UP mode DEFAULT group default qlen 1000
        link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00"""
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_mtu, stderr=""
        )

        assert port.mtu.is_mtu_set(MtuSize.MTU_DEFAULT) is True

    def test_is_mtu_not_set(self, port):
        output_mtu = dedent(
            """\
        2: eth0: <BROADCAST,MULT,UP,LOWER_UP> mtu 1500 qdisc mq master br0 state UP mode DEFAULT group default qlen 1000
        link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00"""
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_mtu, stderr=""
        )

        assert port.mtu.is_mtu_set(MtuSize.MTU_4K) is False

    def test_convert_mtu_str_to_int(self, port):
        assert port.mtu.convert_str_mtu_to_int("4k") == MtuSize.MTU_4K
        assert port.mtu.convert_str_mtu_to_int("default") == MtuSize.MTU_DEFAULT

    def test_convert_mtu_str_to_int_invalid_value(self, port):
        with pytest.raises(ValueError):
            port.mtu.convert_str_mtu_to_int("1500.1")
