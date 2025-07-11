# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import re
from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_connect.exceptions import ConnectionCalledProcessError
from mfd_ethtool import Ethtool
from mfd_typing import PCIAddress, OSName, OSBitness
from mfd_typing.network_interface import LinuxInterfaceInfo, InterfaceInfo

from mfd_network_adapter.network_interface.data_structures import RingBufferSettings, RingBuffer
from mfd_network_adapter.network_interface.exceptions import (
    BrandingStringException,
    DeviceStringException,
    NetworkQueuesException,
    RDMADeviceNotFound,
    RingBufferSettingException,
    DeviceSetupException,
)
from mfd_network_adapter.exceptions import NetworkInterfaceIncomparableObject
from mfd_network_adapter.network_interface.feature.ip import LinuxIP
from mfd_network_adapter.network_interface.feature.link import LinuxLink
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface
from mfd_network_adapter.stat_checker.linux import LinuxStatChecker


class TestLinuxNetworkInterface:
    @pytest.fixture(params=[{"namespace": None}])
    def interface(self, mocker, request):
        pci_address = PCIAddress(0, 0, 0, 0)
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.LINUX
        _connection.get_os_bitness.return_value = OSBitness.OS_64BIT

        interface_info = LinuxInterfaceInfo(
            name="eth0", pci_address=pci_address, namespace=request.param.get("namespace")
        )

        interface = LinuxNetworkInterface(connection=_connection, interface_info=interface_info)
        interface.stat_checker = mocker.create_autospec(LinuxStatChecker)
        mocker.stopall()
        return interface

    @pytest.fixture()
    def interfaces(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        interfaces = []
        interfaces.append(
            LinuxNetworkInterface(
                connection=connection,
                owner=None,
                interface_info=InterfaceInfo(name="eth0", pci_address=PCIAddress(data="0000:18:00.0")),
            )
        )
        interfaces.append(
            LinuxNetworkInterface(
                connection=connection,
                owner=None,
                interface_info=InterfaceInfo(name="eth1", pci_address=PCIAddress(data="0000:10:00.0")),
            )
        )
        yield interfaces
        mocker.stopall()

    def test_get_linux_feature_object(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "eth0"
        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )
        _connection = mocker.create_autospec(RPyCConnection)

        _connection.get_os_name.return_value = OSName.LINUX

        interface = LinuxNetworkInterface(
            connection=_connection, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name=name)
        )
        assert type(interface.ip) is LinuxIP
        assert type(interface.link) is LinuxLink

    def test_get_branding_string(self, interface):
        output = dedent(
            """\
        00:03.0 Ethernet controller: Intel Corporation 82540EM Gigabit Ethernet Controller (rev 02)
            Subsystem: Intel Corporation PRO/1000 MT Desktop Adapter
            Flags: bus master, 66MHz, medium devsel, latency 64, IRQ 19
            Memory at f0000000 (32-bit, non-prefetchable) [size=128K]
            I/O ports at d010 [size=8]
            Capabilities: <access denied>
            Kernel driver in use: e1000
            Kernel modules: e1000
        """
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert interface.get_branding_string() == "Intel Corporation PRO/1000 MT Desktop Adapter"

    def test_get_branding_string_not_found(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        with pytest.raises(
            BrandingStringException,
            match=f"No matching branding string found for pci address: {interface.pci_address.lspci}",
        ):
            interface.get_branding_string()

    def test_get_device_string(self, interface):
        output = dedent(
            """\
        00:03.0 Ethernet controller: Intel Corporation 82540EM Gigabit Ethernet Controller (rev 02)
            Subsystem: Intel Corporation PRO/1000 MT Desktop Adapter
            Flags: bus master, 66MHz, medium devsel, latency 64, IRQ 19
            Memory at f0000000 (32-bit, non-prefetchable) [size=128K]
            I/O ports at d010 [size=8]
            Capabilities: <access denied>
            Kernel driver in use: e1000
            Kernel modules: e1000
        """
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert interface.get_device_string() == "Intel Corporation 82540EM Gigabit Ethernet Controller (rev 02)"

    def test_get_device_string_not_found(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        with pytest.raises(
            DeviceStringException,
            match=f"No matching device string found for pci address: {interface.pci_address.lspci}",
        ):
            interface.get_device_string()

    def test_get_network_queues(self, interface):
        output = dedent(
            f"""
            Channel parameters for {interface.name}:
            Pre-set maximums:
            RX:             n/a
            TX:             n/a
            Other:          1
            Combined:       72
            Current hardware settings:
            RX:             n/a
            TX:             n/a
            Other:          1
            Combined:       72"
            """
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert interface.get_network_queues() == {"rx": None, "tx": None, "other": 1, "combined": 72}

    def test_get_network_queues_no_queues_in_output(self, interface):
        output = "very invalid output"
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        with pytest.raises(
            NetworkQueuesException, match=f"Could not read network queues for interface {interface.name}"
        ):
            interface.get_network_queues()

    def test_set_network_queues_no_values(self, interface):
        with pytest.raises(NetworkQueuesException, match="No values set to queues"):
            interface.set_network_queues(rx=None, tx=None, other=None, combined=None)

    def test_set_network_queues_fail(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="command", stdout="stdout", stderr="stderr"
        )
        with pytest.raises(
            NetworkQueuesException, match=f"Failed to set network queues for interface {interface.name}"
        ):
            interface.set_network_queues(rx=1, tx=None, other=None, combined=None)

    def test_get_rdma_device_name(self, interface):
        interface._interface_info.name = "eth0"
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="iwp94s0f0", stderr="stderr"
        )
        assert interface.get_rdma_device_name() == "iwp94s0f0"

    def test_get_rdma_device_name_failure(self, interface):
        interface._interface_info.name = "eth0"
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=2, args="command", stdout="", stderr="stderr"
        )
        with pytest.raises(RDMADeviceNotFound, match="Failed to find RDMA device for eth0"):
            assert interface.get_rdma_device_name()

    def test_get_numa_node(self, interface):
        output = "0"
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert interface.get_numa_node() == 0

    def test_get_numa_node_failure(self, interface, mocker):
        interface._interface_info.name = "eth0"
        mocker.patch.object(
            interface,
            "get_numa_node",
            side_effect=ConnectionCalledProcessError(1, ["cat", "/sys/class/net/eth0/devices/numa_node"]),
        )
        with pytest.raises(
            ConnectionCalledProcessError,
            match=re.escape(
                "Command '['cat', '/sys/class/net/eth0/devices/numa_node']' returned unexpected exit status "
                "1.\n\nstdout: None"
            ),
        ):
            assert interface.get_numa_node()

    def test_get_ring_settings(self, interface):
        ethtool_output = dedent(
            """\
        Ring parameters for eth1:
        Pre-set maximums:
        RX:             4096
        RX Mini:        n/a
        RX Jumbo:       n/a
        TX:             4096
        Current hardware settings:
        RX:             512
        RX Mini:        n/a
        RX Jumbo:       n/a
        TX:             512
            """
        )
        interface._interface_info.name = "eth0"
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=ethtool_output, stderr="stderr"
        )

        expected_ring_settings = RingBufferSettings()
        expected_ring_settings.maximum.rx = 4096
        expected_ring_settings.maximum.tx = 4096
        expected_ring_settings.current.rx = 512
        expected_ring_settings.current.tx = 512

        assert interface.get_ring_settings() == expected_ring_settings

    def test_set_ring_settings(self, interface):
        ring_settings = RingBuffer(rx=512, tx=512)
        interface.set_ring_settings(ring_settings)
        interface._connection.execute_command.assert_called_once_with(
            "ethtool -G eth0 rx 512 tx 512", custom_exception=RingBufferSettingException
        )

    def test_get_number_of_ports(self, interface, mocker):
        output = "      4  Intel Corporation Ethernet Controller E810-C for SFP (rev 02)"
        interface.get_device_string = mocker.Mock(return_value="Intel Corporation Ethernet Controller E810-C for SFP")
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert interface.get_number_of_ports() == 4
        cmd = (
            "lspci "
            "| grep Eth "
            "| awk -F ':' '{print $NF}' "
            "| uniq -c "
            "| grep 'Intel Corporation Ethernet Controller E810-C for SFP'"
        )
        interface._connection.execute_command.assert_called_with(command=cmd, shell=True, expected_return_codes={0})

    def test_get_number_of_ports_not_found(self, interface, mocker):
        interface.get_device_string = mocker.Mock(return_value="")
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        with pytest.raises(
            DeviceSetupException,
            match="Can't find number of ports in tested adapter.",
        ):
            interface.get_number_of_ports()

    def test__lt__false(self, mocker, interfaces):
        assert interfaces[0].__lt__(None) is False

    def test__lt__(self, mocker, interfaces):
        assert interfaces[1].__lt__(interfaces[0])

    def test__lt__error(self, mocker, interfaces):
        with pytest.raises(
            NetworkInterfaceIncomparableObject, match="Incorrect object passed for comparison with PCIAddress"
        ):
            interfaces[0].__lt__("IncorrectObject")

    def test__gt__false(self, mocker, interfaces):
        assert interfaces[0].__gt__(None) is False

    def test__gt__(self, mocker, interfaces):
        assert interfaces[0].__gt__(interfaces[1])

    def test__gt__error(self, mocker, interfaces):
        with pytest.raises(
            NetworkInterfaceIncomparableObject, match="Incorrect object passed for comparison with PCIAddress"
        ):
            interfaces[0].__gt__("IncorrectObject")
