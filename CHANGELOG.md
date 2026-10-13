## 0.1.4 (2026-10-13)

### Bug Fixes

- **settings**: Each local stack opens on its own localhost name

## 0.1.3 (2026-10-13)

### Bug Fixes

- **compose**: Postgres 18 data sits on a tmpfs it accepts

### Build

- **deps**: Bump the docker-compose group in /config with 4 updates
- **deps**: Bump the pip group with 2 updates
- **deps**: Bump wyld-cz from 0.3.1 to 0.4.1 in the pre-commit group
- **deps**: Bump https://github.com/commitizen-tools/commitizen
- **deps**: Bump https://github.com/astral-sh/ruff-pre-commit

## 0.1.2 (2026-10-07)

### Bug Fixes

- **compose**: Penpot images carry literal tags Dependabot can bump

### Build

- **deps**: Bump https://github.com/astral-sh/ruff-pre-commit
- **deps**: Bump postgres from 15 to 18 in /config

## 0.1.1 (2026-09-25)

### Bug Fixes

- **templates**: export keeps only what the live file holds

### Build

- **deps**: Bump https://github.com/commitizen-tools/commitizen
- **deps**: Bump wyld-cz from 0.3.0 to 0.3.1 in the pre-commit group
- **deps**: Bump commitizen from 4.18.1 to 4.19.0 in the pip group
- **deps**: Bump valkey/valkey from 8.1 to 9.1 in /config
- **deps**: dependabot covers every pinned ecosystem
- **ci**: publish to pypi on tag push

## 0.1.0 (2026-09-20)

### Features

- **tests**: suite for templates, settings and the confirms
- **stack**: disposable penpot stack as an installable package

### Build

- **ci**: github actions and dependabot
- **lint**: pre-commit, commitizen and markdownlint configuration
- **make**: developer entry points and dependencies

### Documentation

- **docs**: readme for users and contributing for the rest
