# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test Geneve Linux."""

from ipaddress import IPv4Interface, IPv6Interface
from unittest.mock import call

import pytest
from mfd_common_libs import log_levels
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.exceptions import GeneveFeatureException
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner


class TestLinuxGeneve:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        owner = LinuxNetworkAdapterOwner(connection=connection)

        yield owner
        mocker.stopall()

    def test_create_setup_geneve_tunnel_ipv4(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.geneve.create_setup_geneve_tunnel(
            tunnel_name="gnv-interface-0",
            inner_ip_addr=IPv4Interface("10.10.10.3/8"),
            remote_ip_addr=IPv4Interface("10.10.10.10/8"),
            vni=40,
        )

        owner._connection.execute_command.assert_has_calls(
            [
                call("ip link add gnv-interface-0 type geneve remote 10.10.10.10/8 id 40 ", expected_return_codes={}),
                call("ip link set gnv-interface-0 up", expected_return_codes={}),
                call("ip addr add 10.10.10.3/8 dev gnv-interface-0", expected_return_codes={}),
            ]
        )

    def test__create_geneve_tunnel_exception(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="RTNETLINK answers: File exists", stderr=""
        )
        with pytest.raises(GeneveFeatureException):
            owner.geneve._create_geneve_tunnel(
                tunnel_name="gnv-interface-0",
                remote_ip_addr=IPv4Interface("10.10.10.10/8"),
                vni=40,
            )

    def test__set_link_up_geneve_tunnel_exception(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="RTNETLINK answers: File exists", stderr=""
        )
        with pytest.raises(GeneveFeatureException):
            owner.geneve._set_link_up_geneve_tunnel(
                tunnel_name="gnv-interface-0",
                ip_addr=IPv4Interface("10.10.10.10/8"),
            )

    def test_create_setup_geneve_tunnel_ipv4_within_namespace(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="", stderr=""
        )
        with pytest.raises(GeneveFeatureException):
            owner.geneve._set_link_up_geneve_tunnel(
                tunnel_name="geneve0",
                ip_addr=IPv4Interface("10.10.10.3/8"),
                namespace_name="ns1",
            )

    def test_create_setup_geneve_tunnel_ipv6(self, owner, caplog):
        caplog.set_level(log_levels.MODULE_DEBUG)
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.geneve.create_setup_geneve_tunnel(
            tunnel_name="gnv-iface-10",
            inner_ip_addr=IPv6Interface("2001:db8:1::3/124"),
            remote_ip_addr=IPv6Interface("2001:db8:1::10/124"),
            vni=40,
        )

        owner._connection.execute_command.assert_has_calls(
            [
                call(
                    "ip -6 link add gnv-iface-10 type geneve remote 2001:db8:1::10/124 id 40 ", expected_return_codes={}
                ),
                call("ip -6 link set gnv-iface-10 up", expected_return_codes={}),
                call("ip -6 addr add 2001:db8:1::3/124 dev gnv-iface-10", expected_return_codes={}),
            ]
        )
        assert "Geneve: gnv-iface-10 created and setup." in caplog.text

    def test_delete_geneve_tunnel(self, owner, caplog):
        caplog.set_level(log_levels.MODULE_DEBUG)
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.geneve.delete_geneve_tunnel(tunnel_name="geneve0")
        owner._connection.execute_command.assert_has_calls(
            [call("ip link set dev geneve0 down"), call("ip link del geneve0", expected_return_codes={})]
        )
        assert "Geneve: geneve0 deleted." in caplog.text

    def test_delete_geneve_tunnel_within_namespace(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.geneve.delete_geneve_tunnel(tunnel_name="geneve0", namespace_name="ns1")
        owner._connection.execute_command.assert_has_calls(
            [
                call("ip netns exec ns1 ip link set dev geneve0 down"),
                call("ip netns exec ns1 ip link del geneve0", expected_return_codes={}),
            ]
        )

    def test__delete_geneve_tunnel_device_not_present(self, owner, caplog):
        caplog.set_level(log_levels.MODULE_DEBUG)
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="", stderr="Cannot find device geneve0"
        )
        owner.geneve._delete_geneve_tunnel(tunnel_name="geneve0")
        assert "Geneve device geneve0 not present!" in caplog.text

    def test_create_setup_geneve_tunnel_ipv4_with_dstport(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.geneve.create_setup_geneve_tunnel(
            tunnel_name="gnv-interface-1",
            inner_ip_addr=IPv4Interface("10.10.10.4/8"),
            remote_ip_addr=IPv4Interface("10.10.10.11/8"),
            vni=41,
            dstport=6081,
        )
        owner._connection.execute_command.assert_has_calls(
            [
                call(
                    "ip link add gnv-interface-1 type geneve remote 10.10.10.11/8 id 41 dstport 6081 ",
                    expected_return_codes={},
                ),
                call("ip link set gnv-interface-1 up", expected_return_codes={}),
                call("ip addr add 10.10.10.4/8 dev gnv-interface-1", expected_return_codes={}),
            ]
        )

    def test_create_setup_geneve_tunnel_ipv6_with_dstport(self, owner, caplog):
        caplog.set_level(log_levels.MODULE_DEBUG)
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.geneve.create_setup_geneve_tunnel(
            tunnel_name="gnv-iface-11",
            inner_ip_addr=IPv6Interface("2001:db8:1::4/124"),
            remote_ip_addr=IPv6Interface("2001:db8:1::11/124"),
            vni=41,
            dstport=6082,
        )
        owner._connection.execute_command.assert_has_calls(
            [
                call(
                    "ip -6 link add gnv-iface-11 type geneve remote 2001:db8:1::11/124 id 41 dstport 6082 ",
                    expected_return_codes={},
                ),
                call("ip -6 link set gnv-iface-11 up", expected_return_codes={}),
                call("ip -6 addr add 2001:db8:1::4/124 dev gnv-iface-11", expected_return_codes={}),
            ]
        )
        assert "Geneve: gnv-iface-11 created and setup." in caplog.text

    def test__create_geneve_tunnel_with_dstport_exception(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="RTNETLINK answers: File exists", stderr=""
        )
        with pytest.raises(GeneveFeatureException):
            owner.geneve._create_geneve_tunnel(
                tunnel_name="gnv-interface-2",
                remote_ip_addr=IPv4Interface("10.10.10.12/8"),
                vni=42,
                dstport=6083,
            )
