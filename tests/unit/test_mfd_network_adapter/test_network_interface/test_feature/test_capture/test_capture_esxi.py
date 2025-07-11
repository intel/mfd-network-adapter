# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
from mfd_common_libs.exceptions import UnexpectedOSException
from mfd_connect import RPyCConnection
from mfd_packet_capture import Tcpdump, PktCap
from mfd_typing import OSName
from mfd_typing.network_interface import InterfaceInfo

from mfd_network_adapter.network_interface.linux import NetworkInterface


class TestCaptureESXI:
    @pytest.fixture
    def interface(self, mocker):
        name = "eth0"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.ESXI

        interface = NetworkInterface(connection=_connection, interface_info=InterfaceInfo(name=name))
        mocker.stopall()
        return interface

    @pytest.fixture()
    def tcpdump(self, mocker, interface):
        mocker.patch(
            "mfd_packet_capture.tcpdump.Tcpdump.check_if_available",
            mocker.create_autospec(Tcpdump.check_if_available),
        )
        mocker.patch(
            "mfd_packet_capture.tcpdump.Tcpdump._get_tool_exec_factory",
            mocker.create_autospec(Tcpdump._get_tool_exec_factory, return_value="tcpdump"),
        )
        mocker.patch("mfd_packet_capture.tcpdump.Tcpdump.get_version", mocker.create_autospec(Tcpdump.get_version))
        interface.capture.tcpdump.start()

    @pytest.fixture()
    def pktcap(self, mocker, interface):
        mocker.patch(
            "mfd_packet_capture.pktcap.PktCap.check_if_available",
            mocker.create_autospec(PktCap.check_if_available),
        )
        mocker.patch(
            "mfd_packet_capture.pktcap.PktCap._get_tool_exec_factory",
            mocker.create_autospec(PktCap._get_tool_exec_factory, return_value="pktcap-uw"),
        )
        mocker.patch("mfd_packet_capture.pktcap.PktCap.get_version", mocker.create_autospec(PktCap.get_version))
        interface.capture.pktcap.start()

    def test_tshark_start_tshark_not_supported(self, interface):
        with pytest.raises(UnexpectedOSException, match="Found unexpected OS"):
            interface.capture.tshark

    def test_tcpdump_start(self, interface, tcpdump):
        assert isinstance(interface.capture.tcpdump, Tcpdump)

    def test_pktcap_start(self, interface, pktcap):
        assert isinstance(interface.capture.pktcap, PktCap)
