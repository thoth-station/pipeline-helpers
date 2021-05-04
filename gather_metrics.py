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

_SCRIPT_DIR = os.getenv("PIPELINE_SCRIPT_DIR", ".")
_OUTPUT_DIR = os.getenv("PIPELINE_OUTPUT_DIR", "..")
_TEST_PATH = os.getenv("MODEL_TEST_PATH", "src/test.py")
_REPO_PATH = os.getenv("REPO_TEST_PATH", "repo")


def gather_metrics() -> None:
    """Gather metrics running a test script created by data scientist."""
    # Move to repo where /features and requirements/.thoth.yaml
    os.chdir(os.path.join(_SCRIPT_DIR, _REPO_PATH))

    # Install requirements.
    args = ["thamos", "install", "-r", f"{_RUNTIME_ENVIRONMENT_TEST}"]
    _LOGGER.info(f"Args to be used to install: {args}")
    process_output = subprocess.run(
        args,
        shell=True,
        capture_output=True,
    )
    _LOGGER.info(f"After installing packages: {process_output}")

    # Execute the supplied script.
    args = ["behave"]
    _LOGGER.info(f"Args to be used in process: {args}")

    with open(os.path.join(_OUTPUT_DIR, _EXEC_STDOUT_FILE), "w") as stdout_file, open(
        os.path.join(_OUTPUT_DIR, _EXEC_STDERR_FILE), "w"
    ) as stderr_file:
        process = subprocess.Popen(args, shell=True, stdout=stdout_file, stderr=stderr_file, universal_newlines=True)

    process.communicate()

    return_code = process.returncode
    if return_code != 0:
        with open(os.path.join(_OUTPUT_DIR, _EXEC_STDERR_FILE), "r") as stderr_file:
            stderr = stderr_file.read()
            _LOGGER.error(f"Error running script in pipeline-helpers: {stderr}")
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
