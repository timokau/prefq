#!/usr/bin/env bash

set -e
set -o pipefail

# run "poetry install" only if dependencies are missing
if ! poetry run python3 -m prefq.examples.static_queries "$@"; then
    echo "...installing missing dependencies"
    poetry install
    poetry run python3 -m prefq.examples.static_queries "$@"
fi
