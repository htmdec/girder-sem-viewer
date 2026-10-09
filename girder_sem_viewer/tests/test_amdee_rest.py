import pytest
from girder.models.folder import Folder
from girder.models.item import Item
from pytest_girder.assertions import assertStatus, assertStatusOk


@pytest.fixture
def folder(server, user):
    folder = Folder().createFolder(user, "test_folder", parentType="user", public=True)
    yield folder
    Folder().remove(folder)


def _subfolder(user, parent, name):
    return Folder().createFolder(parent, name, parentType="folder", creator=user)


@pytest.mark.plugin("sem_viewer")
def test_amdee(server, user, folder):
    resp = server.request(
        path="/amdee/xrd", method="GET", user=user, params={"folderId": folder["_id"]}
    )
    assertStatusOk(resp)
    assert resp.json == {}


@pytest.mark.plugin("sem_viewer")
def test_amdee_requires_login(server, folder):
    resp = server.request(
        path="/amdee/xrd", method="GET", params={"folderId": folder["_id"]}
    )
    assertStatus(resp, 401)


@pytest.mark.plugin("sem_viewer")
def test_amdee_groups_by_sample(server, user, folder):
    """Two scans of the same sample collapse into one partition with two folders."""
    sample = _subfolder(user, folder, "1_2_3_sampleA")
    scan_a = _subfolder(user, sample, "scan001")
    scan_b = _subfolder(user, sample, "scan002")
    for scan in (scan_a, scan_b):
        Item().createItem("foo_master.h5", creator=user, folder=scan)
    # Same sample, same scan folder: the folder id must not be duplicated.
    Item().createItem("bar_master.h5", creator=user, folder=scan_a)

    resp = server.request(
        path="/amdee/xrd", method="GET", user=user, params={"folderId": folder["_id"]}
    )
    assertStatusOk(resp)

    # partition name is run_instruction_sample, i.e. reversed w.r.t. the folder name
    assert list(resp.json) == ["3_2_1"]
    folders = resp.json["3_2_1"]["folders"]
    assert isinstance(folders, list)
    assert sorted(folders) == sorted([str(scan_a["_id"]), str(scan_b["_id"])])


@pytest.mark.plugin("sem_viewer")
def test_amdee_separates_samples(server, user, folder):
    expected = {}
    for name, partition in (
        ("1_2_3_sampleA", "3_2_1"),
        ("4_5_6_sampleB", "6_5_4"),
    ):
        scan = _subfolder(user, _subfolder(user, folder, name), "scan001")
        Item().createItem("foo_master.h5", creator=user, folder=scan)
        expected[partition] = {"folders": [str(scan["_id"])]}

    resp = server.request(
        path="/amdee/xrd", method="GET", user=user, params={"folderId": folder["_id"]}
    )
    assertStatusOk(resp)
    assert resp.json == expected


@pytest.mark.plugin("sem_viewer")
def test_amdee_ignores_unmatched(server, user, folder):
    """Folders that don't look like a sample, and files that aren't master.h5."""
    not_a_sample = _subfolder(user, folder, "scratch")
    Item().createItem("foo_master.h5", creator=user, folder=not_a_sample)

    sample = _subfolder(user, folder, "1_2_3_sampleA")
    Item().createItem("notes.txt", creator=user, folder=sample)

    resp = server.request(
        path="/amdee/xrd", method="GET", user=user, params={"folderId": folder["_id"]}
    )
    assertStatusOk(resp)
    assert resp.json == {}


@pytest.mark.plugin("sem_viewer")
def test_amdee_rejects_unknown_folder(server, user):
    resp = server.request(
        path="/amdee/xrd",
        method="GET",
        user=user,
        params={"folderId": "000000000000000000000000"},
    )
    assertStatus(resp, 400)
