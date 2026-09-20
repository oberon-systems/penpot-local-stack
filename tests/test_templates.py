import io
import json
import zipfile

import pytest

from libs import templates


def test_root_follows_the_settings(tmp_path, monkeypatch):
    (tmp_path / ".penpot.yaml").write_text("templates: shapes\n")
    monkeypatch.chdir(tmp_path)

    assert templates.root() == tmp_path / "shapes"


def test_root_follows_the_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PENPOT_TEMPLATES", str(tmp_path / "elsewhere"))

    assert templates.root() == tmp_path / "elsewhere"


def test_names_lists_only_unpacked_exports(tmp_path, monkeypatch):
    (tmp_path / "templates" / "alpha").mkdir(parents=True)
    (tmp_path / "templates" / "alpha" / "manifest.json").write_text("{}")
    (tmp_path / "templates" / "beta").mkdir()
    monkeypatch.chdir(tmp_path)

    assert templates.names() == ["alpha"]


def test_entries_drop_thumbnails_and_the_objects_behind_them(archive):
    thumbnail = json.dumps({"mediaId": "abc"}).encode()
    zf = archive(
        {
            "files/one/thumbnails/frame.json": thumbnail,
            "objects/abc.svg": b"<svg/>",
            "files/one.json": b"{}",
        }
    )

    assert templates.entries(zf) == ["files/one.json"]


def test_unpack_refuses_raster_images(tmp_path, archive):
    zf = archive({"manifest.json": b"{}", "objects/one.png": b"raster"})

    with pytest.raises(SystemExit, match="only SVG"):
        templates.unpack(zf, tmp_path / "alpha")


def test_unpack_pretty_prints_json_and_keeps_svg(tmp_path, archive):
    zf = archive({"manifest.json": b'{"a":1}', "objects/one.svg": b"<svg/>"})
    target = tmp_path / "alpha"

    templates.unpack(zf, target)

    assert (target / "manifest.json").read_text() == '{\n  "a": 1\n}\n'
    assert (target / "objects" / "one.svg").read_bytes() == b"<svg/>"


def test_unpack_replaces_the_previous_export(tmp_path, archive):
    target = tmp_path / "alpha"
    target.mkdir()
    (target / "stale.json").write_text("{}")

    templates.unpack(archive({"manifest.json": b"{}"}), target)

    assert not (target / "stale.json").exists()


def test_archives_lists_the_penpot_files_next_to_you(tmp_path, monkeypatch):
    (tmp_path / "design.penpot").write_bytes(b"")
    (tmp_path / "notes.txt").write_text("")
    monkeypatch.chdir(tmp_path)

    assert [p.name for p in templates.archives()] == ["design.penpot"]


def test_pack_round_trips_through_unpack(tmp_path):
    source = tmp_path / "alpha"
    (source / "objects").mkdir(parents=True)
    (source / "manifest.json").write_text('{"a": 1}')
    (source / "objects" / "one.svg").write_text("<svg/>")
    back = tmp_path / "back"

    templates.unpack(zipfile.ZipFile(io.BytesIO(templates.pack(source))), back)

    assert (back / "manifest.json").read_text() == '{\n  "a": 1\n}\n'
    assert (back / "objects" / "one.svg").read_text() == "<svg/>"
