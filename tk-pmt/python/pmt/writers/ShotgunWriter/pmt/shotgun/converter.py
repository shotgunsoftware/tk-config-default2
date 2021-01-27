# ShotgunWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import os
import textwrap
from typing import Any, List

import shotgun_api3


class ImgspcSgConverter:
    """Class to handle imgspc format -> sg format conversion"""

    def __init__(
        self,
        sg: shotgun_api3.shotgun.Shotgun,
        mapping_config: dict,
        sg_project: dict = None,
    ):
        """
        :param sg: Shotgun client connection
        :param mapping_config: imgspc -> sg mapping config data
        :param sg_project: Shotgun Project entity; useful when looking for entities
        """
        self._sg = sg
        self.project = sg_project
        # Cache the Shotgun db's schema
        self._schema = sg.schema_read()
        self._mapping_config = mapping_config

    @property
    def sg(self):
        if not self.project:
            raise AttributeError(
                "Cannot query Shotgun for entities without setting `project` attribute"
            )
        return self._sg

    @property
    def steps(self):
        return self.sg.find("Step", [], ["code", "short_name", "entity_type"])

    def get_field_data_type(
        self, sg_entity_type: str, sg_field_name: str
    ) -> str:
        """Looks for the data type of `field_name` on `entity_type`

        :param sg_entity_type: Shotgun entity type
        :param sg_field_name: field on the entity
        :returns: field's data type
        :raises: KeyError
        """
        entity_type_schema = self._schema.get(sg_entity_type)
        if not entity_type_schema:
            raise KeyError(f"Given entity type {sg_entity_type} does not exist")

        field_schema = entity_type_schema.get(sg_field_name)
        if not field_schema:
            raise KeyError(
                f"Field {sg_field_name} does not exist on {sg_entity_type}"
            )

        return field_schema["data_type"]["value"]

    def _entity_type_has_field(
        self, sg_entity_type: str, sg_field_name: str
    ) -> bool:
        return self._schema.get(sg_entity_type, {}).get(sg_field_name) != None

    def _get_entity_type_name_field_code(self, sg_entity_type: str) -> str:
        """
                    AMI, Delivery & Ticket name field is `title`
        `           Attachment (File) is filename
                    Task name is content
                    Except those cases, entity name field should be `code`
                    If we can't found it in the entity type's schema, it must be `name` (Tag for instance)
        """
        if sg_entity_type == "Task":
            return "content"
        elif sg_entity_type == "Attachment":
            return "filename"
        elif sg_entity_type in ["ActionMenuItem", "Delivery", "Ticket"]:
            return "title"
        else:
            return (
                "code"
                if self._schema.get(sg_entity_type, {}).get("code")
                else "name"
            )

    def get_entity_field_types(
        self, sg_entity_type: str, sg_field_name: str
    ) -> List[str]:
        """For entity and multi entity fields, get the entity types that can be contained in the field"""
        if not self._schema.get(sg_entity_type):
            raise AttributeError(
                f"Entity type {sg_entity_type} cannot be found in the Shotgun's schema"
            )
        if not self._schema[sg_entity_type].get(sg_field_name):
            raise AttributeError(
                f"Field {sg_field_name} does not exist on entity type {sg_entity_type}"
            )
        return self._schema[sg_entity_type][sg_field_name]["properties"][
            "valid_types"
        ]["value"]

    def _is_field_editable(
        self, sg_entity_type: str, sg_field_name: str
    ) -> bool:
        """True if the field can be edited, False otherwise"""
        return self._schema[sg_entity_type][sg_field_name]["editable"]["value"]

    def get_step_for_task(self, sg_entity_type: str, imgspc_value: str) -> dict:
        return next(
            (
                step
                for step in self.steps
                if step["entity_type"] == sg_entity_type
                and step["code"] == imgspc_value
            ),
            {},
        )

    def _locate_file(self, file_path: str, project_directory: str) -> str:
        if not os.path.exists(file_path):
            # try as relative path
            file_path = os.path.normpath(
                os.path.join(project_directory, file_path)
            )
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"No attachment file at {file_path}")

        return file_path

    def convert(
        self,
        imgspc_value: Any,
        sg_entity_type: str,
        sg_field_name: str,
        extra_data: dict = None,
    ) -> Any:
        """Using Shotgun site db's schema and queries where needed, convert `imgspc_value` to Shotgun format
        imgspc_val -> sg_val

        :param imgspc_value: imgspc value
        :param sg_entity_type: Shotgun entity type
        :param sg_field_name: field on the entity
        :param extra_data: set key project_data_directory for filesystem operations and `entity` when looking for a specific Task
        :returns: Shotgun converted value
        :raises: KeyError, NotImplementedError
        """
        if extra_data is None:
            extra_data = {}

        field_data_type = self.get_field_data_type(
            sg_entity_type, sg_field_name
        )

        # Plain value, no need for conversion
        if field_data_type in [
            "text",
            "float",
            "integer",
            "number",
            "color",
            "duration",
        ]:
            return imgspc_value

        # Special cases first
        # pipeline steps could be queried like other entity field if able to store in json
        # for which entity type it is a pivot column (Asset, Shot...)
        if (
            field_data_type in ["list", "status_list"]
            or sg_field_name == "step"
        ):
            enum_field = self._mapping_config["Enum"].get(sg_field_name)
            if enum_field:
                return enum_field.get(imgspc_value)
            else:
                raise KeyError(f"No mapping for field `{sg_field_name}`")
        # needs filesystem
        if field_data_type in ["image", "url"]:
            return self._locate_file(
                imgspc_value, extra_data["project_data_directory"]
            )
        if sg_field_name == "attachments" or sg_entity_type == "Attachment":
            res = []
            for file_name in imgspc_value:
                res.append(
                    self._locate_file(
                        file_name, extra_data["project_data_directory"]
                    )
                )
            return res
        # Those fields are polymorphic: they can contain HumanUser and Script entities.
        # We could modify img spc json for those kind of fields, to have a way to specify
        # the type of what we're looking for. Maybe even deciding that we are never looking
        # for Scripts when looking for who created a Version.
        # There is also the possibility to query each table, and returning the first result.
        # Low probability that two entities on two tables have the same name, but still.
        if sg_field_name in ["user", "created_by", "task_assignees"]:
            user_name = extra_data["users"].get(imgspc_value)
            res = self.sg.find_one("HumanUser", [["name", "is", user_name]])
            if field_data_type == "entity":
                return res
            elif field_data_type == "multi_entity":
                return [res]
        if sg_entity_type == "Note" and sg_field_name == "replies":
            return imgspc_value

        if field_data_type == "entity":
            entity_types = self.get_entity_field_types(
                sg_entity_type, sg_field_name
            )
            if len(entity_types) > 1:
                # Need to see how to implement this part with imaginary space format
                raise NotImplementedError(
                    textwrap.fill(
                        textwrap.dedent(
                            f"""
                    Not supporting polymorphic entity fields for the moment:
                    tried to convert data on entity type: {sg_entity_type}, field: {sg_field_name}
                """
                        )
                    )
                )
            # Already taken care in create_task
            if entity_types[0] == "Step":
                return imgspc_value
            entity_type_name_field_code = self._get_entity_type_name_field_code(
                entity_types[0]
            )
            filters = [[entity_type_name_field_code, "is", imgspc_value]]
            if self._entity_type_has_field(entity_types[0], "project"):
                filters.append(["project", "is", self.project])
            if entity_types[0] == "Task" and extra_data.get("entity"):
                filters.append(["entity", "is", extra_data["entity"]])
            return self.sg.find_one(entity_types[0], filters)

        if field_data_type == "multi_entity":
            if not imgspc_value:
                return []
            entity_types = self.get_entity_field_types(
                sg_entity_type, sg_field_name
            )
            if len(entity_types) > 1:
                # Need to see how to implement this part with imaginary space format
                raise NotImplementedError(
                    textwrap.fill(
                        textwrap.dedent(
                            f"""
                    Not supporting polymorphic entity fields for the moment:
                    tried to convert data on entity type: {sg_entity_type}, field: {sg_field_name}
                """
                        )
                    )
                )
            entity_type_name_field_code = self._get_entity_type_name_field_code(
                entity_types[0]
            )
            filters = [
                [
                    {
                        "filter_operator": "any",
                        "filters": [
                            [entity_type_name_field_code, "is", val]
                            for val in imgspc_value
                        ],
                    }
                ]
            ]
            if self._entity_type_has_field(entity_types[0], "project"):
                filters.append(["project", "is", self.project])
            return self.sg.find(entity_types[0], filters)
        # How are stored in imgspc format date, date_time, duration, checkbox (bool) field data types?
        else:
            raise NotImplementedError(
                f"Field type `{field_data_type}` imgspc to sg conversion not yet supported"
            )
