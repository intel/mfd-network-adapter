# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

from mfd_connect import RPyCConnection
from mfd_typing import OSName

from mfd_network_adapter.api.utils.freebsd import convert_to_vf_config_format, update_num_vfs_in_config
from mfd_network_adapter.network_adapter_owner.freebsd import FreeBSDNetworkAdapterOwner

input_config = "[PF]\n\
device = ice0\n\
num_vfs = 3\n\
\n\
[DEFAULT]\n\
\n\
[VF-0]\n\
passthrough = true\n\
max-vlan-allowed = 10\n\
max-mac-filters = 20\n\
allow-promiscuous = true\n\
num-queues = 4\n\
mdd-auto-reset-vf = true\n\
\n\
[VF-1]\n\
passthrough = true\n\
max-vlan-allowed = 10\n\
max-mac-filters = 20\n\
allow-promiscuous = true\n\
num-queues = 4\n\
mdd-auto-reset-vf = true\n\
"

formatted_config = "PF {\n\
device : ice0\n\
num_vfs : 3\n\
}\n\
\n\
DEFAULT {\n\
}\n\
\n\
VF-0 {\n\
passthrough : true\n\
max-vlan-allowed : 10\n\
max-mac-filters : 20\n\
allow-promiscuous : true\n\
num-queues : 4\n\
mdd-auto-reset-vf : true\n\
}\n\
\n\
VF-1 {\n\
passthrough : true\n\
max-vlan-allowed : 10\n\
max-mac-filters : 20\n\
allow-promiscuous : true\n\
num-queues : 4\n\
mdd-auto-reset-vf : true\n\
}\
"

updated_num_vfs = "PF {\n\
device : ice0\n\
num_vfs : 6\n\
}\n\
\n\
DEFAULT {\n\
}\n\
\n\
VF-0 {\n\
passthrough : true\n\
max-vlan-allowed : 10\n\
max-mac-filters : 20\n\
allow-promiscuous : true\n\
num-queues : 4\n\
mdd-auto-reset-vf : true\n\
}\n\
\n\
VF-1 {\n\
passthrough : true\n\
max-vlan-allowed : 10\n\
max-mac-filters : 20\n\
allow-promiscuous : true\n\
num-queues : 4\n\
mdd-auto-reset-vf : true\n\
}\
"


class TestFreeBSDAPI:
    @staticmethod
    def owner(mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.FREEBSD
        return FreeBSDNetworkAdapterOwner(connection=conn)

    def test_convert_to_config_format(self):
        converted_config = convert_to_vf_config_format(input_config)
        assert converted_config == formatted_config

    def test_update_num_vfs_in_config(self):
        assert update_num_vfs_in_config(formatted_config, 6) == updated_num_vfs
