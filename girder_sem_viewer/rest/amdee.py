import re

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import AccessType
from girder.models.folder import Folder
from girder.models.item import Item


regx = re.compile(r"^.*master.h5$", re.IGNORECASE)
sample_regx = re.compile(r"^\d+_\d+_\d+_.*$", re.IGNORECASE)


class AMDEE(Resource):
    def __init__(self):
        super(AMDEE, self).__init__()
        self.resourceName = "amdee"
        self.route("GET", ("xrd",), self.get_xrd)

    @access.user
    @autoDescribeRoute(
        Description("Get a list of folders with XRD data grouped by sample name.")
        .modelParam(
            "folderId",
            "The folder ID to search for XRD data.",
            required=True,
            model=Folder,
            level=AccessType.READ,
            paramType="query",
        )
        .errorResponse("ID was invalid.")
        .errorResponse("Read access was denied for the folder.", 403)
    )
    def get_xrd(self, folder):
        user = self.getCurrentUser()
        data = {}
        query = {
            # "meta.KafkaTopic": "AMDEE_XRD",
            "baseParentType": folder["baseParentType"],
            "baseParentId": folder["baseParentId"],
            "name": regx,
        }
        for item in Item().findWithPermissions(query, user=user):
            parent = Folder().load(item["folderId"], level=AccessType.READ, user=user)
            while parent["parentId"] != folder["_id"]:
                parent = Folder().load(
                    parent["parentId"], level=AccessType.READ, user=user
                )

            if sample_regx.match(parent["name"]):
                sample_id, instruction_id, run_id, _ = parent["name"].split("_", 3)
                partition_name = f"{run_id}_{instruction_id}_{sample_id}"
                if partition_name not in data:
                    data[partition_name] = {"folders": set()}
                data[partition_name]["folders"].add(item["folderId"])

        for key in data:
            data[key]["folders"] = list(data[key]["folders"])

        return data
