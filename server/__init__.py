#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from girder import events, logger
from girder.api import rest
from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.assetstore import Assetstore
from girder.models.folder import Folder
from girder.models.item import Item
from girder.utility import assetstore_utilities, toBool
from girder.utility.progress import ProgressContext


@rest.boundHandler
def import_sem_data(self, event):
    params = event.info["params"]
    if not toBool(params.get("sem", "false")):
        return

    if params["destinationType"] != "folder":
        raise ValidationException("SEM data can only be imported to girder folders")

    progress = toBool(params.get("progress", "false"))

    user = self.getCurrentUser()
    assetstore = Assetstore().load(event.info["id"])
    adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
    parent = self.model(params["destinationType"]).load(
        params["destinationId"], user=user, level=AccessType.ADMIN, exc=True
    )
    importPath = params.get("importPath")
    params["fileIncludeRegex"] = r".*\.(tif|tiff|hdr)$"
    params["fileExcludeRegex"] = r"^_\..*"

    if not os.path.exists(importPath):
        raise ValidationException("Not found: %s." % importPath)
    if not os.path.isdir(importPath):
        raise ValidationException("Not a directory: %s." % importPath)

    with ProgressContext(progress, user=user, title="Mock Data import") as ctx:
        _import_sem(
            adapter,
            parent,
            params["destinationType"],
            ctx,
            user,
            importPath,
            params=params,
        )

    event.preventDefault().addResponse(None)


def _import_sem(adapter, parent, parentType, progress, user, importPath, params=None):
    params = params or {}
    for name in os.listdir(importPath):
        if name.endswith(".hdr"):
            continue
        progress.update(message=name)
        path = os.path.join(importPath, name)
        if os.path.isdir(path):
            folder = Folder().createFolder(
                parent=parent,
                name=name,
                parentType=parentType,
                creator=user,
                reuseExisting=True,
            )
            events.trigger(
                "filesystem_assetstore_imported",
                {"id": folder["_id"], "type": "folder", "importPath": path},
            )
            nextPath = os.path.join(importPath, name)
            _import_sem(
                adapter, folder, "folder", progress, user, nextPath, params=params
            )
        else:
            hdr_file = f"{name.replace('.tif', '-tif')}.hdr"
            if not os.path.isfile(os.path.join(importPath, hdr_file)):
                logger.warning(f"Importing {path} failed because of missing header")
                continue
            item = Item().createItem(
                name=name, creator=user, folder=parent, reuseExisting=True
            )
            item = Item().setMetadata(item, {"sem": True})
            events.trigger(
                "filesystem_assetstore_imported",
                {"id": item["_id"], "type": "item", "importPath": importPath},
            )
            for fname, mimeType in ((name, "image/tiff"), (hdr_file, "text/plain")):
                fpath = os.path.join(importPath, fname)
                if adapter.shouldImportFile(fpath, params):
                    adapter.importFile(item, fpath, user, name=fname, mimeType=mimeType)


def load(info):
    Item().exposeFields(level=AccessType.READ, fields="sem")

    events.bind("rest.post.assetstore/:id/import.before", "sem_viewer", import_sem_data)
