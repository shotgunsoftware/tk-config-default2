# ShotgunWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import json
import os
import re


class Mockgun:
    """Mock Shotgun API
    Avoid HTTP requests when unit-testing
    """

    __slots__ = ("_schema", "mockgun_mod_dir", "_steps")

    assets = [
        {"type": "Asset", "id": 1, "name": "Marble"},
        {"type": "Asset", "id": 2, "name": "Thimble"},
        {"type": "Asset", "id": 3, "name": "GumPack"},
    ]

    published_file_types = [
        {"type": "PublishedFileType", "id": 1, "name": "Maya Scene"},
        {"type": "PublishedFileType", "id": 2, "name": "Alembic Cache"},
        {"type": "PublishedFileType", "id": 3, "name": "Image"},
    ]

    def __init__(self):
        self.mockgun_mod_dir = os.path.dirname(__file__)
        self._schema = None
        self._steps = None

    def schema_read(self):
        return self.schema

    @property
    def schema(self):
        if self._schema:
            return self._schema

        # https://imgspc.shotgunstudio.com DB's schema dumped into a json file
        with open(
            os.path.join(self.mockgun_mod_dir, "mock_schema.json"), "r"
        ) as f:
            self._schema = json.loads(f.read())

        return self._schema

    @property
    def steps(self):
        if self._steps:
            return self._steps

        with open(
            os.path.join(self.mockgun_mod_dir, "mock_steps.json"), "r"
        ) as f:
            self._steps = json.loads(f.read())

        return self._steps

    def find(self, entity_type, filters, *args):
        def look_for_filters(filters, field, condition):
            json_filters = json.dumps(filters)
            field_re = re.compile(
                f'(\["{field}"\,\s"{condition}"\,\s"[\w\s]+"\])'
            )
            res = field_re.findall(json_filters)
            return [json.loads(re) for re in res]

        if entity_type == "Asset":
            # 3rd pos is the filter value when filtering on name
            filter_asset_names = [
                filt[2] for filt in look_for_filters(filters, "code", "is")
            ]
            if not filter_asset_names:
                return self.assets
            return [
                asset
                for asset in self.assets
                if asset["name"] in filter_asset_names
            ]
        elif entity_type == "PublishedFileType":
            filter_pftypes_names = [
                filt[2] for filt in look_for_filters(filters, "code", "is")
            ]
            if not filter_pftypes_names:
                return self.published_file_types
            return [
                pftype
                for pftype in self.published_file_types
                if pftype["name"] in filter_pftypes_names
            ]
        elif entity_type == "Step":
            return self.steps
        else:
            raise NotImplementedError(entity_type)

    def find_one(self, entity_type, filters):
        res = self.find(entity_type, filters)
        return res[0] if res else []
