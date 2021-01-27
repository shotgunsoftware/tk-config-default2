# ShotgunWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import argparse
import json
import logging
import os
import pprint
import uuid
from collections import defaultdict

import shotgun_api3

import pmt
from .converter import ImgspcSgConverter

log = logging.getLogger(__name__)

# --------------
# Shotgun Writer class
# --------------
class ShotgunWriter:
    def __init__(self, config_data):
        self._config_data = config_data
        self._sg = shotgun_api3.Shotgun(
            config_data["SERVER_PATH"],
            config_data["SCRIPT_NAME"],
            config_data["SCRIPT_KEY"],
        )

        with open(config_data["MAPPING_FILE"], "r") as mapping_file:
            self._mappings = json.load(mapping_file)["mappings"]

        self._collision_resolution = config_data.get("COLLISION_RESOLUTION")
        self._sg_pipeline_configuration = self._sg.find_one(
            "PipelineConfiguration",
            [["code", "is", config_data["PIPELINE_CONFIGURATION_NAME"]]],
        )
        log.debug(
            "Pipeline Configuration set to {}".format(
                pprint.pformat(self._sg_pipeline_configuration)
            )
        )

        sg_local_storage = self._sg.find_one(
            "LocalStorage", [["code", "is", "primary"]], ["windows_path"]
        )
        if not sg_local_storage:
            log.error("No 'primary' local storage found in Shotgun.")
            exit()
        else:
            self._local_storage_path = sg_local_storage["windows_path"]
            log.info(
                "Local storage path set to {}".format(self._local_storage_path)
            )
        self._sg_project = None
        self._users = None
        self._create_users()

        if not self._config_data.get("FILESYSTEMLOCATION_TEMPLATES"):
            raise KeyError(
                "No FilesystemLocation templates in the config file. See README.md on how to set up config "
                "file."
            )

        self._imgspc_sg_converter = ImgspcSgConverter(self._sg, self._mappings)

        self._publishedfile_placement_wrong = False

    def write_project_to_shotgun(self, project_entity):
        """Creates a project into Shotgun defined by the json data

        :param project_entity: dict describing the project, in imgspc format
        :type project_entity: dict

        :return: Shotgun project entity that was created
        :rtype: dict
        """
        self._sg_project = None  # clearing old project if any
        sg_project = self._build(project_entity)
        log.info("Project '{}' created successfully".format(sg_project["name"]))
        log.info(
            "You can access it at https://imgspc.shotgunstudio.com/page/project_overview?project_id={}".format(
                sg_project["id"]
            )
        )

        if self._publishedfile_placement_wrong:
            log.warning(
                "Some Published Files could not be located on your local machine. This will inhibit ToolKit "
                "functionality. Ensure you have the data directory '{}' with the same contents as the "
                "'thimble.zip' folder".format(
                    os.path.join(
                        self._local_storage_path, self._sg_project["tank_name"]
                    )
                )
            )
        return sg_project

    def _build(self, entity, sg_parent=None):
        """Recursively builds entity by creating the Shotgun entity and its children if any.

        :param entity: dict describing the entity, in imgspc format
        :type entity: dict
        :param sg_parent: parent entity of entity to be built, in sg format
        :type sg_parent: dict

        :return: the built Shotgun entity
        :rtype: dict
        """
        sg_entity = self._create(entity, sg_parent)
        log.debug("Created {}={}".format(entity["type"], sg_entity))
        self._create_filesystem_location(sg_entity)

        # Ensure to first create assets, then sequences
        children = entity.get("children", [])
        children_assets = filter(
            lambda ent: ent.get("type", "").lower() == "asset", children
        )
        children_sequences = filter(
            lambda ent: ent.get("type", "").lower() == "sequence", children
        )
        other_children = filter(
            lambda ent: ent.get("type", "").lower()
            not in ["asset", "sequence"],
            children,
        )
        for asset in children_assets:
            self._build(asset, sg_entity)
        for sequence in children_sequences:
            self._build(sequence, sg_entity)
        for entity in other_children:
            self._build(entity, sg_entity)

        return sg_entity

    def _create(self, entity, sg_parent=None):
        """Creates Shotgun entity from imgspc entity

        :param entity: dict describing the entity, in imgspc format
        :type entity: dict
        :param sg_parent: dict of parent entity, in sg format
        :type sg_parent: dict
        :return: the created Shotgun entity
        :rtype: dict
        """
        entity_type = entity["type"]
        if not self._mappings.get(entity_type):  # entity not defined in mapping
            raise KeyError(
                "'{}' entity is not defined by imgspc".format(entity_type)
            )

        # modding data to Shotgun field standard
        data = {}
        if self._sg_project:
            data["project"] = self._sg_project
        for imgspc_field in entity:
            sg_field = self._mappings[entity_type].get(imgspc_field)
            if sg_field:  # there exists corresponding Shotgun field
                data[sg_field] = self.convert_data(
                    entity_type, entity[imgspc_field], sg_field
                )

        log.info("Creating {} '{}'".format(entity_type, entity["name"]))
        log.debug(
            "Entity data ={}, parent={}".format(
                pprint.pformat(data), pprint.pformat(sg_parent)
            )
        )
        # switcher directs to correct creation method for specialized entities
        method_switcher = {
            "Project": self._create_project,
            "Task": self._create_task,
            "Shot": self._create_shot,
            "Note": self._create_note,
            "PublishedFile": self._create_published_file,
            "Version": self._create_version,
        }
        method = method_switcher.get(entity_type)

        if not method:
            return self._sg.create(
                entity_type, data
            )  # default entity creation method

        return method(data, sg_parent)

    # -----------------------
    # Entity creation methods
    # -----------------------
    def _create_project(self, project_data, sg_parent=None):
        """Creates Shotgun Project described by entity

        :param project_data: project data in Shotgun compatible form
        :type project_data: dict

        :return: Shotgun project entity
        :rtype: dict
        """
        # check if project with same name already exists
        project_name = project_data["name"]
        existing_project = self._sg.find_one(
            "Project", [["name", "is", project_name]]
        )
        if existing_project:  # name already exists
            if self._collision_resolution == "rename":
                new_name = project_name + "_" + str(uuid.uuid4())
                log.info("Renaming project to " + new_name)
                project_data["name"] = new_name

            elif self._collision_resolution == "archive":
                name_of_archived_proj = (
                    project_name + "_archived_" + str(uuid.uuid4())
                )
                log.info("Archiving old project as " + name_of_archived_proj)
                self._sg.update(
                    "Project",
                    existing_project.get("id"),
                    {"archived": True, "name": name_of_archived_proj},
                )

            else:
                log.info(
                    "Project not created - '{}' already exists & no resolution method specified".format(
                        project_name
                    )
                )
                raise Exception(
                    "Project named "
                    + project_name
                    + " already exists. Use the optional command line "
                    "arguments --col_res for handling name collisions."
                )

        project_data["layout_project"] = self._sg.find_one(
            "Project",
            [["is_template", "is", True], ["name", "contains", "Thimble"]],
        )

        project_data["tank_name"] = "".join(
            c.lower() for c in project_data["name"] if c.isalpha()
        )
        sg_project = self._sg.create("Project", project_data)
        self._sg_project = sg_project
        self._imgspc_sg_converter.project = sg_project
        return sg_project

    def _create_note(self, note_data, sg_parent=None):
        """Creates Shotgun Project described by entity

        :param note_data: note data in shotgun compatible form
        :type note_data: dict
        :param sg_parent: parent entity in shotgun format
        :type sg_parent: dict

        :return: Shotgun shot; name and id
        :rtype: dict
        """
        # Along with a "created_by" field, shotgun notes have a "user" field for the author
        # We assume the creator and author to be the same person
        note_data["user"] = note_data["created_by"]

        note_data["note_links"] = [sg_parent]
        attachments = note_data.pop("attachments", [])
        replies = note_data.pop("replies", [])

        sg_note = self._sg.create("Note", note_data)
        log.debug("Note created: \n{}".format(pprint.pformat(sg_note)))
        for file_name in attachments:
            if not os.path.exists(file_name):  # try as relative path
                file_name = os.path.join(
                    self._config_data["PROJECT_DATA_DIRECTORY"], file_name
                )
            if not os.path.exists(file_name):
                raise FileNotFoundError(file_name)
            self._sg.upload(
                "Note", sg_note["id"], file_name, field_name="attachments"
            )

        for reply in replies:
            author = self._sg.find_one(
                "HumanUser", [["name", "is", self._users[reply["author"]]]]
            )
            self._sg.create(
                "Reply",
                {"content": reply["body"], "user": author, "entity": sg_note},
            )
        return sg_note

    def _create_task(self, task_data, sg_parent=None):
        """Creates Shotgun Project described by entity

        :param task_data: task data in shotgun compatible form
        :type task_data: dict
        :param sg_parent: parent entity in shotgun format
        :type sg_parent: dict

        :return: Shotgun task; name and id
        :rtype: dict
        """
        task_data["entity"] = sg_parent
        logging.debug(f"Creating a Task with data: {pprint.pformat(task_data)}")

        task_data["step"] = self._imgspc_sg_converter.get_step_for_task(
            sg_parent["type"], task_data["step"]
        )

        sg_task = self._sg.create("Task", task_data)
        log.debug("Task created: " + str(sg_task))
        return sg_task

    def _create_shot(self, shot_data, sg_parent=None):
        """Creates Shotgun Project described by entity

        :param shot_data: shot data in shotgun compatible form
        :type shot_data: dict
        :param sg_parent: parent entity in shotgun format
        :type sg_parent: dict

        :return: Shotgun shot; name and id
        :rtype: dict
        """
        if sg_parent["type"] == "Sequence":
            shot_data["sg_sequence"] = sg_parent

        sg_shot = self._sg.create("Shot", shot_data)
        log.debug("Shot created: " + str(sg_shot))
        return sg_shot

    def _create_published_file(self, pf_data, sg_parent=None):
        """Creates Shotgun Published File described by pf_data
        Creates FilesystemLocation entities when necessary

        :param pf_data: Published file data in shotgun compatible form
        :type pf_data: dict
        :param sg_parent: parent entity in shotgun format
        :type sg_parent: dict

        :return: Shotgun PublishedFile; name and id
        :rtype: dict
        """
        if sg_parent["type"] == "Task":
            pf_data["entity"] = sg_parent["entity"]
            pf_data["task"] = sg_parent

        # create downstream file, data maintains upstream's
        elif sg_parent["type"] == "PublishedFile":
            pf_data["entity"] = sg_parent["entity"]
            pf_data["task"] = sg_parent.get("task")

            upstream_pfs = pf_data.get("upstream_published_files", [])
            upstream_pfs.append(sg_parent)
            pf_data["upstream_published_files"] = upstream_pfs

        else:
            pf_data["entity"] = sg_parent

        local_path = os.path.join(
            self._local_storage_path,
            self._sg_project["tank_name"],
            os.path.normpath(pf_data["path_cache"]),
        )
        pf_data["path"] = {"local_path": local_path}

        if not os.path.exists(local_path):
            log.warning(
                "There is no published file {}. Please ensure you have put the data in the right place.".format(
                    local_path
                )
            )
            self._publishedfile_placement_wrong = True

        sg_pf = self._sg.create("PublishedFile", pf_data)
        log.debug("PublishedFile created: " + str(sg_pf))
        return sg_pf

    def _create_version(self, vr_data, sg_parent=None):
        """Creates Shotgun Version described by entity
            Currently only supports mp4 videos attached to versions, not other videos

        :param pf_data: version data in shotgun compatible form
        :type pf_data: dict
        :param sg_parent: parent entity in shotgun format
        :type sg_parent: dict

        :return: Shotgun version; name and id
        :rtype: dict
        """

        # link version to a task if necessary
        task_name = vr_data.get("sg_task")
        if task_name:
            vr_data["sg_task"] = self._sg.find_one(
                "Task",
                [
                    ["entity", "is", sg_parent],
                    [self._mappings["Task"]["name"], "is", task_name],
                ],
            )

        # stashing the mp4_file which can only be uploaded after the version is created
        mp4_file = vr_data.get("sg_uploaded_movie_mp4")
        if mp4_file:
            del vr_data["sg_uploaded_movie_mp4"]

        vr_data["entity"] = sg_parent
        sg_vr = self._sg.create("Version", vr_data)

        if mp4_file:
            self._sg.upload(
                "Version",
                sg_vr["id"],
                mp4_file,
                field_name="sg_uploaded_movie_mp4",
            )

        return sg_vr

    def convert_data(
        self, entity_type, imgspc_value, sg_field_name, extra_data=None
    ):
        """Converts imgspc value into a form compatible with the given Shotgun field
        If the imgspc_value & sg_field_name are not sufficient to find the specific corresponding Shotgun value,
        A list of possible Shotgun values will be returned, to be resolved at the entity creation method
        (where the sg_parent dictate which value is correct)

        :param sg_field_name: name of the Shotgun field you want to convert the value to
        :param imgspc_value: value in imgspc format
        :return: the imgspc_value in Shotgun compatible form
        """

        log.debug(
            "Converting [{}] to a Shotgun form for field '{}'".format(
                imgspc_value, sg_field_name
            )
        )

        extra_data_ = {
            # `self._config_data`["PROJECT_DATA_DIRECTORY"] is set when needed
            "project_data_directory": self._config_data.get(
                "PROJECT_DATA_DIRECTORY"
            ),
            "users": self._users,
        }
        if extra_data:
            extra_data_.update(extra_data)

        sg_value = self._imgspc_sg_converter.convert(
            imgspc_value, entity_type, sg_field_name, extra_data_
        )

        log.debug(
            "Converted [{}] -> [{}] for field '{}'".format(
                imgspc_value, sg_value, sg_field_name
            )
        )
        return sg_value

    def _create_users(self):
        """
        Creates the users defined in the config file if they don't already exist in the database.
        By default these Users are disabled.
        :return:
        """
        self._users = {}
        for permission_group in self._config_data.get("USERS", []):
            if permission_group == "doc":
                continue

            sg_permission_rule_set = self._sg.find_one(
                "PermissionRuleSet", [["code", "is", permission_group]]
            )

            for user_role in self._config_data["USERS"][permission_group]:
                user_name = self._config_data["USERS"][permission_group][
                    user_role
                ]
                self._users[user_role] = user_name
                if self._sg.find_one("HumanUser", [["name", "is", user_name]]):
                    continue
                user_data = {
                    "firstname": user_name.split(" ", 1)[0],
                    "lastname": user_name.split(" ", 1)[1],
                    "permission_rule_set": sg_permission_rule_set,
                    "sg_status_list": "dis",
                    "login": user_name,
                }
                self._sg.create("HumanUser", user_data)

    def set_collision_resolution(self, col_res):
        if col_res == "archive" or col_res == "rename":
            log.debug("collision resolution set to " + col_res)
            self._collision_resolution = col_res
        else:
            log.debug("collision resolution set to None")
            self._collision_resolution = None

    def _create_filesystem_location(self, sg_entity):

        if sg_entity["type"] == "Asset":
            sg_asset = sg_entity
            path_template = self._config_data["FILESYSTEMLOCATION_TEMPLATES"][
                "Asset"
            ]
            local_path = os.path.normpath(
                os.path.join(
                    self._local_storage_path, self._sg_project["tank_name"]
                )
                + "/"
                + path_template.format(
                    sg_asset_type=sg_asset["sg_asset_type"],
                    Asset=sg_asset["code"],
                    Step="",
                )
            )

            if not self._mappings.get("Asset"):
                raise AttributeError("Mapping configuration has no 'Asset' key")
            if not self._mappings["Asset"].get("name"):
                raise AttributeError(
                    "Asset mapping configuration has no 'name' key"
                )
            fsl_data = {
                "code": sg_asset[self._mappings["Asset"]["name"]],
                "entity": sg_asset,
                "is_primary": True,
                "path": {
                    "local_path": local_path,
                    "name": local_path.replace(
                        os.path.join(
                            self._local_storage_path,
                            self._sg_project["tank_name"],
                        ),
                        "[primary]",
                    ),
                },
                "pipeline_configuration": self._sg_pipeline_configuration,
                "project": self._sg_project,
            }
            log.debug(
                "creating asset's FilesystemLocation={}".format(
                    self._sg.create("FilesystemLocation", fsl_data)
                )
            )

        if sg_entity["type"] == "Sequence":
            sg_sequence = sg_entity
            # create the FSL for the Sequence
            path_template = self._config_data["FILESYSTEMLOCATION_TEMPLATES"][
                "Sequence"
            ]
            local_path = os.path.normpath(
                os.path.join(
                    self._local_storage_path, self._sg_project["tank_name"]
                )
                + "/"
                + path_template.format_map(
                    defaultdict(str, Sequence=sg_sequence["code"])
                )
            )

            fsl_data = {
                "code": sg_sequence["code"],
                "entity": sg_sequence,
                "is_primary": True,
                "path": {
                    "local_path": local_path,
                    "name": local_path.replace(
                        os.path.join(
                            self._local_storage_path,
                            self._sg_project["tank_name"],
                        ),
                        "[primary]",
                    ),
                },
                "pipeline_configuration": self._sg_pipeline_configuration,
                "project": self._sg_project,
            }
            log.debug(
                "creating sequence FilesystemLocation={}".format(
                    self._sg.create("FilesystemLocation", fsl_data)
                )
            )

        if sg_entity["type"] == "Shot":
            sg_shot = sg_entity
            path_template = self._config_data["FILESYSTEMLOCATION_TEMPLATES"][
                "Shot"
            ]
            parent_fsl = self._sg.find_one(
                "FilesystemLocation",
                [["entity", "is", sg_shot["sg_sequence"]]],
                ["path"],
            )

            # formatting only the portion of the path template relevant to the shot
            # assuming that the rest of the path has been templated already in the parent file system location
            shot_path = path_template.format_map(
                defaultdict(str, Shot=sg_shot["code"])
            )
            shot_path = shot_path[shot_path.index("/") :]

            local_path = os.path.normpath(
                parent_fsl["path"]["local_path"] + shot_path
            )

            fsl_data = {
                "code": sg_shot["code"],
                "entity": sg_shot,
                "is_primary": True,
                "path": {
                    "local_path": local_path,
                    "name": local_path.replace(
                        os.path.join(
                            self._local_storage_path,
                            self._sg_project["tank_name"],
                        ),
                        "[primary]",
                    ),
                },
                "pipeline_configuration": self._sg_pipeline_configuration,
                "project": self._sg_project,
            }
            log.debug(
                "creating shot FilesystemLocation={}".format(
                    self._sg.create("FilesystemLocation", fsl_data)
                )
            )

        if sg_entity["type"] == "Task":
            sg_task = sg_entity
            # create FileSystemLocation for the task
            path_template = self._config_data["FILESYSTEMLOCATION_TEMPLATES"][
                sg_task["entity"]["type"]
            ]
            parent_fsl = self._sg.find_one(
                "FilesystemLocation",
                [["entity", "is", sg_task["entity"]]],
                ["path"],
            )

            # grab step's information
            sg_step = self._sg.find_one(
                "Step",
                [["id", "is", sg_task["step"]["id"]]],
                ["short_name", "code"],
            )

            # formatting only the portion of the path template relevant to the task
            # assuming that the rest of the path has been templated already in the parent file system location
            task_path = path_template.format_map(
                defaultdict(str, Step=sg_step["short_name"])
            )
            task_path = os.path.normpath(task_path[task_path.index("/") :])
            local_path = os.path.normpath(
                parent_fsl["path"]["local_path"] + task_path
            )

            fsl_data = {
                "code": sg_step["code"],
                "entity": sg_step,
                "is_primary": True,
                "path": {
                    "local_path": local_path,
                    "name": local_path.replace(
                        os.path.join(
                            self._local_storage_path,
                            self._sg_project["tank_name"],
                        ),
                        "[primary]",
                    ),
                },
                "pipeline_configuration": self._sg_pipeline_configuration,
                "project": self._sg_project,
            }
            log.debug(
                "creating step FilesystemLocation={}".format(
                    self._sg.create("FilesystemLocation", fsl_data)
                )
            )


