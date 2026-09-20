import zipfile

import pytest

from libs import cli, prompts
from libs.templates import pack


def test_main_rejects_an_unknown_command(monkeypatch):
    monkeypatch.setattr(cli.sys, "argv", ["penpot-stack", "restart"])

    with pytest.raises(SystemExit, match="usage"):
        cli.main()


def test_write_asks_before_replacing_a_template(tmp_path, monkeypatch):
    (tmp_path / "templates" / "alpha").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prompts, "target", lambda existing: "alpha")
    asked = []
    monkeypatch.setattr(prompts, "confirm", lambda question: bool(asked.append(question)))
    saved = []
    monkeypatch.setattr(cli, "save", lambda *args: saved.append(args))

    assert cli.write(None, "file-id") is False
    assert asked[0].startswith("Overwrite")
    assert saved == []


def test_write_exports_once_confirmed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prompts, "target", lambda existing: "alpha")
    monkeypatch.setattr(prompts, "confirm", lambda question: True)
    saved = []
    monkeypatch.setattr(cli, "save", lambda *args: saved.append(args))

    assert cli.write(None, "file-id") is True
    assert saved == [(None, "file-id", tmp_path / "templates" / "alpha")]


def test_write_stops_when_the_template_pick_is_cancelled(monkeypatch):
    monkeypatch.setattr(prompts, "target", lambda existing: None)
    monkeypatch.setattr(prompts, "confirm", lambda question: pytest.fail("asked anyway"))

    assert cli.write(None, "file-id") is False


def test_down_keeps_everything_when_the_wipe_is_refused(monkeypatch):
    monkeypatch.setattr(cli, "connect", lambda wait: object())
    monkeypatch.setattr(cli, "rpc", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "choices", lambda client: ["a file"])
    monkeypatch.setattr(prompts, "select", lambda question, options: prompts.SKIP)
    monkeypatch.setattr(prompts, "confirm", lambda question: False)
    calls = []
    monkeypatch.setattr(cli, "compose", lambda *args: calls.append(args))

    cli.down()

    assert calls == []


def test_down_drops_a_stack_that_holds_nothing(monkeypatch):
    monkeypatch.setattr(cli, "connect", lambda wait: object())
    monkeypatch.setattr(cli, "rpc", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "choices", lambda client: [])
    monkeypatch.setattr(prompts, "confirm", lambda question: pytest.fail("asked anyway"))
    calls = []
    monkeypatch.setattr(cli, "compose", lambda *args: calls.append(args))

    cli.down()

    assert calls == [("down", "-v")]


def test_import_asks_before_touching_the_stack(tmp_path, monkeypatch):
    (tmp_path / "templates" / "alpha").mkdir(parents=True)
    (tmp_path / "templates" / "alpha" / "manifest.json").write_text("{}")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prompts, "source", lambda existing: "alpha")
    monkeypatch.setattr(prompts, "confirm", lambda question: False)
    monkeypatch.setattr(cli, "session", lambda: pytest.fail("connected anyway"))

    cli.restore()


def template(base, name, content='{"old": true}'):
    target = base / "templates" / name
    target.mkdir(parents=True)
    (target / "manifest.json").write_text(content)
    return target


def test_extract_asks_before_replacing_a_template(tmp_path, monkeypatch):
    source = tmp_path / "drop"
    source.mkdir()
    (source / "manifest.json").write_text('{"new": true}')
    (tmp_path / "design.penpot").write_bytes(pack(source))
    kept = template(tmp_path, "alpha")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prompts, "select", lambda question, options: options[0].value)
    monkeypatch.setattr(prompts, "target", lambda existing: "alpha")
    asked = []
    monkeypatch.setattr(prompts, "confirm", lambda question: bool(asked.append(question)))

    cli.extract()

    assert asked[0].startswith("Overwrite")
    assert (kept / "manifest.json").read_text() == '{"old": true}'


def test_extract_unpacks_once_confirmed(tmp_path, monkeypatch):
    source = tmp_path / "drop"
    source.mkdir()
    (source / "manifest.json").write_text('{"new": true}')
    (tmp_path / "design.penpot").write_bytes(pack(source))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prompts, "select", lambda question, options: options[0].value)
    monkeypatch.setattr(prompts, "target", lambda existing: "beta")
    monkeypatch.setattr(prompts, "confirm", lambda question: True)

    cli.extract()

    written = tmp_path / "templates" / "beta" / "manifest.json"
    assert written.read_text() == '{\n  "new": true\n}\n'


def test_convert_packs_the_template_next_to_you(tmp_path, monkeypatch):
    template(tmp_path, "alpha")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prompts, "source", lambda existing: "alpha")
    monkeypatch.setattr(prompts, "confirm", lambda question: True)

    cli.convert()

    assert zipfile.ZipFile(tmp_path / "alpha.penpot").namelist() == ["manifest.json"]


def test_convert_asks_before_overwriting_an_archive(tmp_path, monkeypatch):
    template(tmp_path, "alpha")
    (tmp_path / "alpha.penpot").write_bytes(b"old")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prompts, "source", lambda existing: "alpha")
    asked = []
    monkeypatch.setattr(prompts, "confirm", lambda question: bool(asked.append(question)))

    cli.convert()

    assert asked[0].startswith("Overwrite")
    assert (tmp_path / "alpha.penpot").read_bytes() == b"old"
