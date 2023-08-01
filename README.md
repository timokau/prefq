# prefq -- Querying Preferences from Real Humans

## Running the server

Running the server only requires a working installation of poetry. Given that, just execute

```bash
./scripts/run_server.sh
```

## Architecture

The high-level architecture is illustrated in the following diagram:
![prefq-diagram](./figures/prefq_diagram/prefq.svg)

## Contributing

This project uses [pre-commit](https://pre-commit.com/) for initial quality and consistency checks. To run these checks on each commit, simply execute `poetry run pre-commit install`. These checks will also be run on each GitHub pull request.
