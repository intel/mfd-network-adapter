# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
from mfd_common_libs.exceptions import UnexpectedOSException
from mfd_connect import RPyCConnection
from mfd_packet_capture import Tshark
from mfd_typing import OSName, OSType
from mfd_typing.network_interface import WindowsInterfaceInfo

from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface


class TestCaptureLinux:
    @pytest.fixture
    def interface(self, mocker):
        name = "eth0"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.WINDOWS
        _connection.get_os_type.return_value = OSType.WINDOWS

        interface = WindowsNetworkInterface(connection=_connection, interface_info=WindowsInterfaceInfo(name=name))
        mocker.stopall()
        return interface

    @pytest.fixture()
    def tshark(self, mocker, interface):
        mocker.patch(
            "mfd_packet_capture.tshark.Tshark.check_if_available",
            mocker.create_autospec(Tshark.check_if_available),
        )
        mocker.patch(
            "mfd_packet_capture.tshark.Tshark._get_tool_exec_factory",
            mocker.create_autospec(Tshark._get_tool_exec_factory, return_value="tshark"),
        )
        mocker.patch("mfd_packet_capture.tshark.Tshark.get_version", mocker.create_autospec(Tshark.get_version))
        interface.capture.tshark.start(filters="", additional_args="")

    def test_tshark_start(self, interface, tshark):
        assert isinstance(interface.capture.tshark, Tshark)

    def test_tcpdump_start_tcpdump_not_supported(self, interface):
        with pytest.raises(UnexpectedOSException, match="Found unexpected OS"):
            interface.capture.tcpdump

    def test_pktcap_start_tcpdump_not_supported(self, interface):
        with pytest.raises(UnexpectedOSException, match="Found unexpected OS"):
            interface.capture.pktcap
