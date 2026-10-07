"""The shipped Compose definition and the nginx route that publishes MCP."""

import json
import os
import secrets
import subprocess
import tempfile
from pathlib import Path

from .settings import Settings, settings

IMAGES = ("frontend", "backend", "mcp", "exporter")


def directory() -> Path:
    here = Path(__file__).resolve().parent
    # Installed, the stack files sit inside the package; in a checkout they are next to libs/.
    roots = (here / "config", here.parent / "config")
    return next(p for p in roots if (p / "compose.yaml").is_file())


def environment(config: Settings) -> dict[str, str]:
    return {
        "PENPOT_PROJECT": config.project,
        "PENPOT_HOST": config.host,
        "PENPOT_PORT": str(config.port),
        "PENPOT_URI": config.url,
        "PENPOT_SECRET_KEY": secrets.token_urlsafe(48),
    }


def pinned(version: str) -> str:
    # The shipped tags stay literal so Dependabot can bump them; a chosen version layers on top.
    services = {f"penpot-{name}": {"image": f"penpotapp/{name}:{version}"} for name in IMAGES}
    return json.dumps({"services": services})


def compose(*args: str) -> None:
    config = settings()
    env = {**environment(config), **os.environ}
    with tempfile.TemporaryDirectory() as scratch:
        files = [directory() / "compose.yaml"]
        if config.version:
            files.append(Path(scratch) / "version.yaml")
            files[-1].write_text(pinned(config.version))
        flags = [flag for path in files for flag in ("-f", str(path))]
        subprocess.run(["docker", "compose", *flags, *args], check=True, env=env)  # noqa: S603, S607


def publish(key: str) -> None:
    location = (
        "location = /mcp/claude {\n"
        f"    rewrite ^ /mcp?userToken={key} break;\n"
        "    proxy_pass http://penpot-mcp:4401;\n"
        "    proxy_http_version 1.1;\n"
        "    proxy_buffering off;\n"
        "}\n"
    )
    script = 'printf "%s" "$1" > /etc/nginx/overrides/server.d/claude-mcp.conf && nginx -s reload'
    compose("exec", "-T", "penpot-frontend", "sh", "-c", script, "sh", location)
