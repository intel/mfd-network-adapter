# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import re
from textwrap import dedent
import time
import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import WindowsInterfaceInfo

from mfd_network_adapter.network_interface.exceptions import (
    LinkException,
    SpeedDuplexException,
    LinkStateException,
)
from mfd_network_adapter.network_interface.feature.link.data_structures import (
    LinkState,
    DuplexType,
    Speed,
    SpeedDuplexInfo,
)
from mfd_network_adapter.network_interface.feature.link.windows import WindowsLink
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface
from mfd_win_registry import WindowsRegistry


class TestWindowsNetworkPort:
    @pytest.fixture()
    def port(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.WINDOWS

        port = WindowsNetworkInterface(
            connection=_connection,
            interface_info=WindowsInterfaceInfo(name="Ethernet 3", pci_address=pci_address),
        )
        mocker.stopall()
        return port

    @pytest.fixture()
    def port_speed(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.WINDOWS

        port_speed = WindowsNetworkInterface(
            connection=_connection,
            interface_info=WindowsInterfaceInfo(name="SLOT 4 Port 2", pci_address=pci_address),
        )
        mocker.stopall()
        return port_speed

    def test_get_link_up(self, port):
        output_link_up = dedent(
            """\
        Name                      InterfaceDescription            ifIndex Status       MacAddress             LinkSpeed
        ----                      --------------------            ------- ------       ----------             ---------
        Ethernet 5                Intel(R) Ethernet  X550 #2      7 Up           A4-BF-01-3F-F8-59         1 Gbps"""
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_link_up, stderr=""
        )
        assert port.link.get_link() is LinkState.UP

    def test_get_link_down(self, port):
        output_link_down = dedent(
            """\
        Name                      InterfaceDescription            ifIndex Status       MacAddress             LinkSpeed
        ----                      --------------------            ------- ------       ----------             ---------
        Ethernet 3                Intel(R) Ethernet X550    10 Disconnected A4-BF-01-3F-F8-5A          0 bps"""
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_link_down, stderr=""
        )
        assert port.link.get_link() is LinkState.DOWN

    def test_set_link_up(self, mocker, port):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.get_link",
            mocker.create_autospec(WindowsLink.get_link, return_value=True),
        )
        port.link.set_link(state=LinkState.UP)
        expected_cmd = 'enable-netadapter "Ethernet 3" -Confirm:$false'
        port._connection.execute_powershell.assert_called_once_with(
            expected_cmd, custom_exception=LinkException, shell=True
        )

    def test_set_link_down(self, mocker, port):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.get_link",
            mocker.create_autospec(WindowsLink.get_link, return_value=True),
        )
        port.link.set_link(state=LinkState.DOWN)
        expected_cmd = 'disable-netadapter "Ethernet 3" -Confirm:$false'
        port._connection.execute_powershell.assert_called_once_with(
            expected_cmd, custom_exception=LinkException, shell=True
        )

    def test_set_speed_duplex(self, mocker, port_speed):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=None),
        )
        mocker.patch(
            "mfd_win_registry.WindowsRegistry._convert_interface_to_index",
            mocker.create_autospec(WindowsRegistry._convert_interface_to_index, return_value="5"),
        )
        feature_enum = {
            "0": "Auto Negotiation",
            "25000": "25 Gbps Full Duplex",
            "50000": "50 Gbps Full Duplex",
            "10": "100 Gbps Full Duplex",
            "PSPath": (
                "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\CurrentControlSet\\control"
                "\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0005\\Ndi\\Params\\*SpeedDuplex\\enum"
            ),
            "PSParentPath": (
                "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\CurrentControlSet"
                "\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0005\\Ndi\\Params\\*SpeedDuplex"
            ),
            "PSChildName": "enum",
            "PSDrive": "HKLM",
            "PSProvider": "Microsoft.PowerShell.Core\\Registry",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_enum",
            mocker.create_autospec(WindowsRegistry.get_feature_enum, return_value=feature_enum),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        port_speed._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        port_speed.link.set_speed_duplex(Speed.G25, DuplexType.FULL)

    def test_set_speed_duplex_doesnt_exist(self, mocker, port_speed):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.set_feature",
            mocker.create_autospec(WindowsRegistry.set_feature, return_value=None),
        )
        mocker.patch(
            "mfd_win_registry.WindowsRegistry._convert_interface_to_index",
            mocker.create_autospec(WindowsRegistry._convert_interface_to_index, return_value="5"),
        )
        feature_enum = {
            "0": "Auto Negotiation",
            "25000": "25 Gbps Full Duplex",
            "50000": "50 Gbps Full Duplex",
            "10": "100 Gbps Full Duplex",
            "PSPath": (
                "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\CurrentControlSet\\control"
                "\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0005\\Ndi\\Params\\*SpeedDuplex\\enum"
            ),
            "PSParentPath": (
                "Microsoft.PowerShell.Core\\Registry::HKEY_LOCAL_MACHINE\\system\\CurrentControlSet"
                "\\control\\class\\{4D36E972-E325-11CE-BFC1-08002BE10318}\\0005\\Ndi\\Params\\*SpeedDuplex"
            ),
            "PSChildName": "enum",
            "PSDrive": "HKLM",
            "PSProvider": "Microsoft.PowerShell.Core\\Registry",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_enum",
            mocker.create_autospec(WindowsRegistry.get_feature_enum, return_value=feature_enum),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        port_speed._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        with pytest.raises(
            SpeedDuplexException,
            match="Cannot find speed: 25 gbps or duplex: auto in available enum",
        ):
            port_speed.link.set_speed_duplex(Speed.G25, DuplexType.AUTO)

    def test_get_available_speed(self, port_speed):
        output = "0\n25000\n50000\n10\n"
        expected = [
            "25 Gbps Full Duplex",
            "50 Gbps Full Duplex",
            "100 Gbps Full Duplex",
        ]
        port_speed.link._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr=""
        )
        assert expected == port_speed.link.get_available_speed()

    def test_get_speed_duplex(self, port_speed):
        output = dedent(
            """\
    LinkSpeed FullDuplex
    --------- ----------
    100 Gbps        True
        """
        )
        expected_cmd = (
            rf'Get-NetAdapter -Name "{port_speed.name}" | '
            rf"Select-Object -Property  {SpeedDuplexInfo.LINKSPEED}, {SpeedDuplexInfo.FULLDUPLEX}"
        )
        expected = {"speed": Speed.G100, "duplex": DuplexType.FULL}
        port_speed.link._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr=""
        )
        assert expected == port_speed.link.get_speed_duplex()
        port_speed._connection.execute_powershell.assert_called_once_with(expected_cmd, custom_exception=LinkException)

    def test_get_speed_duplex_error(self, port_speed):
        output = dedent(
            """\
    LinkOut   FullDuplex
    --------- ----------
    100 Gbps        None
        """
        )
        expected_cmd = (
            rf'Get-NetAdapter -Name "{port_speed.name}" | '
            rf"Select-Object -Property  {SpeedDuplexInfo.LINKSPEED}, {SpeedDuplexInfo.FULLDUPLEX}"
        )
        port_speed.link._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr=""
        )
        with pytest.raises(SpeedDuplexException):
            port_speed.link.get_speed_duplex()
        port_speed._connection.execute_powershell.assert_called_once_with(expected_cmd, custom_exception=LinkException)

    def test_is_auto_negotiation_when_on(self, port_speed, mocker):
        feature_list = {SpeedDuplexInfo.SPEEDDUPLEX: "0"}
        feature_enum = {
            "0": "Auto Negotiation",
            "4": "100 Mbps Full Duplex",
            "6": "1.0 Gbps Full Duplex",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=feature_list),
        )
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_enum",
            mocker.create_autospec(WindowsRegistry.get_feature_enum, return_value=feature_enum),
        )
        assert port_speed.link.is_auto_negotiation() is True

    def test_is_auto_negotiation_when_off(self, port_speed, mocker):
        feature_list = {SpeedDuplexInfo.SPEEDDUPLEX: "4"}
        feature_enum = {
            "0": "Auto Negotiation",
            "4": "100 Mbps Full Duplex",
            "6": "1.0 Gbps Full Duplex",
        }
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value=feature_list),
        )
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_enum",
            mocker.create_autospec(WindowsRegistry.get_feature_enum, return_value=feature_enum),
        )
        assert port_speed.link.is_auto_negotiation() is False

    def test_is_auto_negotiation_raises_exception_when_speed_duplex_not_found(self, port_speed, mocker):
        mocker.patch(
            "mfd_win_registry.WindowsRegistry.get_feature_list",
            mocker.create_autospec(WindowsRegistry.get_feature_list, return_value={}),
        )
        with pytest.raises(
            SpeedDuplexException,
            match=re.escape(f"Cannot find {SpeedDuplexInfo.SPEEDDUPLEX} in available interface features"),
        ):
            port_speed.link.is_auto_negotiation()

    def test_get_link_speed(self, port):
        expected_cmd = f"(Get-NetAdapter -Name '{port.name}').LinkSpeed"
        output = "10 Gbps\n"
        port.link._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert port.link.get_link_speed() == "10 Gbps"
        port.link._connection.execute_powershell.assert_called_once_with(
            expected_cmd,
            custom_exception=LinkException,
            shell=True,
        )

    def test_get_link_speed_if_disconnected(self, port):
        output = "0 bps\n"
        port.link._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        err = "Link is not established"
        with pytest.raises(LinkStateException) as exc:
            port.link.get_link_speed()
        assert str(exc.value) == err

    def test_get_link_speed_if_not_start_with_int(self, port):
        output = "unexpected error"
        port.link._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        err = "Got unexpected link speed format. output='unexpected error'"
        with pytest.raises(LinkStateException) as exc:
            port.link.get_link_speed()
        assert str(exc.value) == err

    def test_get_link_speed_if_no_output(self, port):
        output = ""
        port.link._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        err = "Unable to determine the link speed by PScmdlet. Please run 'Get-NetAdapter | fl' to define the issue."
        with pytest.raises(LinkStateException) as exc:
            port.link.get_link_speed()
        assert str(exc.value) == err

    def test_get_link_speed_if_exception_on_execute(self, port):
        port.link._connection.execute_powershell.side_effect = LinkException(1, cmd="cmd")
        err = "Unable to determine the link speed: Command 'cmd' returned non-zero exit status 1."
        with pytest.raises(LinkStateException) as exc:
            port.link.get_link_speed()
        assert str(exc.value) == err

    def test_get_link_speed_if_execute_not_implemented(self, port):
        port.link._connection.execute_powershell.side_effect = NotImplementedError()
        err = "execute_powershell is not implemented for this connection type."
        with pytest.raises(LinkStateException) as exc:
            port.link.get_link_speed()
        assert str(exc.value) == err
