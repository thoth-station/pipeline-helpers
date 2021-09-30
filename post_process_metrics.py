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

from thoth.pipeline_helpers.common import create_s3_adapter

_DEBUG_LEVEL = bool(int(os.getenv("DEBUG_LEVEL", 0)))

if _DEBUG_LEVEL:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

_LOGGER = logging.getLogger("thoth.post_process_metrics")

DEPLOYMENT_NAMESPACE = os.getenv("PIPELINE_HELPERS_DEPLOYMENT_NAMESPACE", "aicoe-ci")
OVERLAY_NAME = os.getenv("PIPELINE_HELPERS_OVERLAY_NAME")
METRICS_FILE_PATH = os.getenv("PIPELINE_HELPERS_METRICS_FILE_PATH", "metrics.json")
PLATFORM_METRICS_FILE_PATH = os.getenv("PIPELINE_HELPERS_PLATFORM_METRICS_FILE_PATH", "platform_metrics.json")
PR_FILE_PATH = os.getenv("PIPELINE_HELPERS_PR_FILE_PATH", "/workspace/pr/pr.json")
PR_REPO_URL = os.environ["REPO_URL"]
PR_COMMIT_SHA = os.environ["COMMIT_SHA"]


def post_process_metrics() -> None:
    """Post process gathered metrics on AI model deployed."""
    with open(PR_FILE_PATH) as f:
        pr_info = json.load(f)

    repo = pr_info["Base"]["Repo"]["FullName"]

    document_id = "processed_metrics"
    model_version = f"pr-{pr_info['Number']}"

    overlay_name = None

    if OVERLAY_NAME:
        model_version = model_version + f"-{OVERLAY_NAME}"
        overlay_name = OVERLAY_NAME

    with open(METRICS_FILE_PATH) as f:
        metrics = json.load(f)
        metrics["model_version"] = model_version

    # Platform metrics
    with open(PLATFORM_METRICS_FILE_PATH) as f:
        platform_metrics = json.load(f)

    try:
        ceph_adapter = create_s3_adapter(
            ceph_bucket_prefix="data",
            deployment_name=DEPLOYMENT_NAMESPACE,
            repo=repo,
            pr_number=str(pr_info["Number"]),
            overlay_name=overlay_name,
        )
        ceph_adapter.connect()
        is_connected = True
    except Exception as exc:
        _LOGGER.warning(exc)
        is_connected = False

    document_exist = False

    if is_connected:
        # Check if document exists
        document_exist = ceph_adapter.document_exists(document_id=document_id)
        _LOGGER.info(f"Document retrieval status: {document_exist}")

    # All metrics
    metrics_data = {}

    if document_exist:
        _LOGGER.info(f"Found data for {repo} in {document_id}!")

        metrics_data = ceph_adapter.retrieve_document(document_id)
        _LOGGER.info(f"Retrieved data: {metrics_data}")
    else:
        _LOGGER.info(f"Did not find data for {repo} in {document_id}!")

    info_metrics = {
        "test URL": f"{PR_REPO_URL}/blob/{PR_COMMIT_SHA}/features",
        "namespace deployment": DEPLOYMENT_NAMESPACE,
    }

    metrics_data["model_version"] = model_version
    metrics_data["info_metrics"] = info_metrics
    metrics_data["model_application_metrics"] = metrics
    metrics_data["platform_metrics"] = platform_metrics

    _LOGGER.info(f"Processed data to be stored: {metrics_data}")

    # Store on ceph
    if is_connected:
        ceph_adapter.store_document(metrics_data, document_id)


if __name__ == "__main__":
    post_process_metrics()
