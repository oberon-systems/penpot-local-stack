# Developer entry points for penpot-local-stack. Run `make help` for the list.

VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UV ?= uv
STACK := $(PYTHON) bin/penpot-stack

VERSION := $(shell sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)

# Hook environments live in the repository, not in ~/.cache/pre-commit.
export PRE_COMMIT_HOME := $(CURDIR)/.pre-commit

.DEFAULT_GOAL := shell

.PHONY: help install lint test shell up down import export extract convert
.PHONY: build clean require-uv

help:  ## Show the current version and the available targets
	@echo "penpot-local-stack $(VERSION)"
	@echo
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*## "} /^[a-z-]+:.*## / {printf "  %-9s %s\n", $$1, $$2}' \
		$(MAKEFILE_LIST)


# development
install:  ## Create the virtualenv, install everything and wire up the hooks
	python3 -m venv --prompt penpot-local-stack $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(VENV)/bin/pre-commit install

lint:  ## Run the pre-commit hooks over every file
	$(VENV)/bin/pre-commit run --all-files

test:  ## Run the test suite
	$(VENV)/bin/pytest


# stack
up:  ## Start the stack, import a template and open the browser logged in
	$(STACK) up

down:  ## Offer to export, then stop the stack and wipe everything it holds
	$(STACK) down

import:  ## Import a template from templates/ into the running stack
	$(STACK) import

export:  ## Export a file from the running stack back into templates/
	$(STACK) export


# archives
extract:  ## Unpack a .penpot file from this directory into templates/
	$(STACK) extract

convert:  ## Pack a template from templates/ into a .penpot file
	$(STACK) convert


# packaging
build: require-uv clean  ## Build the wheel and the sdist into dist/
	$(UV) build

clean:  ## Remove the build artifacts from dist/
	rm -f dist/*.whl dist/*.tar.gz

require-uv:
	@command -v $(UV) >/dev/null 2>&1 || { \
		echo "$(UV) not found, install it first:" >&2; \
		echo "  https://docs.astral.sh/uv/getting-started/installation/" >&2; \
		exit 1; \
	}


# defaults
shell:  ## Open an interactive subshell with the virtualenv activated
	@rc="$$(mktemp)"; \
	trap 'rm -f "$$rc"' EXIT; \
	cat ~/.bashrc 2> /dev/null > "$$rc" || true; \
	echo 'source $(CURDIR)/$(VENV)/bin/activate' >> "$$rc"; \
	bash --rcfile "$$rc" -i || true
