#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
import io
import logging
import os
import re

try:
    import cherrypy
except ImportError:
    cherrypy = None

import dateutil.parser
import magic
import numpy as np
from girder import auditLogger, events
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import boundHandler, setResponseHeader
from girder.constants import AccessType
from girder.exceptions import FilePathException, GirderException, ValidationException
from girder.models.assetstore import Assetstore
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.plugin import GirderPlugin, registerPluginStaticContent
from girder.utility import assetstore_utilities, search, toBool
from girder.utility.model_importer import ModelImporter
from girder.utility.progress import ProgressContext
from PIL import Image, UnidentifiedImageError

from .rest.amdee import AMDEE

logger = logging.getLogger(__name__)


class IgnoreURLFilter(logging.Filter):
    # simple example of log message filtering
    # https://stackoverflow.com/a/12345788/4084258

    def __init__(self, path, verb="GET", status=200):
        self.verb = verb
        self.path = path
        self.status = status

    def filter(self, record):
        if hasattr(record, "details"):
            if (
                record.details.get("method") == self.verb
                and record.details.get("route") == self.path
                and record.details.get("status") == self.status
            ):
                return False
        match = f"{self.verb} /api/v1/{'/'.join(self.path)}"
        return match not in record.getMessage()


class IgnorePhraseFilter(logging.Filter):
    def __init__(self, phrase):
        self.phrase = phrase

    def filter(self, record):
        return self.phrase not in record.getMessage()


@boundHandler
def import_sem_data(self, event):
    params = event.info["params"]
    if params.get("dataType") not in ("sem", "pdv"):
        logger.warning("Importing using default importer")
        return

    data_type = params["dataType"]
    if data_type == "sem":
        import_cls = SEMHTMDECImporter
    elif data_type == "pdv":
        import_cls = PDVHTMDECImporter
    else:
        raise ValidationException(f"Unknown data type: {data_type}")
    logger.warning(f"Importing using {str(import_cls)} importer")

    if params["destinationType"] != "folder":
        raise ValidationException(
            f"{data_type} data can only be imported to girder folders"
        )

    importPath = params.get("importPath")
    if not os.path.exists(importPath):
        raise ValidationException("Not found: %s." % importPath)
    if not os.path.isdir(importPath):
        raise ValidationException("Not a directory: %s." % importPath)

    progress = toBool(params.get("progress", "false"))
    user = self.getCurrentUser()
    assetstore = Assetstore().load(event.info["id"])
    adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
    parent = self.model(params["destinationType"]).load(
        params["destinationId"], user=user, level=AccessType.ADMIN, exc=True
    )
    params["fileExcludeRegex"] = r"^_\..*"

    with ProgressContext(progress, user=user, title=f"{data_type} data import") as ctx:
        importer = import_cls(adapter, user, ctx, params=params)
        importer.import_data(parent, params["destinationType"], importPath)

    event.preventDefault().addResponse(None)


def _get_model(modelName):
    if modelName == "item":
        model = Item()
    elif modelName == "folder":
        model = Folder()
    else:
        model = None
    return model


def jhuId_search(query, types, user, level, limit, offset):
    results = {}
    allowed = {
        "collection": ["_id", "name", "description"],
        "folder": ["_id", "name", "description", "parentId"],
        "item": ["_id", "name", "description", "folderId"],
    }
    query = {"meta.jhu_id": query}  # Assuming we are searching by JHU ID
    for modelName in types:
        model = _get_model(modelName)
        if model is not None:
            if hasattr(model, "filterResultsByPermission"):
                cursor = model.find(
                    query, fields=allowed[modelName] + ["public", "access"]
                )
                results[modelName] = list(
                    model.filterResultsByPermission(
                        cursor, user, level, limit=limit, offset=offset
                    )
                )
            else:
                results[modelName] = list(
                    model.find(
                        query,
                        fields=allowed[modelName],
                        limit=limit,
                        offset=offset,
                    )
                )
    return results


