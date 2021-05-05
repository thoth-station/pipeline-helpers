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
import subprocess


_LOGGER = logging.getLogger("thoth.gather_metrics")

_RUNTIME_ENVIRONMENT_TEST = os.getenv("TEST_RUNTIME_ENVIRONMENT_NAME", "test")
# We use a file for stdout and stderr not to block on pipe.
_EXEC_STDOUT_FILE = os.getenv("PIPELINE_STDOUT_PATH", "script.stdout")
_EXEC_STDERR_FILE = os.getenv("PIPELINE_STDERR_PATH", "script.stderr")


def gather_metrics() -> None:
    """Gather metrics running a test script created by data scientist."""
    # Install requirements.
    args = ["thamos", "install", "-r", f"{_RUNTIME_ENVIRONMENT_TEST}"]
    _LOGGER.info(f"Args to be used to install: {args}")

    try:
        process_output = subprocess.run(
            args,
            shell=True,
            capture_output=True,
        )
        _LOGGER.info(f"After installing packages: {process_output.stdout.decode('utf-8')}")

    except Exception as behave_feature:
        _LOGGER.error("error running test: %r", behave_feature)
        return

    # Execute the supplied script.
    args = ["behave"]
    _LOGGER.info(f"Args to be used in process: {args}")

    try:
        process_output = subprocess.run(
            args,
            shell=True,
            capture_output=True,
        )
        _LOGGER.info(process_output.stdout.decode("utf-8"))
    except Exception as behave_feature:
        _LOGGER.error("error running test: %r", behave_feature)
        return

    # Load stdout.
    with open("metrics.json", "r") as stdout_file:
        try:
            stdout = json.load(stdout_file)
        except Exception as exc:
            _LOGGER.error(f"Error loading metrics: {exc}")
            return
        _LOGGER.info(f"Metrics collected are {stdout}")

    # TODO: Store result to track changes?


if __name__ == "__main__":
    gather_metrics()
