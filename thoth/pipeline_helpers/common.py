#!/usr/bin/env python3
# pipeline-helpers
# Copyright(C) 2021 Francesco Murdaca
#
# This program is free software: you can redistribute it and / or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Common method for pipeline helpers task."""

import logging
import os
from thoth.storages import CephStore

_DEBUG_LEVEL = bool(int(os.getenv("DEBUG_LEVEL", 0)))

if _DEBUG_LEVEL:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

_LOGGER = logging.getLogger("thoth.gather_metrics")


def connect_to_ceph(ceph_bucket_prefix: str) -> CephStore:
    """Connect to Ceph to store deployment metrics for Thoth."""
    deployment_name = "aicoe-ci"

    prefix = f"{ceph_bucket_prefix}/{deployment_name}/deployment-metrics"
    ceph = CephStore(prefix=prefix)
    ceph.connect()
    return ceph