class HTMDECImporter:
    def __init__(self, adapter, user, progress, params=None):
        self.adapter = adapter
        self.user = user
        self.progress = progress
        self.params = params or {}
        self.mime = magic.Magic(mime=True)

    def import_data(self, parent, parentType, importPath):
        for name in os.listdir(importPath):
            self.progress.update(message=name)
            path = os.path.join(importPath, name)
            if os.path.isdir(path):
                self.recurse_folder(parent, parentType, name, importPath)
            else:
                self.import_item(parent, parentType, name, importPath)

    def recurse_folder(self, parent, parentType, name, importPath):
        folder = Folder().createFolder(
            parent=parent,
            name=name,
            parentType=parentType,
            creator=self.user,
            reuseExisting=True,
        )
        nextPath = os.path.join(importPath, name)
        events.trigger(
            "filesystem_assetstore_imported",
            {"id": folder["_id"], "type": "folder", "importPath": nextPath},
        )
        self.import_data(folder, "folder", nextPath)


class PDVHTMDECImporter(HTMDECImporter):
    def import_item(self, parent, parentType, name, importPath):
        try:
            if date := re.search(r"\d{8}", name):
                date = dateutil.parser.parse(date.group())
                parent = Folder().createFolder(
                    parent=parent,
                    name=f"{date.year}",
                    parentType=parentType,
                    creator=self.user,
                    reuseExisting=True,
                )
                parent = Folder().createFolder(
                    parent=parent,
                    name=f"{date.year}{date.month:02d}{date.day:02d}",
                    parentType=parentType,
                    creator=self.user,
                    reuseExisting=True,
                )
        except dateutil.parser._parser.ParserError:
            pass

        item = Item().createItem(
            name=name, creator=self.user, folder=parent, reuseExisting=True
        )
        item = Item().setMetadata(item, {"pdv": True})

        fpath = os.path.join(importPath, name)
        events.trigger(
            "filesystem_assetstore_imported",
            {"id": item["_id"], "type": "item", "importPath": fpath},
        )
        if self.adapter.shouldImportFile(fpath, self.params):
            self.adapter.importFile(
                item, fpath, self.user, name=name, mimeType=self.mime.from_file(fpath)
            )


class SEMHTMDECImporter(HTMDECImporter):
    def import_item(self, parent, parentType, name, importPath):
        hdr_file = f"{name.replace('.tif', '-tif')}.hdr"
        if not os.path.isfile(os.path.join(importPath, hdr_file)):
            logger.warning(
                f"Importing {os.path.join(importPath, name)} failed because of missing header"
            )
            return
        item = Item().createItem(
            name=name, creator=self.user, folder=parent, reuseExisting=True
        )
        item = Item().setMetadata(item, {"sem": True})
        events.trigger(
            "filesystem_assetstore_imported",
            {
                "id": item["_id"],
                "type": "item",
                "importPath": os.path.join(importPath, name),
            },
        )
        for fname, mimeType in ((name, "image/tiff"), (hdr_file, "text/plain")):
            fpath = os.path.join(importPath, fname)
            if self.adapter.shouldImportFile(fpath, self.params):
                self.adapter.importFile(
                    item, fpath, self.user, name=fname, mimeType=mimeType
                )


def getTiffHeaderFromFile(path):
    try:
        with Image.open(path) as img:
            return next(
                (
                    _
                    for _ in img.tag_v2.values()
                    if isinstance(_, str) and "[User]" in _
                ),
                None,
            )
    except UnidentifiedImageError:
        pass


def getTiffHeaderFromItemMeta(item):
    fileId = item.get("meta", {}).get("headerId")
    if not fileId:
        return
    try:
        fobj = File().load(fileId, force=True, exc=True)
        with File().open(fobj) as fp:
            return fp.read().decode("utf-8")
    except Exception:
        pass


