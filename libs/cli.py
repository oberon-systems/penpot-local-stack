"""The four commands the stack exposes: up, down, import and export."""

import sys
import webbrowser
import zipfile
from pathlib import Path

import httpx
import questionary

from . import prompts
from .compose import compose, publish
from .penpot import connect, drafts, files, profile, register, rpc, session
from .settings import settings
from .templates import archives, load, names, pack, root, save, unpack


def choices(client: httpx.Client) -> list[questionary.Choice]:
    return [questionary.Choice(label, value=value) for label, value in files(client)]


def write(client: httpx.Client, file_id: str) -> bool:
    name = prompts.target(names())
    if name is None:
        return False
    target = root() / name
    known = "Overwrite" if target.exists() else "Export to"
    if not prompts.confirm(f"{known} templates/{name}?"):
        return False
    save(client, file_id, target)
    print(f"exported to {target}")
    return True


def up() -> None:
    template = prompts.source(names(), extra=[prompts.EMPTY])
    if template is None:
        return
    compose("up", "-d", "--wait")
    url = settings().url
    client = connect(wait=300)
    if client is None:
        sys.exit(f"penpot is not answering on {url}")
    publish(register(client))
    if template != prompts.EMPTY:
        load(client, drafts(client), root() / template)
    login = f"{url}/autologin?token={client.cookies['auth-token']}"
    webbrowser.open(login)
    print(f"\nPenpot: {login}")
    print(f"MCP:    {url}/mcp/claude")


def down() -> None:
    client = connect(wait=0)
    if client is not None:
        rpc(client, "login-with-password", **profile())
        stored = choices(client)
        if stored:
            file_id = prompts.select("Export file", [prompts.SKIP, *stored])
            if file_id is None:
                return
            if file_id != prompts.SKIP and not write(client, file_id):
                return
            if not prompts.confirm("Drop the stack and everything left in it?"):
                return
    compose("down", "-v")


def export() -> None:
    client = session()
    stored = choices(client)
    if not stored:
        sys.exit("the stack holds no files to export")
    file_id = prompts.select("Export file", stored)
    if file_id is not None:
        write(client, file_id)


def restore() -> None:
    available = names()
    if not available:
        sys.exit(f"no templates in {root()} to import")
    name = prompts.source(available)
    if name is None or not prompts.confirm(f"Import {name} into the stack?"):
        return
    client = session()
    load(client, drafts(client), root() / name)
    print(f"imported {name}")


def extract() -> None:
    found = archives()
    if not found:
        sys.exit("no .penpot files in the current directory")
    source = prompts.select("Penpot file", [questionary.Choice(p.name, value=p) for p in found])
    if source is None:
        return
    name = prompts.target(names())
    if name is None:
        return
    target = root() / name
    known = "Overwrite" if target.exists() else "Extract into"
    if not prompts.confirm(f"{known} templates/{name}?"):
        return
    unpack(zipfile.ZipFile(source), target)
    print(f"extracted to {target}")


def convert() -> None:
    available = names()
    if not available:
        sys.exit(f"no templates in {root()} to convert")
    name = prompts.source(available)
    if name is None:
        return
    target = Path.cwd() / f"{name}.penpot"
    known = "Overwrite" if target.exists() else "Write"
    if not prompts.confirm(f"{known} {target.name}?"):
        return
    target.write_bytes(pack(root() / name))
    print(f"packed into {target}")


def main() -> None:
    commands = {
        "up": up,
        "down": down,
        "import": restore,
        "export": export,
        "extract": extract,
        "convert": convert,
    }
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        sys.exit(f"usage: {Path(sys.argv[0]).name} {{{'|'.join(commands)}}}")
    commands[sys.argv[1]]()
