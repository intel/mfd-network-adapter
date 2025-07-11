# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Tests for `mfd_ipu` package."""

from dataclasses import dataclass

from _pytest.fixtures import fixture
from mfd_cli_client import CliClient
from mfd_typing import MACAddress
from mfd_typing.network_interface import InterfaceType, VsiInfo, LinuxInterfaceInfo

from mfd_network_adapter.network_adapter_owner.ipu_interface import IPUInterface


class TestIPUInterface:
    @fixture
    def ipu(self, mocker):
        cli_client = mocker.create_autospec(CliClient)

        @dataclass
        class NetworkOwner:
            pass

        class IpuNetworkOwner(IPUInterface, NetworkOwner):
            pass

        return IpuNetworkOwner(cli_client=cli_client)

    def test__update_vsi_info(self, ipu, mocker):
        from mfd_cli_client.base import VsiConfigListEntry

        vsi_config_vport = VsiConfigListEntry(1, 2, False, 4, 5, True, True, MACAddress("AA:BB:CC:DD:EE:FF"))
        vsi_config_vf = VsiConfigListEntry(6, 7, True, 8, 9, True, True, MACAddress("AA:BB:CC:00:00:00"))

        vsi_config_list = [vsi_config_vport, vsi_config_vf]
        ipu._get_mac_address = mocker.Mock(
            return_value=[MACAddress("AA:BB:CC:DD:EE:FF"), MACAddress("AA:BB:CC:00:00:00")]
        )
        ipu.cli_client.get_vsi_config_list = mocker.Mock(return_value=vsi_config_list)

        interfaces = [
            LinuxInterfaceInfo(interface_type=InterfaceType.VPORT, mac_address=MACAddress("AA:BB:CC:DD:EE:FF")),
            LinuxInterfaceInfo(interface_type=InterfaceType.VF, mac_address=MACAddress("AA:BB:CC:00:00:00")),
        ]
        interfaces_expected = [
            LinuxInterfaceInfo(
                interface_type=InterfaceType.VPORT,
                mac_address=MACAddress("AA:BB:CC:DD:EE:FF"),
                vsi_info=VsiInfo(1, 2, False, 4, 5, True, True),
            ),
            LinuxInterfaceInfo(
                interface_type=InterfaceType.VF,
                mac_address=MACAddress("AA:BB:CC:00:00:00"),
                vsi_info=VsiInfo(6, 7, True, 8, 9, True, True),
            ),
        ]

        ipu._update_vsi_info(interfaces=interfaces)
        assert interfaces == interfaces_expected
