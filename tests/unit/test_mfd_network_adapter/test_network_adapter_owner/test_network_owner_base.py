import re

import pytest
from mfd_common_libs.exceptions import UnexpectedOSException
from mfd_connect import RPyCConnection, SSHConnection
from mfd_typing import OSName, PCIAddress, PCIDevice
from mfd_typing.network_interface import InterfaceInfo, WindowsInterfaceInfo, LinuxInterfaceInfo

from mfd_network_adapter import NetworkAdapterOwner
from mfd_network_adapter.network_adapter_owner.exceptions import (
    NetworkAdapterConnectedOSNotSupported,
    NetworkAdapterIncorrectData,
)
from mfd_network_adapter.exceptions import NetworkInterfaceIncomparableObject
from mfd_network_adapter.network_adapter_owner.freebsd import FreeBSDNetworkAdapterOwner
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner
from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface
from .test_freebsd_network_owner import freebsd_expected
from .test_linux_network_owner import linux_expected
from .test_windows_network_owner import windows_expected


@pytest.mark.parametrize("test_data", [linux_expected, windows_expected, freebsd_expected])
class TestNetworkAdapterOwnerPublicAPI:
    @pytest.fixture()
    def owner(self, mocker, test_data):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = test_data["system"]

        o = NetworkAdapterOwner(connection=conn)

        interface_info_class = {
            OSName.LINUX: LinuxInterfaceInfo,
            OSName.FREEBSD: LinuxInterfaceInfo,
            OSName.WINDOWS: WindowsInterfaceInfo,
        }.get(test_data["system"], InterfaceInfo)

        o._get_all_interfaces_info = mocker.Mock(
            return_value=[
                interface_info_class(
                    name=test_data["names"][0],
                    pci_device=test_data["pci_device"],
                    pci_address=test_data["pci_addresses"][0],
                ),
                interface_info_class(
                    name=test_data["names"][1],
                    pci_device=test_data["pci_device"],
                    pci_address=test_data["pci_addresses"][1],
                ),
            ]
        )
        return o

    def test_get_interface_by_pci_device(self, owner, test_data):
        first_interface = owner.get_interface(pci_device=test_data["pci_device"], interface_index=0)
        second_interface = owner.get_interface(pci_device=test_data["pci_device"], interface_index=1)
        assert first_interface.pci_device == test_data["pci_device"]
        assert second_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address == test_data["pci_addresses"][0]
        assert second_interface.pci_address == test_data["pci_addresses"][1]
        assert first_interface.name == test_data["names"][0]
        assert second_interface.name == test_data["names"][1]

    def test_get_interfaces_by_pci_device(self, owner, test_data):
        first_interface = owner.get_interfaces(pci_device=test_data["pci_device"], interface_indexes=[0])[0]
        second_interface = owner.get_interfaces(pci_device=test_data["pci_device"], interface_indexes=[1])[0]
        assert first_interface.pci_device == test_data["pci_device"]
        assert second_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address == test_data["pci_addresses"][0]
        assert second_interface.pci_address == test_data["pci_addresses"][1]
        assert first_interface.name == test_data["names"][0]
        assert second_interface.name == test_data["names"][1]

    def test_get_interfaces_by_pci_device_multiple_indexes(self, owner, test_data):
        interfaces = owner.get_interfaces(pci_device=test_data["pci_device"], interface_indexes=[0, 1])
        first_interface = interfaces[0]
        second_interface = interfaces[1]
        assert first_interface.pci_device == test_data["pci_device"]
        assert second_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address == test_data["pci_addresses"][0]
        assert second_interface.pci_address == test_data["pci_addresses"][1]
        assert first_interface.name == test_data["names"][0]
        assert second_interface.name == test_data["names"][1]

    def test_get_interface_by_pci_address(self, owner, test_data):
        first_interface = owner.get_interface(pci_address=test_data["pci_addresses"][0])
        second_interface = owner.get_interface(pci_address=test_data["pci_addresses"][1])
        assert first_interface.pci_device == test_data["pci_device"]
        assert second_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address == test_data["pci_addresses"][0]
        assert second_interface.pci_address == test_data["pci_addresses"][1]
        assert first_interface.name == test_data["names"][0]
        assert second_interface.name == test_data["names"][1]

    def test_get_interface_by_interface_name(self, owner, test_data):
        first_interface = owner.get_interface(interface_name=test_data["names"][0])
        second_interface = owner.get_interface(interface_name=test_data["names"][1])
        assert first_interface.pci_device == test_data["pci_device"]
        assert second_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address == test_data["pci_addresses"][0]
        assert second_interface.pci_address == test_data["pci_addresses"][1]
        assert first_interface.name == test_data["names"][0]
        assert second_interface.name == test_data["names"][1]

    def test_get_interfaces_by_interface_names(self, owner, test_data):
        interfaces = owner.get_interfaces(interface_names=test_data["names"])
        first_interface = interfaces[0]
        second_interface = interfaces[1]
        assert first_interface.pci_device == test_data["pci_device"]
        assert second_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address == test_data["pci_addresses"][0]
        assert second_interface.pci_address == test_data["pci_addresses"][1]
        assert first_interface.name == test_data["names"][0]
        assert second_interface.name == test_data["names"][1]

    def test_get_interface_by_family(self, owner, test_data):
        first_interface = owner.get_interface(family=test_data["family"], interface_index=0)
        second_interface = owner.get_interface(family=test_data["family"], interface_index=1)
        assert first_interface.pci_device == test_data["pci_device"]
        assert second_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address == test_data["pci_addresses"][0]
        assert second_interface.pci_address == test_data["pci_addresses"][1]
        assert first_interface.name == test_data["names"][0]
        assert second_interface.name == test_data["names"][1]

    def test_get_interfaces_by_family(self, owner, test_data):
        first_interface = owner.get_interfaces(family=test_data["family"], interface_indexes=[0])[0]
        second_interface = owner.get_interfaces(family=test_data["family"], interface_indexes=[1])[0]
        assert first_interface.pci_device == test_data["pci_device"]
        assert second_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address == test_data["pci_addresses"][0]
        assert second_interface.pci_address == test_data["pci_addresses"][1]
        assert first_interface.name == test_data["names"][0]
        assert second_interface.name == test_data["names"][1]

    def test_get_interfaces_by_family_all_default(self, owner, test_data):
        interfaces = owner.get_interfaces(family=test_data["family"])
        first_interface = interfaces[0]
        second_interface = interfaces[1]
        assert first_interface.pci_device == test_data["pci_device"]
        assert second_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address == test_data["pci_addresses"][0]
        assert second_interface.pci_address == test_data["pci_addresses"][1]
        assert first_interface.name == test_data["names"][0]
        assert second_interface.name == test_data["names"][1]

    def test_get_interface_by_speed(self, owner, test_data):
        first_interface = owner.get_interface(speed=test_data["speed"], interface_index=0)
        second_interface = owner.get_interface(speed=test_data["speed"], interface_index=1)
        assert first_interface.pci_device == test_data["pci_device"]
        assert second_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address == test_data["pci_addresses"][0]
        assert second_interface.pci_address == test_data["pci_addresses"][1]
        assert first_interface.name == test_data["names"][0]
        assert second_interface.name == test_data["names"][1]

    def test_get_interfaces_by_speed(self, owner, test_data):
        first_interface = owner.get_interfaces(speed=test_data["speed"], interface_indexes=[0])[0]
        second_interface = owner.get_interfaces(speed=test_data["speed"], interface_indexes=[1])[0]
        assert first_interface.pci_device == test_data["pci_device"]
        assert second_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address == test_data["pci_addresses"][0]
        assert second_interface.pci_address == test_data["pci_addresses"][1]
        assert first_interface.name == test_data["names"][0]
        assert second_interface.name == test_data["names"][1]

    def test_get_interfaces_by_speed_all_default(self, owner, test_data):
        interfaces = owner.get_interfaces(speed=test_data["speed"])
        first_interface = interfaces[0]
        second_interface = interfaces[1]
        assert first_interface.pci_device == test_data["pci_device"]
        assert second_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address == test_data["pci_addresses"][0]
        assert second_interface.pci_address == test_data["pci_addresses"][1]
        assert first_interface.name == test_data["names"][0]
        assert second_interface.name == test_data["names"][1]

    def test_get_interfaces_random_from_system(self, owner, test_data):
        first_interface = owner.get_interfaces(random_interface=True)[0]
        assert first_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address in test_data["pci_addresses"]
        assert first_interface.name in test_data["names"]

    def test_get_interfaces_random_from_adapter(self, owner, test_data):
        first_interface = owner.get_interfaces(pci_device=test_data["pci_device"], random_interface=True)[0]
        assert first_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address in test_data["pci_addresses"]
        assert first_interface.name in test_data["names"]

    def test_get_interfaces_all_from_system(self, owner, test_data):
        first_interface, second_interface = owner.get_interfaces(all_interfaces=True)
        assert first_interface.pci_device == test_data["pci_device"]
        assert second_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address == test_data["pci_addresses"][0]
        assert second_interface.pci_address == test_data["pci_addresses"][1]
        assert first_interface.name == test_data["names"][0]
        assert second_interface.name == test_data["names"][1]

    def test_get_interfaces_all_from_adapter(self, owner, test_data):
        first_interface, second_interface = owner.get_interfaces(
            pci_device=test_data["pci_device"], all_interfaces=True
        )
        assert first_interface.pci_device == test_data["pci_device"]
        assert second_interface.pci_device == test_data["pci_device"]
        assert first_interface.pci_address == test_data["pci_addresses"][0]
        assert second_interface.pci_address == test_data["pci_addresses"][1]
        assert first_interface.name == test_data["names"][0]
        assert second_interface.name == test_data["names"][1]

    def test_unify_speed_str_valid_input(self, owner):
        speed_examples = ["@40G", "@40g", "40", "40G", "40g", "40giga", "40Giga", "40GIGA", "40Gb"]
        for speed in speed_examples:
            assert owner._unify_speed_str(speed) == "@40G"

    def test_unify_speed_str_invalid_input(self, owner):
        invalid_input = "some_input"
        with pytest.raises(
            ValueError,
            match=re.escape(f"Speed format {invalid_input} not matching any of acceptable formats."),
        ):
            owner._unify_speed_str(invalid_input)


