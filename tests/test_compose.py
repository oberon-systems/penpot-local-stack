import json
from pathlib import Path

from libs import compose as module


def test_the_package_carries_the_stack_files():
    assert (module.directory() / "compose.yaml").is_file()
    assert (module.directory() / "autologin.conf").is_file()


def test_compose_runs_docker_against_the_shipped_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PENPOT_VERSION", raising=False)
    seen = {}

    def run(command, **kwargs):
        seen["command"] = command
        seen["env"] = kwargs["env"]

    monkeypatch.setattr(module.subprocess, "run", run)
    module.compose("up", "-d", "--wait")

    assert seen["command"][:3] == ["docker", "compose", "-f"]
    assert seen["command"][3].endswith("compose.yaml")
    assert seen["command"][4:] == ["up", "-d", "--wait"]
    assert seen["env"]["PENPOT_SECRET_KEY"]


def test_the_compose_environment_follows_the_settings(tmp_path, monkeypatch):
    (tmp_path / ".penpot.yaml").write_text("port: 9100\nproject: mockups\nversion: 2.18.0\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PENPOT_PORT", raising=False)
    seen = {}

    monkeypatch.setattr(module.subprocess, "run", lambda command, **kwargs: seen.update(kwargs))
    module.compose("up")

    assert seen["env"]["PENPOT_PORT"] == "9100"
    assert seen["env"]["PENPOT_PROJECT"] == "mockups"
    assert seen["env"]["PENPOT_URI"] == "http://localhost:9100"


def test_a_chosen_version_layers_its_tags_over_the_shipped_file(tmp_path, monkeypatch):
    (tmp_path / ".penpot.yaml").write_text("version: 2.18.0\n")
    monkeypatch.chdir(tmp_path)
    seen = {}

    def run(command, **kwargs):
        seen["command"] = command
        seen["override"] = json.loads(Path(command[5]).read_text())

    monkeypatch.setattr(module.subprocess, "run", run)
    module.compose("up")

    assert seen["command"][2:5] == ["-f", str(module.directory() / "compose.yaml"), "-f"]
    assert seen["command"][6:] == ["up"]
    assert seen["override"]["services"]["penpot-backend"]["image"] == "penpotapp/backend:2.18.0"
    assert len(seen["override"]["services"]) == len(module.IMAGES)
    assert not Path(seen["command"][5]).exists()
