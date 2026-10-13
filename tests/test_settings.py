from pathlib import Path

from libs.settings import settings


def test_defaults_without_a_settings_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    config = settings()

    assert config.templates == Path("templates")
    assert config.port == 9001
    assert config.url == "http://penpot-local.localhost:9001"
    assert config.endpoint == "http://localhost:9001"


def test_penpot_yaml_is_read_from_the_working_directory(tmp_path, monkeypatch):
    (tmp_path / ".penpot.yaml").write_text("templates: shapes\nport: 9100\nversion: 2.18.0\n")
    monkeypatch.chdir(tmp_path)

    config = settings()

    assert config.templates == Path("shapes")
    assert config.port == 9100
    assert config.version == "2.18.0"
    assert config.url == "http://penpot-local.localhost:9100"


def test_the_environment_wins_over_the_file(tmp_path, monkeypatch):
    (tmp_path / ".penpot.yaml").write_text("port: 9100\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PENPOT_PORT", "9200")

    assert settings().port == 9200


def test_a_bind_to_every_interface_is_still_opened_as_localhost(tmp_path, monkeypatch):
    (tmp_path / ".penpot.yaml").write_text("host: 0.0.0.0\nport: 9001\n")
    monkeypatch.chdir(tmp_path)

    assert settings().url == "http://penpot-local.localhost:9001"
    assert settings().endpoint == "http://localhost:9001"


def test_each_local_project_gets_its_own_browser_host(tmp_path, monkeypatch):
    (tmp_path / ".penpot.yaml").write_text("project: alpha\nport: 9002\n")
    monkeypatch.chdir(tmp_path)

    assert settings().url == "http://alpha.localhost:9002"


def test_a_named_host_reaches_the_browser_as_written(tmp_path, monkeypatch):
    (tmp_path / ".penpot.yaml").write_text("host: penpot.example.com\n")
    monkeypatch.chdir(tmp_path)

    assert settings().url == "http://penpot.example.com:9001"
    assert settings().endpoint == "http://penpot.example.com:9001"