class TestNetworkAdapterOwnerCreation:
    def test_linux_owner_created(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.LINUX

        assert isinstance(NetworkAdapterOwner(connection=conn), LinuxNetworkAdapterOwner)

    def test_windows_owner_created(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.WINDOWS

        assert isinstance(NetworkAdapterOwner(connection=conn), WindowsNetworkAdapterOwner)

    def test_freebsd_owner_created(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.FREEBSD

        assert isinstance(NetworkAdapterOwner(connection=conn), FreeBSDNetworkAdapterOwner)

    def test_unsupported_os(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.EFISHELL

        with pytest.raises(NetworkAdapterConnectedOSNotSupported):
            NetworkAdapterOwner(connection=conn)

    def test_ordinary_constructor_os_supported_ok(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.LINUX

        assert isinstance(LinuxNetworkAdapterOwner(connection=conn), LinuxNetworkAdapterOwner)

    def test_ordinary_constructor_os_supported_fail(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.WINDOWS
        with pytest.raises(UnexpectedOSException):
            LinuxNetworkAdapterOwner(connection=conn)


_pci_address = PCIAddress(0000, 24, 00, 0)
_pci_device = PCIDevice("8086", "1563", "8086", "35d4")
_interface_names = ["eth1", "eth2"]
_family = "SGVL"
_speed = "@10G"


class TestNetworkAdapterOwner:
    @pytest.fixture()
    def owner(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.LINUX

        return NetworkAdapterOwner(connection=conn)

    @pytest.mark.parametrize(
        "test_data",
        [
            {"pci_address": _pci_address, "pci_device": _pci_device},
            {"pci_address": _pci_address, "interface_names": _interface_names},
            {"interface_names": _interface_names, "family": _family},
            {"pci_device": _pci_device, "family": _family, "speed": _speed},
            {"pci_address": _pci_address, "speed": _speed},
        ],
    )
    def test_validate_filtering_args_invalid(self, owner, test_data):
        with pytest.raises(NetworkAdapterIncorrectData):
            owner._validate_filtering_args(**test_data)

    def test_validate_filtering_args_valid(self, owner):
        owner._validate_filtering_args(pci_address=_pci_address)
        owner._validate_filtering_args(pci_device=_pci_device)
        owner._validate_filtering_args(speed=_speed)
        owner._validate_filtering_args(family=_family)
        owner._validate_filtering_args(interface_names=_interface_names)
        owner._validate_filtering_args(family=_family, speed=_speed)

    _interfaces_info = [
        InterfaceInfo(pci_address=_pci_address, pci_device=_pci_device, name=_interface_names[0]),
        InterfaceInfo(pci_address=_pci_address, pci_device=_pci_device, name=_interface_names[1]),
        InterfaceInfo(
            pci_address=_pci_address, pci_device=PCIDevice("8086", "1111", "8086", "35d4"), name=_interface_names[0]
        ),
        InterfaceInfo(
            pci_address=_pci_address, pci_device=PCIDevice("8086", "1111", "8086", "35d4"), name=_interface_names[1]
        ),
        InterfaceInfo(pci_address=PCIAddress(0000, 11, 00, 0), pci_device=_pci_device, name=_interface_names[0]),
        InterfaceInfo(pci_address=PCIAddress(0000, 11, 00, 0), pci_device=_pci_device, name=_interface_names[1]),
        InterfaceInfo(
            pci_address=PCIAddress(0000, 11, 00, 0),
            pci_device=PCIDevice("8086", "1111", "8086", "35d4"),
            name=_interface_names[0],
        ),
        InterfaceInfo(
            pci_address=PCIAddress(0000, 11, 00, 0),
            pci_device=PCIDevice("8086", "1111", "8086", "35d4"),
            name=_interface_names[1],
        ),
    ]

    def test_filter_interfaces_info(self, owner):
        filtered = owner._filter_interfaces_info(self._interfaces_info)
        assert len(filtered) == 8

        filtered = owner._filter_interfaces_info(self._interfaces_info, interface_names=_interface_names)
        assert len(filtered) == 8

        filtered = owner._filter_interfaces_info(self._interfaces_info, pci_address=_pci_address)
        assert len(filtered) == 4
        assert filtered[0].pci_address == _pci_address
        assert filtered[1].pci_address == _pci_address
        assert filtered[2].pci_address == _pci_address
        assert filtered[3].pci_address == _pci_address

        filtered = owner._filter_interfaces_info(self._interfaces_info, pci_device=_pci_device)
        assert len(filtered) == 4
        assert filtered[0].pci_device == _pci_device
        assert filtered[1].pci_device == _pci_device
        assert filtered[2].pci_device == _pci_device
        assert filtered[3].pci_device == _pci_device

        filtered = owner._filter_interfaces_info(self._interfaces_info, speed=_speed)
        assert len(filtered) == 4
        assert filtered[0].pci_device == _pci_device
        assert filtered[1].pci_device == _pci_device
        assert filtered[2].pci_device == _pci_device
        assert filtered[3].pci_device == _pci_device

        filtered = owner._filter_interfaces_info(self._interfaces_info, family=_family)
        assert len(filtered) == 4
        assert filtered[0].pci_device == _pci_device
        assert filtered[1].pci_device == _pci_device
        assert filtered[2].pci_device == _pci_device
        assert filtered[3].pci_device == _pci_device

        filtered = owner._filter_interfaces_info(self._interfaces_info, pci_address=_pci_address, interface_indexes=[0])
        assert len(filtered) == 1
        assert filtered[0] == self._interfaces_info[0]

        filtered = owner._filter_interfaces_info(self._interfaces_info, pci_address=_pci_address, random_interface=True)
        assert len(filtered) == 1
        assert filtered[0].pci_address == _pci_address


class TestSortedInterfaces:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(SSHConnection)
        connection.get_os_name.return_value = OSName.LINUX
        host = NetworkAdapterOwner(connection=connection)
        yield host
        mocker.stopall()

    @pytest.fixture()
    def interfaces(self, mocker):
        connection = mocker.create_autospec(SSHConnection)
        connection.get_os_name.return_value = OSName.LINUX
        interfaces = []
        interfaces.append(
            LinuxNetworkInterface(
                connection=connection,
                owner=None,
                interface_info=InterfaceInfo(
                    name="eth0", pci_address=PCIAddress(data="0000:18:00.0"), pci_device=PCIDevice(data="8086:1592")
                ),
            )
        )
        interfaces.append(
            LinuxNetworkInterface(
                connection=connection,
                owner=None,
                interface_info=InterfaceInfo(name="eth1", pci_address=PCIAddress(data="0000:10:00.0")),
            )
        )
        interfaces.append(
            LinuxNetworkInterface(
                connection=connection,
                owner=None,
                interface_info=InterfaceInfo(name="eth2", pci_address=PCIAddress(data="0000:20:00.0")),
            )
        )
        interfaces.append(
            LinuxNetworkInterface(
                connection=connection,
                owner=None,
                interface_info=InterfaceInfo(name="eth3", pci_address=PCIAddress(data="0000:17:00.0")),
            )
        )
        yield interfaces
        mocker.stopall()

    def test_sorted_interfaces(self, mocker, owner, interfaces):
        expected_interfaces = [interfaces[1], interfaces[3], interfaces[0], interfaces[2]]
        mocker.patch(
            "mfd_network_adapter.network_adapter_owner.base.NetworkAdapterOwner.get_interfaces",
            mocker.create_autospec(NetworkAdapterOwner.get_interfaces, return_value=interfaces),
        )
        assert sorted(interfaces) == expected_interfaces

    def test_sorted_interfaces_error(self, mocker, interfaces):
        interfaces.append("Incorrect Object")
        with pytest.raises(
            NetworkInterfaceIncomparableObject, match="Incorrect object passed for comparison with PCIAddress"
        ):
            sorted(interfaces)
