#!/usr/bin/env just --justfile
set dotenv-load := true

BRANCH := `git branch --show-current`
EXTRAS := "dev"
SRC_DIR := "astronomer_telescope"
DOCS_DIR := "docs"
VERSION := `echo $(python -c 'from astronomer_telescope import __version__; print(__version__)')`

default:
  @just --choose

# Print this help text
help:
    @just --list

# Install project and python dependencies (incl. pre-commit) locally
install EDITABLE='':
    pip install {{EDITABLE}} '.[{{EXTRAS}}]'

# Install pre-commit to local project
install-precommit: install
    pre-commit install

# Update the baseline for detect-secrets / pre-commit
update-secrets:
    detect-secrets scan  > .secrets.baseline # `pragma: allowlist secret`

# Run pytests with config from pyproject.toml
test:
    pytest -c pyproject.toml

# Test and emit a coverage report
test-with-coverage:
    pytest -c pyproject.toml --cov=./ --cov-report=xml

test-cicd:
  act pull-request -W .github/workflows/checks.yml --container-architecture linux/amd64

# Run ruff and black (normally done with pre-commit)
lint:
    ruff check .

# Render and serve documentation locally
serve-docs:
    mkdocs serve -w {{DOCS_DIR}} -w {{SRC_DIR}}

# Build documentation locally (likely unnecessary)
build-docs: clean
    mkdocs build

# Deploy documentation to GitHub pages (GHA does this automatically)
deploy-docs UPSTREAM="origin": clean
    mkdocs gh-deploy -r {{UPSTREAM}}

# Tag as v$(<src>.__version__) and push to GH
tag: clean
    # Delete tag if it already exists
    git tag -d v{{VERSION}} || true
    # Tag and push
    git tag v{{VERSION}}

# Remove temporary or build folders
clean:
    rm -rf build dist site *.egg-info
    find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf

deploy-tag: tag
    git push origin v{{VERSION}}

deploy: deploy-tag

# Build the project
build: install clean
    python -m build
    cp dist/{{SRC_DIR}}*.whl .

# Upload to TestPyPi for testing (note: you can only use each version once)
upload-testpypi: build install clean
    python -m twine check dist/*
    TWINE_USER=${TWINE_USER} TWINE_PASS=${TWINE_PASS} python -m twine upload --repository testpypi dist/*

# Upload to PyPi - DO NOT USE THIS, GHA DOES THIS AUTOMATICALLY
upload-pypi: build install clean
    python -m twine check dist/*
    TWINE_USER=${TWINE_USER} TWINE_PASS=${TWINE_PASS} python -m twine upload dist/*

# Package the `airflow_report.pyz`
package-report: clean
  mkdir -p build
  python -m pip install -r airflow_report/requirements.txt --target build
  cp -r airflow_report build
  rm -rf build/*.dist-info/*
  rmdir build/*.dist-info
  python -m zipapp \
    --compress \
    --main airflow_report.__main__:main \
    --python "/usr/bin/env python3" \
    --output airflow_report.pyz \
    build

# Package the `telescope` binary
package-pyinstaller: clean
  python -m PyInstaller --onefile --noconfirm --clean --specpath dist --name astronomer-telescope \
    --hidden-import astronomer_telescope.getters.kubernetes_client \
    --hidden-import astronomer_telescope.getters.docker_client \
    --recursive-copy-metadata astronomer-telescope \
    astronomer_telescope/__main__.py
  cp dist/astronomer-telescope telescope-$(uname -s | awk '{print tolower($0)}' )-$(uname -m)

# Release to GitHub - DO NOT USE THIS, GHA DOES THIS AUTOMATICALLY
local_release: clean
  $(just) build
  $(just) package-report
  $(just) package-pyinstaller
  gh release delete -y v$(VERSION)
  git tag v$(VERSION)
  git push origin v$(VERSION)
  gh release create v$(VERSION) \
    ./astronomer_telescope-$(VERSION)-py3-none-any.whl \
    airflow_report.pyz \
    --prerelease \
    --generate-notes
