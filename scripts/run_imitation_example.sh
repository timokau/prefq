#!/usr/bin/env bash

set -e
set -o pipefail

poetry install -E examples

poetry run python3 -m prefq.examples.imitation_preference_comparisons
