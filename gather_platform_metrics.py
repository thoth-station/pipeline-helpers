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
from datetime import datetime, timedelta

from prometheus_api_client import PrometheusConnect

_DEBUG_LEVEL = bool(int(os.getenv("DEBUG_LEVEL", 0)))

if _DEBUG_LEVEL:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

_LOGGER = logging.getLogger("thoth.gather_platform_metrics")

PROCESS_START = int(os.environ["PIPELINE_HELPERS_PROCESS_START_TIMESTAMP"])
PROCESS_END = int(os.environ["PIPELINE_HELPERS_PROCESS_END_TIMESTAMP"])

THANOS_ENDPOINT = os.environ["THANOS_ENDPOINT"]
THANOS_ACCESS_TOKEN = os.environ["THANOS_ACCESS_TOKEN"]

POD_NAME = os.environ["PIPELINE_HELPERS_CONTAINER_NAME"]
PLATFORM_METRICS_FILE_PATH = os.getenv("PIPELINE_HELPERS_PLATFORM_METRICS_FILE_PATH", "platform_metrics.json")
DEPLOYMENT_NAMESPACE = os.getenv("PIPELINE_HELPERS_DEPLOYMENT_NAMESPACE", "aicoe-ci")


def gather_platform_metrics() -> None:
    """Gather platform metrics from Openshift API (scraped by Prometheus)."""
    pc = PrometheusConnect(
        url=THANOS_ENDPOINT,
        headers={"Authorization": f"bearer {THANOS_ACCESS_TOKEN}"},
        disable_ssl=True,
    )

    is_connected = pc.check_prometheus_connection()
    if not is_connected:
        raise Exception("Pipeline is not able to gather metrics from platform")

    start = datetime.fromtimestamp(PROCESS_START)
    end = datetime.fromtimestamp(PROCESS_END)

    _LOGGER.info("Start time %r", start)
    _LOGGER.info("End time %r", end)

    _LOGGER.info("Considering namespace %r", DEPLOYMENT_NAMESPACE)
    _LOGGER.info("Considering pod name %r", POD_NAME)

    # Memory usage
    query_labels = (
        f'{{namespace="{DEPLOYMENT_NAMESPACE}", container!="", pod="{POD_NAME}"}}'
    )
    query = f"sum(container_memory_working_set_bytes{query_labels}) by (pod)"
    memory_usage = pc.custom_query_range(  # type: ignore
        query=query,
        start_time=start,
        end_time=end,
        step="1h",
    )
    _LOGGER.info("Memory Usage %r", memory_usage)

    # CPU usage
    query_labels = (
        f'{{namespace="{DEPLOYMENT_NAMESPACE}", pod="{POD_NAME}"}}'
    )
    query = F"sum(node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate{query_labels}) by (pod)"
    cpu_usage = pc.custom_query_range(  # type: ignore
        query=query,
        start_time=start,
        end_time=end,
        step="1h",
    )
    _LOGGER.info("CPU Usage %r", cpu_usage)

    if memory_usage and cpu_usage:
        memory_usage_vector = [float(v[1])/1000000 for v in memory_usage[0]["values"] if float(v[1]) > 0]  # in MB
        cpu_usage_vector = [float(v[1]) for v in cpu_usage[0]["values"] if float(v[1]) > 0]
        metric_data = {"CPU max usage": round(max(cpu_usage_vector), 4), "Memory max usage": f"{round(max(memory_usage_vector))}Mi"}
    else:
        metric_data = {"CPU max usage": "N/A", "Memory max usage": "N/A"}

    _LOGGER.info("Platform metrics: %r", metric_data)

    # Store platform metrics.
    with open(PLATFORM_METRICS_FILE_PATH, "w") as stdout_file:
        json.dump(metric_data, stdout_file)



if __name__ == "__main__":
    gather_platform_metrics()
