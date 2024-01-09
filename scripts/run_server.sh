#!/usr/bin/env bash

set -e
set -o pipefail

poetry install
poetry run python3 -m prefq.server "$@"