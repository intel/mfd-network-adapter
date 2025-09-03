# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from dataclasses import dataclass
from pathlib import PurePosixPath
from textwrap import dedent
from typing import List

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_ethtool import Ethtool
from mfd_typing import PCIDevice, PCIAddress, OSName, MACAddress, VendorID, DeviceID, SubDeviceID, SubVendorID
from mfd_typing.network_interface import LinuxInterfaceInfo, InterfaceType, VlanInterfaceInfo

from mfd_network_adapter.exceptions import NetworkAdapterModuleException
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner

sys_class_stdout = dedent(
    """
    total 0
    lrwxrwxrwx 1 root root 0 Dec 29 17:06 eth2 -> ../../devices/pci0000:17/0000:17:01.0/0000:18:00.0/net/eth2
    lrwxrwxrwx 1 root root 0 Dec 29 17:06 br0 -> ../../devices/virtual/net/br0
    lrwxrwxrwx 1 root root 0 May 24 14:16 dummy0 -> ../../devices/virtual/net/dummy0
    lrwxrwxrwx 1 root root 0 Dec 29 17:09 eth3 -> ../../devices/pci0000:5d/0000:5d:00.0/0000:5e:00.0/net/eth3
    lrwxrwxrwx 1 root root 0 Dec 29 17:09 eth1 -> ../../devices/pci0000:5d/0000:5d:00.0/0000:5e:00.1/net/eth1

"""
)
sys_class_vmic_stdout = dedent(
    """
    total 0
    lrwxrwxrwx 1 root root 0 Sep 2 12:13 enP3234353 -> ../../devices/LNXSYSTM:00/LNXSYBUS:00/ACPI0004:00/MSFT1000:00/bad7fd18-7e57-4561-8392-64ea14aa42e6/pci7e57:00/7e57:00:02.0/net/enP3234353
    lrwxrwxrwx 1 root root 0 Sep 2 12:13 enP5618552 -> ../../devices/LNXSYSTM:00/LNXSYBUS:00/ACPI0004:00/MSFT1000:00/5ecacc75-db79-4e48-87c5-ca5c5a9a70ef/pci4b79:00/db79:00:02.0/net/enP5618552
    lrwxrwxrwx 1 root root 0 Sep 2 14:09 eth0 -> ../../devices/LNXSYSTM:00/LNXSYBUS:00/ACPI0004:00/MSFT1000:00/8229b887-f2a9-4b12-8994-38377a7d1d9a/net/eth0
    lrwxrwxrwx 1 root root 0 Sep 2 14:09 eth1 -> ../../devices/LNXSYSTM:00/LNXSYBUS:00/ACPI0004:00/MSFT1000:00/28995f2f-d495-4f98-b662-088946355eb4/net/eth1
    lrwxrwxrwx 1 root root 0 Sep 2 14:09 eth2 -> ../../devices/LNXSYSTM:00/LNXSYBUS:00/ACPI0004:00/MSFT1000:00/7c6fd2f9-ce6c-43e3-8c41-d44954396dc9/net/eth2
    lrwxrwxrwx 1 root root 0 Sep 2 14:09 eth3 -> ../../devices/LNXSYSTM:00/LNXSYBUS:00/ACPI0004:00/MSFT1000:00/73ffadd9-6b65-4138-88a4-2d281a9b6173/net/eth3
    lrwxrwxrwx 1 root root 0 Sep 2 14:09 eth4 -> ../../devices/LNXSYSTM:00/LNXSYBUS:00/ACPI0004:00/MSFT1000:00/8629f04f-37fc-422a-87e3-85b8b3e61515/net/eth4
    lrwxrwxrwx 1 root root 0 Sep 2 14:09 lo -> ../../devices/virtual/net/lo
"""  # noqa: E501
)
cmd_output = {
    "lspci -D -nnvvvmm | grep -B1 -A6 '^Class.*Ethernet'": dedent(
        """\
        Slot:   0000:18:00.0
        Class:  Ethernet controller [0200]
        Vendor: Intel Corporation [8086]
        Device: Ethernet Controller 10G X550T [1563]
        SVendor:        Intel Corporation [8086]
        SDevice:        Device [35d4]
        Rev:    01
        NUMANode:       0
        --
        Slot:   0000:18:00.1
        Class:  Ethernet controller [0200]
        Vendor: Intel Corporation [8086]
        Device: Ethernet Controller 10G X550T [1563]
        SVendor:        Intel Corporation [8086]
        SDevice:        Device [35d4]
        Rev:    01
        NUMANode:       0"""
    ),
    "lspci -v -mm -nn -s 0000:18:00.0": dedent(
        """\
        Slot:   18:00.0
        Class:  Ethernet controller [0200]
        Vendor: Intel Corporation [8086]
        Device: Ethernet Controller 10G X550T [1563]
        SVendor:        Intel Corporation [8086]
        SDevice:        Device [35d4]
        Rev:    01
        NUMANode:       0
        IOMMUGroup:     36"""
    ),
    "lspci -v -mm -nn -s 0000:18:00.1": dedent(
        """\
        Slot:   18:00.1
        Class:  Ethernet controller [0200]
        Vendor: Intel Corporation [8086]
        Device: Ethernet Controller 10G X550T [1563]
        SVendor:        Intel Corporation [8086]
        SDevice:        Device [35d4]
        Rev:    01
        NUMANode:       0
        IOMMUGroup:     36"""
    ),
    "cat /sys/class/net/eth3/device/uevent": dedent(
        """\
        DRIVER=ixgbe
        PCI_CLASS=20000
        PCI_ID=8086:1563
        PCI_SUBSYS_ID=8086:35D4
        PCI_SLOT_NAME=0000:18:00.1
        MODALIAS=pci:v00008086d00001563sv00008086sd000035D4bc02sc00i00"""
    ),
    "cat /sys/class/net/bootnet/device/uevent": dedent(
        """\
        DRIVER=ixgbe
        PCI_CLASS=20000
        PCI_ID=8086:1563
        PCI_SUBSYS_ID=8086:35D4
        PCI_SLOT_NAME=0000:18:00.0
        MODALIAS=pci:v00008086d00001563sv00008086sd000035D4bc02sc00i00"""
    ),
    "lspci -d 8086:1563 -D": dedent(
        """\
        0000:18:00.0 Ethernet controller: Intel Corporation Ethernet Controller 10G X550T (rev 01)
        0000:18:00.1 Ethernet controller: Intel Corporation Ethernet Controller 10G X550T (rev 01)"""
    ),
    "ls /sys/bus/pci/devices/0000:18:00.0/net": "bootnet",
    "ls /sys/bus/pci/devices/0000:18:00.1/net": "eth3",
}


linux_expected = {
    "system": OSName.LINUX,
    "pci_device": PCIDevice("8086", "1563", "8086", "35d4"),
    "pci_addresses": [PCIAddress(0000, 24, 00, 0), PCIAddress(0000, 24, 00, 1)],
    "names": ["bootnet", "eth3"],
    "family": "SGVL",
    "speed": "@10G",
    "cmd_output": cmd_output,
}


