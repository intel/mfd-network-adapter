# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Route feature."""

from typing import Union

from .base import BaseRouteFeature
from .freebsd import FreeBSDRoute
from .linux import LinuxRoute
from .windows import WindowsRoute

RouteFeatureType = Union[BaseRouteFeature, FreeBSDRoute, LinuxRoute, WindowsRoute]
