# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for adapter owner for FreeBSD OS."""

import configparser
import io
import logging
import re
from ipaddress import IPv4Interface
from typing import List, Pattern, Iterator, Match, TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels, os_supported
from mfd_typing import PCIDevice, PCIAddress, OSName, VendorID, DeviceID, SubVendorID, SubDeviceID
from mfd_typing.network_interface import LinuxInterfaceInfo, InterfaceType, VlanInterfaceInfo

from .base import NetworkAdapterOwner
from .exceptions import NetworkAdapterNotFound
from ..api.utils.freebsd import update_num_vfs_in_config, convert_to_vf_config_format
from ..exceptions import VirtualFunctionCreationException

if TYPE_CHECKING:
    from pathlib import Path  # noqa: F401

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBSDNetworkAdapterOwner(NetworkAdapterOwner):
    """Class for handle owner of network adapters in FreeBSD systems."""

    __init__ = os_supported(OSName.FREEBSD)(NetworkAdapterOwner.__init__)

    _pci_address_core_regex = r"(?P<domain>[0-9a-f]+):(?P<bus>[0-9a-f]+):(?P<slot>[0-9a-f]+)"
    _full_pci_address_regex = rf"{_pci_address_core_regex}.(?P<func>[0-7]+)"

    def _get_regex_pattern(self) -> Pattern:
        """
        Get regex pattern based on FreeBSD version.

        :return: Pattern object
        """
        pattern_old = (
            r"(?P<name>\w+)(?:@)pci(?P<pci>\d+:\d+:\d+:\d+)"
            r"(?::\s+class=)(?P<class>\w+)"
            r"(?:\s+card=0x)(?P<subd>.{4})(?P<subvid>.{4})"
            r"(?:\s+chip=0x)(?P<did>.{4})(?P<vid>.{4})"
            r"(?:\s+rev=)(?P<rev>\w+)"
            r"(?:\s+hdr=)(?P<hdr>\w+)"
            r"(\n\s+vendor\s+=\s+\'(?P<vendor>.*)\')?"
            r"(\n\s+device\s+=\s+\'(?P<device>.*)\')?"
            r"(?:\n\s+class.*)?"
            r"(?:\n\s+subclass.*)?"
        )
        pattern_new = (
            r"(?P<name>\w+)"
            r"(?:@)pci(?P<pci>\d+:\d+:\d+:\d+)"
            r"(?::\s+class=)(?P<class>\w+)"
            r"(?:\s+rev=\w+)(?:\s+hdr=\w+)"
            r"(?:\s+vendor=)(?P<vid>\w+)"
            r"(?:\s+device=)(?P<did>\w+)"
            r"(?:\s+subvendor=)(?P<subvid>\w+)"
            r"(?:\s+subdevice=)(?P<subd>\w+)"
            r"(\n\s+vendor\s+=\s+\'(?P<vendor>.*)\')?"
            r"(\n\s+device\s+=\s+\'(?P<device>.*)\')?"
            r"(?:\n\s+class.*)?"
            r"(?:\n\s+subclass.*)?"
        )
        os_version = self._connection.execute_command("uname -K").stdout
        if int(os_version) < 1300085:
            pattern = re.compile(pattern_old, re.M)
        else:
            pattern = re.compile(pattern_new, re.M)
        return pattern

    def _get_output_from_pciconf(self) -> List:
        """
        Get output from pciconf command filtered by device class.

        :return: list of entries from command
        """
        entries = []
        output = self._connection.execute_command("pciconf -l -v").stdout
        for match in self._get_regex_pattern().finditer(output):
            if not match.group("class").startswith("0x02"):
                continue
            entries.append(match)
        return entries

    def _get_all_interfaces_info(self) -> List[LinuxInterfaceInfo]:
        """
        Get all interfaces info for each InterfaceType.

        :return: List of LinuxInterfaceInfo
        """
        info: List[LinuxInterfaceInfo] = []
        for match in self._get_output_from_pciconf():
            name = match.group("name")
            if name.startswith("virtio_pci") or name.startswith("mlx5_core"):
                result = self._connection.execute_command(
                    f"sysctl -a | grep -F ': {name}'", shell=True, expected_return_codes=None
                )
                if result.return_code != 0:
                    # If an error occurred while getting virtio_pci configuration
                    # - most probably it's not the interface we're looking for
                    continue
                name = self._virtio_mlx_wa_name(name, result.stdout)

            data = {
                "pci_device": PCIDevice(
                    VendorID(match.group("vid")),
                    DeviceID(match.group("did")),
                    SubVendorID(match.group("subvid")),
                    SubDeviceID(match.group("subd")),
                ),
                "pci_address": PCIAddress(data=match.group("pci")),
                "name": name,
                "installed": not name.startswith("none"),
                "branding_string": match.group("device").strip(),
                "interface_type": InterfaceType.VF
                if "virtual function" in match.group("device").casefold()
                else InterfaceType.PF,
            }
            info.append(LinuxInterfaceInfo(**data))

        info.extend(self._get_vlan_interfaces_data())

        inet_info_iterator = self._get_inet_information()
        self._mark_management_interface(info, inet_info_iterator)

        return info

    def _mark_management_interface(self, info: List[LinuxInterfaceInfo], inet_info: Iterator[Match[str]]) -> None:
        """
        Find and remove management interface from list.

        :param info: List of LinuxInterfaceInfo instances
        :param inet_info: Iterator with inet info matches
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg="Trying to find management interface.")
        for match in inet_info:
            if match.groupdict().get("inet") is None or "broadcast" not in match.group("flags").casefold():
                continue
            ip = re.search(
                r"(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) netmask (?P<netmask>0x[0-9A-Fa-f]+)", match.group("inet")
            )
            if ip and self.is_management_interface(IPv4Interface(ip.group("ip"))):
                for nic in info:
                    if nic.name == match.group("name"):
                        nic.interface_type = InterfaceType.MANAGEMENT
                        break
                break

    def _get_inet_information(self) -> Iterator[Match[str]]:
        """
        Get list of information about the interfaces from ifconfig.

        Gather name, flags, options and IP address.

        :return finditer matches from ifconfig inet
        """
        cmd = "ifconfig -a inet"
        result = self._connection.execute_command(cmd)
        return re.finditer(
            r"\s*(?P<name>\w+):\s+(flags=(?P<flags>.*))\n"
            r"\s+(options=(?P<options>.*))(?:\n\s+)?"
            r"(inet\s?(?P<inet>.*))?",
            result.stdout,
            re.MULTILINE,
        )

    @staticmethod
    def _virtio_mlx_wa_name(name: str, output: str) -> str:
        """
        Get workaround name for Mellanox or virtio KVM.

        :param name: Name of interface
        :param output: Output from sysctl and interface
        :return: Changed name
        """
        if name.startswith("mlx5_core"):
            logger.warning(msg="Workaround for Mellanox mlx5_core.")
            # workaround for mismatch in the naming of Mellanox interfaces in output of pciconf and ifconfig
            mlx_match = re.search(rf"dev.(?P<dev>\S+).(?P<num>\d+).conf.device_name: {name}", output)
            name = f"{mlx_match.group('dev')}{mlx_match.group('num')}"
        elif name.startswith("virtio_pci"):
            logger.warning(msg="Workaround for virtio.")
            # workaround for mismatch in the naming of KVM virtual interfaces in output of pciconf and ifconfig
            virtio_device_match = re.search(rf"dev.(?P<dev>\S+).(?P<num>\d+).%parent: {name}", output)
            name = f"{virtio_device_match.group('dev')}{virtio_device_match.group('num')}"
        else:
            logger.log(level=log_levels.MODULE_DEBUG, msg="Doesn't need to apply workaround for interface name.")
        return name

    def _get_vlan_interfaces_data(self) -> List[LinuxInterfaceInfo]:
        """
        Get data related with VLAN interfaces from ifconfig vlan.

        :return: List of LinuxInterfaceInfo including Vlan information
        """
        vlan_interfaces_data = []
        vlan_re = re.compile(
            r"\svlan: (?P<vlan_id>\d+)"
            r"(?:\svlanproto: \d+.\dq|\svlanpcp: \d+)(?:\svlanpcp: \d+)?"
            r"\sparent interface: (?P<parent>\w+)"
        )
        result = self._connection.execute_command("ifconfig -g vlan")
        for vlan_interface in result.stdout.splitlines():
            cmd = f"ifconfig {vlan_interface}"
            result = self._connection.execute_command(cmd)
            match = vlan_re.search(result.stdout)
            if not match:
                raise NetworkAdapterNotFound(f"Cannot get vlan id and parent device\n{result.stdout}")
            vlan_interfaces_data.append(
                LinuxInterfaceInfo(
                    interface_type=InterfaceType.VLAN,
                    vlan_info=VlanInterfaceInfo(parent=match.group("parent"), vlan_id=int(match.group("vlan_id"))),
                )
            )
        return vlan_interfaces_data

    def _load_config_file(
        self, interface_name: str, config_dir: "Path | str" = "/home/user", config_name: str | None = None
    ) -> bool:
        """
        Load config file into the system and create Virtual Functions.

        :param interface_name: Name of network interface
        :param config_dir: Directory where config file is stored
        :param config_name: Name of configuration file ex. iovctl.conf
        :return: True if config file was loaded into the system, False if not.
        """
        config_name = config_name if config_name else f"iovctl_{interface_name}.conf"
        return self._connection.execute_command(f"iovctl -C -f {config_dir}/{config_name}").return_code == 0

    def _verify_if_loaded_vfs_are_correct(self, vfs_count: int) -> bool:
        """
        Verify if number of created Virtual Functions are equal to number specified in the config file.

        :param vfs_count: Expected number of Virtual Functions
        :return: True if number of Virtual Functions is equal to vfs_count parameter, False if not.
        """
        interfaces = self._get_all_interfaces_info()
        vf_num = 0
        for interface in interfaces:
            if interface.interface_type is InterfaceType.VF:
                vf_num += 1
        return vf_num == vfs_count

    def add_vfs_to_config_file(
        self,
        interface_name: str,
        vfs_count: int,
        passthrough: bool = False,
        max_vlan_allowed: int | None = None,
        max_mac_filters: int | None = None,
        allow_promiscuous: bool = False,
        num_queues: int | None = None,
        mdd_auto_reset_vf: bool = False,
        config_dir: "Path | str" = "/home/user",
        mirror_src_vsi: int | None = None,
        config_name: str | None = None,
        mac_addr: tuple[str, ...] | None = None,
        allow_set_mac: bool = False,
        mac_anti_spoof: bool = True,
        **kwargs,
    ) -> None:
        """
        Add specified number of Virtual Functions to the conf file for the Physical Function.

        :param interface_name: Name of the interface representing Physical Function
        :param vfs_count: Number of Virtual Functions to be assigned
        :param passthrough: Enable or disable passthrough mode on Virtual Function
        :param max_vlan_allowed: Number of maximum vlan's that are allowed to be created on Virtual Function
        :param max_mac_filters: Number of maximum MAC filters that are allowed to be created on Virtual Function
        :param allow_promiscuous: Allow or disallow enabling of promiscuous mode on Virtual Function
        :param num_queues: Number of Rx/Tx queues that will be assigned to Virtual Function
        :param mdd_auto_reset_vf: Enable or disable auto reset of Virtual Function on MDD event
        :param config_dir: Directory where config file will be created
        :param mirror_src_vsi: Source VSI for mirroring
        :param config_name: Name of configuration file ex. iovctl.conf
        :param mac_addr: MAC address of the Virtual Function, tuple needs to be same length as vfs_count
        :param allow_set_mac: Allow or disallow setting MAC address on Virtual Function
        :param mac_anti_spoof: Enable or disable MAC anti-spoofing on Virtual Function, default in cfg is True
        :param kwargs: Additional arguments
        :return: None
        """
        macs = iter(mac_addr) if mac_addr else None
        config_name = config_name if config_name else f"iovctl_{interface_name}.conf"
        logger.log(level=log_levels.MFD_INFO, msg=f"Config file name: {config_name}")
        file = self._connection.path(f"{config_dir}/{config_name}")
        config = configparser.ConfigParser(default_section="DEF")
        config_string = io.StringIO()

        file_content = file.read_text()

        if file_content == "":
            config.add_section("PF")
            config["PF"] = {"device": interface_name, "num_vfs": vfs_count}
            config.add_section("DEFAULT")

        existing_vfs = file_content.count("VF-")

        for vf_num in range(existing_vfs, existing_vfs + vfs_count):
            config.add_section(f"VF-{vf_num}")
            if passthrough:
                config[f"VF-{vf_num}"]["passthrough"] = "true"
            if max_vlan_allowed is not None:
                config[f"VF-{vf_num}"]["max-vlan-allowed"] = str(max_vlan_allowed)
            if max_mac_filters is not None:
                config[f"VF-{vf_num}"]["max-mac-filters"] = str(max_mac_filters)
            if allow_set_mac:
                config[f"VF-{vf_num}"]["allow-set-mac"] = "true"
            if mac_addr is not None:
                config[f"VF-{vf_num}"]["mac-addr"] = str(next(macs))
            if allow_promiscuous:
                config[f"VF-{vf_num}"]["allow-promisc"] = "true"
            if num_queues is not None:
                config[f"VF-{vf_num}"]["num-queues"] = str(num_queues)
            if mdd_auto_reset_vf:
                config[f"VF-{vf_num}"]["mdd-auto-reset-vf"] = "true"
            if not mac_anti_spoof:
                config[f"VF-{vf_num}"]["mac-anti-spoof"] = "false"
            if mirror_src_vsi is not None:
                config[f"VF-{vf_num}"]["mirror-src-vsi"] = str(mirror_src_vsi)
            if kwargs:
                for key, value in kwargs.items():
                    config[f"VF-{vf_num}"][key.replace("_", "-")] = str(value).lower()
        config.write(config_string)
        config_string_value = convert_to_vf_config_format(config_string.getvalue())
        if existing_vfs > 0:
            config_string_value = file_content + config_string_value
            config_string_value = update_num_vfs_in_config(config_string_value, existing_vfs + vfs_count)
        file.write_text(config_string_value)

    def create_vfs(
        self,
        interface_name: str,
        vfs_count: int,
        config_dir: "Path | str" = "/home/user",
        config_name: str | None = None,
    ) -> None:
        """
        Create specified number of Virtual Functions based on the conf file for the Physical Function.

        :param interface_name: Name of the interface representing Physical Function
        :param vfs_count: Number of Virtual Functions to be assigned
        :param config_dir: Directory where config file is stored
        :param config_name: Name of configuration file ex. iovctl.conf
        :return: None
        """
        config_name = config_name if config_name else f"iovctl_{interface_name}.conf"
        if self._load_config_file(interface_name, config_name, config_dir):
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"Successfully loaded config file {config_dir}/{config_name}.",
            )
        else:
            raise VirtualFunctionCreationException(f"Could not load config file {config_dir}/{config_name}")
        if self._verify_if_loaded_vfs_are_correct(vfs_count):
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"Successfully created {vfs_count} VFs assigned to {interface_name} interface.",
            )
        else:
            raise VirtualFunctionCreationException(
                f"Could not create {vfs_count} VFs assigned to {interface_name} interface!"
            )

    def delete_vfs(
        self,
        interface_name: str,
        config_dir: "Path | str" = "/home/user",
        remove_conf: bool = True,
        config_name: str | None = None,
    ) -> None:
        """
        Delete all Virtual Functions assigned to the Physical Function.

        :param interface_name: Name of the interface representing Physical Function
        :param config_dir: Directory where config file is stored
        :param remove_conf: Decides whether conf file should be removed after deleting Virtual Functions
        :param config_name: Name of configuration file ex. iovctl.conf
        :return: None
        """
        config_name = config_name if config_name else f"iovctl_{interface_name}.conf"
        self._connection.execute_command(
            f"iovctl -D -f {config_dir}/{config_name}",
            expected_return_codes={0},
        )
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Successfully deleted all VFs assigned to {interface_name} interface.",
        )
        if remove_conf:
            self._connection.path(f"{config_dir}/{config_name}").unlink()
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"Successfully deleted config file {config_dir}/{config_name}.",
            )
