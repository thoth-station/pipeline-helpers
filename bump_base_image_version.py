#!/usr/bin/env python3
# pipeline-helpers
# Copyright(C) 2022 Red Hat, Inc.
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

"""Automatically bump the base image version used to deliver container images."""

import json
import logging
import os
import requests
import typing
import yaml

from packaging import version
from typing import Optional
from thoth.common import init_logging

init_logging()

_DEBUG_LEVEL = bool(int(os.getenv("DEBUG_LEVEL", 0)))
_LOGGER = logging.getLogger("thoth.bump_base_image_version")
if _DEBUG_LEVEL:
    _LOGGER.setLevel(logging.DEBUG)


CONFIG_FILE_PATH = os.getenv("CONFIG_FILE_PATH", ".aicoe-ci.yaml")
REPOSITORY_PATH = os.getenv("REPOSITORY_PATH")  # type: Optional[str]
BASE_IMAGE_FIELD_YAML = os.getenv("BASE_IMAGE_FIELD_YAML", "base-image")
QUAY_TOKEN = os.getenv("THOTH_QUAY_TOKEN")


def _find_config_files_base_image_keys(file_dict: dict) -> typing.List[list]:
    """Find all paths to a base image in a key-value config file."""
    current = [[key, file_dict, [key]] for key in file_dict.keys()]
    paths = []

    while current:
        next_ = []
        for [key, dict_, current_path] in current:
            if isinstance(key, str) and key == BASE_IMAGE_FIELD_YAML:
                paths.append(current_path)
            else:
                if isinstance(dict_[key], list):
                    for index, elem in enumerate(dict_[key]):
                        next_.append([index, dict_[key], current_path + [index]])

                elif isinstance(dict_[key], dict):
                    for key_ in dict_[key].keys():
                        next_.append([key_, dict_[key], current_path + [key_]])

        current = next_

    return paths


def bump_base_image_versions() -> None:
    """Bump the base image version for container images to the latest available on Quay."""
    if REPOSITORY_PATH:
        config_file = os.path.join(REPOSITORY_PATH, CONFIG_FILE_PATH)

    else:
        config_file = CONFIG_FILE_PATH

    with open(config_file, "r") as yaml_file:
        loaded_file = yaml.safe_load(yaml_file)
        base_image_paths = _find_config_files_base_image_keys(loaded_file)

        base_image_urls = []
        for base_image_path in base_image_paths:
            path_index = 0
            base_image_url = loaded_file
            while path_index < len(base_image_path):
                base_image_url = base_image_url[base_image_path[path_index]]
                path_index += 1

            base_image_urls.append("/".join(base_image_url.split("/")[1:]))

    base_image_url_to_latest_version = {}

    for base_image_url in base_image_urls:
        _LOGGER.info(f"Requesting the latest base image version from Quay.io for {base_image_url}")

        r = requests.get(
            f"https://quay.io/api/v1/repository/{base_image_url.split(':')[0]}",
            headers={"Authorization": f"Bearer {QUAY_TOKEN}"},
        ).text
        image_versions = [
            version.strip("v") for version in json.loads(r).get("tags", {}).keys() if version.startswith("v")
        ]

        latest_image_version = base_image_url.split(":")[1].strip("v")
        for image_version in image_versions:
            if version.parse(image_version) > version.parse(latest_image_version):
                latest_image_version = image_version

        latest_image_version = "v" + latest_image_version

        base_image_url_to_latest_version["quay.io/" + base_image_url] = latest_image_version

    current_version = base_image_url.split(":")[1]
    if current_version != latest_image_version:
        for base_image, latest_version in base_image_url_to_latest_version.items():
            os.system(f"sed -i s@{base_image}@{base_image.split(':')[0] + ':' + latest_version}@g {config_file}")

        _LOGGER.info(f"File {config_file} has been updated with latest base image versions.")


if __name__ == "__main__":
    bump_base_image_versions()
