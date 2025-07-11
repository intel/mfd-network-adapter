# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import PCIDevice, PCIAddress, VendorID, DeviceID, SubVendorID, SubDeviceID, MACAddress, OSName
from mfd_typing.network_interface import InterfaceInfo

from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner
from mfd_network_adapter.network_adapter_owner.exceptions import ESXiInterfacesLinkUpTimeout
from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_network_adapter.network_interface.feature.link import LinkState


class TestESXiNetworkOwner:
    output_lspci_n = dedent(
        """
        0000:31:00.0 Class 0200: 8086:1521 [vmnic4]
        0000:31:00.1 Class 0200: 8086:1521 [vmnic5]
        0000:31:00.2 Class 0200: 8086:1521 [vmnic6]
        0000:31:00.3 Class 0200: 8086:1521 [vmnic7]
        0000:4b:00.0 Class 0200: 8086:1593 [vmnic0]
        0000:4b:00.1 Class 0200: 8086:1593 [vmnic1]
        0000:4b:00.2 Class 0200: 8086:1593 [vmnic2]
        0000:4b:00.3 Class 0200: 8086:1593 [vmnic3]
        0000:98:00.0 Class 0200: 14e4:16d8 [vmnic14]
        0000:98:00.1 Class 0200: 14e4:16d8 [vmnic15]
        0000:b1:00.0 Class 0200: 8086:10fb [vmnic8]
        0000:b1:00.1 Class 0200: 8086:10fb [vmnic9]
        0000:ca:00.0 Class 0200: 8086:1572 [vmnic10]
        0000:ca:00.1 Class 0200: 8086:1572 [vmnic11]
        0000:ca:00.2 Class 0200: 8086:1572 [vmnic12]
        0000:ca:00.3 Class 0200: 8086:1572 [vmnic13]
        0000:ca:02.0 Class 0200: 8086:154c [PF_0.202.0_VF_0]
        0000:ca:02.1 Class 0200: 8086:154c [PF_0.202.0_VF_1]
        0000:cb:00.0 Class 0200: 8086:154c [PF_0.202.1_VF_0]
        0000:cb:00.1 Class 0200: 8086:154c [PF_0.202.1_VF_1]
        """
    )

    output_lspci_p = dedent(
        """
        0000:31:00.0 8086:1521 103c:8157 255/   /     D V igbn         vmnic4
        0000:31:00.1 8086:1521 103c:8157 255/   /     C V igbn         vmnic5
        0000:31:00.2 8086:1521 103c:8157 255/   /     B V igbn         vmnic6
        0000:31:00.3 8086:1521 103c:8157 255/   /     A V igbn         vmnic7
        0000:4b:00.0 8086:1593 8086:0005 255/   /     A V icen         vmnic0
        0000:4b:00.1 8086:1593 8086:0005 255/   /     A V icen         vmnic1
        0000:4b:00.2 8086:1593 8086:0005 255/   /     A V icen         vmnic2
        0000:4b:00.3 8086:1593 8086:0005 255/   /     A V icen         vmnic3
        0000:98:00.0 14e4:16d8 14e4:1602 255/   /     A V bnxtnet      vmnic14
        0000:98:00.1 14e4:16d8 14e4:1602 255/   /     B V bnxtnet      vmnic15
        0000:b1:00.0 8086:10fb 8086:000c 255/   /     A V ixgben       vmnic8
        0000:b1:00.1 8086:10fb 8086:000c 255/   /     B V ixgben       vmnic9
        0000:ca:00.0 8086:1572 8086:0004 255/   /     A V i40en        vmnic10
        0000:ca:00.1 8086:1572 8086:0000 255/   /     A V i40en        vmnic11
        0000:ca:00.2 8086:1572 8086:0000 255/   /     A V i40en        vmnic12
        0000:ca:00.3 8086:1572 8086:0000 255/   /     A V i40en        vmnic13
        """
    )

    output_esxcfg_nics = dedent(
        """Name    PCI          Driver      Link Speed      Duplex MAC Address       MTU    Description
        vmnic0  0000:4b:00.0 icen        Up   25000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Controller E810-C for SFP
        vmnic1  0000:4b:00.1 icen        Up   25000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Controller E810-C for SFP
        vmnic10 0000:ca:00.0 i40en       Up   10000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Controller X710 for 10GbE SFP+
        vmnic11 0000:ca:00.1 i40en       Up   10000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Controller X710 for 10GbE SFP+
        vmnic12 0000:ca:00.2 i40en       Up   10000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Controller X710 for 10GbE SFP+
        vmnic13 0000:ca:00.3 i40en       Up   10000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Controller X710 for 10GbE SFP+
        vmnic14 0000:98:00.0 bnxtnet     Down 0Mbps      Half   00:00:00:00:00:00 1500   Broadcom BCM57416 NetXtreme-E 10GBASE-T RDMA Ethernet Controller
        vmnic15 0000:98:00.1 bnxtnet     Down 0Mbps      Half   00:00:00:00:00:00 1500   Broadcom BCM57416 NetXtreme-E 10GBASE-T RDMA Ethernet Controller
        vmnic2  0000:4b:00.2 icen        Up   25000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Controller E810-C for SFP
        vmnic3  0000:4b:00.3 icen        Up   25000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Controller E810-C for SFP
        vmnic4  0000:31:00.0 igbn        Up   1000Mbps   Full   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
        vmnic5  0000:31:00.1 igbn        Down 0Mbps      Half   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
        vmnic6  0000:31:00.2 igbn        Down 0Mbps      Half   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
        vmnic7  0000:31:00.3 igbn        Down 0Mbps      Half   00:00:00:00:00:00 1500   Intel(R) I350 Gigabit Network Connection
        vmnic8  0000:b1:00.0 ixgben      Up   10000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) 82599 10 Gigabit Dual Port Network Connection
        vmnic9  0000:b1:00.1 ixgben      Up   10000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) 82599 10 Gigabit Dual Port Network Connection
        """  # noqa: E501
    )

    @pytest.fixture()
    def owner(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.ESXI
        host = ESXiNetworkAdapterOwner(connection=conn)
        return host

    @pytest.fixture()
    def owner2(self, owner):
        owner._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="command", stdout=self.output_lspci_n, stderr="stderr"),
            ConnectionCompletedProcess(return_code=0, args="command", stdout=self.output_lspci_p, stderr="stderr"),
            ConnectionCompletedProcess(return_code=0, args="command", stdout=self.output_esxcfg_nics, stderr="stderr"),
        ]
        return owner

    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "eth0"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.ESXI
        interface = ESXiNetworkInterface(
            connection=connection, owner=None, interface_info=InterfaceInfo(name=name, pci_address=pci_address)
        )
        yield interface
        mocker.stopall()

    def test__get_net_devices(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=self.output_lspci_n, stderr="stderr"
        )
        devices = owner._get_net_devices()
        assert len(devices) == 16
        assert PCIAddress(domain=0, bus=0x31, slot=0, func=0) in devices
        assert PCIAddress(domain=0, bus=0xCA, slot=0, func=3) in devices

    def test__get_devices(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=self.output_lspci_p, stderr="stderr"
        )
        devices = owner._get_devices()
        assert len(devices) == 16
        assert PCIAddress(domain=0, bus=0x31, slot=0, func=0) in devices
        assert PCIAddress(domain=0, bus=0xCA, slot=0, func=3) in devices
        assert devices[PCIAddress(domain=0, bus=0x31, slot=0, func=0)] == PCIDevice(
            vendor_id=VendorID("8086"),
            device_id=DeviceID("1521"),
            sub_vendor_id=SubVendorID("103C"),
            sub_device_id=SubDeviceID("8157"),
        )

    def test__get_esxcfg_nics(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=self.output_esxcfg_nics, stderr="stderr"
        )
        devices = owner._get_esxcfg_nics(owner._connection)
        assert len(devices) == 16
        assert PCIAddress(domain=0, bus=0x31, slot=0, func=0) in devices
        assert PCIAddress(domain=0, bus=0xCA, slot=0, func=3) in devices
        assert "vmnic4" == devices[PCIAddress(domain=0, bus=0x31, slot=0, func=0)]["name"]
        assert MACAddress("00:00:00:00:00:00") == devices[PCIAddress(domain=0, bus=0x31, slot=0, func=0)]["mac"]
        assert "I350" in devices[PCIAddress(domain=0, bus=0x31, slot=0, func=0)]["branding_string"]
        assert "igbn" in devices[PCIAddress(domain=0, bus=0x31, slot=0, func=0)]["driver"]
        assert LinkState.UP == devices[PCIAddress(domain=0, bus=0x31, slot=0, func=0)]["link"]
        assert "1000Mbps" in devices[PCIAddress(domain=0, bus=0x31, slot=0, func=0)]["speed"]
        assert "Full" in devices[PCIAddress(domain=0, bus=0x31, slot=0, func=0)]["duplex"]
        assert "1500" in devices[PCIAddress(domain=0, bus=0x31, slot=0, func=0)]["mtu"]

    def test_all_interfaces(self, owner2):
        devices = owner2._get_all_interfaces_info()
        assert len(devices) == 16

    def test_filter_interfaces_all(self, owner2):
        all_interfaces_info = owner2._get_all_interfaces_info()
        devices = owner2._filter_interfaces_info(all_interfaces_info=all_interfaces_info)
        assert len(devices) == 16

    def test_filter_interfaces_random(self, owner2):
        all_interfaces_info = owner2._get_all_interfaces_info()
        devices = owner2._filter_interfaces_info(all_interfaces_info=all_interfaces_info, random_interface=True)
        assert len(devices) == 1

    def test_filter_interfaces_pci_address(self, owner2):
        all_interfaces_info = owner2._get_all_interfaces_info()
        devices = owner2._filter_interfaces_info(
            all_interfaces_info=all_interfaces_info, pci_address=PCIAddress(domain=0, bus=0xCA, slot=0, func=3)
        )
        assert len(devices) == 1
        assert devices[0].name == "vmnic13"

    def test_filter_interfaces_pci_device_all_1(self, owner2):
        all_interfaces_info = owner2._get_all_interfaces_info()
        devices = owner2._filter_interfaces_info(
            all_interfaces_info,
            pci_device=PCIDevice(
                vendor_id=VendorID("8086"),
                device_id=DeviceID("1521"),
                sub_vendor_id=SubVendorID("103C"),
                sub_device_id=SubDeviceID("8157"),
            ),
        )
        assert len(devices) == 4

    def test_filter_interfaces_pci_device_all_2(self, owner2):
        all_interfaces_info = owner2._get_all_interfaces_info()
        devices = owner2._filter_interfaces_info(
            all_interfaces_info,
            pci_device=PCIDevice(
                vendor_id=VendorID("14e4"),
                device_id=DeviceID("16d8"),
                sub_vendor_id=SubVendorID(0),
                sub_device_id=SubDeviceID(0),
            ),
        )
        assert len(devices) == 2

    def test_filter_interfaces_pci_device_random(self, owner2):
        all_interfaces_info = owner2._get_all_interfaces_info()
        devices = owner2._filter_interfaces_info(
            all_interfaces_info,
            pci_device=PCIDevice(
                vendor_id=VendorID("8086"),
                device_id=DeviceID("1521"),
                sub_vendor_id=SubVendorID("103C"),
                sub_device_id=SubDeviceID("8157"),
            ),
            random_interface=True,
        )
        assert len(devices) == 1

    def test_filter_interfaces_family(self, owner2):
        all_interfaces_info = owner2._get_all_interfaces_info()
        devices = owner2._filter_interfaces_info(all_interfaces_info, family="PVL")
        assert len(devices) == 4
        assert devices[0].name == "vmnic4"
        assert devices[1].name == "vmnic5"
        assert devices[2].name == "vmnic6"
        assert devices[3].name == "vmnic7"

    def test_filter_interfaces_speed(self, owner2):
        all_interfaces_info = owner2._get_all_interfaces_info()
        devices = owner2._filter_interfaces_info(all_interfaces_info, speed="@100G")
        assert len(devices) == 4
        assert devices[0].name == "vmnic0"
        assert devices[1].name == "vmnic1"
        assert devices[2].name == "vmnic2"
        assert devices[3].name == "vmnic3"

    def test_get_interfaces(self, owner2):
        devices = owner2.get_interfaces(speed="@100G")
        assert len(devices) == 4
        assert devices[0].name == "vmnic0"
        assert devices[1].name == "vmnic1"
        assert devices[2].name == "vmnic2"
        assert devices[3].name == "vmnic3"

    def test_get_interface(self, owner2):
        device = owner2.get_interface(speed="@40G")
        assert device.name == "vmnic10"

    def test_wait_for_interfaces_up_all_up(self, mocker, owner, interface):
        mock_timeout_counter = mocker.patch("mfd_network_adapter.network_adapter_owner.esxi.TimeoutCounter")
        mock_timeout_counter.return_value = False
        mocker.patch("mfd_network_adapter.network_adapter_owner.esxi.sleep")
        owner._get_esxcfg_nics = mocker.Mock(
            return_value={
                interface.pci_address: {
                    "name": "name",
                    "mac": "mac",
                    "branding_string": "branding_string",
                    "driver": "driver",
                    "link": LinkState.UP,
                    "speed": "speed",
                    "duplex": "duplex",
                    "mtu": "mtu",
                }
            }
        )
        owner.wait_for_interfaces_up(interfaces=[interface])

    def test_wait_for_interfaces_up_timeout(self, mocker, owner, interface):
        mock_timeout_counter = mocker.patch("mfd_network_adapter.network_adapter_owner.esxi.TimeoutCounter")
        mock_timeout_counter.return_value.__bool__.side_effect = [False, False, False, False, True]
        mocker.patch("mfd_network_adapter.network_adapter_owner.esxi.sleep")
        owner._get_esxcfg_nics = mocker.Mock(
            return_value={
                interface.pci_address: {
                    "name": "name",
                    "mac": "mac",
                    "branding_string": "branding_string",
                    "driver": "driver",
                    "link": LinkState.DOWN,
                    "speed": "speed",
                    "duplex": "duplex",
                    "mtu": "mtu",
                }
            }
        )
        with pytest.raises(ESXiInterfacesLinkUpTimeout):
            owner.wait_for_interfaces_up(interfaces=[interface, interface])
