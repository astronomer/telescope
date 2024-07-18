This project welcomes contributions. All Pull Requests should include proper testing, documentation, and follow all existing checks and practices.

# Contributing Quickstart (on a Mac)

2) Run `just install-precommit` (run [`brew install just` or other method]() if required)
3) Make a new branch, from `main`
4) Code, test, PR
5) Bump version in `astronomer-telescope/__init__.py` according to [semantic versioning](https://semver.org/)
6) Merge into `main`
7) run `just tag` and `just deploy-tag` to create a release

# How to contribute

## Dependencies

Set up a `venv`
```bash
python -m venv .venv
source .venv/bin/activate
```

To install dependencies and prepare [`pre-commit`](https://pre-commit.com/) hooks you would need to run `install` command:

```bash
just install
just install-precommit
```

## Versioning

- This project follows [Semantic Versioning](https://semver.org/)

## Development

### Pre-Commit

This project uses `pre-commit`. Install it with `just install-precommit`

### Installing Locally

Install with `just install`

## Linting

This project
uses [`black` (link)](https://black.readthedocs.io/en/stable/), and [`ruff` (link)](https://beta.ruff.rs/).
They run with pre-commit but you can run them directly with `just lint` in the root.

## Testing

This project utilizes [Doctests](https://docs.python.org/3/library/doctest.html) and `pytest`.
With the `dev` extras installed, you can run all tests with `just test` in the root of the project.
It will automatically pick up it's configuration from `pyproject.toml`
