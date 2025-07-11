# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for link feature for Linux."""

import logging
import re
import time
from typing import Dict, List, Union, TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_ethtool import Ethtool
from mfd_kernel_namespace import add_namespace_call_command

from .base import BaseFeatureLink
from .data_structures import AutoNeg, DuplexType, LinkState, Speed, LINUX_SPEEDS
from ...exceptions import LinkException, SpeedDuplexException, IPFeatureException

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxLink(BaseFeatureLink):
    """Linux class for link feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize LinuxLink.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._ethtool = Ethtool(connection=connection)

    def set_link(self, state: LinkState) -> None:
        """
        Set link up or down for network port.

        :param state: LinkState attribute.
        :raises LinkException: if command execution failed.
        """
        state_name = state.name.lower()
        cmd = f"ip link set {self._interface().name} {state_name}"
        self._connection.execute_command(
            add_namespace_call_command(cmd, namespace=self._interface().namespace), custom_exception=LinkException
        )

    def get_link(self) -> LinkState:
        """
        Get link status for network port.

        :raises LinkException: if command execution failed.
        :return: LinkState attribute.
        """
        cmd = f"ip link show {self._interface().name}"
        output = self._connection.execute_command(
            add_namespace_call_command(cmd, namespace=self._interface().namespace), custom_exception=LinkException
        ).stdout

        state = re.findall(r"state (DOWN|UP)", output)[0]
        if state == "DOWN" or re.findall("NO-CARRIER", output):
            return LinkState.DOWN
        return LinkState.UP

    def get_link_speed(self) -> Union[str, None]:
        """
        Get link speed.

        :raises LinkException: if command execution failed.
        :return: link speed (for example 10000Mb/s), None if link speed cannot be determined.
        """
        cmd = f"ethtool {self._interface().name}"
        output = self._connection.execute_command(
            add_namespace_call_command(cmd, namespace=self._interface().namespace), custom_exception=LinkException
        ).stdout

        for dev_features in output.splitlines():
            try:
                if "Speed" not in dev_features:
                    continue
                link_speed = dev_features.split(":")[-1].strip()
                if "unknown!" in link_speed.casefold():
                    break
                else:
                    return link_speed
            except ValueError:
                raise Exception("Unable to determine the link speed")
        logger.log(level=log_levels.MODULE_DEBUG, msg="Link speed not found")

    def get_index(self) -> int:
        """
        Parse ip link command output to receive index.

        :raises LinkException: if command execution failed.
        :return: index of adapter.
        """
        cmd = f"ip link show dev {self._interface().name}"
        output = self._connection.execute_command(
            add_namespace_call_command(cmd, namespace=self._interface().namespace), custom_exception=LinkException
        ).stdout
        index = output.split(":")[0]
        return int(index)

    def link_off_xdp(self) -> None:
        """
        Link off XDP application from device.

        :raises LinkException: if command execution failed.
        """
        cmd = f"ip link set dev {self._interface().name} xdp off"
        self._connection.execute_command(
            add_namespace_call_command(cmd, namespace=self._interface().namespace), custom_exception=LinkException
        )

    def get_speed_duplex(self) -> Dict[str, Union[Speed, DuplexType]]:
        """Get speed and duplex setting at once.

        :return: dict: Indicating the speed and duplex pertaining Speed and DuplexType Enum
        :raises SpeedDuplexException: When unable to determine speed and/or duplex type
        """
        output = self._ethtool.get_standard_device_info(device_name=self._interface().name)
        """
        output:
            link_detected=["yes"],
            speed=["100000Mb/s"],
            duplex=["Full"],
        """
        tokens = {"Speed": output.speed[0], "Duplex": output.duplex[0], "Link detected": output.link_detected[0]}
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Speed: {tokens['Speed']}, Duplex: {tokens['Duplex']}, Link: {tokens['Link detected']}",
        )

        if tokens["Speed"] in ("Unknown!", None) or tokens["Duplex"] in ("Unknown!", None):
            raise SpeedDuplexException(
                f"Unable to fetch Speed and/or Duplex values for {self._interface().name}. Ethtool output: {output}"
            )

        speed_val = re.match(r"(?P<speed>\d+)(?P<unit>\D)", tokens["Speed"])
        speed = next((i for i in LINUX_SPEEDS if LINUX_SPEEDS[i] == speed_val.group("speed")), None)
        return {"speed": speed, "duplex": DuplexType(tokens["Duplex"].lower())}

    def get_available_speed(self) -> List[str]:
        """Get all available speeds or all supported speeds for the interface.

        :return: list of available speed/duplex
        """
        output = self._ethtool.get_standard_device_info(device_name=self._interface().name)
        return output.advertised_link_modes

    def set_speed_duplex(self, speed: Speed, duplex: DuplexType, autoneg: AutoNeg = AutoNeg.NONE) -> None:
        """Set speed, duplex and autonegotation. Setting speed or duplex to auto sets autonegotiation on.

        :param speed: speed to set
        :param duplex: duplex type
        :param autoneg: Autonegotiate of link speed and duplex.
        """
        if speed is LINUX_SPEEDS[Speed.AUTO] or duplex is DuplexType.AUTO:
            params = "autoneg on"
        else:
            params = (
                f"speed {LINUX_SPEEDS[speed]} duplex {duplex.value}"
                f"{' autoneg on' if autoneg is AutoNeg.ON else ''}{' autoneg off' if autoneg is AutoNeg.OFF else ''}"
            )
        self._ethtool.change_generic_options(
            device_name=self._interface().name,
            param_name=params,
            param_value="",
            namespace=self._interface().namespace,
        )
        self.set_link(LinkState.DOWN)
        time.sleep(1)
        self.set_link(LinkState.UP)

    def reset_interface(self) -> None:
        """
        Reset the PCI device.

        :raises IPFeatureException: If interface doesn't have a pci address.
        """
        pci_address = self._interface()._interface_info.pci_address
        if pci_address is None:
            raise IPFeatureException(f"No pci address found for {self._interface().name}")
        self._connection.execute_command(
            (
                "echo 1 > /sys/bus/pci/devices/0000"
                rf"\:{pci_address.bus:02x}\:{pci_address.slot:02x}.{pci_address.func:x}/reset"
            ),
            shell=True,
        )

    def is_auto_negotiation(self) -> bool:
        """
        Check whether the interface is in auto negotiation mode.

        :return: True if auto negotiation is enabled, False otherwise.
        """
        info = self._ethtool.get_standard_device_info(device_name=self._interface().name)
        if hasattr(info, "auto_negotiation"):
            return info.auto_negotiation[0] == "on"
        return False
