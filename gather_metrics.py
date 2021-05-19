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

_DEBUG_LEVEL = bool(int(os.getenv("DEBUG_LEVEL", 0)))

if _DEBUG_LEVEL:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

_LOGGER = logging.getLogger("thoth.gather_metrics")

RUNTIME_ENVIRONMENT_TEST = os.getenv("TEST_RUNTIME_ENVIRONMENT_NAME", "test")
METRICS_FILE_PATH = os.getenv("PIPELINE_HELPERS_METRICS_FILE_PATH", "metrics.json")
TEST_COMMAND = os.getenv("PIPELINE_HELPERS_TEST_COMMAND", "behave")


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
    _LOGGER.info(f"Executing command to gather metrics... {TEST_COMMAND}")

    try:
        process_output = subprocess.run(TEST_COMMAND, shell=True, capture_output=True, check=True)
        _LOGGER.info(f"Finished running test with: {process_output.stdout.decode('utf-8')}")

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


if __name__ == "__main__":
    gather_metrics()
