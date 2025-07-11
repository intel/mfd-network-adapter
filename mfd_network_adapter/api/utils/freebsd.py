# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for utils FreeBSD static api."""

import re


def convert_to_vf_config_format(config: str) -> str:
    """
    Convert ConfigParser string to FreeBSD Virtual Function config format.

    :param config: Config string.
    :return: String containing formatted config content.
    """
    pattern = re.compile(r"\[(\w+-?\w*)\]\n((?:[^\[]*\n?)*)")
    matches = pattern.findall(config)
    result = ""

    for match in matches:
        section_name = match[0]
        section_content = match[1].strip()

        if section_name == "DEFAULT":
            result += "\nDEFAULT {\n}\n"
        else:
            formatted_content = section_content.replace("=", ":")
            result += f"\n{section_name} {{\n{formatted_content}\n}}\n"

    return result.strip()


def update_num_vfs_in_config(config: str, vfs_num: int) -> str:
    """
    Update num_vfs in config string.

    :param config: Config string
    :param vfs_num: Number of actual num_vfs
    :return: String that has updated number of Virtual Functions in the proper line.
    """
    pattern = r"num_vfs\s*:\s*(?P<num_vfs>\d+)"
    match = re.search(pattern, config)
    if match:
        old_value = match.group("num_vfs")
        new_pattern = rf"num_vfs\s*:\s*{re.escape(old_value)}"
        config = re.sub(new_pattern, f"num_vfs : {vfs_num}", config)
    return config
