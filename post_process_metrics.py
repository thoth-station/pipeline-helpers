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

import pandas as pd
from thoth.pipeline_helpers.common import create_s3_adapter

_DEBUG_LEVEL = bool(int(os.getenv("DEBUG_LEVEL", 0)))

if _DEBUG_LEVEL:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

_LOGGER = logging.getLogger("thoth.post_process_metrics")

METRICS_FILE_PATH = os.getenv("PIPELINE_HELPERS_METRICS_FILE_PATH", "metrics.json")
PR_FILE_PATH = os.getenv("PIPELINE_HELPERS_PR_FILE_PATH", "/workspace/pr/pr.json")
PR_REPO_URL = os.environ["REPO_URL"]

def post_process_metrics() -> None:
    """Post process gathered metrics on AI model deployed."""
    with open(PR_FILE_PATH) as f:
        pr_info = json.load(f)

    repo = pr_info["Base"]["Repo"]["FullName"]

    ceph_adapter = create_s3_adapter(ceph_bucket_prefix="data", repo=repo)
    ceph_adapter.connect()

    document_id = "processed_metrics"

    with open(METRICS_FILE_PATH) as f:
        metrics = json.load(f)
        metrics["model_version"] = f"pr-{pr_info['Number']}"

    document_exist = ceph_adapter.document_exists(document_id=document_id)

    _LOGGER.info(f"Document retrieval status: {document_exist}")

    metrics_data = {}

    if document_exist:
        _LOGGER.info(f"Found data for {repo} in {document_id}!")

        metrics_data = ceph_adapter.retrieve_document(document_id)
        _LOGGER.info(f"Retrieved data: {metrics_data}")
    else:
        _LOGGER.info(f"Did not find data for {repo} in {document_id}!")

    metrics_data[metrics["model_version"]] = metrics

    _LOGGER.info(f"Processed data to be stored: {metrics_data}")

    # Store on ceph
    ceph_adapter.store_document(metrics_data, document_id)

    # Store locally for next step
    with open("pr-comment", "w") as pr_comment:
        report = ""

        df = pd.DataFrame([model_v for model_v in metrics_data.values()])
        report += "The following table shows gathered metrics on your deployed models."
        report += f"Test used to collect metrics can be found here {PR_REPO_URL}/features."
        report += "\n\n" + df.to_markdown(index=False)

        _LOGGER.info(f"PR comment is:\n{report}")
        pr_comment.write(report)


if __name__ == "__main__":
    post_process_metrics()
