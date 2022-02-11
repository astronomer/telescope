#* Variables
SHELL := /usr/bin/env bash
PYTHON := python3

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

.PHONY: outputs-remove
outputs-remove:
	rm -rf report.json charts report_output.xlsx report_summary.txt

.PHONY: clean-all
clean-all: outputs-remove pycache-remove build-remove docker-remove

build: build-remove
	poetry build

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

BRANCH := $(shell git branch --show-current)
TELESCOPE_VERSION := $(shell poetry version --short)
TELESCOPE_TAG := "v$(TELESCOPE_VERSION)"
# clean-all package_report
release:
	git tag $(TELESCOPE_TAG)
	git push origin $(TELESCOPE_TAG)
#	gh release create --target dev -t v$(poetry version --short)

main_release:
	gh release create --target main -t v$(poetry version --short)
