# Contributing

Everything in the checkout runs through `make`, on the system `python3`:
there is no virtualenv here and nothing installs itself. Python 3.12 or newer
with the packages from `requirements.txt`, Docker with the Compose plugin, and
[uv](https://docs.astral.sh/uv/) for `make build`.

- [Layout](#layout)
- [Make targets](#make-targets)
- [Working on the stack](#working-on-the-stack)
- [Tests and linters](#tests-and-linters)
- [Continuous integration](#continuous-integration)
- [Releases](#releases)

## Layout

```text
bin/penpot-stack   launcher, runs the code straight from the checkout
libs/              the modules: cli, settings, compose, penpot, templates, prompts
config/            compose.yaml and autologin.conf
install/           the curl installer and its documentation
tests/             pytest suite, no network and no Docker
```

The wheel carries `libs/` and `config/` under one importable name: the build
maps `libs` to `penpot_stack` and `config` to `penpot_stack/config`, so the
Compose file ships with the code and `penpot-stack` runs from anywhere. That
mapping lives in `[tool.hatch.build.targets.wheel]` in `pyproject.toml`.

Modules import each other relatively, which is what lets the same files work
as `libs` in the checkout and as `penpot_stack` once installed.

`libs/settings.py` is the only place that decides anything configurable: a
pydantic-settings model filled from defaults, then `.penpot.yaml` in the
working directory, then `PENPOT_*` variables. `config/compose.yaml` reads the
same names through `${PENPOT_PORT:-9001}` style defaults, so the file still
runs under a bare `docker compose`. `.penpot.yaml.example` in the repository
root is the documented shape of that file and what `install.sh` copies into a
directory; `.penpot.yaml` itself is gitignored, so the checkout runs on the
defaults until you copy the example over.

Nothing in the checkout installs that package, so an editable install never
comes up - which is just as well, because hatchling rejects a dev-mode install
whose `sources` rewrite replaces a prefix.

## Make targets

| Target         | What it does                                               |
| -------------- | ---------------------------------------------------------- |
| `make`         | Open an interactive subshell with `PRE_COMMIT_HOME` set    |
| `make test`    | Run the pytest suite                                       |
| `make lint`    | Run the pre-commit hooks over every file                   |
| `make up`      | Start the stack from the checkout                          |
| `make down`    | Offer the export, confirm the wipe, stop the stack         |
| `make import`  | Import a template into the running stack                   |
| `make export`  | Export a file back into `templates/`                       |
| `make extract` | Unpack a `.penpot` file into `templates/`, no stack needed |
| `make convert` | Pack a template into a `.penpot` file, no stack needed     |
| `make build`   | Build the wheel and the sdist into `dist/`                 |
| `make clean`   | Remove the build artifacts                                 |

Start by giving your `python3` what `requirements.txt` lists, however this
machine installs packages, then wire up the hooks once:

```bash
pre-commit install
```

## Working on the stack

`make up` and the rest run `python3 bin/penpot-stack`, so they use the working
tree against `templates/` in the repository root. Point `PENPOT_TEMPLATES` somewhere else to keep the repository clean:

```bash
PENPOT_TEMPLATES=~/mockups make up
```

The stack itself is `config/compose.yaml`: Penpot frontend, backend, exporter
and MCP, with Postgres on tmpfs and Valkey without persistence. Nothing in it
is meant to survive `down`.

## Tests and linters

```bash
make test
make lint
```

The tests cover the parts that do not need Penpot: template discovery, the
export filter that drops thumbnails and refuses raster images, the Compose
command, and every confirm in the command flow. Anything that talks to the
API is mocked, so the suite needs neither network nor Docker.

`make lint` runs ruff, shellcheck, shfmt, markdownlint and the commit-message
checks through pre-commit. Both are expected to pass before a commit.

## Continuous integration

`.github/workflows/ci.yml` runs on every pull request and on pushes to `main`:
one job runs the pre-commit hooks over all files, the other runs the suite on
Python 3.12, 3.13 and 3.14. Actions are pinned by commit, with the version in
a trailing comment. Nothing is published from CI.

Dependabot watches three ecosystems weekly: `pip` for `requirements.txt`,
`pre-commit` for the hook revisions and `github-actions` for those pins.

## Releases

The version lives in `pyproject.toml` and is bumped with commitizen, which
writes the changelog and the tag:

```bash
cz bump
git push --follow-tags
```

Users upgrade by re-running `install/install.sh`, which unfolds a tag with
`--ref`, so a release is the tag itself.

`make build` puts the wheel and the sdist in `dist/`. Uploading them is not
wired into this repository, by hand or from CI.
