# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for enhanced data path feature esxi feature."""

import re
from typing import TYPE_CHECKING


from mfd_network_adapter.network_interface.feature.ens.base import BaseFeatureENS
from mfd_network_adapter.network_interface.feature.ens.consts import ENS_DATA_REGEX_TEMPLATE

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface
    from mfd_connect.base import ConnectionCompletedProcess


class ESXiFeatureENS(BaseFeatureENS):
    """Class for ENS feature on ESXi."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize ESXiFeatureENS.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

    def _check_if_nsxt_present(self, result: "ConnectionCompletedProcess") -> bool:
        """
        Check if NSX-T is present on the host.

        :param result: ConnectionCompletedProcess object
        :return: True if NSX-T is present, False if not.
        """
        return not (result.return_code != 0 or "esxcfg-nics: invalid option -- 'e'" in result.stdout)

    def is_ens_capable(self) -> bool:
        """
        Get vmnic ens capability.

        - esxcg-nics -e is supported only on hosts with NSX-T libs.

        :return: True if a driver is ENS capable, False if not.
        """
        result = self._get_ens_settings()
        if not self._check_if_nsxt_present(result):
            return False
        found = re.search(
            ENS_DATA_REGEX_TEMPLATE.format(interface_name=self._interface().name),
            result.stdout,
            re.I,
        )
        capable = found.group("ens_capable").strip().lower() if found else ""
        return capable == "true"

    def is_ens_enabled(self) -> bool:
        """
        Get vmnic ens status.

        - esxcg-nics -e is supported only on hosts with NSX-T libs.

        :return: True if driver is ENS enabled, False if not.
        """
        result = self._get_ens_settings()
        if not self._check_if_nsxt_present(result):
            service_name = self._interface().driver.get_drv_info(refresh=True).get("driver")
        else:
            found = re.search(
                ENS_DATA_REGEX_TEMPLATE.format(interface_name=self._interface().name),
                result.stdout,
                re.I,
            )
            if not found:
                return False
            service_name = found.group("driver")
            is_ens_str = found.group("ens_enabled")
            service_name = service_name + "_ens" if is_ens_str.lower() == "true" else service_name
        return service_name.endswith("_ens")

    def is_ens_unified_driver(self) -> bool:
        """
        Get driver unified status.

        :return: True if a driver is ENS unified, False if not.
        """
        service_name = self._interface().driver.get_drv_info(refresh=True).get("driver")
        return not service_name.endswith("_ens") and self.is_ens_enabled()

    def is_ens_interrupt_capable(self) -> bool:
        """
        Get vmnic ens interrupt capability.

        - esxcg-nics -e is supported only on hosts with NSX-T libs.

        :return: True if driver is ENS INTERRUPT capable, False if not.
        """
        result = self._get_ens_settings()
        if not self._check_if_nsxt_present(result):
            return False

        found = re.search(
            ENS_DATA_REGEX_TEMPLATE.format(interface_name=self._interface().name),
            result.stdout,
            re.I,
        )
        if not found:
            return False
        intr_capable = (
            intr_capable_value.strip().lower() if (intr_capable_value := found.group("ens_intr_capable")) else ""
        )
        return intr_capable == "true"

    def _get_ens_settings(self) -> "ConnectionCompletedProcess":
        """
        Get vmnic ens settings.

        :return: ConnectionCompletedProcess object
        """
        return self._connection.execute_command("esxcfg-nics -e", expected_return_codes=None, stderr_to_stdout=True)

    def is_ens_interrupt_enabled(self) -> bool:
        """
        Get vmnic ens interrupt status.

        - esxcg-nics -e is supported only on hosts with NSX-T libs.

        :return: True if a driver has ENS INTERRUPT enabled, False if not.
        """
        result = self._get_ens_settings()
        if not self._check_if_nsxt_present(result):
            return False

        found = re.search(
            ENS_DATA_REGEX_TEMPLATE.format(interface_name=self._interface().name),
            result.stdout,
            re.I,
        )
        if not found:
            return False
        intr_enabled = (
            intr_enabled_value.strip().lower() if (intr_enabled_value := found.group("ens_intr_enabled")) else ""
        )
        return intr_enabled == "true"
