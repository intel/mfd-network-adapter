# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from itertools import zip_longest
from textwrap import dedent

import pytest
from mfd_common_libs import log_levels
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import PCIDevice, PCIAddress, OSName, VendorID, DeviceID, SubVendorID, SubDeviceID
from mfd_typing.network_interface import LinuxInterfaceInfo, InterfaceType, VlanInterfaceInfo

from mfd_network_adapter.exceptions import VirtualFunctionCreationException
from mfd_network_adapter.network_adapter_owner.freebsd import FreeBSDNetworkAdapterOwner

cmd_output = {
    "pciconf -l pci0:24:0:0": dedent(
        "ix0@pci0:24:0:0:        class=0x020000 rev=0x01 hdr=0x00 vendor=0x8086 device=0x1563 subvendor=0x8086 subdevice=0x35d4"  # noqa: E501
    ),
    "pciconf -l pci0:24:0:1": dedent(
        "ix1@pci0:24:0:1:        class=0x020000 rev=0x01 hdr=0x00 vendor=0x8086 device=0x1563 subvendor=0x8086 subdevice=0x35d4"  # noqa: E501
    ),
    "uname -K": dedent("1300139"),
    "pciconf -l -v": dedent(
        """ix0@pci0:24:0:0:        class=0x020000 rev=0x01 hdr=0x00 vendor=0x8086 device=0x1563 subvendor=0x8086 subdevice=0x35d4
    vendor     = 'Intel Corporation'
    device     = 'Ethernet Controller 10G X550T'
    class      = network
    subclass   = ethernet
ix1@pci0:24:0:1:        class=0x020000 rev=0x01 hdr=0x00 vendor=0x8086 device=0x1563 subvendor=0x8086 subdevice=0x35d4
    vendor     = 'Intel Corporation'
    device     = 'Ethernet Controller 10G X550T'
    class      = network
    subclass   = ethernet

"""  # noqa: E501
    ),
    "lspci -d 8086:1563 -D": dedent(
        """0000:18:00.0 Ethernet controller: Intel Corporation Ethernet Controller 10G X550T (rev 01)
0000:18:00.1 Ethernet controller: Intel Corporation Ethernet Controller 10G X550T (rev 01)
"""
    ),
    "lspci -v -mm -nn -s 0000:18:00.0": dedent(
        """Slot:   18:00.0
Class:  Ethernet controller [0200]
Vendor: Intel Corporation [8086]
Device: Ethernet Controller 10G X550T [1563]
SVendor:        Intel Corporation [8086]
SDevice:        Device [35d4]
Rev:    01
"""
    ),
    "lspci -v -mm -nn -s 0000:18:00.1": dedent(
        """Slot:   18:00.1
Class:  Ethernet controller [0200]
Vendor: Intel Corporation [8086]
Device: Ethernet Controller 10G X550T [1563]
SVendor:        Intel Corporation [8086]
SDevice:        Device [35d4]
Rev:    01
"""
    ),
}

initial_config = dedent(
    "PF {\n\
device : ice0\n\
num_vfs : 2\n\
}\n\
\n\
DEFAULT {\n\
}\n\
\n\
VF-0 {\n\
passthrough : true\n\
max-vlan-allowed : 16\n\
max-mac-filters : 16\n\
allow-set-mac : true\n\
mac-addr : 00:00:00:00:00:00\n\
allow-promisc : true\n\
num-queues : 4\n\
mdd-auto-reset-vf : true\n\
mac-anti-spoof : true\n\
mirror-src-vsi : 4\n\
kwargs-bool-test : true\n\
kwargs-int-test : 1\n\
kwargs-str-test : test\n\
}\n\
\n\
VF-1 {\n\
passthrough : true\n\
max-vlan-allowed : 16\n\
max-mac-filters : 16\n\
allow-set-mac : true\n\
mac-addr : 00:00:00:00:00:00\n\
allow-promisc : true\n\
num-queues : 4\n\
mdd-auto-reset-vf : true\n\
mac-anti-spoof : true\n\
mirror-src-vsi : 4\n\
kwargs-bool-test : true\n\
kwargs-int-test : 1\n\
kwargs-str-test : test\n\
}\
"
)
freebsd_expected = {
    "system": OSName.FREEBSD,
    "pci_device": PCIDevice("8086", "1563", "8086", "35D4"),
    "pci_addresses": [PCIAddress(0000, 24, 00, 0), PCIAddress(0000, 24, 00, 1)],
    "names": ["ix0", "ix1"],
    "family": "SGVL",
    "speed": "@10G",
    "cmd_output": cmd_output,
}


