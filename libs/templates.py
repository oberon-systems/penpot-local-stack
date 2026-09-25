"""Templates on disk: unpacked Penpot exports the stack imports from and exports back to."""

import io
import json
import re
import shutil
import sys
import zipfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any

import httpx

from .penpot import rpc, state, stream
from .settings import settings

ROOT = "00000000-0000-0000-0000-000000000000"
SHAPE = re.compile(r"(files/[^/]+/pages/[^/]+/)[^/]+\.json$")
TRACKED = re.compile(r"files/[^/]+/((?:pages|components)/.+)$")
STATE = "state.json"


def root() -> Path:
    return settings().templates.resolve()


def names() -> list[str]:
    return sorted(p.parent.name for p in root().glob("*/manifest.json"))


def archives() -> list[Path]:
    return sorted(Path.cwd().glob("*.penpot"))


def pack(source: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in source.rglob("*") if p.is_file() and p != source / STATE):
            archive.write(path, path.relative_to(source).as_posix())
    return buffer.getvalue()


def load(client: httpx.Client, project: str, source: Path) -> None:
    file_id = json.loads((source / "manifest.json").read_text())["files"][0]["id"]
    rpc(client, "create-file", id=file_id, name=source.name, projectId=project)
    stream(
        client,
        "import-binfile",
        data={"name": source.name, "project-id": project, "file-id": file_id},
        files={"file": (f"{source.name}.penpot", pack(source), "application/zip")},
    )


def download(client: httpx.Client, file_id: str) -> zipfile.ZipFile:
    result = stream(
        client,
        "export-binfile",
        json={"fileId": file_id, "includeLibraries": False, "embedAssets": True},
    )
    # Transit encodes the link either as a tagged string or as a tagged map, depending on Penpot.
    url = re.search(r'"~r([^"]+)"|"~#uri"\s*:\s*"([^"]+)"', result)
    if url is None:
        sys.exit(f"export-binfile: no download link in {result}")
    response = client.get(url.group(1) or url.group(2))
    response.raise_for_status()
    return zipfile.ZipFile(io.BytesIO(response.content))


def entries(archive: zipfile.ZipFile, current: dict[str, Any] | None = None) -> list[str]:
    # Frame thumbnails are raster renders Penpot regenerates, so they never reach the template.
    thumbnails = [n for n in archive.namelist() if "/thumbnails/" in n]
    objects = {f"objects/{json.loads(archive.read(n))['mediaId']}." for n in thumbnails}
    kept = [
        n
        for n in archive.namelist()
        if n not in thumbnails and not n.startswith(tuple(objects)) and not n.endswith("/")
    ]
    return live(archive, kept, current)


def key(name: str) -> str:
    return PurePosixPath(name).name.split(".")[0]


def live(archive: zipfile.ZipFile, names: list[str], current: dict[str, Any] | None) -> list[str]:
    # Penpot keeps deleted work in the export until its own GC runs; the live state decides
    # on export, while an offline extract has only reachability to go by.
    texts = {n: archive.read(n).decode() for n in names if n.endswith(".json")}
    kept = tracked(names, current) if current else reachable(texts, names)
    kept = prune(texts, kept, lambda n: "/components/" in n and json.loads(texts[n]).get("deleted"))
    kept = prune(texts, kept, lambda n: "/media/" in n)
    return prune(texts, kept, lambda n: n.startswith("objects/"))


def tracked(names: list[str], current: dict[str, Any]) -> list[str]:
    pages = current["pages"]
    known = {f"pages/{p}.json" for p in pages}
    known |= {f"pages/{p}/{s}.json" for p, page in pages.items() for s in page["shapes"]}
    known |= {f"components/{c}.json" for c in current["components"]}
    return [n for n in names if not (m := TRACKED.match(n)) or m.group(1) in known]


def reachable(texts: dict[str, str], names: list[str]) -> list[str]:
    shapes = {n: json.loads(texts[n]) for n in names if SHAPE.match(n)}
    seen: set[str] = set()
    todo = [n for n in shapes if key(n) == ROOT]
    while todo:
        name = todo.pop()
        if name in seen or name not in shapes:
            continue
        seen.add(name)
        page = SHAPE.match(name).group(1)  # type: ignore[union-attr]
        todo += [f"{page}{child}.json" for child in shapes[name].get("shapes", [])]
    return [n for n in names if n not in shapes or n in seen]


def prune(texts: dict[str, str], names: list[str], candidate: Callable[[str], bool]) -> list[str]:
    # A candidate lives while any other kept JSON mentions its id,
    # so a deleted component that live copies still point at stays.
    while True:
        dead = {
            n
            for n in names
            if candidate(n)
            and not any(key(n) in texts[o] for o in names if o in texts and key(o) != key(n))
        }
        if not dead:
            return names
        names = [n for n in names if n not in dead]


def unpack(archive: zipfile.ZipFile, target: Path, current: dict[str, Any] | None = None) -> None:
    kept = entries(archive, current)
    raster = [n for n in kept if not n.endswith((".json", ".svg"))]
    if raster:
        sys.exit("only SVG images are allowed, replace these:\n  " + "\n  ".join(raster))
    shutil.rmtree(target, ignore_errors=True)
    for name in kept:
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        content = archive.read(name)
        if name.endswith(".json"):
            content = (json.dumps(json.loads(content), indent=2) + "\n").encode()
        path.write_bytes(content)
    if current:
        (target / STATE).write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n")


def save(client: httpx.Client, file_id: str, target: Path) -> None:
    unpack(download(client, file_id), target, state(client, file_id))
