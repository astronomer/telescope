#* Variables
SHELL := /usr/bin/env bash
PYTHON := python3

#* Docker variables
IMAGE := telescope
VERSION := latest

#* Build Variables
BRANCH := $(shell git branch --show-current)
TELESCOPE_VERSION := $(shell poetry version --short)
TELESCOPE_TAG := "v$(TELESCOPE_VERSION)"

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
	poetry lock -n
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
	rm -rf report.json charts report_output.xlsx report_summary.txt telescope-*.whl airflow_report.pyz

.PHONY: clean-all
clean-all: outputs-remove pycache-remove build-remove docker-remove

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


build: build-remove
	poetry build
	mv dist/telescope*.whl .

delete_tag:
	- git tag -d $(TELESCOPE_TAG)
	- git push origin --delete $(TELESCOPE_TAG)

# clean-all package_report
release: clean-all delete_tag
	$(MAKE) build
	$(MAKE) package_report
	- gh release delete -y $(TELESCOPE_TAG)
	git tag $(TELESCOPE_TAG)
	git push origin $(TELESCOPE_TAG)
	gh release create $(TELESCOPE_TAG) \
		./telescope-$(TELESCOPE_VERSION)-py3-none-any.whl \
		airflow_report.pyz \
		--draft --prerelease \
		--generate-notes
