#!/usr/bin/env bash

set -e
set -o pipefail

# We need an older version of setuptools (and pip) to install gym 0.21. Poetry
# doesn't support specifying the setuptools version used at build time.

# The workaround is:

# (1) Set up a poetry environment without gym, but with the required setuptools version (poetry *does* allow specifying a setuptools version to be used at runtime).
poetry install
# (2) Use pip to install gym 0.21.0 inside of this environment. This will use the proper (runtime) version of setuptools.
poetry run pip install gym==0.21.0
# (3) Use poetry to install the full environment. It will reuse the already existing version of gym.
poetry install -E examples
# (4) Run the example script.
poetry run python3 -m prefq.examples.imitation_preference_comparisons
