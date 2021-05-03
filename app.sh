#!/usr/bin/env sh
#
# This script is run by OpenShift's s2i. Here we guarantee that we run desired
# command
#

set -o nounset
set -o errexit
set -o errtrace
set -o pipefail
trap 'echo "Aborting due to errexit on line $LINENO. Exit code: $?" >&2' ERR

THOTH_PIPELINE_TASK=${THOTH_PIPELINE_TASK:?'THOTH_PIPELINE_TASK is not selected!'}

if [ "$THOTH_PIPELINE_TASK" = "gather_metrics" ]; then
    exec python3 gather_metrics.py
fi
