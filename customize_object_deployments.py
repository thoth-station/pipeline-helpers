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

"""This script run in a pipeline task to customize Kuberneetes objects for deployment of an AI model."""

import io
import json
import yaml
import os
import logging


_DEBUG_LEVEL = bool(int(os.getenv("DEBUG_LEVEL", 0)))

if _DEBUG_LEVEL:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

_LOGGER = logging.getLogger("thoth.customize_object_deployments")

IMAGE_URL = os.environ["PIPELINE_HELPERS_IMAGE_URL_DEPLOYMENT"]


def customize_object_deployments() -> None:
    """Customize object for deployment."""
    with open("/workspace/pr/pr.json") as f:
        pr_info = json.load(f)

    label = f'{pr_info["Base"]["Repo"]["Name"]}-pr-{pr_info["Number"]}'

    # Handle DC YAMLfile
    with open("/opt/app-root/src/manifests/template/deploymentconfig.yaml", "r") as stream:
        dc_loaded = yaml.safe_load(stream)

    new_dc = dict(dc_loaded)
    new_dc["metadata"]["name"] = label
    new_dc["metadata"]["labels"] = {}
    new_dc["metadata"]["labels"]["service"] = label
    new_dc["spec"]["template"]["spec"]["containers"][0]["name"] = label
    new_dc["spec"]["template"]["metadata"]["labels"]["service"] = label
    new_dc["spec"]["template"]["spec"]["containers"][0]["image"] = IMAGE_URL
    new_dc["spec"]["selector"]["service"] = label

    _LOGGER.info(f"Updated Deployment Config: {new_dc}")

    # TODO: Handle cases with different S2i options
    # Write DC YAML file
    with io.open("/workspace/repo/customized_deploymentconfig.yaml", "w", encoding="utf8") as outfile:
        yaml.dump(new_dc, outfile, default_flow_style=False, allow_unicode=True)

    # Handle Route YAMLfile
    with open("/opt/app-root/src/manifests/template/route.yaml", "r") as stream:
        route_loaded = yaml.safe_load(stream)

    new_route = dict(route_loaded)
    new_route["metadata"]["name"] = label
    new_route["metadata"]["labels"]["service"] = label
    new_route["spec"]["to"]["name"] = label
    _LOGGER.info(f"Updated Route: {new_route}")

    # Write Route YAML file
    with io.open("/workspace/repo/customized_route.yaml", "w", encoding="utf8") as outfile:
        yaml.dump(new_route, outfile, default_flow_style=False, allow_unicode=True)

    # Handle Service YAML file
    with open("/opt/app-root/src/manifests/template/service.yaml", "r") as stream:
        service_loaded = yaml.safe_load(stream)

    new_service = dict(service_loaded)
    new_service["metadata"]["name"] = label
    new_service["metadata"]["labels"]["service"] = label
    new_service["spec"]["selector"]["service"] = label
    _LOGGER.info(f"Updated Service: {new_service}")

    # Write Route YAML file
    with io.open("/workspace/repo/customized_service.yaml", "w", encoding="utf8") as outfile:
        yaml.dump(new_service, outfile, default_flow_style=False, allow_unicode=True)


if __name__ == "__main__":
    customize_object_deployments()
