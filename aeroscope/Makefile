#* Variables
SHELL := /usr/bin/env bash
PYTHON := python3

#* Build Variables
AEROSCOPE_VERSION := $(shell poetry version --short)
AEROSCOPE_TAG := "aeroscope-v$(AEROSCOPE_VERSION)"

.PHONY: dist-remove
dist-remove:
	rm -rf dist/

.PHONY: build
build: dist-remove
	poetry build

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
	- git tag -d $(AEROSCOPE_TAG)
	- git push origin --delete $(AEROSCOPE_TAG)

.PHONY:tag
tag: delete-tag
	git tag $(AEROSCOPE_TAG)
	git push origin $(AEROSCOPE_TAG)
