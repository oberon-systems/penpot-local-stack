import io
import json
import zipfile

import pytest

from libs import templates

ROOT = "00000000-0000-0000-0000-000000000000"


def page(*shapes: dict) -> dict[str, bytes]:
    root = {"id": ROOT, "shapes": [s["id"] for s in shapes]}
    return {f"files/f/pages/p/{s['id']}.json": json.dumps(s).encode() for s in (root, *shapes)}


def used(storage: str) -> dict[str, bytes]:
    return {
        **page({"id": "image", "fills": [{"fillImage": {"id": "media"}}]}),
        "files/f/media/media.json": json.dumps({"id": "media", "mediaId": storage}).encode(),
    }


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
    zf = archive({"manifest.json": b"{}", "objects/one.png": b"raster", **used("one")})

    with pytest.raises(SystemExit, match="only SVG"):
        templates.unpack(zf, tmp_path / "alpha")


def test_unpack_pretty_prints_json_and_keeps_svg(tmp_path, archive):
    zf = archive({"manifest.json": b'{"a":1}', "objects/one.svg": b"<svg/>", **used("one")})
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
    for name, content in used("one").items():
        (source / name).parent.mkdir(parents=True, exist_ok=True)
        (source / name).write_bytes(content)
    back = tmp_path / "back"

    templates.unpack(zipfile.ZipFile(io.BytesIO(templates.pack(source))), back)

    assert (back / "manifest.json").read_text() == '{\n  "a": 1\n}\n'
    assert (back / "objects" / "one.svg").read_text() == "<svg/>"


def test_entries_drop_shapes_unreachable_from_the_root(archive):
    shapes = page({"id": "kept", "shapes": []})
    shapes["files/f/pages/p/lost.json"] = json.dumps({"id": "lost"}).encode()

    assert sorted(templates.entries(archive(shapes))) == sorted(
        [f"files/f/pages/p/{ROOT}.json", "files/f/pages/p/kept.json"]
    )


def test_entries_drop_deleted_components_nothing_copies(archive):
    zf = archive(
        {
            **page({"id": "copy", "componentId": "held"}),
            "files/f/components/held.json": json.dumps({"id": "held", "deleted": True}).encode(),
            "files/f/components/gone.json": json.dumps({"id": "gone", "deleted": True}).encode(),
            "files/f/components/live.json": json.dumps({"id": "live"}).encode(),
        }
    )

    kept = templates.entries(zf)

    assert "files/f/components/held.json" in kept
    assert "files/f/components/live.json" in kept
    assert "files/f/components/gone.json" not in kept


def test_entries_drop_media_only_deleted_components_use(archive):
    fills = [{"fillImage": {"id": "orphan"}}]
    component = {"id": "gone", "deleted": True, "objects": {"x": {"fills": fills}}}
    zf = archive(
        {
            **used("kept"),
            "objects/kept.json": b"{}",
            "objects/kept.svg": b"<svg/>",
            "files/f/components/gone.json": json.dumps(component).encode(),
            "files/f/media/orphan.json": json.dumps({"mediaId": "dropped"}).encode(),
            "objects/dropped.json": b"{}",
            "objects/dropped.png": b"raster",
        }
    )

    kept = templates.entries(zf)

    assert {"files/f/media/media.json", "objects/kept.json", "objects/kept.svg"} <= set(kept)
    assert not {n for n in kept if "orphan" in n or "dropped" in n or "gone" in n}


def test_entries_keep_only_what_the_live_state_holds(archive):
    zf = archive(
        {
            **page({"id": "kept", "shapes": []}, {"id": "gone"}),
            "files/f/pages/p.json": b"{}",
            "files/f/pages/q.json": b"{}",
            f"files/f/pages/q/{ROOT}.json": json.dumps({"shapes": []}).encode(),
            "files/f/components/live.json": b"{}",
            "files/f/components/gone.json": b"{}",
        }
    )
    current = {
        "pages": {"p": {"name": "Page", "shapes": {ROOT: "Root", "kept": "Kept"}}},
        "components": {"live": "Live"},
    }

    assert sorted(templates.entries(zf, current)) == sorted(
        [
            "files/f/pages/p.json",
            f"files/f/pages/p/{ROOT}.json",
            "files/f/pages/p/kept.json",
            "files/f/components/live.json",
        ]
    )


def test_unpack_writes_the_state_and_pack_leaves_it_out(tmp_path, archive):
    current = {"pages": {}, "components": {}}
    target = tmp_path / "alpha"

    templates.unpack(archive({"manifest.json": b"{}"}), target, current)

    assert json.loads((target / "state.json").read_text()) == current
    packed = zipfile.ZipFile(io.BytesIO(templates.pack(target)))
    assert packed.namelist() == ["manifest.json"]