formatted_config_added_vfs = dedent(
    "\n\
VF-2 {\n\
passthrough : true\n \
max-vlan-allowed : 16\n \
max-mac-filters : 16\n \
allow-set-mac : true\n \
mac-addr : 00:00:00:00:00:00\n \
allow-promisc : true\n \
num-queues : 4\n \
mdd-auto-reset-vf : true\n \
mac-anti-spoof : true\n \
mirror-src-vsi : 4\n \
kwargs-bool-test : true\n \
kwargs-int-test : 1\n \
kwargs-str-test : test\n\
\n\
VF-3 {\n\
passthrough : true\n \
max-vlan-allowed : 16\n \
max-mac-filters : 16\n \
allow-set-mac : true\n \
mac-addr : 00:00:00:00:00:00\n \
allow-promisc : true\n \
num-queues : 4\n \
mdd-auto-reset-vf : true\n \
mac-anti-spoof : true\n \
mirror-src-vsi : 4\n \
kwargs-bool-test : true\n \
kwargs-int-test : 1\n \
kwargs-str-test : test\n\
}\
"
)

formatted_config = dedent(
    "PF {\n\
device : ice0\n\
num_vfs : 4\n\
}\n\
\n\
DEFAULT {\n\
}\n\
\n\
VF-0 {\n\
passthrough : true\n \
max-vlan-allowed : 16\n \
max-mac-filters : 16\n \
allow-set-mac : true\n \
mac-addr : 00:00:00:00:00:00\n \
allow-promisc : true\n \
num-queues : 4\n \
mdd-auto-reset-vf : true\n \
mac-anti-spoof : true\n \
mirror-src-vsi : 4\n \
kwargs-bool-test : true\n \
kwargs-int-test : 1\n \
kwargs-str-test : test\n\
}\n\
\n\
VF-1 {\n\
passthrough : true\n \
max-vlan-allowed : 16\n \
max-mac-filters : 16\n \
allow-set-mac : true\n \
mac-addr : 00:00:00:00:00:00\n \
allow-promisc : true\n \
num-queues : 4\n \
mdd-auto-reset-vf : true\n \
mac-anti-spoof : true\n \
mirror-src-vsi : 4\n \
kwargs-bool-test : true\n \
kwargs-int-test : 1\n \
kwargs-str-test : test\n\
\n\
VF-2 {\n\
passthrough : true\n \
max-vlan-allowed : 16\n \
max-mac-filters : 16\n \
allow-set-mac : true\n \
mac-addr : 00:00:00:00:00:00\n \
allow-promisc : true\n \
num-queues : 4\n \
mdd-auto-reset-vf : true\n \
mac-anti-spoof : true\n \
mirror-src-vsi : 4\n \
kwargs-bool-test : true\n \
kwargs-int-test : 1\n \
kwargs-str-test : test\n\
\n\
VF-3 {\n\
passthrough : true\n \
max-vlan-allowed : 16\n \
max-mac-filters : 16\n \
allow-set-mac : true\n \
mac-addr : 00:00:00:00:00:00\n \
allow-promisc : true\n \
num-queues : 4\n \
mdd-auto-reset-vf : true\n \
mac-anti-spoof : true\n \
mirror-src-vsi : 4\n \
kwargs-bool-test : true\n \
kwargs-int-test : 1\n \
kwargs-str-test : test\n\
}\
"
)