@access.public
@boundHandler
@autoDescribeRoute(
    Description("Get Tiff metadata from an item").modelParam(
        "id", model="item", level=AccessType.READ
    )
)
def get_tiff_metadata(self, item):
    try:
        child_file = list(Item().childFiles(item))[0]
    except IndexError:
        return
    try:
        path = File().getLocalFilePath(child_file)
    except FilePathException:
        path = None

    header = None
    if path:
        header = getTiffHeaderFromFile(path)

    if not header:
        header = getTiffHeaderFromItemMeta(item)

    if not header:
        header = "[MAIN]\r\nnoheader=1\r\n"

    setResponseHeader("Content-Type", "text/plain")
    return header


@access.public
@boundHandler
@autoDescribeRoute(
    Description("Get thumbnail for SEM data").modelParam(
        "id", model="item", level=AccessType.READ
    )
)
def get_sem_thumbnail(self, item):
    try:
        child_file = list(Item().childFiles(item))[0]
    except IndexError:
        return
    try:
        path = File().getLocalFilePath(child_file)
    except FilePathException:
        path = None

    if not path:
        return

    try:
        with Image.open(path, "r") as im:
            if im.mode == "F":  # Floating-point grayscale
                imarray = np.array(im)
                imarray = (
                    (imarray - imarray.min()) / (imarray.max() - imarray.min()) * 255
                )  # Normalize to [0, 255]
                im = Image.fromarray(
                    imarray.astype("uint8")
                )  # Convert back to 8-bit grayscale

            elif im.mode in ["I;16", "I"]:  # 16-bit or 32-bit integer grayscale
                im = im.point(lambda i: i * (255 / max(im.getextrema())))

            elif im.mode not in ["L"]:
                im = im.convert("RGB").convert("L")
            im = im.resize((1200, 1200), Image.LANCZOS)
            fp = io.BytesIO()
            im.save(fp, format="PNG")
            return base64.b64encode(fp.getvalue()).decode()
    except UnidentifiedImageError:
        pass


@access.user
@boundHandler
@autoDescribeRoute(
    Description("Create folders recursively")
    .param("parentId", "The ID of the parent object", required=True)
    .param("parentType", "The type of the parent object", required=True)
    .param("path", "The path to create", required=True)
)
def create_folders(self, parentId, parentType, path):
    user = self.getCurrentUser()
    parent = ModelImporter.model(parentType).load(
        parentId, user=user, level=AccessType.WRITE, exc=True
    )
    for name in path.split("/"):
        parent = Folder().createFolder(
            parent=parent,
            name=name,
            parentType=parentType,
            creator=self.getCurrentUser(),
            reuseExisting=True,
        )
        parentType = "folder"
    return Folder().filter(parent, user)


class SemViewerPlugin(GirderPlugin):
    DISPLAY_NAME = "SEM Viewer"

    def load(self, info):
        Item().exposeFields(level=AccessType.READ, fields="sem")
        File().ensureIndex(["sha512", {"sparse": False}])

        info["apiRoot"].item.route("GET", (":id", "tiff_metadata"), get_tiff_metadata)
        info["apiRoot"].item.route("GET", (":id", "tiff_thumbnail"), get_sem_thumbnail)
        info["apiRoot"].folder.route("POST", ("recursive",), create_folders)

        info["apiRoot"].amdee = AMDEE()

        events.bind(
            "rest.post.assetstore/:id/import.before", "sem_viewer", import_sem_data
        )
        try:
            search.addSearchMode("jhuId", jhuId_search)
        except GirderException:
            logger.warning("Search mode already registered, skipping.")
        for app in info["serverRoot"].apps.values():
            app.log.access_log.addFilter(IgnoreURLFilter(("system", "check")))
            app.log.access_log.addFilter(IgnorePhraseFilter("Uptime-Kuma"))

        auditLogger.addFilter(IgnoreURLFilter(("system", "check")))
        auditLogger.addFilter(IgnorePhraseFilter("Uptime-Kuma"))

        registerPluginStaticContent(
            plugin="sem_viewer",
            css=["/style.css"],
            js=["/girder-plugin-sem-viewer.umd.cjs"],
            staticDir=os.path.join(os.path.dirname(__file__), "web_client", "dist"),
            tree=info["serverRoot"],
        )
