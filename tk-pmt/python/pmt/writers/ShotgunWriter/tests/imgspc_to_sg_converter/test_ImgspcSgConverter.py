# ShotgunWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import json
import os
import unittest

from .mockgun import Mockgun

from ...pmt.shotgun.converter import ImgspcSgConverter


class ImgspcSgConverterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):

        cls.sg = Mockgun()
        cls.pmt_root_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))
        )
        mapping_cfg_path = os.path.join(
            cls.pmt_root_dir, "pmt", "shotgun", "mappings.json"
        )
        with open(mapping_cfg_path, "r") as mapping_cfg:
            cls.converter = ImgspcSgConverter(
                cls.sg,
                json.load(mapping_cfg)["mappings"],
                {"type": "Project", "id": 1},
            )

    def test_get_field_data_type(self):
        self.assertEqual(
            self.converter.get_field_data_type("Note", "client_note"),
            "checkbox",
        )
        self.assertEqual(
            self.converter.get_field_data_type("Task", "due_date"), "date"
        )
        self.assertEqual(
            self.converter.get_field_data_type("HumanUser", "created_at"),
            "date_time",
        )
        self.assertEqual(
            self.converter.get_field_data_type("Task", "est_in_mins"),
            "duration",
        )
        self.assertEqual(
            self.converter.get_field_data_type("PublishedFile", "entity"),
            "entity",
        )
        self.assertEqual(
            self.converter.get_field_data_type("Cut", "fps"), "float"
        )
        self.assertEqual(
            self.converter.get_field_data_type("Sequence", "image"), "image"
        )
        self.assertEqual(
            self.converter.get_field_data_type(
                "PublishedFile", "filmstrip_image_id"
            ),
            "integer",
        )
        self.assertEqual(
            self.converter.get_field_data_type("Asset", "sg_asset_type"), "list"
        )
        self.assertEqual(
            self.converter.get_field_data_type("Sequence", "assets"),
            "multi_entity",
        )
        self.assertEqual(
            self.converter.get_field_data_type("Shot", "cut_in"), "number"
        )
        self.assertEqual(
            self.converter.get_field_data_type("Task", "time_percent_of_est"),
            "percent",
        )
        self.assertEqual(
            self.converter.get_field_data_type("Task", "splits"), "serializable"
        )
        self.assertEqual(
            self.converter.get_field_data_type("Task", "sg_status_list"),
            "status_list",
        )
        self.assertEqual(
            self.converter.get_field_data_type("Sequence", "open_notes_count"),
            "summary",
        )
        self.assertEqual(
            self.converter.get_field_data_type("Shot", "code"), "text"
        )
        self.assertEqual(
            self.converter.get_field_data_type("PublishedFile", "path"), "url"
        )

        # Not an entity type
        self.assertRaises(
            KeyError, self.converter.get_field_data_type, "Klurg", "entity"
        )
        # Existing entity type, but not the field
        self.assertRaises(
            KeyError,
            self.converter.get_field_data_type,
            "PublishedFile",
            "gloogloox",
        )

    def test_get_entity_field_types(self):

        self.assertEqual(
            self.converter.get_entity_field_types(
                "PublishedFile", "published_file_type"
            ),
            ["PublishedFileType"],
        )
        self.assertEqual(
            self.converter.get_entity_field_types("Version", "sg_task"),
            ["Task"],
        )
        self.assertEqual(
            self.converter.get_entity_field_types("Note", "note_links"),
            [
                "Asset",
                "Camera",
                "Cut",
                "Department",
                "Group",
                "MocapSetup",
                "MocapTake",
                "MocapTakeRange",
                "Performer",
                "Phase",
                "PhysicalAsset",
                "Playlist",
                "Release",
                "Revision",
                "Sequence",
                "ShootDay",
                "Shot",
                "TaskTemplate",
                "Version",
                "Level",
                "Episode",
                "Routine",
                "Launch",
            ],
        )

    def test_convert_data(self):

        self.assertEqual(
            self.converter.convert("Thimble", "Project", "name"), "Thimble"
        )
        self.assertEqual(
            self.converter.convert("character", "Asset", "sg_asset_type"),
            "Character",
        )
        self.assertEqual(
            self.converter.convert(["Marble", "Thimble"], "Shot", "assets"),
            [
                {"type": "Asset", "id": 1, "name": "Marble"},
                {"type": "Asset", "id": 2, "name": "Thimble"},
            ],
        )
        self.assertEqual(self.converter.convert([], "Shot", "assets"), [])
        self.assertEqual(
            self.converter.convert("revision", "Version", "sg_status_list"),
            "rev",
        )
        self.assertEqual(
            self.converter.convert(
                "Maya Scene", "PublishedFile", "published_file_type"
            ),
            {"type": "PublishedFileType", "id": 1, "name": "Maya Scene"},
        )
        self.assertEqual(
            self.converter.convert(
                "thumbnails/Thimble_1557.png",
                "Version",
                "sg_uploaded_movie_mp4",
                {
                    "project_data_directory": os.path.join(
                        self.pmt_root_dir, "thimble_data"
                    )
                },
            ),
            os.path.normpath(
                os.path.join(
                    self.pmt_root_dir,
                    "thimble_data",
                    "thumbnails",
                    "Thimble_1557.png",
                )
            ),
        )

    def test_cannot_query_shotgun_if_no_project(self):

        converter_without_project = ImgspcSgConverter(self.sg, None)
        # entity type field need to query Shotgun, but no project has been defined
        self.assertRaises(
            AttributeError,
            converter_without_project.convert,
            "Maya Scene",
            "PublishedFile",
            "published_file_type",
        )

    def test_get_step_for_task(self):

        self.assertEqual(
            self.converter.get_step_for_task("Shot", "Character FX"),
            {
                "type": "Step",
                "id": 136,
                "code": "Character FX",
                "short_name": "CFX",
                "entity_type": "Shot",
            },
        )

        self.assertEqual(
            self.converter.get_step_for_task("Asset", "Art"),
            {
                "type": "Step",
                "id": 13,
                "code": "Art",
                "short_name": "ART",
                "entity_type": "Asset",
            },
        )

        self.assertEqual(
            self.converter.get_step_for_task("Sequence", "Modelling"), {}
        )


if __name__ == "__main__":
    unittest.main()
