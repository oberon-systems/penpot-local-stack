# penpot-local-stack

A disposable [Penpot](https://penpot.app) stack for drawing UI mockups, built
for AI-driven UI/UX work. Penpot itself is open source; its code is at
[penpot/penpot](https://github.com/penpot/penpot).

The stack exists so a design session leaves nothing behind but the drawing.
It runs from a Compose file with no persistent state: the database lives in
tmpfs and goes away with the containers, the profile is created on every
start, and the only thing that survives is `templates/` in your directory.
Mockups are stored there as unpacked Penpot exports, JSON plus SVG, so git
shows readable diffs and an agent can read a mockup directly instead of
looking at a picture of it.

- [Install](#install)
- [Settings](#settings)
- [Design loop](#design-loop)
- [Commands](#commands)
- [Templates](#templates)
- [Connect Penpot MCP](#connect-penpot-mcp)

## Install

Docker with the Compose plugin and Python 3.12 or newer have to be there
already, and that `python3` needs `httpx`, `questionary`, `pydantic-settings`
and `PyYAML`. The installer checks and tells you what is missing; it never
installs anything itself.

Run it in the directory that will hold the mockups:

```bash
curl -fsSL https://raw.githubusercontent.com/oberon-systems/penpot-local-stack/main/install/install.sh | bash
```

It downloads the stack and lays it out:

```text
bin/ libs/ config/   the stack, run by the system python3
.penpot.yaml         settings, read from the directory you run in
Makefile             up, down, import, export, extract, convert
templates/           unpacked Penpot exports, empty at first
```

Re-running it replaces `bin/`, `libs/` and `config/`, which is the upgrade,
and keeps `.penpot.yaml` and `templates/`. `--ref` unfolds a branch or a tag
instead of `main`. See [install/README.md](install/README.md) for the details.

## Settings

The installer copies `.penpot.yaml.example` from the repository to
`.penpot.yaml` next to the `Makefile`, and every command reads that file from
the directory it runs in:

```yaml
templates: templates
host: 127.0.0.1
port: 9001
project: penpot-local
version: 2.17.2
```

| Key         | Default                | What it sets                    |
| ----------- | ---------------------- | ------------------------------- |
| `templates` | `templates`            | Where the unpacked exports live |
| `host`      | `127.0.0.1`            | The address Penpot binds to     |
| `port`      | `9001`                 | The port Penpot binds to        |
| `project`   | `penpot-local`         | The Compose project name        |
| `version`   | `2.17.2`               | The Penpot image tag            |
| `email`     | `designer@example.com` | The throwaway profile           |
| `password`  | `penpot-local`         | Its password                    |

Drop a key to fall back to its default. Every key also answers to an
environment variable with a `PENPOT_` prefix, and the variable wins over the
file:

```bash
PENPOT_PORT=9100 make up
```

## Design loop

Start the stack and pick a template or `(empty)`:

```bash
make up
```

`up` creates a throwaway profile and opens the browser already logged in
through the printed `/autologin` link. If that session is lost, log in as
`designer@example.com` with the password `penpot-local`.

Draw in the browser at `http://localhost:9001`, or wherever `port` points. When you are done, pick the
file to export and the template to write it to, then let the stack go down:

```bash
make down
```

`down` writes the export into `templates/<name>/` and runs
`docker compose down -v`, which drops the database and the assets. Pick
`(skip export)` to throw the work away; the wipe is confirmed first whenever
the stack still holds a file.

## Commands

| Target         | What it does                                              |
| -------------- | --------------------------------------------------------- |
| `make up`      | Start the stack, import a template, open the browser      |
| `make down`    | Offer the export, confirm the wipe, stop the stack        |
| `make import`  | Import a template into the running stack, after a confirm |
| `make export`  | Export a file into `templates/`, after a confirm          |
| `make extract` | Unpack a `.penpot` file into `templates/`                 |
| `make convert` | Pack a template into a `.penpot` file                     |

`import` and `export` work against a running stack, so a template can be
swapped in or a file saved off without ending the session. Both ask before
they touch anything: `import` names the template it is about to load, `export`
says whether it writes a new template or overwrites one that is already there.

`extract` and `convert` are the offline pair and need no stack at all.
`extract` lists the `.penpot` files next to you, asks which template to write
and unpacks the archive under the same rules as `export`: frame thumbnails are
dropped, JSON is reformatted, and an archive holding raster images is refused
with the offending files listed. `convert` goes the other way and packs
`templates/<name>/` into `<name>.penpot`, which is what you hand to a Penpot
that is not this one. Both confirm before writing, and say whether they are
creating something or overwriting it.

## Templates

- One directory per template: `manifest.json`, `files/` and `objects/`.
- Templates are read from `templates/` in the current directory. Set
  `PENPOT_TEMPLATES` to read them from somewhere else.
- Images and icons must be SVG. An export that holds raster images is refused
  and the offending files are listed, so you can replace them and export
  again.
- Frame thumbnails are raster renders Penpot rebuilds on its own, so the
  export leaves them out.
- Import keeps the Penpot file id, so a round trip changes only what you drew.

## Connect Penpot MCP

`up` enables MCP for the throwaway profile, issues its key and serves it
behind the fixed `/mcp/claude` URL, so an agent needs the server added only
once. Add it, then restart the agent:

```bash
claude mcp add --transport http penpot http://localhost:9001/mcp/claude
```

After later `up` runs, reconnect `penpot` from `/mcp` instead of restarting.
While the stack is down, the server just shows as failed.

The MCP plugin runs inside the Penpot browser tab. Keep a file open in the
workspace while the agent works; a hidden or unloaded tab stops MCP.