# MAIN FUNCTION
def create_shotgun_project(
    project_filepath,
    config_filepath,
    collision_resolution=None,
    log_level="INFO",
):
    """Creates a project into Shotgun from the files given

    :param log_level: specifies level of logs to print
    :param collision_resolution: dictates how to handle creating a project whose name is already in use,
        rename: rename current project,
        archive: archive & rename existing project.
    :param config_filepath: path to the Shotgun config file, containing the parameters of the target Shotgun server
    :type config_filepath: str
    :param project_filepath: path to the json file containing the project's data in imgspc format
    :type project_filepath: str

    :return: Shotgun project entity that was created
    :rtype: dict
    """

    logging.root.setLevel(log_level)
    log.info("Setting log level to " + log_level)

    # normalizing paths
    project_filepath = os.path.normpath(project_filepath)
    config_filepath = os.path.normpath(config_filepath)

    log.info("Using project file {}".format(project_filepath))
    log.info("Using config file {}".format(config_filepath))

    with open(config_filepath, "r") as config_json_file:
        config_data = json.load(config_json_file)
        if not os.path.exists(
            config_data["MAPPING_FILE"]
        ):  # path is not absolute
            config_data["MAPPING_FILE"] = os.path.join(
                os.path.dirname(config_filepath), config_data["MAPPING_FILE"]
            )  # try as relative path
        if not os.path.exists(config_data["MAPPING_FILE"]):
            log.warning("No mapping file at " + config_data["MAPPING_FILE"])
            raise FileNotFoundError(
                "No mapping file at " + config_data["MAPPING_FILE"]
            )

        config_data["CONFIG_DIRECTORY"] = os.path.dirname(config_filepath)
        config_data["MAPPING_FILE"] = os.path.normpath(
            config_data["MAPPING_FILE"]
        )
        log.info("Using mapping file {}".format(config_data["MAPPING_FILE"]))

    with open(project_filepath, "r") as project_json_file:
        project_data = json.load(project_json_file)
        config_data["PROJECT_DATA_DIRECTORY"] = os.path.dirname(
            project_filepath
        )

    config_data["COLLISION_RESOLUTION"] = collision_resolution
    sg_writer = ShotgunWriter(config_data)
    return sg_writer.write_project_to_shotgun(project_data)


def main():
    if os.name != "nt":
        log.error("The Project Migration tool can only run on Windows")
        raise OSError("The Project Migration tool can only run on Windows")

    # collecting cmd line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "project_filepath",
        type=str,
        help="Full path to the project file you wish to use",
    )
    parser.add_argument(
        "config_filepath",
        type=str,
        help="Full path to the shotgun configuration file you wish to use",
    )
    parser.add_argument(
        "--col_res",
        choices=["archive", "rename"],
        help="specifies the collision resolution method if project's name already exists. archive: "
        "archives the existing Shotgun project, rename: changes the name of the project "
        "about to be created, leaving the existing Shotgun project untouched",
    )

    parser.add_argument(
        "--log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="specifies the level of logs to print",
        default="INFO",
    )

    args = parser.parse_args()
    create_shotgun_project(
        args.project_filepath,
        args.config_filepath,
        args.col_res,
        args.log_level,
    )
    log.info("Log file can be found at {}".format(pmt.LOG_FILE_PATH))


if __name__ == "__main__":
    main()
