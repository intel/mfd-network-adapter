# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest
from mfd_connect import SSHConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_const import Speed
from mfd_ethtool import Ethtool
from mfd_ethtool.exceptions import EthtoolExecutionError
from mfd_typing import OSName, PCIDevice
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.exceptions import LLDPFeatureException
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface


class TestLinux:
    @pytest.fixture()
    def lldp_obj(self, mocker):
        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )
        pci_device = PCIDevice(data="8086:159B")
        name = "eth0"
        _connection = mocker.create_autospec(SSHConnection)
        _connection.get_os_name.return_value = OSName.LINUX

        interface = LinuxNetworkInterface(
            connection=_connection,
            interface_info=LinuxInterfaceInfo(pci_device=pci_device, name=name),
        )
        yield interface.lldp
        mocker.stopall()

    def test_set_fwlldp_enabled(self, lldp_obj):
        lldp_obj._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="", return_code=0, stderr=""
        )
        lldp_obj.set_fwlldp(enabled=State.ENABLED)
        lldp_obj._connection.execute_command.assert_called_with(
            f"ethtool --set-priv-flags {lldp_obj._interface().name} fw-lldp-agent on",
            custom_exception=EthtoolExecutionError,
            expected_return_codes=frozenset({0}),
        )

    def test_set_fwlldp_disabled(self, lldp_obj):
        lldp_obj._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="", return_code=0, stderr=""
        )
        lldp_obj.set_fwlldp(enabled=State.DISABLED)
        lldp_obj._connection.execute_command.assert_called_with(
            f"ethtool --set-priv-flags {lldp_obj._interface().name} fw-lldp-agent off",
            custom_exception=EthtoolExecutionError,
            expected_return_codes=frozenset({0}),
        )

    def test_set_fwlldp_error_enable(self, lldp_obj):
        lldp_obj._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="", return_code=1, stderr=""
        )
        lldp_obj.speed = Speed.G1
        pci_device = lldp_obj._interface().pci_device
        temp_pci_device = PCIDevice(data="8086:1562")
        lldp_obj._interface()._interface_info.pci_device = temp_pci_device
        with pytest.raises(LLDPFeatureException, match="FW-LLDP not supported"):
            lldp_obj.set_fwlldp(enabled=State.ENABLED)
        lldp_obj._interface()._interface_info.pci_device = pci_device

    def test_is_fwlldp_enabled(self, lldp_obj):
        output = dedent(
            r"""
            Private flags for eth0:
            link-down-on-close           : off
            fw-lldp-agent                : on
            channel-inline-fd-mark       : off
            channel-pkt-inspect-optimize : on
            channel-pkt-clean-bp-stop    : off
            channel-pkt-clean-bp-stop-cfg: off
            vf-true-promisc-support      : off
            mdd-auto-reset-vf            : off
            vf-vlan-pruning              : off
            legacy-rx                    : off
            cgu_fast_lock                : off
            dpll_monitor                 : off
            extts_filter                 : off
            itu_g8262_filter_used        : off
            allow-no-fec-modules-in-auto : off
            """
        )
        lldp_obj._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert lldp_obj.is_fwlldp_enabled() is True
        lldp_obj._connection.execute_command.assert_called_with(
            f"ethtool --show-priv-flags {lldp_obj._interface().name}",
            custom_exception=EthtoolExecutionError,
            expected_return_codes=frozenset({0}),
        )

    def test_is_fwlldp_enabled_error(self, lldp_obj):
        output = dedent(
            r"""
            Private flags for eth0:
            link-down-on-close           : off
            channel-inline-fd-mark       : off
            channel-pkt-inspect-optimize : on
            channel-pkt-clean-bp-stop    : off
            channel-pkt-clean-bp-stop-cfg: off
            vf-true-promisc-support      : off
            mdd-auto-reset-vf            : off
            vf-vlan-pruning              : off
            legacy-rx                    : off
            cgu_fast_lock                : off
            dpll_monitor                 : off
            extts_filter                 : off
            itu_g8262_filter_used        : off
            allow-no-fec-modules-in-auto : off
            """
        )
        lldp_obj._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        with pytest.raises(Exception, match="'EthtoolShowPrivFlags' object has no attribute 'fw_lldp_agent'"):
            lldp_obj.is_fwlldp_enabled()
