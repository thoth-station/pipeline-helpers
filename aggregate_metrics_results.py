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

"""This script run in a pipeline task to aggreagate metrics for a AI model deployed."""

import os
import logging
import json

import pandas as pd
from thoth.pipeline_helpers.common import create_s3_adapter

_DEBUG_LEVEL = bool(int(os.getenv("DEBUG_LEVEL", 0)))

if _DEBUG_LEVEL:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

_LOGGER = logging.getLogger("thoth.post_process_metrics")

DEPLOYMENT_NAMESPACE = os.getenv("PIPELINE_HELPERS_DEPLOYMENT_NAMESPACE", "aicoe-ci")
PR_FILE_PATH = os.getenv("PIPELINE_HELPERS_PR_FILE_PATH", "/workspace/pr/pr.json")
MAX_LIMIT_RESULTS = int(os.getenv("PIPELINE_HELPERS_MAX_LIMIT_RESULTS", 10))


def post_process_metrics() -> None:
    """Post process gathered metrics on AI model deployed."""
    with open(PR_FILE_PATH) as f:
        pr_info = json.load(f)

    repo = pr_info["Base"]["Repo"]["FullName"]

    try:
        ceph_adapter = create_s3_adapter(
            ceph_bucket_prefix="data",
            deployment_name=DEPLOYMENT_NAMESPACE,
            repo=repo,
        )
        ceph_adapter.connect()
        is_connected = True
    except Exception as exc:
        _LOGGER.warning(exc)
        is_connected = False

    # All metrics
    metrics_data: dict = {}
    metrics_data["info_metrics"] = []
    metrics_data["model_application_metrics"] = []
    metrics_data["platform_metrics"] = []

    _LOGGER.info(f"Limit of results shown is set to {MAX_LIMIT_RESULTS}!")

    if is_connected:
        for document_id in ceph_adapter.get_document_listing():
            if "processed_metrics" in document_id:
                metrics_retrieved = ceph_adapter.retrieve_document(document_id)
                _LOGGER.info(f"Retrieved data for {document_id}")
                _LOGGER.debug(f"info_metrics: {metrics_retrieved['info_metrics']}")
                _LOGGER.debug(f"model_application_metrics: {metrics_retrieved['model_application_metrics']}")
                _LOGGER.debug(f"platform_metrics: {metrics_retrieved['platform_metrics']}")
                metrics_retrieved["model_application_metrics"]["namespace deployment"] = metrics_retrieved[
                    "info_metrics"
                ]["namespace deployment"]
                metrics_retrieved["model_application_metrics"]["test URL"] = metrics_retrieved["info_metrics"][
                    "test URL"
                ]
                metrics_data["model_application_metrics"].append(metrics_retrieved["model_application_metrics"])
                metrics_retrieved["platform_metrics"]["model_version"] = metrics_retrieved["model_application_metrics"][
                    "model_version"
                ]
                metrics_data["platform_metrics"].append(metrics_retrieved["platform_metrics"])

    else:
        _LOGGER.info("Could not connect to Ceph to retrieve object stored!")

    _LOGGER.info(f"Processed data to be stored: {metrics_data}")

    # Store on ceph
    if is_connected:
        ceph_adapter.store_document(metrics_data, "aggregated_metrics")

    # Store locally for next step
    with open("pr-comment", "w") as pr_comment:
        report = ""

        report += "# AICoE CI results"

        if is_connected:
            if len(metrics_data["model_application_metrics"]) <= MAX_LIMIT_RESULTS:
                df_metrics = pd.DataFrame(metrics_data["model_application_metrics"])
                df_platform = pd.DataFrame(metrics_data["platform_metrics"])
            else:
                df_metrics = pd.DataFrame(metrics_data["model_application_metrics"][: MAX_LIMIT_RESULTS - 1])
                df_platform = pd.DataFrame(metrics_data["platform_metrics"][: MAX_LIMIT_RESULTS - 1])

            report += "\n\n## Model and application metrics"
            report += (
                "\n\nThe following table shows gathered metrics for model and application on your deployed models."
            )
            report += "\n\n" + df_metrics.to_markdown(index=False)

            report += "\n\n## Platform metrics"
            report += "\n\nThe following table shows gathered metrics from platform on your deployed models."
            report += "\n\n" + df_platform.to_markdown(index=False)
        else:
            report += (
                "\n\nPipeline is not able to connect to Ceph to retrieve objects stored, contact Thoth maintainers!"
            )

        _LOGGER.info(f"PR comment is:\n{report}")
        pr_comment.write(report)


if __name__ == "__main__":
    post_process_metrics()
