"""The shipped Compose definition and the nginx route that publishes MCP."""

import os
import secrets
import subprocess
from pathlib import Path

from .settings import Settings, settings


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
        "PENPOT_VERSION": config.version,
        "PENPOT_URI": config.url,
        "PENPOT_SECRET_KEY": secrets.token_urlsafe(48),
    }


def compose(*args: str) -> None:
    env = {**environment(settings()), **os.environ}
    command = ["docker", "compose", "-f", str(directory() / "compose.yaml"), *args]
    subprocess.run(command, check=True, env=env)  # noqa: S603, S607


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
