# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test ARP ESXi."""

import pytest
from ipaddress import IPv4Interface, IPv6Interface

from mfd_connect import RPyCConnection
from mfd_typing import OSName
from mfd_connect.base import ConnectionCompletedProcess

from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner
from mfd_network_adapter.network_adapter_owner.exceptions import ARPFeatureException


class TestESXiInterrupt:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.ESXI
        host = ESXiNetworkAdapterOwner(connection=connection)
        yield host
        mocker.stopall()

    def test_del_arp_entry_ipv4(self, owner):
        output = ""
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        owner.arp.del_arp_entry(ip=IPv4Interface("10.10.10.10"))
        owner._connection.execute_command.assert_called_with(
            "esxcli network ip neighbor remove -a 10.10.10.10 -v 4", shell=True, custom_exception=ARPFeatureException
        )

    def test_del_arp_entry_ipv6(self, owner):
        output = ""
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        owner.arp.del_arp_entry(ip=IPv6Interface("2001:db8:85a3::8a2e:370:7334"))
        owner._connection.execute_command.assert_called_with(
            "esxcli network ip neighbor remove -a 2001:db8:85a3::8a2e:370:7334 -v 6",
            shell=True,
            custom_exception=ARPFeatureException,
        )

    def test_del_arp_entry_error(self, owner):
        owner._connection.execute_command.side_effect = ARPFeatureException(
            cmd="esxcli network ip neighbor remove -a 10.10.10.10 -v 4", returncode=1, stderr=""
        )
        with pytest.raises(ARPFeatureException):
            owner.arp.del_arp_entry(ip=IPv4Interface("10.10.10.10"))
