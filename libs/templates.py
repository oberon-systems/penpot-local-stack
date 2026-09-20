"""Templates on disk: unpacked Penpot exports the stack imports from and exports back to."""

import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

import httpx

from .penpot import rpc, stream
from .settings import settings


def root() -> Path:
    return settings().templates.resolve()


def names() -> list[str]:
    return sorted(p.parent.name for p in root().glob("*/manifest.json"))


def archives() -> list[Path]:
    return sorted(Path.cwd().glob("*.penpot"))


def pack(source: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
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


def entries(archive: zipfile.ZipFile) -> list[str]:
    # Frame thumbnails are raster renders Penpot regenerates, so they never reach the template.
    thumbnails = [n for n in archive.namelist() if "/thumbnails/" in n]
    objects = {f"objects/{json.loads(archive.read(n))['mediaId']}." for n in thumbnails}
    return [
        n
        for n in archive.namelist()
        if n not in thumbnails and not n.startswith(tuple(objects)) and not n.endswith("/")
    ]


def unpack(archive: zipfile.ZipFile, target: Path) -> None:
    kept = entries(archive)
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


def save(client: httpx.Client, file_id: str, target: Path) -> None:
    unpack(download(client, file_id), target)
