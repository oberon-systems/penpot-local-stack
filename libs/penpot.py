"""The Penpot RPC API: the throwaway profile, the session and the calls the commands need."""

import sys
import time
from typing import Any

import httpx

from .settings import settings


def profile() -> dict[str, str]:
    config = settings()
    return {"email": config.email, "password": config.password}


def rpc(client: httpx.Client, command: str, **params: Any) -> Any:
    response = client.post(f"/api/rpc/command/{command}", json=params)
    if response.is_error:
        sys.exit(f"{command}: {response.status_code} {response.text}")
    return response.json() if response.content else None


def stream(client: httpx.Client, command: str, **kwargs: Any) -> str:
    event = ""
    with client.stream("POST", f"/api/rpc/command/{command}", **kwargs) as response:
        if response.is_error:
            sys.exit(f"{command}: {response.status_code} {response.read().decode()}")
        for line in response.iter_lines():
            if line.startswith("event:"):
                event = line.removeprefix("event:").strip()
            elif line.startswith("data:") and event in ("end", "error"):
                if event == "error":
                    sys.exit(f"{command}: {line}")
                return line.removeprefix("data:")
    sys.exit(f"{command}: stream closed without a result")


def connect(wait: float) -> httpx.Client | None:
    client = httpx.Client(
        base_url=settings().url,
        headers={"Accept": "application/json"},
        timeout=60,
        follow_redirects=True,
    )
    deadline = time.monotonic() + wait
    while True:
        try:
            if client.post("/api/rpc/command/get-profile", json={}).is_success:
                return client
        except httpx.TransportError:
            pass
        if time.monotonic() > deadline:
            return None
        time.sleep(2)


def session() -> httpx.Client:
    client = connect(wait=0)
    if client is None:
        sys.exit(f"penpot is not answering on {settings().url}, run `up` first")
    rpc(client, "login-with-password", **profile())
    return client


def register(client: httpx.Client) -> str:
    token = rpc(client, "prepare-register-profile", fullname="Designer", **profile())["token"]
    rpc(client, "register-profile", token=token)
    rpc(client, "update-profile-props", props={"mcpEnabled": True})
    return str(rpc(client, "create-access-token", name="mcp", type="mcp")["token"])


def drafts(client: httpx.Client) -> str:
    projects = rpc(client, "get-all-projects")
    return str(next(p["id"] for p in projects if p["isDefault"] and p["isDefaultTeam"]))


def files(client: httpx.Client) -> list[tuple[str, str]]:
    return [
        (f"{project['name']} / {file['name']}", file["id"])
        for project in rpc(client, "get-all-projects")
        for file in rpc(client, "get-project-files", projectId=project["id"])
    ]
