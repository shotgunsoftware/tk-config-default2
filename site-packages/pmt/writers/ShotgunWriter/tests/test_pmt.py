# ShotgunWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

# test script for Shotgun writer
import json
import os
import tempfile
import unittest
from pprint import pprint

import shotgun_api3

from ..pmt.shotgun import shotgun_writer

# The tests here take a certain amount of time to run, they are to be executed explicitly


# context manager responsible for deleting projects when theyre no longer needed
class ShotgunProjectCreationScope:
    def __init__(
        self,
        sg,
        sg_writer=None,
        project_entity=None,
        project_filepath=None,
        config_filepath=None,
        fields=None,
    ):
        if not fields:
            fields = ["id", "archived", "name"]

        self._sg = sg
        self._fields = fields

        if project_filepath and config_filepath:  # files are provided:
            self._sg_entity = shotgun_writer.create_shotgun_project(
                project_filepath, config_filepath, log_level="INFO"
            )

        elif sg_writer and project_entity:
            self._sg_entity = sg_writer.write_project_to_shotgun(project_entity)

    def __enter__(self):  # retrieving project populated with values
        return self._sg_entity["id"]

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._sg.delete("Project", self._sg_entity["id"])


# tester class
class ShotgunWriterTester(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sg = shotgun_api3.Shotgun(
            os.environ["PMT_TEST_SERVER_PATH"],
            os.environ["PMT_TEST_SCRIPT_NAME"],
            os.environ["PMT_TEST_SCRIPT_KEY"],
        )
        cls.config_data = {
            "SERVER_PATH": os.environ["PMT_TEST_SERVER_PATH"],
            "SCRIPT_NAME": os.environ["PMT_TEST_SCRIPT_NAME"],
            "SCRIPT_KEY": os.environ["PMT_TEST_SCRIPT_KEY"],
            "MAPPING_FILE": os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "pmt",
                "shotgun",
                "mappings.json",
            ),
            "PIPELINE_CONFIGURATION_NAME": "Primary",
            "FILESYSTEMLOCATION_TEMPLATES": {
                "Asset": "assets/{sg_asset_type}/{Asset}/{Step}",
                "Sequence": "sequences/{Sequence}/{Shot}/{Step}",
                "Shot": "sequences/{Sequence}/{Shot}/{Step}",
            },
            "USERS": {
                "Admin": {},
                "Artist": {
                    "ANIMATOR": "Annie Mader",
                    "LIGHTER": "Lai Tso",
                    "MODELLER": "Maude Ella",
                    "TEXTURER": "Tagir Shulga",
                    "PRODUCER": "Promi Duha",
                    "RIGGER": "Ricky Gervais",
                },
                "Manager": {},
            },
        }

        cls.config_filepath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "test_data",
            "test_config_data.json",
        )

        print(cls.config_data["MAPPING_FILE"])

        with open(cls.config_data["MAPPING_FILE"], "r") as mapping_file:
            cls.mappings = json.load(mapping_file)["mappings"]

        cls.sg_writer = shotgun_writer.ShotgunWriter(cls.config_data)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    # tests project creation from json file
    def explicit_test_write_from_json_to_shotgun(self):
        print("\ntest_write_from_json_to_shotgun")

        temp_config_filepath = os.path.join(
            tempfile.gettempdir(), "pmt_test_shotgun_config.json"
        )
        temp_project_filepath = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "thimble_data",
            "test_thimble.json",
        )

        # mocking config and project files as temp files
        try:
            # create temp config file
            with open(temp_config_filepath, "w") as config_file:
                json.dump(self.config_data, config_file)

            # create temp project file with thimble data + unique name
            with open(temp_project_filepath, "w") as test_project_file:
                data_filepath = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "thimble_data",
                    "thimble.json",
                )
                with open(data_filepath, "r") as thimble_file:
                    thimble_data = json.load(thimble_file)
                    thimble_data["name"] = "ThimbleRandomName"
                    thimble_data["tank_name"] = "thimble"

                json.dump(thimble_data, test_project_file)
            with ShotgunProjectCreationScope(
                self.sg,
                project_filepath=temp_project_filepath,
                config_filepath=temp_config_filepath,
                fields=list(self.mappings["Project"].values()),
            ) as sg_project_id:

                sg_project = self.sg.find_one(
                    "Project", [["id", "is", sg_project_id]]
                )
                self.sg_writer._sg_project = sg_project
                self.sg_writer._imgspc_sg_converter.project = sg_project
                entities_to_verify = [
                    thimble_data
                ]  # queue of entities to verify

                while entities_to_verify:  # not empty
                    entity = entities_to_verify.pop()

                    # find and collect entity from shotgun
                    filters = [
                        [
                            self.mappings[entity["type"]]["name"],
                            "is",
                            entity["name"],
                        ]
                    ]
                    fields = list(self.mappings[entity["type"]].values())
                    if entity["type"] != "Project":
                        filters.append(["project", "is", sg_project])
                    if entity["type"] == "Task":
                        filters.append(["entity", "is", entity["sg_parent"]])
                        fields.append("entity")
                    elif entity["type"] == "PublishedFile":
                        fields.append("entity")
                        sg_parent = entity["sg_parent"]

                        if sg_parent["type"] == "PublishedFile":
                            sg_task = sg_parent.get("task")
                            sg_parent = sg_parent["entity"]

                        if sg_parent["type"] == "Task":
                            sg_task = sg_parent
                            sg_parent = sg_parent["entity"]

                        if sg_task:
                            filters.append(["task", "is", sg_task])

                        filters.append(["entity", "is", sg_parent])

                    elif entity["type"] == "Note":
                        filters.append(["subject", "is", entity.get("name")])
                        filters.append(["content", "is", entity.get("body")])
                        for attachment in entity.get("attachments", []):
                            filters.append(
                                [
                                    "attachments",
                                    "name_contains",
                                    attachment.split("/")[1],
                                ]
                            )

                    sg_entity = self.sg.find_one(
                        entity["type"], filters, fields=fields
                    )

                    for child in entity.get("children", []):
                        # storing parent incase field validation needs it
                        child["sg_parent"] = sg_entity
                        entities_to_verify.append(child)

                    # assert fields are equal
                    for imgspc_field in entity:
                        sg_field = self.mappings[entity["type"]].get(
                            imgspc_field
                        )

                        # can't test image equality - thumbnail file name is lost when we upload it to Shotgun
                        if not sg_field or sg_field in [
                            "image",
                            "sg_uploaded_movie_mp4",
                        ]:
                            continue

                        sg_value = sg_entity[sg_field]
                        expected_value = entity[imgspc_field]

                        if sg_field == "task_assignees":
                            # assert shotgun equivalence for each value in the task assignee lists.
                            sg_expected_value = self.sg_writer.convert_data(
                                entity["type"], expected_value, sg_field
                            )
                            for ix in range(0, len(sg_value)):
                                self.assertEqual(
                                    sg_value[ix]["id"],
                                    sg_expected_value[ix]["id"],
                                )
                                self.assertEqual(
                                    sg_value[ix]["type"],
                                    sg_expected_value[ix]["type"],
                                )

                        elif isinstance(sg_value, list):
                            # ensure all the names of the listed entities are present in the shotgun list
                            for sg_ent in sg_value:
                                sg_entity_name = sg_ent["name"]
                                for name in expected_value:
                                    # Replies in Notes
                                    if isinstance(name, dict):
                                        if (
                                            sg_ent.get("type") == "Reply"
                                            and name.get("body")
                                            == sg_entity_name
                                        ):
                                            expected_value.remove(name)
                                    # files under thumbnails get stripped of their "thumbnails/" prefix
                                    elif (
                                        os.path.basename(name) == sg_entity_name
                                    ):
                                        # found the matching entry
                                        expected_value.remove(name)

                            self.assertEqual([], expected_value)

                        elif (
                            sg_field == "step"
                        ):  # imgspc expected value is a department
                            sg_value = self.sg.find_one(
                                "Step",
                                [["id", "is", sg_value["id"]]],
                                ["entity_type", "code"],
                            )
                            self.assertEqual(
                                sg_value["code"],
                                self.mappings["Enum"]["step"][expected_value],
                            )
                            self.assertEqual(
                                sg_value["entity_type"],
                                entity["sg_parent"]["type"],
                            )
                            continue
                        else:
                            if (
                                isinstance(sg_value, dict)
                                and sg_value.get("type") == "Task"
                            ):
                                extra_data = {"entity": sg_entity["entity"]}
                            else:
                                extra_data = None

                            sg_expected_value = self.sg_writer.convert_data(
                                entity["type"],
                                expected_value,
                                sg_field,
                                extra_data,
                            )
                            if isinstance(sg_expected_value, dict):
                                # ensure Shotgun equivalence, i.e. the type and id are the same
                                self.assertEqual(
                                    sg_value["id"], sg_expected_value["id"]
                                )
                                self.assertEqual(
                                    sg_value["type"], sg_expected_value["type"]
                                )
                            elif isinstance(sg_value, dict):
                                # we cant determine what the equivalent sg entity should be,
                                # in this scenario the expected value should simply be the name of the sg value
                                self.assertEqual(
                                    sg_value["name"], sg_expected_value
                                )  # self.mappings[ sg_value["type"] ]["name"]
                            else:
                                self.assertEqual(sg_value, sg_expected_value)

                    for child in entity.get("children", []):
                        # storing parent incase field validation needs it
                        child["sg_parent"] = sg_entity
                        entities_to_verify.append(child)

        finally:  # deleting files
            try:
                os.remove(temp_config_filepath)
            except FileNotFoundError:
                pass
            try:
                os.remove(temp_project_filepath)
            except FileNotFoundError:
                pass

    # tests scenario where attempting to create Shotgun projects with name collisions
    def explicit_test_create_project_name_collision(self):
        print("\ntest_create_project_name_collision")

        proj_name = "TestingNameCollision"
        project_entity = {"type": "Project", "name": proj_name}

        # no collision resolution
        self.sg_writer.set_collision_resolution(None)
        with ShotgunProjectCreationScope(
            self.sg, sg_writer=self.sg_writer, project_entity=project_entity
        ) as original_project_id:
            # With these scopes how can i test the exception is raised;;;;

            # test on rename
            self.sg_writer.set_collision_resolution("rename")
            with ShotgunProjectCreationScope(
                self.sg, sg_writer=self.sg_writer, project_entity=project_entity
            ) as renamed_project_id:
                original_project = self.sg.find_one(
                    "Project",
                    [["id", "is", original_project_id]],
                    ["name", "id", "archived"],
                )
                renamed_project = self.sg.find_one(
                    "Project",
                    [["id", "is", renamed_project_id]],
                    ["name", "id", "archived"],
                )
                self.assertEqual(original_project["name"], proj_name)
                self.assertNotEqual(renamed_project["name"], proj_name)

            # test on archive
            self.sg_writer.set_collision_resolution("archive")
            with ShotgunProjectCreationScope(
                self.sg, sg_writer=self.sg_writer, project_entity=project_entity
            ) as new_project_id:
                original_project = self.sg.find_one(
                    "Project",
                    [["id", "is", original_project_id]],
                    ["name", "id", "archived"],
                )
                new_project = self.sg.find_one(
                    "Project",
                    [["id", "is", new_project_id]],
                    ["name", "id", "archived"],
                )
                self.assertNotEqual(
                    original_project["name"], new_project["name"]
                )  # both projects got created with
                # diff names
                self.assertEqual(original_project["archived"], True)


if __name__ == "__main__":
    unittest.main()
