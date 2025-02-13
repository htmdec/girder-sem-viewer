import base64
import random
from io import BytesIO

import pytest
from girder.constants import AccessType
from girder.models.folder import Folder
from girder.models.item import Item
from PIL import Image
from pytest_girder.assertions import assertStatusOk


@pytest.fixture
def random_tiff():
    buffer = BytesIO()
    image = Image.new("F", (100, 100))
    pixels = image.load()
    for i in range(100):
        for j in range(100):
            pixels[i, j] = random.uniform(0, 255)

    image.save(buffer, format="TIFF")
    buffer.seek(0)
    return buffer


@pytest.fixture
def tiff_item(server, user, random_tiff, fsAssetstore):
    folder = Folder().createFolder(user, "test_folder", parentType="user", public=True)
    Folder().setUserAccess(folder, user, level=AccessType.WRITE, save=True)
    upload = server.uploadFile(
        "random.tiff",
        random_tiff.getvalue(),
        user,
        folder,
        parentType="folder",
        mimeType="image/tiff",
    )
    item = Item().load(upload["itemId"], force=True)
    yield item
    Item().remove(item)
    Folder().remove(folder)


@pytest.mark.plugin("sem_viewer")
def test_no_metadata(server, user, tiff_item):
    resp = server.request(
        path=f"/item/{tiff_item['_id']}/tiff_metadata",
        method="GET",
        user=user,
    )
    assertStatusOk(resp)
    assert resp.json == "[MAIN]\r\nnoheader=1\r\n"


@pytest.mark.plugin("sem_viewer")
def test_img_thumbnail(server, user, tiff_item):
    resp = server.request(
        path=f"/item/{tiff_item['_id']}/tiff_thumbnail",
        method="GET",
        user=user,
    )
    assertStatusOk(resp)
    data = base64.b64decode(resp.body[0])
    image = Image.open(BytesIO(data))
    assert image.format == "PNG"
    assert image.size == (1200, 1200)
