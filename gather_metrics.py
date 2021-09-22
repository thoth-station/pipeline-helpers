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

"""This script run in a pipeline task to execute test and gather metrics for a AI model deployed."""

import os
import logging
import json
import sys
import subprocess

from datetime import datetime

_DEBUG_LEVEL = bool(int(os.getenv("DEBUG_LEVEL", 0)))

if _DEBUG_LEVEL:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

_LOGGER = logging.getLogger("thoth.gather_metrics")

RUNTIME_ENVIRONMENT_TEST = os.getenv("PIPELINE_HELPERS_TEST_RUNTIME_ENVIRONMENT_NAME")
METRICS_FILE_PATH = os.getenv("PIPELINE_HELPERS_METRICS_FILE_PATH", "metrics.json")
TEST_TYPE = os.getenv("PIPELINE_HELPERS_TEST_TYPE", "behave")
TEST_NAME = os.environ["PIPELINE_HELPERS_TEST_NAME"]


def gather_metrics() -> None:
    """Gather metrics running a test script created by data scientist."""
    # Install requirements from test overlay.
    args_env = ""

    if RUNTIME_ENVIRONMENT_TEST:
        args_env = f" -r {RUNTIME_ENVIRONMENT_TEST}"

    args = [f"thamos install{args_env}"]

    _LOGGER.info(f"Args to be used to install: {args}")

    try:
        process_output = subprocess.run(
            args,
            shell=True,
            capture_output=True,
        )
        _LOGGER.info(f"After installing packages: {process_output.stdout.decode('utf-8')}")

    except Exception as behave_feature:
        _LOGGER.error("error installing packages: %r", behave_feature)
        sys.exit(1)

    # Execute the supplied script.
    test_command = f"{TEST_TYPE} -i {TEST_NAME}"
    _LOGGER.info(f"Executing command to gather metrics... {test_command}")

    try:
        start = datetime.utcnow()
        subprocess.run(test_command, shell=True, check=True)
        _LOGGER.info("Finished running test successfully.")
        end = datetime.utcnow()

    except Exception as exc:
        _LOGGER.error("Error running test: %r", exc)
        sys.exit(1)

    # Load metrics from file created by behave.
    with open(METRICS_FILE_PATH, "r") as stdout_file:
        try:
            stdout = json.load(stdout_file)
        except Exception as exc:
            _LOGGER.error(f"Error loading metrics: {exc}")
            sys.exit(1)
        _LOGGER.info(f"Metrics collected are {stdout}")

    # Store timestamps for platform metrics.
    with open("/tekton/results/gather_timestamp_started", "w") as result_start:
        result_start.write(json.dumps(datetime.timestamp(start)))

    with open("/tekton/results/gather_timestamp_ended", "w") as result_end:
        result_end.write(json.dumps(datetime.timestamp(end)))


if __name__ == "__main__":
    gather_metrics()
