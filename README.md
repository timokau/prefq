# prefq -- Querying Preferences from Real Humans

## Running the server

Running the server only requires a working installation of poetry. Given that, just execute

```bash
./scripts/run_server.sh
```

## Running the Imitation Example

This is handled by the `./scripts/run_imitation_example.sh` script, which you can execute to run the example.

## Architecture

The high-level architecture is illustrated in the following diagram:
![prefq-diagram](./figures/prefq_diagram/prefq.svg)

## Contributing

This project uses [pre-commit](https://pre-commit.com/) for initial quality and consistency checks. To run these checks on each commit.

1. install poetry: `curl -sSL https://install.python-poetry.org | python3 -`
2. install pre-commit checks: `poetry run pre-commit install`

For automatic code formatting according to these consistency checks you can use black in combination with pylint. This will ease your workflow, as your code will be adjusted automatically, instead of formatting everything manually. 

1. `pip install pylint`
2. `pip install black`

Whenever you run `git commit`, pylint and black will attempt to [reformat](https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html) your code on all staged changes. If changes are made you can just save the formatted file(s) and run `git add <formatted files>`.
