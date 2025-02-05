import pytest
from girder.models.folder import Folder
from pytest_girder.assertions import assertStatusOk


@pytest.fixture
def folder(server, user):
    folder = Folder().createFolder(user, "test_folder", parentType="user", public=True)
    yield folder
    Folder().remove(folder)


@pytest.mark.plugin("sem_viewer")
def test_amdee(server, user, folder):
    resp = server.request(
        path="/amdee/xrd", method="GET", user=user, params={"folderId": folder["_id"]}
    )
    assertStatusOk(resp)
