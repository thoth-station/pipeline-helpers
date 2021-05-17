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

"""This script run in a pipeline task to post process gathered metrics for a AI model deployed."""

import os
import logging
import json

from thoth.pipeline_helpers.common import connect_to_ceph

_DEBUG_LEVEL = bool(int(os.getenv("DEBUG_LEVEL", 0)))

if _DEBUG_LEVEL:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

_LOGGER = logging.getLogger("thoth.post_process_metrics")

METRICS_FILE_PATH = os.getenv("PIPELINE_HELPERS_METRICS_FILE_PATH", "metrics.json")
PR_FILE_PATH = os.getenv("PIPELINE_HELPERS_PR_FILE_PATH", "/workspace/pr/pr.json")


def post_process_metrics() -> None:
    """Post process gathered metrics on AI model deployed."""
    ceph_adapter = connect_to_ceph(ceph_bucket_prefix="data")

    with open(PR_FILE_PATH) as f:
        pr_info = json.load(f)

    repo = pr_info["Base"]["Repo"]["FullName"]

    ceph_adapter = connect_to_ceph(ceph_bucket_prefix="data", repo=repo)
    document_id = "processed_metrics"

    with open(METRICS_FILE_PATH) as f:
        metrics = json.load(f)
        metrics["model_version"] = f"pr-{pr_info['Number']}"

    document_exist = ceph_adapter.document_exists(document_id=document_id)

    _LOGGER.info(f"Document retrieval status: {document_exist}")

    retrieved_data = []

    if document_exist:

        retrieved_data = ceph_adapter.retrieve_document(document_id)
        _LOGGER.info(f"Retrieved data: {retrieved_data}")

    retrieved_data.append(metrics)

    _LOGGER.info(f"Processed data to be stored: {retrieved_data}")

    with open("processed_metrics.json", "w") as processed_metrics:
        json.dump(retrieved_data, processed_metrics, indent=2)


if __name__ == "__main__":
    post_process_metrics()
