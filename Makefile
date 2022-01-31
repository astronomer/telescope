#* Variables
SHELL := /usr/bin/env bash
PYTHON := python

#* Docker variables
IMAGE := telescope
VERSION := latest

#* Poetry
.PHONY: poetry-download
poetry-download:
	curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | $(PYTHON) -

.PHONY: poetry-remove
poetry-remove:
	curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | $(PYTHON) - --uninstall

#* Installation
.PHONY: install
install:
	poetry lock -n && poetry export --without-hashes > requirements.txt
	poetry install -n

.PHONY: pre-commit-install
pre-commit-install:
	poetry run pre-commit install

#* Formatters
.PHONY: codestyle
codestyle:
	poetry run pyupgrade --exit-zero-even-if-changed --py37-plus **/*.py
	poetry run isort --settings-path pyproject.toml ./
	poetry run black --config pyproject.toml ./

.PHONY: formatting
formatting: codestyle

#* Linting
.PHONY: test
test:
	poetry run pytest -c pyproject.toml

.PHONY: check-codestyle
check-codestyle:
	poetry run isort --diff --check-only --settings-path pyproject.toml ./
	poetry run black --diff --check --config pyproject.toml ./
	-echo "Skipping darglint..."
	-# poetry run darglint --verbosity 2 telescope tests

.PHONY: mypy
mypy:
	-echo "Skipping mypy..."
	-# poetry run mypy --config-file pyproject.toml ./

.PHONY: check-safety
check-safety:
	poetry check
	poetry run safety check --full-report
	poetry run bandit -ll --recursive telescope tests

.PHONY: lint
lint: test check-codestyle mypy check-safety

#* Docker
# Example: make docker VERSION=latest
# Example: make docker IMAGE=some_name VERSION=0.1.0
.PHONY: docker-build
docker-build:
	@echo Building docker $(IMAGE):$(VERSION) ...
	docker build \
		-t $(IMAGE):$(VERSION) . \
		-f ./docker/Dockerfile --no-cache

# Example: make clean_docker VERSION=latest
# Example: make clean_docker IMAGE=some_name VERSION=0.1.0
.PHONY: docker-remove
docker-remove:
	@echo Removing docker $(IMAGE):$(VERSION) ...
	docker rmi -f $(IMAGE):$(VERSION)

#* Cleaning
.PHONY: pycache-remove
pycache-remove:
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf

.PHONY: build-remove
build-remove:
	rm -rf build/

.PHONY: clean-all
clean-all: pycache-remove build-remove docker-remove

package_report: build-remove
	mkdir -p build
	python -m pip install -r airflow_report/requirements.txt --target build
	cp -r airflow_report build
	rm -f build/*.dist-info/*
	rmdir build/*.dist-info
	python -m zipapp \
		--compress \
		--main airflow_report.__main__:main \
		--python "/usr/bin/env python3" \
		--output airflow_report.pyz \
		build

package_pyoxidizer: build-remove install
	pyoxidizer build

package_nuitka: build-remove install
	python -m nuitka \
		--enable-plugin=multiprocessing \
		--enable-plugin=numpy \
		--standalone \
		--assume-yes-for-downloads \
		--include-package-data=telescope \
		--include-module=telescope.getters.kubernetes_client \
		--include-module=telescope.getters.docker_client \
		--include-package=plotly \
		--include-package-data=plotly \
		--include-package=kaleido \
		--output-dir build \
		telescope/__main__.py


#		--onefile \
#		--enable-plugin=anti-bloat \
#		--noinclude-pytest-mode=nofollow \
#		--noinclude-setuptools-mode=nofollow \
#		--warn-implicit-exceptions \
#		--warn-unusual-code \
#		--show-memory \
#		--show-modules \
#		--show-progress \
# standalone implies --follow-imports
# You may also want to use "--python- flag=no_site" to avoid the "site.py" module, which can save a lot of code dependencies.
# Nuitka-Options:INFO: Detected static libpython to exist, consider '--static-libpython=yes' for better performance, but errors may happen.

# FileNotFoundError: [Errno 2] No such file or directory: '/Users/mac/telescope/build/__main__.dist/plotly/package_data/templates/plotly.json'
