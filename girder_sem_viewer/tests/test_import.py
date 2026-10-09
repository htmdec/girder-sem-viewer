import pytest
from girder.events import Event
from girder.models.folder import Folder
from girder.models.item import Item
from pytest_girder.assertions import assertStatus, assertStatusOk

from girder_sem_viewer import import_sem_data


@pytest.fixture
def folder(server, admin):
    folder = Folder().createFolder(admin, "import_dest", parentType="user", public=True)
    yield folder
    Folder().remove(folder)


def _import(server, admin, assetstore, folder, importPath, **extra):
    params = {
        "importPath": str(importPath),
        "destinationId": str(folder["_id"]),
        "destinationType": "folder",
        "progress": "false",
    }
    params.update(extra)
    return server.request(
        path=f"/assetstore/{assetstore['_id']}/import",
        method="POST",
        user=admin,
        params=params,
    )


def test_default_importer_is_left_alone():
    """Without a dataType we must not prevent girder's own import handler."""
    event = Event("rest.post.assetstore/:id/import.before", {"params": {}, "id": "x"})
    import_sem_data(event)
    assert not event.defaultPrevented
    assert event.responses == []

    event = Event(
        "rest.post.assetstore/:id/import.before",
        {"params": {"dataType": "something-else"}, "id": "x"},
    )
    import_sem_data(event)
    assert not event.defaultPrevented


@pytest.mark.plugin("sem_viewer")
def test_import_rejects_non_folder_destination(server, admin, fsAssetstore, tmp_path):
    resp = _import(
        server,
        admin,
        fsAssetstore,
        {"_id": admin["_id"]},
        tmp_path,
        destinationType="user",
        dataType="sem",
    )
    assertStatus(resp, 400)
    assert resp.json["message"] == "sem data can only be imported to girder folders"


@pytest.mark.plugin("sem_viewer")
def test_import_rejects_missing_path(server, admin, fsAssetstore, folder, tmp_path):
    missing = tmp_path / "nope"
    resp = _import(server, admin, fsAssetstore, folder, missing, dataType="sem")
    assertStatus(resp, 400)
    assert resp.json["message"] == f"Not found: {missing}."


@pytest.mark.plugin("sem_viewer")
def test_import_rejects_non_directory(server, admin, fsAssetstore, folder, tmp_path):
    afile = tmp_path / "a_file.txt"
    afile.write_text("hello")
    resp = _import(server, admin, fsAssetstore, folder, afile, dataType="sem")
    assertStatus(resp, 400)
    assert resp.json["message"] == f"Not a directory: {afile}."


@pytest.mark.plugin("sem_viewer")
def test_import_sem(server, admin, fsAssetstore, folder, tmp_path):
    sub = tmp_path / "run01"
    sub.mkdir()
    (sub / "image.tif").write_bytes(b"not really a tiff")
    (sub / "image-tif.hdr").write_text("[User]\r\nfoo=bar\r\n")
    # No matching .hdr, so this one is skipped entirely.
    (sub / "orphan.tif").write_bytes(b"orphan")
    # Excluded by the fileExcludeRegex the handler forces on.
    (sub / "_.excluded.tif").write_bytes(b"excluded")
    (sub / "_.excluded-tif.hdr").write_text("[User]\r\n")

    resp = _import(server, admin, fsAssetstore, folder, tmp_path, dataType="sem")
    assertStatusOk(resp)
    assert resp.json is None

    imported = Folder().findOne({"parentId": folder["_id"], "name": "run01"})
    assert imported is not None

    item = Item().findOne({"folderId": imported["_id"], "name": "image.tif"})
    assert item is not None
    assert item["meta"] == {"sem": True}
    assert sorted(f["name"] for f in Item().childFiles(item)) == [
        "image-tif.hdr",
        "image.tif",
    ]

    assert Item().findOne({"folderId": imported["_id"], "name": "orphan.tif"}) is None

    excluded = Item().findOne({"folderId": imported["_id"], "name": "_.excluded.tif"})
    assert excluded is not None
    assert list(Item().childFiles(excluded)) == []


@pytest.mark.plugin("sem_viewer")
def test_import_pdv(server, admin, fsAssetstore, folder, tmp_path):
    (tmp_path / "20240115_scan.csv").write_text("a,b\n")
    (tmp_path / "99999999_scan.csv").write_text("a,b\n")
    (tmp_path / "undated.csv").write_text("a,b\n")

    resp = _import(server, admin, fsAssetstore, folder, tmp_path, dataType="pdv")
    assertStatusOk(resp)

    year = Folder().findOne({"parentId": folder["_id"], "name": "2024"})
    assert year is not None
    day = Folder().findOne({"parentId": year["_id"], "name": "20240115"})
    assert day is not None

    item = Item().findOne({"folderId": day["_id"], "name": "20240115_scan.csv"})
    assert item is not None
    assert item["meta"] == {"pdv": True}
    assert [f["name"] for f in Item().childFiles(item)] == ["20240115_scan.csv"]

    # Unparseable dates and names without a date land directly in the destination.
    for name in ("99999999_scan.csv", "undated.csv"):
        assert Item().findOne({"folderId": folder["_id"], "name": name}) is not None
