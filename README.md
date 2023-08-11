# prefq -- Querying Preferences from Real Humans

## Running the server

Running the server only requires a working installation of poetry. Given that, just execute

```bash
./scripts/run_server.sh
```

## Running the Imitation Example

Unfortunately, running the example is a bit messy because we depend on imitation, which in turn depends on gym 0.21, which requires an older version of setuptools to be installed.

This is handled by the `./scripts/run_imitation_example.sh` script, which you can execute to run the example.

## Architecture

The high-level architecture is illustrated in the following diagram:
![prefq-diagram](./figures/prefq_diagram/prefq.svg)

## Contributing

This project uses [pre-commit](https://pre-commit.com/) for initial quality and consistency checks. To run these checks on each commit, simply execute `poetry run pre-commit install`. These checks will also be run on each GitHub pull request.
