#* Variables
SHELL := /usr/bin/env bash
PYTHON := python3

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

.PHONY: check-safety
check-safety:
	poetry check
	poetry run safety check --full-report
	poetry run bandit -ll --recursive telescope tests

.PHONY: lint
lint: test check-codestyle mypy check-safety

#* Cleaning
.PHONY: pycache-remove
pycache-remove:
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf

.PHONY: build-remove
build-remove:
	rm -rf build/

.PHONY: dist-remove
dist-remove:
	rm -rf dist/

.PHONY: outputs-remove
outputs-remove:
	rm -rf report.json charts report_output.xlsx report_summary.txt telescope-*.whl airflow_report.pyz telescope-*

.PHONY: clean-all
clean-all: outputs-remove pycache-remove build-remove dist-remove

.PHONY: package-report
package-report: build-remove
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

.PHONY: package-pyinstaller
package-pyinstaller: dist-remove
	poetry run PyInstaller --onefile --noconfirm --clean --specpath dist --name telescope \
		--hidden-import telescope.getters.kubernetes_client \
		--hidden-import telescope.getters.docker_client \
		--recursive-copy-metadata telescope \
		telescope/__main__.py
	cp dist/telescope telescope-$(shell uname -s | awk '{print tolower($$0)}' )-$(shell uname -m)

.PHONY: build
build: build-remove
	poetry build
	mv dist/telescope*.whl .

.PHONY: delete_tag
delete-tag:
	- git tag -d $(TELESCOPE_TAG)
	- git push origin --delete $(TELESCOPE_TAG)

# clean-all package_report
.PHONY: release
release: clean-all delete-tag
	git tag $(TELESCOPE_TAG)
	git push origin $(TELESCOPE_TAG)
