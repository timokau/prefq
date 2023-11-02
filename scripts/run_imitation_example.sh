#!/usr/bin/env bash

set -e
set -o pipefail

# First check if we can already install the full environment without issues. In
# that case we are done. This is the case if the environment was already
# installed previously, i.e., this speeds up the process on the second run.
if ! poetry install -E examples; then
	poetry install -E examples
fi

poetry run python3 -m prefq.examples.imitation_preference_comparisons