class TestLinuxNetworkOwner:
    @pytest.fixture()
    def owner(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.LINUX
        return LinuxNetworkAdapterOwner(connection=conn)

    def test__gather_all_sys_class_interfaces_not_virtual_vmnic(self, owner, mocker):
        result = owner._gather_all_sys_class_interfaces_not_virtual(
            sys_class_net_lines=sys_class_vmic_stdout.splitlines(), namespace=None
        )
        assert len(result) == 7
        assert len([iface for iface in result if iface.interface_type == InterfaceType.VMNIC]) == 5
        assert all(iface.uuid is not None for iface in result if iface.interface_type == InterfaceType.VMNIC)

    def test__update_interfaces_with_sys_class_net_data_not_virtual_vmnic_handling(self, owner, mocker):
        """Test that VMNIC interfaces are extended and removed from sys_class_interfaces."""
        # Prepare sys_class_net_lines with VMNIC and PF
        sys_class_net_lines = [
            "lrwxrwxrwx 1 root root 0 Dec 29 17:06 vmnic1 -> ../../devices/pci0000:17/0000:17:01.0/0000:18:00.1/net/vmnic1",  # noqa: E501
            "lrwxrwxrwx 1 root root 0 Dec 29 17:06 eth3 -> ../../devices/pci0000:17/0000:17:01.0/0000:18:00.1/net/eth3",  # noqa: E501
        ]
        namespace = "ns2"
        # Patch _gather_all_sys_class_interfaces_not_virtual to return VMNIC and PF
        vmnic_iface = LinuxInterfaceInfo(
            name="vmnic1", interface_type=InterfaceType.VMNIC, installed=True, namespace=namespace
        )
        pf_iface = LinuxInterfaceInfo(name="eth3", interface_type=InterfaceType.PF, installed=True, namespace=namespace)
        mocker.patch.object(
            LinuxNetworkAdapterOwner,
            "_gather_all_sys_class_interfaces_not_virtual",
            return_value=[vmnic_iface, pf_iface],
        )
        # Patch other static methods to no-op
        mocker.patch.object(LinuxNetworkAdapterOwner, "_update_pci_device_in_sys_class_net")
        mocker.patch.object(LinuxNetworkAdapterOwner, "_mark_vport_interfaces")
        mocker.patch.object(LinuxNetworkAdapterOwner, "_update_pfs")
        mocker.patch.object(LinuxNetworkAdapterOwner, "_gather_all_vmbus_interfaces", return_value=[])
        interfaces = []
        owner._update_interfaces_with_sys_class_net_data_not_virtual(interfaces, sys_class_net_lines, namespace)
        # VMNIC should be added to interfaces, and not present in sys_class_interfaces
        assert any(iface.name == "vmnic1" and iface.interface_type == InterfaceType.VMNIC for iface in interfaces)
        assert not any(iface.name == "vmnic1" for iface in [pf_iface])

    def test_load_driver_file(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(args="", return_code=0)
        owner.load_driver_file(driver_filepath=PurePosixPath("/home/driver40/driver.k"))
        owner._connection.execute_command.assert_called_once_with("insmod /home/driver40/driver.k")

    def test_load_driver_file_with_params(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(args="", return_code=0)
        owner.load_driver_file(driver_filepath=PurePosixPath("/home/driver40/driver.k"), params={"quiet": True})
        owner._connection.execute_command.assert_called_once_with("insmod /home/driver40/driver.k quiet=True")

    def test_load_driver_module(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(args="", return_code=0)
        owner.load_driver_module(driver_name="driver12")
        owner._connection.execute_command.assert_called_once_with("modprobe driver12")

    def test_load_driver_module_with_params(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(args="", return_code=0)
        owner.load_driver_module(driver_name="driver12", params={"quiet": True})
        owner._connection.execute_command.assert_called_once_with("modprobe driver12 quiet=True")

    def test_unload_driver_module(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(args="", return_code=0)
        owner.unload_driver_module(driver_name="driver12")
        owner._connection.execute_command.assert_called_once_with("modprobe -r driver12")

    def test_reload_driver_module(self, owner, mocker):
        time_sleep = 10
        owner.unload_driver_module = mocker.create_autospec(owner.unload_driver_module)
        owner.load_driver_module = mocker.create_autospec(owner.load_driver_module)
        time_patch = mocker.patch("mfd_network_adapter.network_adapter_owner.linux.time.sleep")
        driver_name = "driver12"
        owner.reload_driver_module(driver_name=driver_name, reload_time=time_sleep)
        owner.unload_driver_module.assert_called_once_with(driver_name=driver_name)
        owner.load_driver_module.assert_called_once_with(driver_name=driver_name, params=None)
        time_patch.assert_called_once_with(time_sleep)

    def test__get_network_namespaces(self, owner, mocker):
        stdout = dedent(
            """
        siemanko_namespace4
        siemanko_namespace3
        siemanko_namespace2
        siemanko_namespace (id: 0)
        """
        )
        owner._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, stdout=stdout, args=0)
        )

        assert owner._get_network_namespaces() == [
            "siemanko_namespace4",
            "siemanko_namespace3",
            "siemanko_namespace2",
            "siemanko_namespace",
        ]

    def test__update_data_based_on_sys_class_net(self, owner, mocker):
        namespace = "foo"
        owner._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(stdout=sys_class_stdout, return_code=0, args="")
        )
        interfaces = [
            LinuxInterfaceInfo(
                installed=False,
                interface_type=InterfaceType.ETH_CONTROLLER,
                pci_device=PCIDevice(data="8086:1572"),
                pci_address=PCIAddress(data="0000:18:00.0"),
                namespace=namespace,
            )
        ]
        owner._update_vlans = mocker.Mock(return_value=None)
        owner._update_virtual_function_interfaces = mocker.Mock(return_value=None)
        owner._update_data_based_on_sys_class_net(interfaces=interfaces, namespace=namespace)

        eth2 = LinuxInterfaceInfo(
            name="eth2",
            pci_address=PCIAddress(data="0000:18:00.0"),
            installed=True,
            interface_type=InterfaceType.PF,
            namespace=namespace,
            pci_device=PCIDevice(data="8086:1572"),
        )
        eth3 = LinuxInterfaceInfo(
            name="eth3",
            pci_address=PCIAddress(data="0000:5e:00.0"),
            installed=True,
            interface_type=InterfaceType.PF,
            namespace=namespace,
        )
        eth1 = LinuxInterfaceInfo(
            name="eth1",
            pci_address=PCIAddress(data="0000:5e:00.1"),
            installed=True,
            interface_type=InterfaceType.PF,
            namespace=namespace,
        )
        br0 = LinuxInterfaceInfo(
            name="br0", installed=True, interface_type=InterfaceType.VIRTUAL_DEVICE, namespace=namespace
        )
        dummy0 = LinuxInterfaceInfo(
            name="dummy0", installed=True, interface_type=InterfaceType.VIRTUAL_DEVICE, namespace=namespace
        )

        expected = [eth2, eth3, eth1, br0, dummy0]

        assert expected == interfaces

    def test__get_interfaces_from_sys_class_net_data_virtual(self, owner):
        namespace = "foo"
        br0 = LinuxInterfaceInfo(
            name="br0", installed=True, interface_type=InterfaceType.VIRTUAL_DEVICE, namespace=namespace
        )
        dummy0 = LinuxInterfaceInfo(
            name="dummy0", installed=True, interface_type=InterfaceType.VIRTUAL_DEVICE, namespace=namespace
        )
        assert [br0, dummy0] == owner._get_interfaces_from_sys_class_net_data_virtual(
            sys_class_net_lines=sys_class_stdout.splitlines(), namespace=namespace
        )

    def test__gather_all_sys_class_interfaces_not_virtual(self, owner):
        eth2 = LinuxInterfaceInfo(
            name="eth2", pci_address=PCIAddress(data="0000:18:00.0"), installed=True, interface_type=InterfaceType.PF
        )
        eth3 = LinuxInterfaceInfo(
            name="eth3", pci_address=PCIAddress(data="0000:5e:00.0"), installed=True, interface_type=InterfaceType.PF
        )
        eth1 = LinuxInterfaceInfo(
            name="eth1", pci_address=PCIAddress(data="0000:5e:00.1"), installed=True, interface_type=InterfaceType.PF
        )

        interfaces_expected = [eth2, eth3, eth1]
        assert interfaces_expected == owner._gather_all_sys_class_interfaces_not_virtual(
            sys_class_net_lines=sys_class_stdout.splitlines(), namespace=None
        )

    def test__update_pci_device_in_sys_class_net(self, owner):
        eth2 = LinuxInterfaceInfo(
            name="eth2", pci_address=PCIAddress(data="0000:18:00.0"), installed=True, interface_type=InterfaceType.PF
        )
        eth3 = LinuxInterfaceInfo(
            name="eth3", pci_address=PCIAddress(data="0000:5e:00.0"), installed=True, interface_type=InterfaceType.PF
        )
        eth1 = LinuxInterfaceInfo(
            name="eth1", pci_address=PCIAddress(data="0000:5e:00.1"), installed=True, interface_type=InterfaceType.PF
        )

        s_eth2 = LinuxInterfaceInfo(pci_address=PCIAddress(data="0000:18:00.0"), pci_device=PCIDevice(data="8086:2222"))
        s_eth3 = LinuxInterfaceInfo(pci_address=PCIAddress(data="0000:5e:00.0"), pci_device=PCIDevice(data="8086:3333"))
        s_eth1 = LinuxInterfaceInfo(pci_address=PCIAddress(data="0000:5e:00.1"), pci_device=PCIDevice(data="8086:1111"))

        source_list = [s_eth1, s_eth2, s_eth3]
        destination_list = [eth2, eth3, eth1]

        ex_eth2 = LinuxInterfaceInfo(
            name="eth2",
            pci_address=PCIAddress(data="0000:18:00.0"),
            installed=True,
            interface_type=InterfaceType.PF,
            pci_device=PCIDevice(data="8086:2222"),
        )
        ex_eth3 = LinuxInterfaceInfo(
            name="eth3",
            pci_address=PCIAddress(data="0000:5e:00.0"),
            installed=True,
            interface_type=InterfaceType.PF,
            pci_device=PCIDevice(data="8086:3333"),
        )
        ex_eth1 = LinuxInterfaceInfo(
            name="eth1",
            pci_address=PCIAddress(data="0000:5e:00.1"),
            installed=True,
            interface_type=InterfaceType.PF,
            pci_device=PCIDevice(data="8086:1111"),
        )

        expected_list = [ex_eth2, ex_eth3, ex_eth1]
        owner._update_pci_device_in_sys_class_net(source_list=source_list, destination_list=destination_list)
        assert expected_list == destination_list

    def test__mark_vport_interfaces(self, owner):
        eth2 = LinuxInterfaceInfo(
            name="eth2",
            pci_device=PCIDevice(data="8086:1452"),
            pci_address=PCIAddress(data="0000:18:00.0"),
            installed=True,
            interface_type=InterfaceType.PF,
        )
        eth3 = LinuxInterfaceInfo(
            name="eth3",
            pci_device=PCIDevice(data="8086:1452"),
            pci_address=PCIAddress(data="0000:18:00.0"),
            installed=True,
            interface_type=InterfaceType.PF,
        )

        sys_class_list = [eth2, eth3]

        eth2_lspci = LinuxInterfaceInfo(
            pci_address=PCIAddress(data="0000:18:00.0"),
            installed=False,
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_device=PCIDevice(data="8086:1452"),
        )
        eth4_lspci = LinuxInterfaceInfo(
            pci_address=PCIAddress(data="0000:5e:00.0"),
            installed=False,
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_device=PCIDevice(data="8086:3333"),
        )

        target_list = [eth2_lspci, eth4_lspci]

        eth2_updated = LinuxInterfaceInfo(
            name="eth2",
            pci_device=PCIDevice(data="8086:1452"),
            pci_address=PCIAddress(data="0000:18:00.0"),
            installed=True,
            interface_type=InterfaceType.VPORT,
        )
        eth3_updated = LinuxInterfaceInfo(
            name="eth3",
            pci_device=PCIDevice(data="8086:1452"),
            pci_address=PCIAddress(data="0000:18:00.0"),
            installed=True,
            interface_type=InterfaceType.VPORT,
        )
        expected = [eth4_lspci, eth2_updated, eth3_updated]

        owner._mark_vport_interfaces(sys_class_interfaces=sys_class_list, interfaces=target_list)

        assert sys_class_list == []
        assert target_list == expected

    def test__mark_bts_interfaces(self, owner, mocker):
        eth2_lspci = LinuxInterfaceInfo(
            name="eth2",
            installed=False,
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_device=PCIDevice(data="8086:1452"),
        )
        nac_eth2_lspci = LinuxInterfaceInfo(
            name="nac_eth2",
            installed=False,
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_device=PCIDevice(data="8086:3333"),
        )

        @dataclass
        class ETHToolParsed:
            bus_info: List[str]

        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_driver_information",
            mocker.create_autospec(Ethtool.get_driver_information, return_value=ETHToolParsed(["0000:f5:00.0"])),
        )

        mocker.patch(
            "mfd_network_adapter.network_adapter_owner.linux.LinuxNetworkAdapterOwner._get_lspci_interfaces",
            return_value=[
                LinuxInterfaceInfo(
                    pci_address=PCIAddress(domain=0, bus=2, slot=0, func=0),
                    pci_device=PCIDevice(
                        vendor_id=VendorID("8086"), device_id=DeviceID("1452"), sub_vendor_id=None, sub_device_id=None
                    ),
                    name=None,
                    interface_type=InterfaceType.ETH_CONTROLLER,
                    mac_address=None,
                    installed=False,
                    branding_string=None,
                    vlan_info=None,
                    namespace=None,
                    vsi_info=None,
                ),
                LinuxInterfaceInfo(
                    pci_address=PCIAddress(domain=0, bus=245, slot=0, func=0),
                    pci_device=PCIDevice(
                        vendor_id=VendorID("8086"),
                        device_id=DeviceID("0DBD"),
                        sub_vendor_id=SubVendorID("8086"),
                        sub_device_id=SubDeviceID("0000"),
                    ),
                    name=None,
                    interface_type=InterfaceType.ETH_CONTROLLER,
                    mac_address=None,
                    installed=False,
                    branding_string=None,
                    vlan_info=None,
                    namespace=None,
                    vsi_info=None,
                ),
            ],
        )

        interfaces = [eth2_lspci, nac_eth2_lspci]
        owner._mark_bts_interfaces(interfaces=interfaces)

        assert nac_eth2_lspci.interface_type is InterfaceType.BTS
        assert nac_eth2_lspci.pci_address == PCIAddress(data="0000:f5:00.0")
        assert eth2_lspci.interface_type is not InterfaceType.BTS
        assert nac_eth2_lspci.pci_device == PCIDevice(
            vendor_id=VendorID("8086"),
            device_id=DeviceID("0DBD"),
            sub_vendor_id=SubVendorID("8086"),
            sub_device_id=SubDeviceID("0000"),
        )

    def test__update_pfs(self, owner):
        eth2_lspci = LinuxInterfaceInfo(
            pci_address=PCIAddress(data="0000:18:00.0"),
            installed=False,
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_device=PCIDevice(data="8086:1452"),
        )
        eth3_lspci = LinuxInterfaceInfo(
            pci_address=PCIAddress(data="0000:5e:00.0"),
            installed=False,
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_device=PCIDevice(data="8086:1452"),
        )

        eth2 = LinuxInterfaceInfo(
            name="eth2",
            pci_device=PCIDevice(data="8086:1452"),
            pci_address=PCIAddress(data="0000:18:00.0"),
            installed=True,
            interface_type=InterfaceType.PF,
        )
        eth3 = LinuxInterfaceInfo(
            name="eth3",
            pci_device=PCIDevice(data="8086:1452"),
            pci_address=PCIAddress(data="0000:5e:00.0"),
            installed=True,
            interface_type=InterfaceType.PF,
        )

        eth_foo = LinuxInterfaceInfo(name="foo")

        sys_class = [eth2, eth3, eth_foo]
        lspci = [eth2_lspci, eth3_lspci]

        owner._update_pfs(sys_class_interfaces=sys_class, interfaces=lspci)

        eth2_ex = LinuxInterfaceInfo(
            name="eth2",
            pci_device=PCIDevice(data="8086:1452"),
            pci_address=PCIAddress(data="0000:18:00.0"),
            installed=True,
            interface_type=InterfaceType.PF,
        )
        eth3_ex = LinuxInterfaceInfo(
            name="eth3",
            pci_device=PCIDevice(data="8086:1452"),
            pci_address=PCIAddress(data="0000:5e:00.0"),
            installed=True,
            interface_type=InterfaceType.PF,
        )
        expected = [eth2_ex, eth3_ex, eth_foo]
        assert sys_class == [eth_foo]
        assert lspci == expected

    def test__get_vlan_info(self, owner):
        stdout = dedent(
            """
        23: eth9.8@if17: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
            link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00 link-netnsid 0 promiscuity 0
            vlan protocol 802.1Q id 8 <REORDER_HDR> addrgenmode eui64 numtxqueues 1 numrxqueues 1 gso_max_size 65536
            gso_max_segs 65535
        """
        )

        expected_vlan_info = VlanInterfaceInfo(vlan_id=8, parent="if17")
        assert owner._get_vlan_info(stdout) == expected_vlan_info

    def test__get_vlan_interfaces(self, owner, mocker):
        stdout = """config  eth1.69 """
        expected_vlans = ["eth1.69"]

        owner._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(args=0, return_code=0, stdout=stdout)
        )

        assert owner._get_vlan_interfaces(namespace="") == expected_vlans

    def test__update_vlans(self, owner, mocker):
        vlan_ifaces = ["foo", "bar"]
        vlan_info = VlanInterfaceInfo(vlan_id=1, parent="parent")
        owner._get_vlan_interfaces = mocker.Mock(return_value=vlan_ifaces)
        owner._get_vlan_info = mocker.Mock(return_value=vlan_info)

        iface_1 = LinuxInterfaceInfo(name="foo", interface_type=InterfaceType.VIRTUAL_DEVICE)
        iface_2 = LinuxInterfaceInfo(name="bar", interface_type=InterfaceType.VIRTUAL_DEVICE)
        iface_3 = LinuxInterfaceInfo(name="dunno", interface_type=InterfaceType.PF)
        ifaces = [iface_1, iface_2, iface_3]

        iface_1_updated = LinuxInterfaceInfo(name="foo", interface_type=InterfaceType.VLAN, vlan_info=vlan_info)
        iface_2_updated = LinuxInterfaceInfo(name="bar", interface_type=InterfaceType.VLAN, vlan_info=vlan_info)
        expected_ifaces = [iface_1_updated, iface_2_updated, iface_3]
        owner._update_vlans(ifaces)
        assert ifaces == expected_ifaces

    def test__mark_management_interface_is_conn_ip(self, owner, mocker):
        name = "br0"
        iface_1 = LinuxInterfaceInfo(name=name, interface_type=InterfaceType.PF)
        stdout_mgmt = dedent(
            f"""
        inet 10.10.10.10/24 brd 10.10.10.10 scope global dynamic {name}
        """
        )
        owner._connection._ip = "10.10.10.10"
        owner._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args=0, stdout=stdout_mgmt)
        )
        interfaces = [iface_1]
        iface_1_updated = LinuxInterfaceInfo(name=name, interface_type=InterfaceType.MANAGEMENT)
        expected_interfaces = [iface_1_updated]
        owner._mark_management_interface(interfaces=interfaces)
        assert interfaces == expected_interfaces

    def test__mark_management_interface_in_management_network(self, owner, mocker):
        name = "eth1"
        name_2 = "eth2"
        conn_ip = "10.10.10.10"
        mgmt_ip = "10.12.1.1"
        iface_1 = LinuxInterfaceInfo(name=name, interface_type=InterfaceType.PF)
        iface_2 = LinuxInterfaceInfo(name=name_2, interface_type=InterfaceType.PF)
        stdout_mgmt = dedent(
            f"""
        inet {conn_ip}/24 brd 10.10.10.10 scope global dynamic {name}
        inet {mgmt_ip}/24 brd 10.10.10.10 scope global dynamic {name_2}
        """
        )
        owner._connection._ip = conn_ip
        owner._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args=0, stdout=stdout_mgmt)
        )
        interfaces = [iface_1, iface_2]
        iface_1_updated = LinuxInterfaceInfo(name=name, interface_type=InterfaceType.MANAGEMENT)
        iface_2_updated = LinuxInterfaceInfo(name=name_2, interface_type=InterfaceType.MANAGEMENT)

        expected_interfaces = [iface_1_updated, iface_2_updated]
        owner._mark_management_interface(interfaces=interfaces)
        assert interfaces == expected_interfaces

    def test__remove_tunnel_interfaces(self, owner, mocker):
        stdout_tunnel = dedent(
            """
        ipip0:
        eth2:
        """
        )
        name = "eth1"
        name_2 = "eth2"
        iface_1 = LinuxInterfaceInfo(name=name, interface_type=InterfaceType.PF)
        iface_2 = LinuxInterfaceInfo(name=name_2, interface_type=InterfaceType.PF)
        interfaces = [iface_1, iface_2]
        expected_interfaces = [iface_1]

        owner._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(args=0, return_code=0, stdout=stdout_tunnel)
        )

        assert owner._remove_tunnel_interfaces(interfaces=interfaces, namespace=None) == expected_interfaces

    def test__get_lspci_interfaces(self, owner, mocker):
        stdout_lspci = dedent(
            """
            Slot:   0000:05:00.0
            Class:  Ethernet controller [0200]
            Vendor: Intel Corporation [8086]
            Device: I210 Gigabit Network Connection [1533]
            SVendor:        Intel Corporation [8086]
            SDevice:        Ethernet Server Adapter I210-T1 [0001]
            Rev:    03
            NUMANode:       0

            Slot:   0000:06:00.0
            Class:  Ethernet controller [0200]
            Vendor: Intel Corporation [8086]
            Device: I210 Gigabit Network Connection [1533]
            Rev:    03
            NUMANode:       0

            Slot:   0000:07:00.0
            Class:  Ethernet controller [0200]
            Vendor: Intel Corporation [8086]
            Device: I210 Gigabit Network Connection [1533]
            Rev:    03
            NUMANode:       0

            Slot:   0002:f4:00.0
            Class:  Ethernet controller [0200]
            Vendor: Intel Corporation [8086]
            Device: Ethernet Connection E822-L for backplane [1897]
            SVendor:        Intel Corporation [8086]
            SDevice:        Device [0000]
            Rev:    20
            NUMANode:       0

            Slot:   0002:f4:00.1
            Class:  Ethernet controller [0200]
            Vendor: Intel Corporation [8086]
            Device: Ethernet Connection E822-L for backplane [1897]
            SVendor:        Intel Corporation [8086]
            SDevice:        Device [0000]
            Rev:    20
            NUMANode:       0
            """
        )
        iface_1 = LinuxInterfaceInfo(
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_address=PCIAddress(data="0000:05:00.0"),
            pci_device=PCIDevice(data="8086:1533:8086:0001"),
            installed=False,
        )
        iface_2 = LinuxInterfaceInfo(
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_address=PCIAddress(data="0000:06:00.0"),
            pci_device=PCIDevice(data="8086:1533"),
            installed=False,
        )
        iface_3 = LinuxInterfaceInfo(
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_address=PCIAddress(data="0000:07:00.0"),
            pci_device=PCIDevice(data="8086:1533"),
            installed=False,
        )
        iface_4 = LinuxInterfaceInfo(
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_address=PCIAddress(data="0002:f4:00.0"),
            pci_device=PCIDevice(data="8086:1897:8086:0000"),
            installed=False,
        )
        iface_5 = LinuxInterfaceInfo(
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_address=PCIAddress(data="0002:f4:00.1"),
            pci_device=PCIDevice(data="8086:1897:8086:0000"),
            installed=False,
        )

        owner._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(args=0, return_code=0, stdout=stdout_lspci)
        )
        expected_interfaces = [iface_1, iface_2, iface_3, iface_4, iface_5]
        interfaces = owner._get_lspci_interfaces(namespace=None)
        assert interfaces == expected_interfaces

    def test__get_lspci_interfaces_non_zero_domain(self, owner, mocker):
        stdout_lspci = dedent(
            """
            Slot:   1cb6:00:01.0
            Class:  Ethernet controller [0200]
            Vendor: Intel Corporation [8086]
            Device: Device [1452]
            SVendor:        Intel Corporation [8086]
            SDevice:        Device [0000]
            Rev:    10
            """
        )

        iface_1 = LinuxInterfaceInfo(
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_address=PCIAddress(data="1cb6:00:01.0"),
            pci_device=PCIDevice(data="8086:1452:8086:0000"),
            installed=False,
        )

        owner._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(args=0, return_code=0, stdout=stdout_lspci)
        )
        expected_interfaces = [iface_1]
        interfaces = owner._get_lspci_interfaces(namespace=None)
        assert interfaces == expected_interfaces

    def test__get_lspci_interfaces_additional_newline(self, owner, mocker):
        stdout_lspci = dedent(
            """
            Slot:   0000:03:00.0
            Class:  Ethernet controller [0200]
            Vendor: Intel Corporation [8086]
            Device: I210 Gigabit Network Connection [1533]
            Rev:    03
            NUMANode:       0
            IOMMUGroup:     25


            Slot:   0000:89:00.0
            Class:  Ethernet controller [0200]
            Vendor: Intel Corporation [8086]
            Device: Ethernet Connection E823-C for QSFP [188b]
            SVendor:        Intel Corporation [8086]
            SDevice:        Device [0000]
            NUMANode:       0
            IOMMUGroup:     44


            Slot:   0000:89:00.1
            Class:  Ethernet controller [0200]
            Vendor: Intel Corporation [8086]
            Device: Ethernet Connection E823-C for QSFP [188b]
            SVendor:        Intel Corporation [8086]
            SDevice:        Device [0000]
            NUMANode:       0
            IOMMUGroup:     45
            """
        )
        iface_1 = LinuxInterfaceInfo(
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_address=PCIAddress(data="0000:03:00.0"),
            pci_device=PCIDevice(data="8086:1533:8086:0000"),
            installed=False,
        )
        iface_2 = LinuxInterfaceInfo(
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_address=PCIAddress(data="0000:89:00.0"),
            pci_device=PCIDevice(data="8086:188b:8086:0000"),
            installed=False,
        )
        iface_3 = LinuxInterfaceInfo(
            interface_type=InterfaceType.ETH_CONTROLLER,
            pci_address=PCIAddress(data="0000:89:00.1"),
            pci_device=PCIDevice(data="8086:188b:8086:0000"),
            installed=False,
        )

        owner._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(args=0, return_code=0, stdout=stdout_lspci)
        )
        expected_interfaces = [iface_1, iface_2, iface_3]
        interfaces = owner._get_lspci_interfaces(namespace=None)
        assert interfaces == expected_interfaces

    def test__get_lspci_interfaces_rc_1(self, owner, mocker):
        owner._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(args=0, return_code=1, stdout="")
        )
        assert owner._get_lspci_interfaces(namespace=None) == []

    def test__update_virtual_interfaces(self, owner, mocker):
        findstdout = dedent(
            """
            /sys/class/net/eth9/device/physfn
            /sys/class/net/eth8/device/physfn
            /sys/class/net/eth6/device/physfn
            """
        )
        findstderr = dedent(
            """
            find: File system loop detected; ‘/sys/class/net/bootnet/upper_br0/lower_bootnet’ is part of the same file
            system loop as ‘/sys/class/net/bootnet’.
            find: File system loop detected; ‘/sys/class/net/bootnet/upper_br0/subsystem’ is part of the same file
            system loop as ‘/sys/class/net/’.
            find: File system loop detected; ‘/sys/class/net/bootnet/subsystem’ is part of the same file system
            loop as ‘/sys/class/net/’.
            find: File system loop detected; ‘/sys/class/net/bootnet/master/lower_bootnet’ is part of the same file
            system loop as ‘/sys/class/net/bootnet’.
            """
        )

        owner._connection.execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(args=0, return_code=1, stdout=findstdout, stderr=findstderr)
        )

        iface_1 = LinuxInterfaceInfo(name="eth9", interface_type=InterfaceType.PF)
        iface_2 = LinuxInterfaceInfo(name="eth6", interface_type=InterfaceType.PF)
        iface_3 = LinuxInterfaceInfo(name="eth8", interface_type=InterfaceType.PF)

        iface_1_exp = LinuxInterfaceInfo(name="eth9", interface_type=InterfaceType.VF)
        iface_2_exp = LinuxInterfaceInfo(name="eth6", interface_type=InterfaceType.VF)
        iface_3_exp = LinuxInterfaceInfo(name="eth8", interface_type=InterfaceType.VF)
        interfaces = [iface_1, iface_2, iface_3]
        owner._update_virtual_function_interfaces(interfaces=interfaces, namespace="")

        assert interfaces == [iface_1_exp, iface_2_exp, iface_3_exp]

    def test_create_vfs(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(args="", return_code=0)
        owner.create_vfs(interface_name="eth0", vfs_count=3)
        owner._connection.execute_command.assert_called_once_with(
            command="echo 3 > /sys/class/net/eth0/device/sriov_numvfs", shell=True
        )

    def test_delete_vfs(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(args="", return_code=0)
        owner.delete_vfs(interface_name="eth50")
        owner._connection.execute_command.assert_called_once_with(
            command="echo 0 > /sys/class/net/eth50/device/sriov_numvfs", shell=True
        )

    def test__update_mac_addresses(self, owner):
        ip_a_output = dedent(
            """
            2: ens801f0np0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc mq state DOWN group default qlen 1000
                link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
                altname enp94s0f0np0
            3: ens801f1np1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
                link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
                altname enp94s0f1np1
                inet 198.108.8.1/24 scope global ens801f1np1
                   valid_lft forever preferred_lft forever
                inet6 64:ff9b::1:108:8:1/112 scope global
                   valid_lft forever preferred_lft forever
                inet6 fe80::746a:6144:5e27:d873/64 scope link noprefixroute
                   valid_lft forever preferred_lft forever
            4: eno1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
                link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
                altname enp24s0f0
                inet 10.10.10.10/24 brd 10.10.10.10 scope global dynamic noprefixroute eno1
                   valid_lft 19751sec preferred_lft 19751sec
                inet6 fe80::7307:c806:e8f4:942f/64 scope link noprefixroute
                   valid_lft forever preferred_lft forever
            5: eno2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
                link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
                altname enp24s0f1
                inet 100.0.0.1/24 scope global eno2
                   valid_lft forever preferred_lft forever
                inet6 fe80::2aa3:f846:49b5:1a7/64 scope link noprefixroute
                   valid_lft forever preferred_lft forever
            14: ppp0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UNKNOWN group default
                    qlen 3
                link/ppp
                inet 10.10.10.10 peer 192.168.108.2/32 scope global ppp0
                   valid_lft forever preferred_lft forever
                inet6 fe80::f4e3:6b8c:3c0b:f1b1 peer fe80::cc81:b8a0:3450:80ff/128 scope link
                   valid_lft forever preferred_lft forever
            15: ppp1: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UNKNOWN group default
                qlen 3
                link/ppp
                inet 10.10.10.10 peer 192.168.108.3/32 scope global ppp1
                   valid_lft forever preferred_lft forever
                inet6 fe80::7801:b910:4a01:d5ba peer fe80::41d3:c921:51d:eb10/128 scope link
                   valid_lft forever preferred_lft forever
            16: ens192: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
                link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
                altname enp11s0
                inet 1.1.11.1/8 scope global ens192
                   valid_lft forever preferred_lft forever
                inet6 3001:1::1:b:1/64 scope global
                   valid_lft forever preferred_lft forever
                inet6 fe80::250:56ff:fe8a:63cd/64 scope link
                   valid_lft forever preferred_lft forever
            17: ens192.164@ens192: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN group default qlen 1000
                link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
        """
        )

        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", return_code=0, stdout=ip_a_output
        )

        a = LinuxInterfaceInfo(name="ens801f0np0")
        b = LinuxInterfaceInfo(name="ens801f1np1")
        c = LinuxInterfaceInfo(name="eno1")
        d = LinuxInterfaceInfo(name="eno2")
        e = LinuxInterfaceInfo(name="ens192")
        f = LinuxInterfaceInfo(name="ens192.164")
        interfaces = [a, b, c, d, e, f]

        a_ex = LinuxInterfaceInfo(name="ens801f0np0", mac_address=MACAddress(addr="00:00:00:00:00:00"))
        b_ex = LinuxInterfaceInfo(name="ens801f1np1", mac_address=MACAddress(addr="00:00:00:00:00:00"))
        c_ex = LinuxInterfaceInfo(name="eno1", mac_address=MACAddress(addr="00:00:00:00:00:00"))
        d_ex = LinuxInterfaceInfo(name="eno2", mac_address=MACAddress(addr="00:00:00:00:00:00"))
        e_ex = LinuxInterfaceInfo(name="ens192", mac_address=MACAddress(addr="00:00:00:00:00:00"))
        f_ex = LinuxInterfaceInfo(name="ens192.164", mac_address=MACAddress(addr="00:00:00:00:00:00"))

        interfaces_expected = [a_ex, b_ex, c_ex, d_ex, e_ex, f_ex]

        owner._update_mac_addresses(interfaces=interfaces, namespace=None)

        assert interfaces == interfaces_expected

    def test_get_pci_addresses_by_pci_device(self, owner, mocker):
        pci_device = PCIDevice(data="8086:1539:8086:0000")
        pci_addresses = [PCIAddress(data="0000:50:00.0"), PCIAddress(data="0000:50:00.1")]
        lspci_interfaces = [
            LinuxInterfaceInfo(
                pci_device=pci_device,
                pci_address=pci_addresses[0],
            ),
            LinuxInterfaceInfo(
                pci_device=pci_device,
                pci_address=pci_addresses[1],
            ),
            LinuxInterfaceInfo(
                pci_device=PCIDevice(data="8086:1539:1111:2222"),
                pci_address=PCIAddress(data="0000:77:00.0"),
            ),
        ]
        owner._get_lspci_interfaces = mocker.Mock(return_value=lspci_interfaces)
        assert owner.get_pci_addresses_by_pci_device(pci_device) == pci_addresses

    def test_get_pci_device_by_pci_address(self, owner, mocker):
        pci_device = PCIDevice(data="8086:1539:8086:0000")
        pci_address = PCIAddress(data="0000:50:00.0")
        lspci_interfaces = [
            LinuxInterfaceInfo(
                pci_device=pci_device,
                pci_address=pci_address,
            ),
            LinuxInterfaceInfo(
                pci_device=PCIDevice(data="8086:1539:1111:2222"),
                pci_address=PCIAddress(data="0000:77:00.0"),
            ),
        ]
        owner._get_lspci_interfaces = mocker.Mock(return_value=lspci_interfaces)
        assert owner.get_pci_device_by_pci_address(pci_address) == pci_device

    def test_get_pci_device_by_pci_address_no_device_found(self, owner, mocker):
        lspci_interfaces = [
            LinuxInterfaceInfo(
                pci_device=PCIDevice(data="8086:1539:8086:0000"),
                pci_address=PCIAddress(data="0000:50:00.0"),
            ),
            LinuxInterfaceInfo(
                pci_device=PCIDevice(data="8086:1539:1111:2222"),
                pci_address=PCIAddress(data="0000:77:00.0"),
            ),
        ]
        owner._get_lspci_interfaces = mocker.Mock(return_value=lspci_interfaces)
        with pytest.raises(NetworkAdapterModuleException):
            owner.get_pci_device_by_pci_address(PCIAddress(data="0000:11:22.0"))

    def test__gather_all_vmbus_interfaces(self, owner):
        sys_class_stdout_vmbus = dedent(
            """total 0
            lrwxrwxrwx 1 root root 0 Jul 19 16:13 enP41140s2 -> ../../devices/LNXSYSTM:00/LNXSYBUS:00/ACPI0004:00/VMBUS:00/dc839ab6-a0b4-4485-ad3c-a0402d6ee7a4/pcia0b4:00/a0b4:00:02.0/net/enP41140s2   # noqa: E501
            lrwxrwxrwx 1 root root 0 Jul 19 16:13 enP7350s3 -> ../../devices/LNXSYSTM:00/LNXSYBUS:00/ACPI0004:00/VMBUS:00/225041dc-1cb6-4eeb-8e75-53d9d3dbdf12/pci1cb6:00/1cb6:00:02.0/net/enP7350s3     # noqa: E501
            lrwxrwxrwx 1 root root 0 Jul 19 18:11 eth0 -> ../../devices/LNXSYSTM:00/LNXSYBUS:00/ACPI0004:00/VMBUS:00/828b56fe-4d8f-4a4f-b820-8558c3ea8377/net/eth0  # noqa: E501
            lrwxrwxrwx 1 root root 0 Jul 19 16:11 eth1 -> ../../devices/LNXSYSTM:00/LNXSYBUS:00/ACPI0004:00/VMBUS:00/3e0a6632-83e3-4a2e-987d-bbc63c1d2781/net/eth1  # noqa: E501
            lrwxrwxrwx 1 root root 0 Jul 19 16:11 eth2 -> ../../devices/LNXSYSTM:00/LNXSYBUS:00/ACPI0004:00/VMBUS:00/55576575-61c9-48ec-884d-da572bb5b98d/net/eth2  # noqa: E501
            lrwxrwxrwx 1 root root 0 Jul 19 18:11 lo -> ../../devices/virtual/net/lo
            """  # noqa E501
        )
        namespace = "foo"

        iface_1 = LinuxInterfaceInfo(
            name="eth0", interface_type=InterfaceType.VMBUS, installed=True, namespace=namespace
        )
        iface_2 = LinuxInterfaceInfo(
            name="eth1", interface_type=InterfaceType.VMBUS, installed=True, namespace=namespace
        )
        iface_3 = LinuxInterfaceInfo(
            name="eth2", interface_type=InterfaceType.VMBUS, installed=True, namespace=namespace
        )

        expected_ifaces = [iface_1, iface_2, iface_3]
        gathered_ifaces = owner._gather_all_vmbus_interfaces(
            sys_class_net_lines=sys_class_stdout_vmbus.splitlines(), namespace=namespace
        )

        assert gathered_ifaces == expected_ifaces

    def test__mark_bonding_interfaces(self, owner, mocker):
        stdout_bonding = dedent(
            """
        6: eth3: <BROADCAST,MULTICAST> mtu 1500 qdisc mq state DOWN group default qlen 1000
            link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
            altname eno2
            altname enp24s0f1
        7: aaa: <NO-CARRIER,BROADCAST,MULTICAST,MASTER,UP> mtu 1500 qdisc noqueue state DOWN group default qlen 1000
            link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
            inet6 fe80::a6bf:1ff:fe44:f21a/64 scope link
               valid_lft forever preferred_lft forever
        """
        )
        stdout_bonding_2 = dedent(
            """
            6: eth3: <BROADCAST,SLAVE,MULTICAST> mtu 1500 qdisc mq state DOWN group default qlen 1000
                link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
                altname eno2
                altname enp24s0f1
            7: aaa: <NO-CARRIER,BROADCAST,MULTICAST,MASTER,UP> mtu 1500 qdisc noqueue state DOWN group default qlen 1000
                link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
                inet6 fe80::a6bf:1ff:fe44:f21a/64 scope link
                   valid_lft forever preferred_lft forever
            """
        )
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=stdout_bonding, return_code=0
        )
        mocker.patch.object(owner.bonding, "get_bond_interfaces", return_value=["aaa"])
        iface_1 = LinuxInterfaceInfo(name="eth3", interface_type=InterfaceType.PF, installed=True)
        iface_2 = LinuxInterfaceInfo(name="aaa", interface_type=InterfaceType.GENERIC, installed=True)
        ifaces = [iface_1, iface_2]
        owner._mark_bonding_interfaces(ifaces)
        assert iface_2.interface_type == InterfaceType.BOND

        # where eth3 is a slave
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=stdout_bonding_2, return_code=0
        )
        mocker.patch.object(owner.bonding, "get_children", return_value=["eth3"])
        owner._mark_bonding_interfaces(ifaces)
        assert iface_1.interface_type == InterfaceType.BOND_SLAVE

    def test__mark_bonding_interfaces_interface_name_none(self, owner, mocker):
        # Test when interface.name is None, should just continue
        stdout_bonding = """
        6: eth3: <BROADCAST,MULTICAST> mtu 1500 qdisc mq state DOWN group default qlen 1000
        """
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=stdout_bonding, return_code=0
        )
        mocker.patch.object(owner.bonding, "get_bond_interfaces", return_value=[])
        iface = LinuxInterfaceInfo(name=None, interface_type=InterfaceType.GENERIC, installed=True)
        # Should not raise
        owner._mark_bonding_interfaces([iface])

    def test__mark_bonding_interfaces_no_bonding_interfaces(self, owner, mocker):
        """Test _mark_bonding_interfaces when no bonding interfaces exist."""
        mocker.patch.object(owner.bonding, "get_bond_interfaces", return_value=[])

        iface_1 = LinuxInterfaceInfo(name="eth0", interface_type=InterfaceType.PF, installed=True)
        iface_2 = LinuxInterfaceInfo(name="eth1", interface_type=InterfaceType.VF, installed=True)
        interfaces = [iface_1, iface_2]

        original_types = [iface.interface_type for iface in interfaces]

        owner._mark_bonding_interfaces(interfaces)

        # Interface types should remain unchanged
        assert iface_1.interface_type == original_types[0]
        assert iface_2.interface_type == original_types[1]

    def test__mark_bonding_interfaces_multiple_bond_interfaces(self, owner, mocker):
        """Test _mark_bonding_interfaces with multiple bond interfaces."""
        mocker.patch.object(owner.bonding, "get_bond_interfaces", return_value=["bond0", "bond1"])
        mocker.patch.object(owner.bonding, "get_children")
        owner.bonding.get_children.side_effect = lambda bonding_interface: {
            "bond0": ["eth0", "eth1"],
            "bond1": ["eth2", "eth3"],
        }.get(bonding_interface, [])

        bond0 = LinuxInterfaceInfo(name="bond0", interface_type=InterfaceType.GENERIC, installed=True)
        bond1 = LinuxInterfaceInfo(name="bond1", interface_type=InterfaceType.VIRTUAL_DEVICE, installed=True)
        eth0 = LinuxInterfaceInfo(name="eth0", interface_type=InterfaceType.PF, installed=True)
        eth1 = LinuxInterfaceInfo(name="eth1", interface_type=InterfaceType.PF, installed=True)
        eth2 = LinuxInterfaceInfo(name="eth2", interface_type=InterfaceType.PF, installed=True)
        eth3 = LinuxInterfaceInfo(name="eth3", interface_type=InterfaceType.VF, installed=True)
        eth4 = LinuxInterfaceInfo(name="eth4", interface_type=InterfaceType.PF, installed=True)  # Not a slave

        interfaces = [bond0, bond1, eth0, eth1, eth2, eth3, eth4]

        owner._mark_bonding_interfaces(interfaces)

        # Bond interfaces should be marked as BOND
        assert bond0.interface_type == InterfaceType.BOND
        assert bond1.interface_type == InterfaceType.BOND

        # Child interfaces should be marked as BOND_SLAVE
        assert eth0.interface_type == InterfaceType.BOND_SLAVE
        assert eth1.interface_type == InterfaceType.BOND_SLAVE
        assert eth2.interface_type == InterfaceType.BOND_SLAVE
        assert eth3.interface_type == InterfaceType.BOND_SLAVE

        # Non-child interface should remain unchanged
        assert eth4.interface_type == InterfaceType.PF

    def test__mark_bonding_interfaces_bond_with_no_children(self, owner, mocker):
        """Test _mark_bonding_interfaces when bond interface has no children."""
        mocker.patch.object(owner.bonding, "get_bond_interfaces", return_value=["bond0"])
        mocker.patch.object(owner.bonding, "get_children", return_value=[])

        bond0 = LinuxInterfaceInfo(name="bond0", interface_type=InterfaceType.GENERIC, installed=True)
        eth0 = LinuxInterfaceInfo(name="eth0", interface_type=InterfaceType.PF, installed=True)

        interfaces = [bond0, eth0]

        owner._mark_bonding_interfaces(interfaces)

        # Bond interface should still be marked as BOND
        assert bond0.interface_type == InterfaceType.BOND

        # Other interface should remain unchanged
        assert eth0.interface_type == InterfaceType.PF

    def test__mark_bonding_interfaces_empty_interface_list(self, owner, mocker):
        """Test _mark_bonding_interfaces with empty interface list."""
        mocker.patch.object(owner.bonding, "get_bond_interfaces", return_value=["bond0"])

        interfaces = []

        # Should not raise an exception
        owner._mark_bonding_interfaces(interfaces)

        assert interfaces == []

    def test__mark_bonding_interfaces_mixed_none_names(self, owner, mocker):
        """Test _mark_bonding_interfaces with mix of None and valid interface names."""
        mocker.patch.object(owner.bonding, "get_bond_interfaces", return_value=["bond0"])
        mocker.patch.object(owner.bonding, "get_children", return_value=["eth0"])

        bond0 = LinuxInterfaceInfo(name="bond0", interface_type=InterfaceType.GENERIC, installed=True)
        none_iface = LinuxInterfaceInfo(name=None, interface_type=InterfaceType.VF, installed=True)
        eth0 = LinuxInterfaceInfo(name="eth0", interface_type=InterfaceType.PF, installed=True)

        interfaces = [bond0, none_iface, eth0]

        owner._mark_bonding_interfaces(interfaces)

        # Bond interface should be marked as BOND
        assert bond0.interface_type == InterfaceType.BOND

        # Interface with None name should remain unchanged
        assert none_iface.interface_type == InterfaceType.VF

        # Child interface should be marked as BOND_SLAVE
        assert eth0.interface_type == InterfaceType.BOND_SLAVE

    def test__update_mac_addresses_malformed_output(self, owner):
        """Test _update_mac_addresses with malformed ip addr output."""
        # Test with output missing MAC addresses
        ip_a_output_no_mac = dedent(
            """
            2: ens801f0np0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc mq state DOWN group default qlen 1000
                link/loopback
                altname enp94s0f0np0
            3: ens801f1np1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
                link/ether 00:11:22:33:44:55 brd ff:ff:ff:ff:ff:ff
                altname enp94s0f1np1
        """
        )

        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", return_code=0, stdout=ip_a_output_no_mac
        )

        iface_no_mac = LinuxInterfaceInfo(name="ens801f0np0")
        iface_with_mac = LinuxInterfaceInfo(name="ens801f1np1")
        interfaces = [iface_no_mac, iface_with_mac]

        owner._update_mac_addresses(interfaces=interfaces, namespace=None)

        # Interface without MAC should remain without MAC address
        assert iface_no_mac.mac_address is None

        # Interface with MAC should get the MAC address
        assert iface_with_mac.mac_address == MACAddress(addr="00:11:22:33:44:55")

    def test__update_mac_addresses_empty_output(self, owner):
        """Test _update_mac_addresses with empty ip addr output."""
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(args="", return_code=0, stdout="")

        iface = LinuxInterfaceInfo(name="eth0")
        interfaces = [iface]

        owner._update_mac_addresses(interfaces=interfaces, namespace=None)

        # Interface should remain without MAC address
        assert iface.mac_address is None

    def test__update_mac_addresses_interface_not_in_output(self, owner):
        """Test _update_mac_addresses when interface is not in ip addr output."""
        ip_a_output = dedent(
            """
            2: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
                link/ether 00:11:22:33:44:55 brd ff:ff:ff:ff:ff:ff
        """
        )

        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", return_code=0, stdout=ip_a_output
        )

        eth0 = LinuxInterfaceInfo(name="eth0")  # Not in output
        eth1 = LinuxInterfaceInfo(name="eth1")  # In output
        interfaces = [eth0, eth1]

        owner._update_mac_addresses(interfaces=interfaces, namespace=None)

        # eth0 should remain without MAC address
        assert eth0.mac_address is None

        # eth1 should get the MAC address
        assert eth1.mac_address == MACAddress(addr="00:11:22:33:44:55")

    def test__update_mac_addresses_with_namespace(self, owner):
        """Test _update_mac_addresses with namespace parameter."""
        ip_a_output = dedent(
            """
            2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
                link/ether aa:bb:cc:dd:ee:ff brd ff:ff:ff:ff:ff:ff
        """
        )

        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", return_code=0, stdout=ip_a_output
        )

        eth0 = LinuxInterfaceInfo(name="eth0")
        interfaces = [eth0]

        owner._update_mac_addresses(interfaces=interfaces, namespace="test_ns")

        # Should call with namespace
        expected_command = "ip netns exec test_ns ip a"
        owner._connection.execute_command.assert_called_with(command=expected_command)

        # Interface should get the MAC address
        assert eth0.mac_address == MACAddress(addr="aa:bb:cc:dd:ee:ff")

    def test__update_mac_addresses_complex_interface_names(self, owner):
        """Test _update_mac_addresses with complex interface names (VLAN, bridge, etc.)."""
        ip_a_output = dedent(
            """
            5: eth0.100@eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
                link/ether 00:11:22:33:44:55 brd ff:ff:ff:ff:ff:ff
            6: br-12345: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default
                link/ether 02:42:ac:11:00:01 brd ff:ff:ff:ff:ff:ff
            7: veth123abc@if8: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-12345
                link/ether 66:77:88:99:aa:bb brd ff:ff:ff:ff:ff:ff
        """
        )

        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", return_code=0, stdout=ip_a_output
        )

        vlan_iface = LinuxInterfaceInfo(name="eth0.100")
        bridge_iface = LinuxInterfaceInfo(name="br-12345")
        veth_iface = LinuxInterfaceInfo(name="veth123abc")
        interfaces = [vlan_iface, bridge_iface, veth_iface]

        owner._update_mac_addresses(interfaces=interfaces, namespace=None)

        # All interfaces should get their MAC addresses
        assert vlan_iface.mac_address == MACAddress(addr="00:11:22:33:44:55")
        assert bridge_iface.mac_address == MACAddress(addr="02:42:ac:11:00:01")
        assert veth_iface.mac_address == MACAddress(addr="66:77:88:99:aa:bb")

    def test__mark_bonding_interfaces_exception_handling(self, owner, mocker):
        """Test _mark_bonding_interfaces handles exceptions from bonding feature gracefully."""
        mocker.patch.object(owner.bonding, "get_bond_interfaces", side_effect=Exception("Bonding error"))

        eth0 = LinuxInterfaceInfo(name="eth0", interface_type=InterfaceType.PF, installed=True)
        interfaces = [eth0]

        # Should raise the exception from get_bond_interfaces
        with pytest.raises(Exception, match="Bonding error"):
            owner._mark_bonding_interfaces(interfaces)

    def test__mark_bonding_interfaces_get_children_exception(self, owner, mocker):
        """Test _mark_bonding_interfaces handles exceptions from get_children gracefully."""
        mocker.patch.object(owner.bonding, "get_bond_interfaces", return_value=["bond0"])
        mocker.patch.object(owner.bonding, "get_children", side_effect=Exception("Get children error"))

        bond0 = LinuxInterfaceInfo(name="bond0", interface_type=InterfaceType.GENERIC, installed=True)
        interfaces = [bond0]

        # Should raise the exception from get_children
        with pytest.raises(Exception, match="Get children error"):
            owner._mark_bonding_interfaces(interfaces)

    def test__mark_bonding_interfaces_interface_type_preservation(self, owner, mocker):
        """Test that _mark_bonding_interfaces preserves original interface types when appropriate."""
        mocker.patch.object(owner.bonding, "get_bond_interfaces", return_value=["bond0"])
        mocker.patch.object(owner.bonding, "get_children", return_value=["eth0"])

        # Test various initial interface types
        bond0 = LinuxInterfaceInfo(name="bond0", interface_type=InterfaceType.ETH_CONTROLLER, installed=True)
        eth0_pf = LinuxInterfaceInfo(name="eth0", interface_type=InterfaceType.PF, installed=True)
        eth1_vf = LinuxInterfaceInfo(name="eth1", interface_type=InterfaceType.VF, installed=True)
        eth2_virtual = LinuxInterfaceInfo(name="eth2", interface_type=InterfaceType.VIRTUAL_DEVICE, installed=True)

        interfaces = [bond0, eth0_pf, eth1_vf, eth2_virtual]

        owner._mark_bonding_interfaces(interfaces)

        # Bond interface should change from ETH_CONTROLLER to BOND
        assert bond0.interface_type == InterfaceType.BOND

        # Slave interface should change to BOND_SLAVE regardless of original type
        assert eth0_pf.interface_type == InterfaceType.BOND_SLAVE

        # Non-slave interfaces should keep their original types
        assert eth1_vf.interface_type == InterfaceType.VF
        assert eth2_virtual.interface_type == InterfaceType.VIRTUAL_DEVICE

    def test__update_mac_addresses_command_construction(self, owner):
        """Test that _update_mac_addresses constructs the correct command."""
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(args="", return_code=0, stdout="")

        interfaces = []

        # Test without namespace
        owner._update_mac_addresses(interfaces=interfaces, namespace=None)
        owner._connection.execute_command.assert_called_with(command="ip a")

        # Test with namespace
        owner._update_mac_addresses(interfaces=interfaces, namespace="testns")
        expected_command = "ip netns exec testns ip a"
        owner._connection.execute_command.assert_called_with(command=expected_command)

    def test__mark_bonding_interfaces_duplicate_names(self, owner, mocker):
        """Test _mark_bonding_interfaces with duplicate interface names."""
        mocker.patch.object(owner.bonding, "get_bond_interfaces", return_value=["bond0"])
        mocker.patch.object(owner.bonding, "get_children", return_value=["eth0"])

        # Create interfaces with duplicate names
        bond0_1 = LinuxInterfaceInfo(name="bond0", interface_type=InterfaceType.GENERIC, installed=True)
        bond0_2 = LinuxInterfaceInfo(name="bond0", interface_type=InterfaceType.ETH_CONTROLLER, installed=True)
        eth0_1 = LinuxInterfaceInfo(name="eth0", interface_type=InterfaceType.PF, installed=True)
        eth0_2 = LinuxInterfaceInfo(name="eth0", interface_type=InterfaceType.VF, installed=True)

        interfaces = [bond0_1, bond0_2, eth0_1, eth0_2]

        owner._mark_bonding_interfaces(interfaces)

        # Both bond0 interfaces should be marked as BOND
        assert bond0_1.interface_type == InterfaceType.BOND
        assert bond0_2.interface_type == InterfaceType.BOND

        # Both eth0 interfaces should be marked as BOND_SLAVE
        assert eth0_1.interface_type == InterfaceType.BOND_SLAVE
        assert eth0_2.interface_type == InterfaceType.BOND_SLAVE

    def test__mark_bonding_interfaces_case_sensitivity(self, owner, mocker):
        """Test _mark_bonding_interfaces with case sensitivity scenarios."""
        mocker.patch.object(owner.bonding, "get_bond_interfaces", return_value=["Bond0"])  # Uppercase B
        mocker.patch.object(owner.bonding, "get_children", return_value=["Eth0"])  # Uppercase E

        bond_lower = LinuxInterfaceInfo(name="bond0", interface_type=InterfaceType.GENERIC, installed=True)
        bond_upper = LinuxInterfaceInfo(name="Bond0", interface_type=InterfaceType.GENERIC, installed=True)
        eth_lower = LinuxInterfaceInfo(name="eth0", interface_type=InterfaceType.PF, installed=True)
        eth_upper = LinuxInterfaceInfo(name="Eth0", interface_type=InterfaceType.PF, installed=True)

        interfaces = [bond_lower, bond_upper, eth_lower, eth_upper]

        owner._mark_bonding_interfaces(interfaces)

        # Only exact case matches should be marked
        assert bond_lower.interface_type == InterfaceType.GENERIC  # Unchanged
        assert bond_upper.interface_type == InterfaceType.BOND  # Changed
        assert eth_lower.interface_type == InterfaceType.PF  # Unchanged
        assert eth_upper.interface_type == InterfaceType.BOND_SLAVE  # Changed

    def test__update_mac_addresses_partial_matches(self, owner):
        """Test _update_mac_addresses with interfaces that partially match output names."""
        ip_a_output = dedent(
            """
            2: eth0: <BROADCAST,MULTICAST> mtu 1500 qdisc mq state DOWN group default qlen 1000
                link/ether 00:11:22:33:44:55 brd ff:ff:ff:ff:ff:ff
            3: eth01: <BROADCAST,MULTICAST> mtu 1500 qdisc mq state DOWN group default qlen 1000
                link/ether aa:bb:cc:dd:ee:ff brd ff:ff:ff:ff:ff:ff
        """
        )

        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", return_code=0, stdout=ip_a_output
        )

        eth0 = LinuxInterfaceInfo(name="eth0")
        eth01 = LinuxInterfaceInfo(name="eth01")
        eth1 = LinuxInterfaceInfo(name="eth1")  # Not in output

        interfaces = [eth0, eth01, eth1]

        owner._update_mac_addresses(interfaces=interfaces, namespace=None)

        # Exact matches should get MAC addresses
        assert eth0.mac_address == MACAddress(addr="00:11:22:33:44:55")
        assert eth01.mac_address == MACAddress(addr="aa:bb:cc:dd:ee:ff")

        # Non-matching interface should remain without MAC
        assert eth1.mac_address is None

    def test__update_mac_addresses_special_characters_in_names(self, owner):
        """Test _update_mac_addresses with special characters in interface names."""
        ip_a_output = dedent(
            """
            2: eth0-test: <BROADCAST,MULTICAST> mtu 1500 qdisc mq state DOWN group default qlen 1000
                link/ether 00:11:22:33:44:55 brd ff:ff:ff:ff:ff:ff
            3: vlan.100: <BROADCAST,MULTICAST> mtu 1500 qdisc mq state DOWN group default qlen 1000
                link/ether aa:bb:cc:dd:ee:ff brd ff:ff:ff:ff:ff:ff
            4: bridge_test: <BROADCAST,MULTICAST> mtu 1500 qdisc mq state DOWN group default qlen 1000
                link/ether 11:22:33:44:55:66 brd ff:ff:ff:ff:ff:ff
        """
        )

        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", return_code=0, stdout=ip_a_output
        )

        dash_iface = LinuxInterfaceInfo(name="eth0-test")
        dot_iface = LinuxInterfaceInfo(name="vlan.100")
        underscore_iface = LinuxInterfaceInfo(name="bridge_test")

        interfaces = [dash_iface, dot_iface, underscore_iface]

        owner._update_mac_addresses(interfaces=interfaces, namespace=None)

        # All interfaces should get their MAC addresses
        assert dash_iface.mac_address == MACAddress(addr="00:11:22:33:44:55")
        assert dot_iface.mac_address == MACAddress(addr="aa:bb:cc:dd:ee:ff")
        assert underscore_iface.mac_address == MACAddress(addr="11:22:33:44:55:66")

    def test__mark_bonding_interfaces_verify_call_sequence(self, owner, mocker):
        """Test that _mark_bonding_interfaces calls bonding methods in correct sequence."""
        get_bond_interfaces_mock = mocker.patch.object(owner.bonding, "get_bond_interfaces", return_value=["bond0"])
        get_children_mock = mocker.patch.object(owner.bonding, "get_children", return_value=["eth0"])

        bond0 = LinuxInterfaceInfo(name="bond0", interface_type=InterfaceType.GENERIC, installed=True)
        eth0 = LinuxInterfaceInfo(name="eth0", interface_type=InterfaceType.PF, installed=True)

        interfaces = [bond0, eth0]

        owner._mark_bonding_interfaces(interfaces)

        # Verify get_bond_interfaces is called first
        get_bond_interfaces_mock.assert_called_once()

        # Verify get_children is called for each bond interface
        get_children_mock.assert_called_once_with(bonding_interface="bond0")

        # Verify call order
        assert get_bond_interfaces_mock.call_count == 1
        assert get_children_mock.call_count == 1
