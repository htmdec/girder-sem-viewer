import base64
import random
from io import BytesIO

import numpy
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
def folder(server, user):
    folder = Folder().createFolder(user, "test_folder", parentType="user", public=True)
    Folder().setUserAccess(folder, user, level=AccessType.WRITE, save=True)
    yield folder
    Folder().remove(folder)


@pytest.fixture
def tiff_item(server, user, random_tiff, folder, fsAssetstore):
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


@pytest.fixture
def uint16_tiff():
    rng = numpy.random.default_rng(42)
    arr = rng.integers(0, 65535, size=(100, 100), dtype=numpy.uint16)
    buffer = BytesIO()
    Image.fromarray(arr).save(buffer, format="TIFF")
    buffer.seek(0)
    return buffer


@pytest.fixture
def uint16_tiff_item(server, user, uint16_tiff, folder, fsAssetstore):
    upload = server.uploadFile(
        "uint16.tiff",
        uint16_tiff.getvalue(),
        user,
        folder,
        parentType="folder",
        mimeType="image/tiff",
    )
    item = Item().load(upload["itemId"], force=True)
    yield item
    Item().remove(item)


@pytest.fixture
def empty_item(server, user, folder):
    item = Item().createItem("no_files", creator=user, folder=folder)
    yield item
    Item().remove(item)


@pytest.fixture
def text_item(server, user, folder, fsAssetstore):
    upload = server.uploadFile(
        "notes.txt",
        b"this is not an image",
        user,
        folder,
        parentType="folder",
        mimeType="text/plain",
    )
    item = Item().load(upload["itemId"], force=True)
    yield item
    Item().remove(item)


@pytest.fixture
def item_with_header(server, user, folder, random_tiff, fsAssetstore):
    """A tiff whose header lives in a separate file referenced by item metadata."""
    header_upload = server.uploadFile(
        "header.hdr",
        b"[User]\r\nSystemType=SEM\r\n",
        user,
        folder,
        parentType="folder",
        mimeType="text/plain",
    )
    upload = server.uploadFile(
        "with_header.tiff",
        random_tiff.getvalue(),
        user,
        folder,
        parentType="folder",
        mimeType="image/tiff",
    )
    item = Item().load(upload["itemId"], force=True)
    item = Item().setMetadata(item, {"headerId": str(header_upload["_id"])})
    yield item
    Item().remove(item)
    Item().remove(Item().load(header_upload["itemId"], force=True))


@pytest.mark.plugin("sem_viewer")
def test_metadata_item_without_files(server, user, empty_item):
    resp = server.request(
        path=f"/item/{empty_item['_id']}/tiff_metadata",
        method="GET",
        user=user,
    )
    assertStatusOk(resp)
    assert resp.json is None


@pytest.mark.plugin("sem_viewer")
def test_thumbnail_item_without_files(server, user, empty_item):
    resp = server.request(
        path=f"/item/{empty_item['_id']}/tiff_thumbnail",
        method="GET",
        user=user,
    )
    assertStatusOk(resp)
    assert resp.json is None


@pytest.mark.plugin("sem_viewer")
def test_metadata_from_item_meta(server, user, item_with_header):
    resp = server.request(
        path=f"/item/{item_with_header['_id']}/tiff_metadata",
        method="GET",
        user=user,
    )
    assertStatusOk(resp)
    assert resp.json == "[User]\r\nSystemType=SEM\r\n"


@pytest.mark.plugin("sem_viewer")
def test_metadata_with_dangling_header_id(server, user, folder, random_tiff, fsAssetstore):
    upload = server.uploadFile(
        "dangling.tiff",
        random_tiff.getvalue(),
        user,
        folder,
        parentType="folder",
        mimeType="image/tiff",
    )
    item = Item().load(upload["itemId"], force=True)
    Item().setMetadata(item, {"headerId": "000000000000000000000000"})

    resp = server.request(
        path=f"/item/{item['_id']}/tiff_metadata",
        method="GET",
        user=user,
    )
    assertStatusOk(resp)
    assert resp.json == "[MAIN]\r\nnoheader=1\r\n"
    Item().remove(item)


@pytest.mark.plugin("sem_viewer")
def test_metadata_from_non_image(server, user, text_item):
    """getTiffHeaderFromFile swallows UnidentifiedImageError and we fall back."""
    resp = server.request(
        path=f"/item/{text_item['_id']}/tiff_metadata",
        method="GET",
        user=user,
    )
    assertStatusOk(resp)
    assert resp.json == "[MAIN]\r\nnoheader=1\r\n"


@pytest.mark.plugin("sem_viewer")
def test_thumbnail_from_non_image(server, user, text_item):
    resp = server.request(
        path=f"/item/{text_item['_id']}/tiff_thumbnail",
        method="GET",
        user=user,
    )
    assertStatusOk(resp)
    assert resp.json is None


@pytest.mark.plugin("sem_viewer")
def test_thumbnail_uint16(server, user, uint16_tiff_item):
    """16-bit grayscale goes through the percentile-clipping branch."""
    resp = server.request(
        path=f"/item/{uint16_tiff_item['_id']}/tiff_thumbnail",
        method="GET",
        user=user,
    )
    assertStatusOk(resp)
    data = base64.b64decode(resp.body[0])
    image = Image.open(BytesIO(data))
    assert image.format == "PNG"
    assert image.mode == "L"
    assert image.size == (1200, 1200)
    # Clipping to the 1st/99th percentile must stretch the data over the full range.
    extrema = image.getextrema()
    assert extrema[0] == 0
    assert extrema[1] == 255


@pytest.fixture
def rgb_tiff_item(server, user, folder, fsAssetstore):
    buffer = BytesIO()
    Image.new("RGB", (100, 100), (12, 34, 56)).save(buffer, format="TIFF")
    upload = server.uploadFile(
        "rgb.tiff",
        buffer.getvalue(),
        user,
        folder,
        parentType="folder",
        mimeType="image/tiff",
    )
    item = Item().load(upload["itemId"], force=True)
    yield item
    Item().remove(item)


@pytest.mark.plugin("sem_viewer")
def test_thumbnail_rgb_is_converted_to_grayscale(server, user, rgb_tiff_item):
    resp = server.request(
        path=f"/item/{rgb_tiff_item['_id']}/tiff_thumbnail",
        method="GET",
        user=user,
    )
    assertStatusOk(resp)
    image = Image.open(BytesIO(base64.b64decode(resp.body[0])))
    assert image.format == "PNG"
    assert image.mode == "L"
    assert image.size == (1200, 1200)
