# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_network_adapter.exceptions import NetworkAdapterModuleException
from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner
from mfd_typing import PCIDevice, PCIAddress, OSName, VendorID, DeviceID, SubDeviceID, SubVendorID, MACAddress
from mfd_typing.network_interface import WindowsInterfaceInfo, InterfaceType, ClusterInfo


windows_expected = {
    "system": OSName.WINDOWS,
    "pci_device": PCIDevice("8086", "1563", "8086", "35D4"),
    "pci_addresses": [PCIAddress(0000, 24, 00, 1), PCIAddress(0000, 24, 00, 0)],
    "names": ["Ethernet 4", "SLOT 7 Port 2"],
    "family": "SGVL",
    "speed": "@10G",
}


class TestWindowsNetworkOwner:
    @pytest.fixture()
    def owner(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.WINDOWS
        return WindowsNetworkAdapterOwner(connection=conn)

    def test__update_nic_if_virtual(self, owner):
        nic = WindowsInterfaceInfo()
        nic.branding_string = "randombranding"
        nic.pnp_device_id = "randompnp"
        nic.service_name = "randomservice"
        nic.interface_type = InterfaceType.GENERIC

        owner._update_nic_if_virtual(nic)
        assert nic.interface_type is InterfaceType.PF

        nic.pnp_device_id = "iansmini"
        owner._update_nic_if_virtual(nic)
        assert nic.interface_type is InterfaceType.VF

        nic.service_name = "VMSMP"
        owner._update_nic_if_virtual(nic)
        assert nic.interface_type is InterfaceType.VF

        nic.branding_string = "Intel(R) Ethernet Adaptive Virtual Function"
        owner._update_nic_if_virtual(nic)
        assert nic.interface_type is InterfaceType.VF

        nic.branding_string = "Microsoft Hyper-V Network Adapter #10"
        nic.interface_type = None
        owner._update_nic_if_virtual(nic)
        assert nic.interface_type is InterfaceType.VMNIC

    def test_mark_mng_interface(self, owner):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0,
            args="",
            stderr="",
            stdout=dedent(
                """
            Index     : 0
            IPAddress :

            Index     : 1
            IPAddress :

            Index     : 2
            IPAddress :

            Index     : 3
            IPAddress :

            Index     : 4
            IPAddress :

            Index     : 5
            IPAddress :

            Index     : 6
            IPAddress :

            Index     : 7
            IPAddress : {10.10.10.10, fe80::eda6:1ac1:7f77:66e7}

            Index     : 8
            IPAddress :

            Index     : 9
            IPAddress : {1.1.1.1, fe80::2b4f:38e5:6ada:20a5}"""
            ),
        )
        ip = "10.10.10.10"
        owner._connection._ip = ip
        nics = [WindowsInterfaceInfo(index="7")]
        owner._mark_mng_interface(nics)
        assert nics[0].interface_type is InterfaceType.MANAGEMENT

    def test_get_pci_device(self, owner):
        nic = WindowsInterfaceInfo()
        nic.service_name = "NdisImPlatformMp"
        assert owner._get_pci_device(nic) is None

        nic.service_name = "TbtP2pNdisDrv"
        assert owner._get_pci_device(nic) == PCIDevice(vendor_id=VendorID("8086"), device_id=DeviceID("fff1"))

        nic.service_name = "randomservice"
        nic.pnp_device_id = r"PCI\VEN_8086&DEV_1592&SUBSYS_00028086&REV_01\30F307FFFFB7A64000"
        assert owner._get_pci_device(nic) == PCIDevice(
            vendor_id=VendorID("8086"),
            device_id=DeviceID("1592"),
            sub_device_id=SubDeviceID("0002"),
            sub_vendor_id=SubVendorID("8086"),
        )

    def test_parse_pci(self, owner):
        output = dedent(
            r""" # noqa E501
            DeviceDesc          : @netxix64.inf,%s1563.dual.description%;Intel(R) Ethernet Controller X550
            LocationInformation : @System32\drivers\pci.sys,#65536;PCI bus %1, device %2, function %3;(24,0,1)
            Capabilities        : 16
            UINumber            : 0
            Address             : 1
            ContainerID         : {00000000-0000-0000-ffff-ffffffffffff}
            HardwareID          : {PCI\VEN_8086&DEV_1563&SUBSYS_35D48086&REV_01, PCI\VEN_8086&DEV_1563&SUBSYS_35D48086, PCI\VEN_8086&DEV_1563&CC_020000, PCI\VEN_8086&DEV_1563&CC_0200}
            CompatibleIDs       : {PCI\VEN_8086&DEV_1563&REV_01, PCI\VEN_8086&DEV_1563, PCI\VEN_8086&CC_020000, PCI\VEN_8086&CC_0200...}
            ConfigFlags         : 0
            ClassGUID           : {4d36e972-e325-11ce-bfc1-08002be10318}
            Service             : ixgbi
            Driver              : {4d36e972-e325-11ce-bfc1-08002be10318}\0002
            Mfg                 : @netxix64.inf,%intel%;Intel Corporation
            FriendlyName        : Intel(R) Ethernet Controller X550
            PSPath              : Microsoft.PowerShell.Core\Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Enum\PCI\VEN_8086&DEV_1563&SUBSYS_35D48086&REV_01\0000C9FFFF00000001
            PSParentPath        : Microsoft.PowerShell.Core\Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Enum\PCI\VEN_8086&DEV_1563&SUBSYS_35D48086&REV_01
            PSChildName         : 0000C9FFFF00000001
            PSDrive             : HKLM
            PSProvider          : Microsoft.PowerShell.Core\Registry"""  # noqa E501
        )
        assert owner._parse_pci(output) == PCIAddress(data="0000:18:00.1")

    def test_verify_all_interfaces_are_in_same_installed_state(self, owner):
        nics = [WindowsInterfaceInfo(), WindowsInterfaceInfo()]
        nics[0].pnp_device_id = nics[1].pnp_device_id = (
            r"PCI\VEN_8086&DEV_1563&SUBSYS_35D48086&REV_01\0000C9FFFF00000001"
        )
        nics[0].installed = nics[1].installed = True
        assert owner._verify_all_interfaces_are_in_same_installed_state(nics) is True

        nics[0].installed = nics[1].installed = False
        assert owner._verify_all_interfaces_are_in_same_installed_state(nics) is True

        nics[0].installed = True
        assert owner._verify_all_interfaces_are_in_same_installed_state(nics) is False

    def test_get_available_interfaces(self, owner):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0,
            args="",
            stderr="",
            stdout=dedent(
                r"""
            __GENUS             : 2
            __CLASS             : Win32_NetworkAdapter
            __SUPERCLASS        :
            __DYNASTY           :
            __RELPATH           :
            __PROPERTY_COUNT    : 13
            __DERIVATION        : {}
            __SERVER            :
            __NAMESPACE         :
            __PATH              :
            Description         : Intel(R) Ethernet Controller X550
            GUID                : {F9E5C035-3B25-4CCF-8308-780F3623F0C6}
            Index               : 2
            Installed           : True
            MACAddress          : 00:00:00:00:00:00
            Manufacturer        : Intel Corporation
            Name                : Intel(R) Ethernet Controller X550
            NetConnectionID     : Ethernet 2
            NetConnectionStatus : 7
            PNPDeviceID         : PCI\VEN_8086&DEV_1563&SUBSYS_35D48086&REV_01\0000C9FFFF00000001
            ProductName         : Intel(R) Ethernet Controller X550
            ServiceName         : ixgbi
            Speed               : 9223372036854775807
            PSComputerName      :

            __GENUS             : 2
            __CLASS             : Win32_NetworkAdapter
            __SUPERCLASS        :
            __DYNASTY           :
            __RELPATH           :
            __PROPERTY_COUNT    : 13
            __DERIVATION        : {}
            __SERVER            :
            __NAMESPACE         :
            __PATH              :
            Description         : Intel(R) Ethernet Controller X550
            GUID                : {653E6E88-A9D0-4018-881F-74F81720251D}
            Index               : 3
            Installed           : True
            MACAddress          : 00:00:00:00:00:00
            Manufacturer        : Intel Corporation
            Name                : Intel(R) Ethernet Controller X550
            NetConnectionID     : Ethernet 3
            NetConnectionStatus : 2
            PNPDeviceID         : PCI\VEN_8086&DEV_1563&SUBSYS_35D48086&REV_01\0000C9FFFF00000000
            ProductName         : Intel(R) Ethernet Controller X550
            ServiceName         : ixgbi
            Speed               :
            PSComputerName      : """
            ),
        )
        nics = owner._get_available_interfaces()
        expected_nics = [
            WindowsInterfaceInfo(
                pci_address=None,
                pci_device=None,
                name="Ethernet 2",
                interface_type=InterfaceType.GENERIC,
                mac_address=MACAddress("00:00:00:00:00:00"),
                installed=True,
                branding_string="Intel(R) Ethernet Controller X550",
                vlan_info=None,
                description="Intel(R) Ethernet Controller X550",
                index="2",
                manufacturer="Intel Corporation",
                net_connection_status="7",
                pnp_device_id="PCI\\VEN_8086&DEV_1563&SUBSYS_35D48086&REV_01\\0000C9FFFF00000001",
                product_name="Intel(R) Ethernet Controller X550",
                service_name="ixgbi",
                guid="{F9E5C035-3B25-4CCF-8308-780F3623F0C6}",
                speed="9223372036854775807",
                cluster_info=None,
            ),
            WindowsInterfaceInfo(
                pci_address=None,
                pci_device=None,
                name="Ethernet 3",
                interface_type=InterfaceType.GENERIC,
                mac_address=MACAddress("00:00:00:00:00:00"),
                installed=True,
                branding_string="Intel(R) Ethernet Controller X550",
                vlan_info=None,
                description="Intel(R) Ethernet Controller X550",
                index="3",
                manufacturer="Intel Corporation",
                net_connection_status="2",
                pnp_device_id="PCI\\VEN_8086&DEV_1563&SUBSYS_35D48086&REV_01\\0000C9FFFF00000000",
                product_name="Intel(R) Ethernet Controller X550",
                service_name="ixgbi",
                guid="{653E6E88-A9D0-4018-881F-74F81720251D}",
                speed="",
                cluster_info=None,
            ),
        ]
        assert nics == expected_nics

    def test_update_vlan_info(self, owner):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0,
            args="",
            stderr="",
            stdout=dedent(
                """
            InterfaceAlias : Ethernet 5
            vlanid         : 0

            InterfaceAlias : Ethernet 3
            vlanid         :

            InterfaceAlias : Ethernet 4
            vlanid         : 50

            InterfaceAlias : vEthernet (TEST_SWITCH5)
            vlanid         : """
            ),
        )
        nics = [WindowsInterfaceInfo(name="Ethernet 4")]
        owner._update_vlan_info(nics)
        assert nics[0].vlan_info.vlan_id == 50

    def test_update_pci_addresses(self, owner):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0,
            args="",
            stderr="",
            stdout=dedent(
                """
            Name     : Ethernet 5
            Segment  : 0
            Bus      : 94
            Device   : 0
            Function : 1

            Name     : Ethernet 4
            Segment  : 1
            Bus      : 2
            Device   : 3
            Function : 4"""
            ),
        )
        nics = [WindowsInterfaceInfo(name="Ethernet 4"), WindowsInterfaceInfo(name="Ethernet 5")]
        owner._update_pci_addresses(nics)
        pci_address = PCIAddress(domain=0, bus=94, slot=0, func=1)
        pci_address2 = PCIAddress(domain=1, bus=2, slot=3, func=4)
        assert nics[0].pci_address == pci_address2
        assert nics[1].pci_address == pci_address

    def test__update_cluster(self, owner):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0,
            args="",
            stderr="",
            stdout=dedent(
                """
                Name                           Network
                ----                           -------
                NODE-1 - Management            Cluster Network 1
                NODE-2 - Management            Cluster Network 1
                NODE-3 - Management            Cluster Network 1
                NODE-4 - Management            Cluster Network 1
                NODE-1 - vSMB1                 Cluster Network 2
                NODE-1 - vSMB2                 Cluster Network 2
                NODE-1 - vSMB3                 Cluster Network 2
                NODE-1 - vSMB4                 Cluster Network 2
                NODE-2 - vSMB1                 Cluster Network 2
                NODE-2 - vSMB2                 Cluster Network 2
                NODE-2 - vSMB3                 Cluster Network 2
                NODE-2 - vSMB4                 Cluster Network 2
                NODE-3 - vSMB1                 Cluster Network 2
                NODE-3 - vSMB2                 Cluster Network 2
                NODE-3 - vSMB3                 Cluster Network 2
                NODE-3 - vSMB4                 Cluster Network 2
                NODE-4 - vSMB1                 Cluster Network 2
                NODE-4 - vSMB2                 Cluster Network 2
                NODE-4 - vSMB3                 Cluster Network 2
                NODE-4 - vSMB4                 Cluster Network 2
                NODE-1 - Embedded LOM 1 Port 1 Cluster Network 3
                NODE-2 - Embedded LOM 1 Port 1 Cluster Network 3
                NODE-3 - Embedded LOM 1 Port 1 Cluster Network 3
                NODE-4 - Embedded LOM 1 Port 1 Cluster Network 3
                NODE-2 - PCIe Slot 6 Port 1    Cluster Network 4
                NODE-2 - PCIe Slot 6 Port 2    Cluster Network 4
                NODE-3 - PCIe Slot 6 Port 2    Cluster Network 4
                """
            ),
        )

        nics = [
            WindowsInterfaceInfo(name="vSMB3"),
            WindowsInterfaceInfo(name="vSMB4"),
            WindowsInterfaceInfo(name="Management"),
        ]
        owner._update_cluster(nics)

        # interface type assertions
        assert InterfaceType.CLUSTER_STORAGE == nics[0].interface_type
        assert InterfaceType.CLUSTER_STORAGE == nics[1].interface_type
        assert InterfaceType.CLUSTER_MANAGEMENT == nics[2].interface_type

        # cluster network assertions
        assert "Cluster Network 2" == nics[0].cluster_info.network
        assert "Cluster Network 2" == nics[0].cluster_info.network
        assert "Cluster Network 1" == nics[2].cluster_info.network

    def test__get_all_interfaces_info_cluster_case(self, owner, mocker):
        nics = [
            WindowsInterfaceInfo(name="vSMB1", mac_address=MACAddress("00:00:00:00:00:00")),
            WindowsInterfaceInfo(name="Management", mac_address=MACAddress("00:00:00:00:00:00")),
            WindowsInterfaceInfo(name="Ethernet 2", mac_address=MACAddress("00:00:00:00:00:00")),
        ]
        owner._get_interfaces_and_verify_states = mocker.Mock(return_value=nics)

        expected_nics = [
            WindowsInterfaceInfo(
                name="vSMB1",
                mac_address=MACAddress("00:00:00:00:00:00"),
                interface_type=InterfaceType.CLUSTER_STORAGE,
                pci_device=PCIDevice(data="8086:1572"),
                cluster_info=ClusterInfo(node=None, network="Cluster Network 2"),
            ),
            WindowsInterfaceInfo(
                name="Management",
                mac_address=MACAddress("00:00:00:00:00:00"),
                interface_type=InterfaceType.CLUSTER_MANAGEMENT,
                pci_device=PCIDevice(data="8086:1572"),
                cluster_info=ClusterInfo(node=None, network="Cluster Network 1"),
            ),
            WindowsInterfaceInfo(
                name="Ethernet 2",
                mac_address=MACAddress("00:00:00:00:00:00"),
                interface_type=InterfaceType.GENERIC,
                pci_device=PCIDevice(data="8086:1572"),
            ),
        ]

        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0,
            args="",
            stderr="",
            stdout=dedent(
                """
                Name                           Network
                ----                           -------
                NODE-1 - Management            Cluster Network 1
                NODE-2 - Management            Cluster Network 1
                NODE-3 - Management            Cluster Network 1
                NODE-4 - Management            Cluster Network 1
                NODE-1 - vSMB1                 Cluster Network 2
                NODE-1 - vSMB2                 Cluster Network 2
                NODE-1 - vSMB3                 Cluster Network 2
                NODE-1 - vSMB4                 Cluster Network 2
                NODE-2 - vSMB1                 Cluster Network 2
                NODE-2 - vSMB2                 Cluster Network 2
                NODE-2 - vSMB3                 Cluster Network 2
                NODE-2 - vSMB4                 Cluster Network 2
                NODE-3 - vSMB1                 Cluster Network 2
                NODE-3 - vSMB2                 Cluster Network 2
                NODE-3 - vSMB3                 Cluster Network 2
                NODE-3 - vSMB4                 Cluster Network 2
                NODE-4 - vSMB1                 Cluster Network 2
                NODE-4 - vSMB2                 Cluster Network 2
                NODE-4 - vSMB3                 Cluster Network 2
                NODE-4 - vSMB4                 Cluster Network 2
                NODE-1 - Embedded LOM 1 Port 1 Cluster Network 3
                NODE-2 - Embedded LOM 1 Port 1 Cluster Network 3
                NODE-3 - Embedded LOM 1 Port 1 Cluster Network 3
                NODE-4 - Embedded LOM 1 Port 1 Cluster Network 3
                NODE-2 - PCIe Slot 6 Port 1    Cluster Network 4
                NODE-2 - PCIe Slot 6 Port 2    Cluster Network 4
                NODE-3 - PCIe Slot 6 Port 2    Cluster Network 4
                """
            ),
        )
        mocker.patch(
            "mfd_network_adapter.network_adapter_owner.windows.WindowsNetworkAdapterOwner._get_pci_device",
            mocker.Mock(return_value=PCIDevice(data="8086:1572")),
        )
        mocker.patch(
            "mfd_network_adapter.network_adapter_owner.windows.WindowsNetworkAdapterOwner._update_nic_if_virtual",
            mocker.Mock(return_value=None),
        )
        mocker.patch(
            "mfd_network_adapter.network_adapter_owner.windows.WindowsNetworkAdapterOwner._update_pci_addresses",
            mocker.Mock(return_value=None),
        )
        returned_nics = owner._get_all_interfaces_info()

        assert returned_nics == expected_nics

    def test_get_log_cpu_no(self, owner):
        output = dedent(
            """
            __GENUS                   : 2
            __CLASS                   : Win32_ComputerSystem
            __SUPERCLASS              :
            __DYNASTY                 :
            __RELPATH                 :
            __PROPERTY_COUNT          : 1
            __DERIVATION              : {}
            __SERVER                  :
            __NAMESPACE               :
            __PATH                    :
            NumberOfLogicalProcessors : 72
            PSComputerName            : """
        )
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr=""
        )
        assert 72 == owner.get_log_cpu_no()

    def test_get_log_cpu_no_fail(self, owner):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="Output", stderr=""
        )
        with pytest.raises(NetworkAdapterModuleException, match="Failed to fetch the logical processors count"):
            owner.get_log_cpu_no()
