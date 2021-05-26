# Copyright (c) 2021 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import base64
import os
import xml.etree.ElementTree as ET

import sgtk
from sgtk.util import LocalFileStorageManager
import vrAssetsModule

HookBaseClass = sgtk.get_hook_baseclass()


class VREDMaterialsPublishPlugin(HookBaseClass):

    ############################################################################
    # standard publish plugin properties

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """

        # look for icon one level up from this hook's folder in "icons" folder
        return os.path.join(self.disk_location, "icons", "publish.png")

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Publish Material to Shotgun"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        loader_url = "https://support.shotgunsoftware.com/hc/en-us/articles/219033078"

        return """
            Publishes the material to Shotgun. A <b>Publish</b> entry will be
            created in Shotgun which will include a reference to the file's current
            path on disk. Other users will be able to access the published file via
            the <b><a href='%s'>Loader</a></b> so long as they have access to
            the file's location on disk.
            """ % (
            loader_url,
        )

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to recieve
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts
        as part of its environment configuration.
        """
        return {
            "Library Project ID": {
                "type": "int",
                "default": None,
                "description": "Photoshop export image options.",
            },
            "Pipeline Config Name": {
                "type": "str",
                "default": sgtk.commands.constants.PRIMARY_PIPELINE_CONFIG_NAME,
                "description": "Name of the pipeline configuration to use when getting the library project config.",
            },
            "Publish Material Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published VRED material. Should"
                "correspond to a template defined in "
                "templates.yml.",
            },
        }

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["vred.material"]

    def accept(self, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        # the Project Library ID is mandatory
        if settings["Library Project ID"].value is None:
            self.logger.warning(
                "Library Project ID is mandatory. Skipping this plugin!"
            )
            return {"accepted": False}

        # the Publish Material Template is mandatory
        if settings["Publish Material Template"].value is None:
            self.logger.warning(
                "Publish Material Template is mandatory. Skipping this plugin!"
            )
            return {"accepted": False}

        return {"accepted": True}

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        # check if the library project exists in Shotgun
        library_project = self.parent.shotgun.find_one(
            "Project", [["id", "is", settings["Library Project ID"].value]]
        )
        if not library_project:
            self.logger.error("Couldn't find Library Project in SG.")
            return False

        # TODO: improve the way we retrieve pipeline configs
        # TODO: ensure the Pipeline Config is cached on disk
        # get the pipeline configuration and the tank instance associated to the library project
        pc_local_path = self.__get_pipeline_configuration_local_path(
            settings["Library Project ID"].value, settings["Pipeline Config Name"].value
        )
        if not pc_local_path:
            self.logger.error(
                "Couldn't get the pipeline configuration associated to the Library Project."
            )
            return False

        tk_library = sgtk.sgtk_from_path(pc_local_path)
        if not tk_library:
            self.logger.error("Couldn't get sgtk instance for the Library Project.")
            return False
        item.properties["tk_library"] = tk_library

        # get the material template from the Library project configuration
        material_template = tk_library.templates.get(
            settings["Publish Material Template"].value
        )
        if not material_template:
            self.logger.error(
                "Couldn't get Publish Material Template from the Library project configuration."
            )
            return False

        # store the item in its properties
        item.properties["material_template"] = material_template

        # get the path to the VRED preference file
        preference_path = os.path.join(
            os.environ.get("APPDATA"), "VREDPro", "preferences.xml"
        )
        if not os.path.isfile(preference_path):
            self.logger.error("Couldn't access VRED preference file")
            return False

        item.properties["preference_path"] = preference_path

        # TODO: check if the material already exists in the Asset Manager, if so return False but offer a fix to
        #   load it and replace the existing material by the one from the library

        return True

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # build the publish path. We'll need it to setup the VRED Asset Manager path
        template_fields = {"Material": item.properties.material.getName()}
        material_path = item.properties.material_template.apply_fields(template_fields)
        library_path = os.path.dirname(material_path).replace("\\", "/")

        # access VRED preferences to ensure that the path to the Asset Manager is correctly setup, otherwise add it to
        # the prefs
        tree = ET.parse(item.properties.preference_path)
        root_node = tree.getroot()
        asset_node = root_node.find(".//*[@name='Assets Urls Materials']")
        material_urls = base64.b64decode(asset_node.text).decode("utf-8")

        paths = material_urls.split("file:///")
        if library_path not in paths:
            paths.append(library_path)
            # update the preferences
            encoded_paths = [
                str(base64.b64encode("file:///{}".format(p).encode("utf-8")), "utf-8")
                for p in paths
                if p != ""
            ]
            encoded_urls = "|{}|".format(":".join(encoded_paths))
            # TODO: add the paths to the preference file and reload them; we should find a way to manage preferences
            #   inside of the SG environment instead of erasing global preferences
            #   can we introduce an environment variable to dynamically change the preferences location?

        # create the material in Shotgun
        sg_data = {
            "project": {"type": "Project", "id": settings["Library Project ID"].value},
            "code": item.properties.material.getName(),
        }
        sg_material = self.parent.shotgun.create("CustomEntity02", sg_data)

        # export the file to the filesystem
        vrAssetsModule.createMaterialAsset(item.properties.material, library_path)

        # finally, publish it to SG
        material_context = item.properties.tk_library.context_from_entity_dictionary(
            sg_material
        )
        publish_data = {
            "tk": item.properties.tk_library,
            "context": material_context,
            "comment": item.description,
            "path": material_path,
            "name": item.properties.material.getName(),
            "version_number": 1,
            "thumbnail_path": os.path.join(
                material_path, "{}.png".format(item.properties.material.getName())
            ),
            "published_file_type": "VRED Material",
        }
        item.properties.sg_publish_data = sgtk.util.register_publish(**publish_data)

        # update the thumbnail of the material entity
        self.parent.shotgun.upload_thumbnail(
            sg_material["type"],
            sg_material["id"],
            os.path.join(
                material_path, "{}.png".format(item.properties.material.getName())
            ),
        )

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once
        all the publish tasks have completed, and can for example
        be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        pass

    def __get_pipeline_configuration_local_path(self, project_id, config_name):
        """
        Get the path to the local configuration (the one which stands in the Sgtk cache folder) in order to be able
        to build a :class`sgtk.Sgtk` instance from this path

        :param project_id: Id of the project we want to retrieve the config for
        :returns: The local path to the config if we could determine which config to use, None otherwise.
        """

        plugin_id = "basic.desktop"

        # first, start the toolkit manager to get all the pipeline configurations related to the distant project
        # here, we are going to use the default plugin id "basic.*" to find the pipeline configurations
        mgr = sgtk.bootstrap.ToolkitManager()
        mgr.plugin_id = sgtk.commands.constants.DEFAULT_PLUGIN_ID
        pipeline_configurations = mgr.get_pipeline_configurations(
            {"type": "Project", "id": project_id}
        )

        if not pipeline_configurations:
            self.logger.warning(
                "Couldn't retrieve any pipeline configuration linked to project {}".format(
                    project_id
                )
            )
            return

        if len(pipeline_configurations) == 1:
            pipeline_config = pipeline_configurations[0]

        else:

            # try to determine which configuration we want to use:
            # 1- if one and only one pipeline configuration is restricted to this project, use it
            # 2- if one pipeline configuration is named Primary and linked to this project, use it
            # 3- reject all the other cases

            pipeline_config = self.__get_project_pipeline_configuration(
                pipeline_configurations, project_id
            )

            if not pipeline_config:
                pipeline_config = self.__get_primary_pipeline_configuration(
                    pipeline_configurations, project_id, config_name
                )

        if not pipeline_config:
            self.logger.warning(
                "Couldn't get the pipeline configuration linked to project {}: too many configurations".format(
                    project_id
                )
            )
            return None

        config_local_path = LocalFileStorageManager.get_configuration_root(
            self.parent.sgtk.shotgun_url,
            project_id,
            plugin_id,
            pipeline_config["id"],
            LocalFileStorageManager.CACHE,
        )

        # ensure that the config is cached locally
        if not os.path.exists(config_local_path):
            mgr.pipeline_configuration = pipeline_config["id"]
            mgr.plugin_id = plugin_id
            mgr.prepare_engine(
                self.parent.engine.name, {"type": "Project", "id": project_id}
            )

        return os.path.join(config_local_path, "cfg")

    @staticmethod
    def __get_project_pipeline_configuration(pipeline_configurations, project_id):
        """
        Parse the pipeline configuration list in order to find if one of them is only used by this project.

        :param pipeline_configurations: List of pipeline configurations to parse
        :param project_id:              Id of the project we want to get the pipeline configuration for
        :returns: The pipeline configuration if only one config has been defined for this project, None otherwise.
        """

        pipeline_configuration = None

        for pc in pipeline_configurations:
            if not pc["project"]:
                continue
            if pc["project"]["id"] == project_id:
                if pipeline_configuration:
                    return None
                pipeline_configuration = pc

        return pipeline_configuration

    @staticmethod
    def __get_primary_pipeline_configuration(
        pipeline_configurations, project_id, config_name
    ):
        """
        Parse the pipeline configuration list in order to find if one of them has been defined as "Primary" for this
        project.

        :param pipeline_configurations: List of pipeline configurations to parse
        :param project_id:              Id of the project we want to get the pipeline configuration for
        :returns: The pipeline configuration if a "Primary" config has been found for this project, None otherwise.
        """

        for pc in pipeline_configurations:
            # if pc["name"] == sgtk.commands.constants.PRIMARY_PIPELINE_CONFIG_NAME:
            if pc["name"] == config_name:
                return pc

        return None
