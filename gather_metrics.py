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

_RUNTIME_ENVIRONMENT_TEST = os.getenv("TEST_RUNTIME_ENVIRONMENT_NAME", "test")
# We use a file for stdout and stderr not to block on pipe.
_EXEC_STDOUT_FILE = os.getenv("PIPELINE_STDOUT_PATH", "script.stdout")
_EXEC_STDERR_FILE = os.getenv("PIPELINE_STDERR_PATH", "script.stderr")


def gather_metrics() -> None:
    """Gather metrics running a test script created by data scientist."""
    # Install requirements.
    args = [f"thamos install -r {_RUNTIME_ENVIRONMENT_TEST}"]
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
    args = ["behave"]
    _LOGGER.info(f"Args to be used in process: {args}")

    try:
        process_output = subprocess.run(
            args,
            shell=True,
            capture_output=True,
        )
        _LOGGER.info(f"Successfully run the test: {process_output.stdout.decode('utf-8')}")

    except Exception:
        _LOGGER.error("Error running test: %r", process_output.stderr.decode("utf-8"))
        sys.exit(1)

    # Load stdout.
    with open("/opt/app-root/src/metrics.json", "r") as stdout_file:
        try:
            stdout = json.load(stdout_file)
        except Exception as exc:
            _LOGGER.error(f"Error loading metrics: {exc}")
            sys.exit(1)
        _LOGGER.info(f"Metrics collected are {stdout}")

    # TODO: Store result to track changes?


if __name__ == "__main__":
    gather_metrics()