class TestFreeBSDNetworkOwner:
    @pytest.fixture()
    def owner(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.FREEBSD
        return FreeBSDNetworkAdapterOwner(connection=conn)

    def test__get_vlan_interfaces_data(self, owner):
        expected_output = [
            LinuxInterfaceInfo(
                interface_type=InterfaceType.VLAN, vlan_info=VlanInterfaceInfo(parent="iavf0", vlan_id=10)
            )
        ]
        output_freebsd_12_2 = """
            vlan0: flags=8842<BROADCAST,RUNNING,SIMPLEX,MULTICAST> metric 0 mtu 1500
            options=600703<RXCSUM,TXCSUM,TSO4,TSO6,LRO,RXCSUM_IPV6,TXCSUM_IPV6>
            ether 00:00:00:00:00:00
            groups: vlan
            vlan: 10 vlanpcp: 0 parent interface: iavf0
            media: Ethernet autoselect (40Gbase-SR4 <full-duplex>)
            status: active
            nd6 options=29<PERFORMNUD,IFDISABLED,AUTO_LINKLOCAL>
            """
        output_freebsd_13_0 = """
            vlan0: flags=8842<BROADCAST,RUNNING,SIMPLEX,MULTICAST> metric 0 mtu 1500
            options=4600703<RXCSUM,TXCSUM,TSO4,TSO6,LRO,RXCSUM_IPV6,TXCSUM_IPV6,NOMAP>
            ether 00:00:00:00:00:00
            groups: vlan
            vlan: 10 vlanproto: 802.1q vlanpcp: 0 parent interface: iavf0
            media: Ethernet autoselect (100GBase-SR4 <full-duplex>)
            status: active
            nd6 options=29<PERFORMNUD,IFDISABLED,AUTO_LINKLOCAL>
            """
        owner._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(args="", return_code=0, stdout="vlan0"),
            ConnectionCompletedProcess(args="", return_code=0, stdout=output_freebsd_12_2),
        ]
        assert owner._get_vlan_interfaces_data() == expected_output
        owner._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(args="", return_code=0, stdout="vlan0"),
            ConnectionCompletedProcess(args="", return_code=0, stdout=output_freebsd_13_0),
        ]
        assert owner._get_vlan_interfaces_data() == expected_output

    def test_get_inet_information(self, owner):
        output = """\
        ix0: flags=8863<UP,BROADCAST,RUNNING,SIMPLEX,MULTICAST> metric 0 mtu 1500
        options=4e53fbb<RXCSUM,TXCSUM,VLAN_MTU>
        inet 10.10.10.10 netmask 0xffffff80 broadcast 10.10.10.107
        ix1: flags=8822<BROADCAST,SIMPLEX,MULTICAST> metric 0 mtu 1500
        options=4e53fbb<RXCSUM,TXCSUM,VLAN_MTU>
        lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> metric 0 mtu 16384
        options=680003<RXCSUM,TXCSUM,LINKSTATE,RXCSUM_IPV6,TXCSUM_IPV6>
        inet 127.0.0.1 netmask 0xff000000
        ixl0: flags=8822<BROADCAST,SIMPLEX,MULTICAST> metric 0 mtu 1500
        options=4e507bb<RXCSUM,TXCSUM,VLAN_MTU,VLAN_HWTAGGING>
        ixl1: flags=8822<BROADCAST,SIMPLEX,MULTICAST> metric 0 mtu 1500
        options=4e507bb<RXCSUM,TXCSUM,VLAN_MTU,VLAN_HWTAGGING>
        iavf0: flags=8822<BROADCAST,SIMPLEX,MULTICAST> metric 0 mtu 1500
        options=4e507bb<RXCSUM,TXCSUM,VLAN_MTU,NOMAP>"""
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", return_code=0, stdout=output
        )
        expected_outputs = [
            {
                "name": "ix0",
                "flags": "8863<UP,BROADCAST,RUNNING,SIMPLEX,MULTICAST> metric 0 mtu 1500",
                "options": "4e53fbb<RXCSUM,TXCSUM,VLAN_MTU>",
                "inet": "10.10.10.10 netmask 0xffffff80 broadcast 10.10.10.107",
            },
            {
                "name": "ix1",
                "flags": "8822<BROADCAST,SIMPLEX,MULTICAST> metric 0 mtu 1500",
                "options": "4e53fbb<RXCSUM,TXCSUM,VLAN_MTU>",
                "inet": None,
            },
            {
                "name": "lo0",
                "flags": "8049<UP,LOOPBACK,RUNNING,MULTICAST> metric 0 mtu 16384",
                "options": "680003<RXCSUM,TXCSUM,LINKSTATE,RXCSUM_IPV6,TXCSUM_IPV6>",
                "inet": "127.0.0.1 netmask 0xff000000",
            },
            {
                "name": "ixl0",
                "flags": "8822<BROADCAST,SIMPLEX,MULTICAST> metric 0 mtu 1500",
                "options": "4e507bb<RXCSUM,TXCSUM,VLAN_MTU,VLAN_HWTAGGING>",
                "inet": None,
            },
            {
                "name": "ixl1",
                "flags": "8822<BROADCAST,SIMPLEX,MULTICAST> metric 0 mtu 1500",
                "options": "4e507bb<RXCSUM,TXCSUM,VLAN_MTU,VLAN_HWTAGGING>",
                "inet": None,
            },
            {
                "name": "iavf0",
                "flags": "8822<BROADCAST,SIMPLEX,MULTICAST> metric 0 mtu 1500",
                "options": "4e507bb<RXCSUM,TXCSUM,VLAN_MTU,NOMAP>",
                "inet": None,
            },
        ]
        for output, match in zip_longest(expected_outputs, list(owner._get_inet_information()), fillvalue=None):
            assert output == match.groupdict()

    @pytest.fixture()
    def inet_info(self, owner):
        output = """\
                        ix0: flags=8863<UP,BROADCAST,RUNNING,SIMPLEX,MULTICAST> metric 0 mtu 1500
                        options=4e53fbb<RXCSUM,TXCSUM,VLAN_MTU>
                        inet 10.10.10.10 netmask 0xffffff80 broadcast 10.10.10.107
                        ix1: flags=8822<BROADCAST,SIMPLEX,MULTICAST> metric 0 mtu 1500
                        options=4e53fbb<RXCSUM,TXCSUM,VLAN_MTU>
                        lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> metric 0 mtu 16384
                        options=680003<RXCSUM,TXCSUM,LINKSTATE,RXCSUM_IPV6,TXCSUM_IPV6>
                        inet 127.0.0.1 netmask 0xff000000
                        ixl0: flags=8822<BROADCAST,SIMPLEX,MULTICAST> metric 0 mtu 1500
                        options=4e507bb<RXCSUM,TXCSUM,VLAN_MTU,VLAN_HWTAGGING>
                        ixl1: flags=8822<BROADCAST,SIMPLEX,MULTICAST> metric 0 mtu 1500
                        options=4e507bb<RXCSUM,TXCSUM,VLAN_MTU,VLAN_HWTAGGING>
                        iavf0: flags=8822<BROADCAST,SIMPLEX,MULTICAST> metric 0 mtu 1500
                        options=4e507bb<RXCSUM,TXCSUM,VLAN_MTU,NOMAP>"""
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", return_code=0, stdout=output
        )
        yield owner._get_inet_information()

    def test_mark_management_interface(self, owner, inet_info):
        interfaces_list = [
            LinuxInterfaceInfo(
                pci_address=PCIAddress(domain=0, bus=24, slot=0, func=0),
                pci_device=PCIDevice(
                    vendor_id=VendorID("8086"),
                    device_id=DeviceID("1563"),
                    sub_vendor_id=SubVendorID("8086"),
                    sub_device_id=SubDeviceID("35D4"),
                ),
                name="ix0",
                interface_type=InterfaceType.PF,
                mac_address=None,
                installed=True,
                branding_string="Ethernet Controller X550",
                vlan_info=None,
            ),
            LinuxInterfaceInfo(
                pci_address=PCIAddress(domain=0, bus=24, slot=0, func=1),
                pci_device=PCIDevice(
                    vendor_id=VendorID("8086"),
                    device_id=DeviceID("1563"),
                    sub_vendor_id=SubVendorID("8086"),
                    sub_device_id=SubDeviceID("35D4"),
                ),
                name="ix1",
                interface_type=InterfaceType.PF,
                mac_address=None,
                installed=True,
                branding_string="Ethernet Controller X550",
                vlan_info=None,
            ),
            LinuxInterfaceInfo(
                pci_address=PCIAddress(domain=0, bus=94, slot=0, func=0),
                pci_device=PCIDevice(
                    vendor_id=VendorID("8086"),
                    device_id=DeviceID("1572"),
                    sub_vendor_id=SubVendorID("8086"),
                    sub_device_id=SubDeviceID("0007"),
                ),
                name="ixl0",
                interface_type=InterfaceType.PF,
                mac_address=None,
                installed=True,
                branding_string="Ethernet Controller X710 for 10GbE SFP+",
                vlan_info=None,
            ),
            LinuxInterfaceInfo(
                pci_address=PCIAddress(domain=0, bus=94, slot=0, func=1),
                pci_device=PCIDevice(
                    vendor_id=VendorID("8086"),
                    device_id=DeviceID("1572"),
                    sub_vendor_id=SubVendorID("8086"),
                    sub_device_id=SubDeviceID("0000"),
                ),
                name="ixl1",
                interface_type=InterfaceType.PF,
                mac_address=None,
                installed=True,
                branding_string="Ethernet Controller X710 for 10GbE SFP+",
                vlan_info=None,
            ),
        ]
        new_list = interfaces_list[::]
        owner._connection._ip = "10.10.10.10"
        owner._mark_management_interface(info=interfaces_list, inet_info=inet_info)
        assert interfaces_list == new_list
        assert interfaces_list[0].interface_type == InterfaceType.MANAGEMENT
        assert all(interface.interface_type != InterfaceType.MANAGEMENT for interface in interfaces_list[1:])

    def test__get_all_interfaces_info(self, owner, mocker, inet_info):
        expected_output = [
            LinuxInterfaceInfo(
                pci_address=PCIAddress(domain=0, bus=24, slot=0, func=0),
                pci_device=PCIDevice(
                    vendor_id=VendorID("8086"),
                    device_id=DeviceID("1563"),
                    sub_vendor_id=SubVendorID("8086"),
                    sub_device_id=SubDeviceID("35D4"),
                ),
                name="ix0",
                interface_type=InterfaceType.MANAGEMENT,
                mac_address=None,
                installed=True,
                branding_string="Ethernet Controller X550",
                vlan_info=None,
            ),
            LinuxInterfaceInfo(
                pci_address=PCIAddress(domain=0, bus=24, slot=0, func=1),
                pci_device=PCIDevice(
                    vendor_id=VendorID("8086"),
                    device_id=DeviceID("1563"),
                    sub_vendor_id=SubVendorID("8086"),
                    sub_device_id=SubDeviceID("35D4"),
                ),
                name="ix1",
                interface_type=InterfaceType.PF,
                mac_address=None,
                installed=True,
                branding_string="Ethernet Controller X550",
                vlan_info=None,
            ),
            LinuxInterfaceInfo(
                pci_address=PCIAddress(domain=0, bus=94, slot=0, func=0),
                pci_device=PCIDevice(
                    vendor_id=VendorID("8086"),
                    device_id=DeviceID("1572"),
                    sub_vendor_id=SubVendorID("8086"),
                    sub_device_id=SubDeviceID("0007"),
                ),
                name="ixl0",
                interface_type=InterfaceType.PF,
                mac_address=None,
                installed=True,
                branding_string="Ethernet Controller X710 for 10GbE SFP+",
                vlan_info=None,
            ),
            LinuxInterfaceInfo(
                pci_address=PCIAddress(domain=0, bus=94, slot=0, func=1),
                pci_device=PCIDevice(
                    vendor_id=VendorID("8086"),
                    device_id=DeviceID("1572"),
                    sub_vendor_id=SubVendorID("8086"),
                    sub_device_id=SubDeviceID("0000"),
                ),
                name="ixl1",
                interface_type=InterfaceType.PF,
                mac_address=None,
                installed=True,
                branding_string="Ethernet Controller X710 for 10GbE SFP+",
                vlan_info=None,
            ),
            LinuxInterfaceInfo(
                pci_address=PCIAddress(domain=0, bus=0, slot=5, func=0),
                pci_device=PCIDevice(
                    vendor_id=VendorID("8086"),
                    device_id=DeviceID("154c"),
                    sub_vendor_id=SubVendorID("8086"),
                    sub_device_id=SubDeviceID("0000"),
                ),
                name="iavf0",
                interface_type=InterfaceType.VF,
                mac_address=None,
                installed=True,
                branding_string="Ethernet Virtual Function 700 Series",
                vlan_info=None,
            ),
        ]
        pciconf_output = dedent(
            """/
        ix0@pci0:24:0:0:	class=0x020000 rev=0x01 hdr=0x00 vendor=0x8086 device=0x1563 subvendor=0x8086 subdevice=0x35d4
        vendor     = 'Intel Corporation'
        device     = 'Ethernet Controller X550'
        class      = network
        subclass   = ethernet
        ix1@pci0:24:0:1:	class=0x020000 rev=0x01 hdr=0x00 vendor=0x8086 device=0x1563 subvendor=0x8086 subdevice=0x35d4
        vendor     = 'Intel Corporation'
        device     = 'Ethernet Controller X550'
        class      = network
        subclass   = ethernet
        ixl0@pci0:94:0:0:	class=0x020000 rev=0x01 hdr=0x00 vendor=0x8086 device=0x1572 subvendor=0x8086 subdevice=0x0007
        vendor     = 'Intel Corporation'
        device     = 'Ethernet Controller X710 for 10GbE SFP+'
        class      = network
        subclass   = ethernet
        ixl1@pci0:94:0:1:	class=0x020000 rev=0x01 hdr=0x00 vendor=0x8086 device=0x1572 subvendor=0x8086 subdevice=0x0000
        vendor     = 'Intel Corporation'
        device     = 'Ethernet Controller X710 for 10GbE SFP+'
        class      = network
        subclass   = ethernet
        iavf0@pci0:0:5:0:	class=0x020000 rev=0x02 hdr=0x00 vendor=0x8086 device=0x154c subvendor=0x8086 subdevice=0x0000
        vendor     = 'Intel Corporation'
        device     = 'Ethernet Virtual Function 700 Series'
        class      = network
        subclass   = ethernet"""  # noqa E501
        )
        owner._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(args="", return_code=0, stdout=pciconf_output),
            ConnectionCompletedProcess(args="", return_code=0, stdout="1300086"),
        ]
        vlan_info_mock = mocker.patch.object(owner, "_get_vlan_interfaces_data", mocker.Mock(return_value=[]))
        wa_mock = mocker.patch.object(owner, "_virtio_mlx_wa_name")
        inet_info_mock = mocker.patch.object(owner, "_get_inet_information", mocker.Mock(return_value=inet_info))

        owner._connection._ip = "10.10.10.10"
        assert expected_output == owner._get_all_interfaces_info()
        vlan_info_mock.assert_called_once()
        inet_info_mock.assert_called_once()
        wa_mock.assert_not_called()

    def test__load_config_file(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(args="", return_code=0)
        owner._load_config_file(interface_name="ice0", config_name="iovctl_ice0.conf", config_dir="/home/user")
        owner._connection.execute_command.assert_called_once_with("iovctl -C -f /home/user/iovctl_ice0.conf")

    def test__verify_if_loaded_vfs_are_correct(self, owner, mocker):
        expected_vf_num = 1
        expected_output = [
            LinuxInterfaceInfo(
                pci_address=PCIAddress(domain=0, bus=24, slot=0, func=0),
                pci_device=PCIDevice(
                    vendor_id=VendorID("8086"),
                    device_id=DeviceID("1563"),
                    sub_vendor_id=SubVendorID("8086"),
                    sub_device_id=SubDeviceID("35D4"),
                ),
                name="ix0",
                interface_type=InterfaceType.MANAGEMENT,
                mac_address=None,
                installed=True,
                branding_string="Ethernet Controller X550",
                vlan_info=None,
            ),
            LinuxInterfaceInfo(
                pci_address=PCIAddress(domain=0, bus=24, slot=0, func=1),
                pci_device=PCIDevice(
                    vendor_id=VendorID("8086"),
                    device_id=DeviceID("1563"),
                    sub_vendor_id=SubVendorID("8086"),
                    sub_device_id=SubDeviceID("35D4"),
                ),
                name="ix1",
                interface_type=InterfaceType.PF,
                mac_address=None,
                installed=True,
                branding_string="Ethernet Controller X550",
                vlan_info=None,
            ),
            LinuxInterfaceInfo(
                pci_address=PCIAddress(domain=0, bus=94, slot=0, func=0),
                pci_device=PCIDevice(
                    vendor_id=VendorID("8086"),
                    device_id=DeviceID("1592"),
                    sub_vendor_id=SubVendorID("8086"),
                    sub_device_id=SubDeviceID("0007"),
                ),
                name="ice0",
                interface_type=InterfaceType.PF,
                mac_address=None,
                installed=True,
                branding_string="Ethernet Controller E810-XXV-2",
                vlan_info=None,
            ),
            LinuxInterfaceInfo(
                pci_address=PCIAddress(domain=0, bus=94, slot=0, func=1),
                pci_device=PCIDevice(
                    vendor_id=VendorID("8086"),
                    device_id=DeviceID("1592"),
                    sub_vendor_id=SubVendorID("8086"),
                    sub_device_id=SubDeviceID("0000"),
                ),
                name="ice1",
                interface_type=InterfaceType.PF,
                mac_address=None,
                installed=True,
                branding_string="Ethernet Controller E810-XXV-2",
                vlan_info=None,
            ),
            LinuxInterfaceInfo(
                pci_address=PCIAddress(domain=0, bus=0, slot=5, func=0),
                pci_device=PCIDevice(
                    vendor_id=VendorID("8086"),
                    device_id=DeviceID("154c"),
                    sub_vendor_id=SubVendorID("8086"),
                    sub_device_id=SubDeviceID("0000"),
                ),
                name="iavf0",
                interface_type=InterfaceType.VF,
                mac_address=None,
                installed=True,
                branding_string="Ethernet Virtual Function 800 Series",
                vlan_info=None,
            ),
        ]
        mocker.patch.object(owner, "_get_all_interfaces_info", mocker.Mock(return_value=expected_output))
        assert owner._verify_if_loaded_vfs_are_correct(expected_vf_num)

    def test_add_vfs_to_config_file(self, owner, mocker):
        mock_file = mocker.MagicMock()
        mock_file.read_text.return_value = initial_config
        mock_file.write_text = mocker.MagicMock()

        mock_connection = mocker.MagicMock()
        mock_connection.path.return_value = mock_file
        owner._connection = mock_connection

        mock_convert_to_vf_config_format = mocker.patch(
            "mfd_network_adapter.network_adapter_owner.freebsd.convert_to_vf_config_format"
        )
        mock_convert_to_vf_config_format.return_value = formatted_config_added_vfs

        mock_update_num_vfs_in_config = mocker.patch(
            "mfd_network_adapter.network_adapter_owner.freebsd.update_num_vfs_in_config"
        )
        mock_update_num_vfs_in_config.return_value = formatted_config

        owner.add_vfs_to_config_file(
            interface_name="ice0",
            vfs_count=2,
            passthrough=True,
            max_vlan_allowed=16,
            max_mac_filters=16,
            num_queues=4,
            mdd_auto_reset_vf=True,
            config_dir="/home/user",
            mac_addr=("00:00:00:00:00:00", "00:00:00:00:00:00"),
            allow_promiscuous=True,
            allow_set_mac=True,
            mac_anti_spoof=False,
            mirror_src_vsi=3,
            kwargs_bool_test=True,
            kwargs_int_test=1,
            kwargs_str_test="Test",
        )

        mock_file.read_text.assert_called_once()
        mock_convert_to_vf_config_format.assert_called_once()
        mock_update_num_vfs_in_config.assert_called_once_with(initial_config + formatted_config_added_vfs, 4)
        mock_file.write_text.assert_called_once_with(formatted_config)

    def test_create_vfs_success(self, owner, mocker):
        mocker.patch.object(owner, "_load_config_file", return_value=True)
        mocker.patch.object(owner, "_verify_if_loaded_vfs_are_correct", return_value=True)
        mock_logger_log = mocker.patch("mfd_network_adapter.network_adapter_owner.freebsd.logger.log")

        interface_name = "ice0"
        vfs_count = 2
        config_dir = "/home/user"
        config_name = "iovctl_ice0.conf"
        owner.create_vfs(interface_name, vfs_count, config_dir, config_name)

        mock_logger_log.assert_any_call(
            level=log_levels.MODULE_DEBUG,
            msg=f"Successfully loaded config file {config_dir}/{config_name}.",
        )
        mock_logger_log.assert_any_call(
            level=log_levels.MODULE_DEBUG,
            msg=f"Successfully created {vfs_count} VFs assigned to {interface_name} interface.",
        )

    def test_create_vfs_fail(self, owner, mocker):
        mocker.patch.object(owner, "_load_config_file", return_value=False)
        mocker.patch("mfd_network_adapter.network_adapter_owner.freebsd.logger.log")

        interface_name = "ice0"
        vfs_count = 2
        config_name = "iovctl_ice0.conf"
        config_dir = "/home/user"
        with pytest.raises(VirtualFunctionCreationException) as exc_info:
            owner.create_vfs(interface_name, vfs_count, config_dir, config_name)

        assert str(exc_info.value) == f"Could not load config file {config_dir}/{config_name}"

    def test_delete_vfs(self, owner, mocker):
        mock_execute_command = mocker.patch.object(owner._connection, "execute_command")
        mock_logger_log = mocker.patch("mfd_network_adapter.network_adapter_owner.freebsd.logger.log")

        interface_name = "ice0"
        config_name = "iovctl_ice0.conf"
        config_dir = "/home/user"
        remove_conf = True
        owner.delete_vfs(interface_name, config_dir, remove_conf, config_name)

        mock_execute_command.assert_called_once_with(
            f"iovctl -D -f {config_dir}/{config_name}", expected_return_codes={0}
        )
        mock_logger_log.assert_any_call(
            level=log_levels.MODULE_DEBUG, msg=f"Successfully deleted all VFs assigned to {interface_name} interface."
        )
        mock_logger_log.assert_any_call(
            level=log_levels.MODULE_DEBUG,
            msg=f"Successfully deleted config file {config_dir}/{config_name}.",
        )
