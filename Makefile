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
	curl -sSL https://install.python-poetry.org | $(PYTHON) -

.PHONY: poetry-remove
poetry-remove:
	curl -sSL https://install.python-poetry.org | $(PYTHON) - --uninstall

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

.PHONY: test-with-coverage
test-with-coverage:
	poetry run pytest -c pyproject.toml --cov=./ --cov-report=xml

.PHONY: check-codestyle
check-codestyle:
	poetry run isort --diff --check-only --settings-path pyproject.toml ./
	poetry run black --diff --check --config pyproject.toml ./

.PHONY: check-safety
check-safety:
	poetry check
	poetry run safety check --full-report
	poetry run bandit -ll --recursive astronomer_telescope tests

.PHONY: lint
lint: test check-codestyle check-safety

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
	rm -rf report.json charts report_output.xlsx report_summary.txt astronomer_telescope-*.whl airflow_report.pyz astronomer_telescope-*

.PHONY: clean-all
clean-all: outputs-remove pycache-remove build-remove dist-remove

.PHONY: package-report
package-report: build-remove
	mkdir -p build
	poetry run python -m pip install -r airflow_report/requirements.txt --target build
	cp -r airflow_report build
	rm -f build/*.dist-info/*
	rmdir build/*.dist-info
	poetry run python -m zipapp \
		--compress \
		--main airflow_report.__main__:main \
		--python "/usr/bin/env python3" \
		--output airflow_report.pyz \
		build

.PHONY: package-pyinstaller
package-pyinstaller: dist-remove
	poetry run python -m PyInstaller --onefile --noconfirm --clean --specpath dist --name astronomer-telescope \
		--hidden-import astronomer_telescope.getters.kubernetes_client \
		--hidden-import astronomer_telescope.getters.docker_client \
		--recursive-copy-metadata astronomer-telescope \
		astronomer_telescope/__main__.py
	cp dist/astronomer-telescope telescope-$(shell uname -s | awk '{print tolower($$0)}' )-$(shell uname -m)

.PHONY: build
build: build-remove
	poetry build
	mv dist/astronomer_telescope*.whl .


.PHONY: publish_test
publish_test: build
	# Note: you first need to run
	# `poetry config repositories.testpypi https://test.pypi.org/legacy/`
	# and `poetry config pypi-token.pypi pypi-A.............` with a token
	poetry publish --repository testpypi --skip-existing -n

.PHONY: publish
publish: build
	# Note: you first need to run
	# `poetry config pypi-token.pypi pypi-A.............` with a token
	poetry publish --skip-existing -n

.PHONY: delete-tag
delete-tag:
	- git tag -d $(TELESCOPE_TAG)
	- git push origin --delete $(TELESCOPE_TAG)


.PHONY:tag
tag: clean-all delete-tag
	git tag $(TELESCOPE_TAG)
	git push origin $(TELESCOPE_TAG)


.PHONY: local_release
local_release: clean-all delete-tag
	$(MAKE) build
	$(MAKE) package-report
	$(MAKE) package-pyinstaller
	- gh release delete -y $(TELESCOPE_TAG)
	git tag $(TELESCOPE_TAG)
	git push origin $(TELESCOPE_TAG)
	gh release create $(TELESCOPE_TAG) \
		./astronomer_telescope-$(TELESCOPE_VERSION)-py3-none-any.whl \
		airflow_report.pyz \
		--prerelease \
		--generate-notes
