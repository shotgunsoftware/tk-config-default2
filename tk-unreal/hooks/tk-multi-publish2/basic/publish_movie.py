# This file is based on templates provided and copyrighted by Autodesk, Inc.
# This file has been modified by Epic Games, Inc. and is subject to the license 
# file included in this repository.

import sgtk
import os
import unreal
import pprint
import subprocess
import sys
import datetime

HookBaseClass = sgtk.get_hook_baseclass()


class UnrealMoviePublishPlugin(HookBaseClass):
    """
    Plugin for publishing an Unreal sequence as a rendered movie file.

    This hook relies on functionality found in the base file publisher hook in
    the publish2 app and should inherit from it in the configuration. The hook
    setting for this plugin should look something like this::

        hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_session.py"

    To learn more about writing a publisher plugin, visit
    http://developer.shotgunsoftware.com/tk-multi-publish2/plugin.html
    """

    # NOTE: The plugin icon and name are defined by the base file plugin.

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        return """Publishes the sequence as a rendered movie to Shotgun. A 
        <b>Publish</b> entry will be created in Shotgun which will include a
        reference to the movie's current path on disk. A <b>Version</b> entry
        will also be created in Shotgun with the movie file being uploaded 
        there. Other users will be able to review the movie in the browser or 
        in RV."""

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """

        # inherit the settings from the base publish plugin
        base_settings = super(UnrealMoviePublishPlugin, self).settings or {}

        # Here you can add any additional settings specific to this plugin
        publish_template_setting = {
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published work files. Should"
                               "correspond to a template defined in "
                               "templates.yml.",
            }
        }

        # update the base settings
        base_settings.update(publish_template_setting)

        return base_settings

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["unreal.asset.LevelSequence"]

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
        
        accepted = True
        publisher = self.parent

        # ensure the publish template is defined
        publish_template_setting = settings.get("Publish Template")
        publish_template = publisher.get_template_by_name(publish_template_setting.value)
        if not publish_template:
            self.logger.debug(
                "A publish template could not be determined for the "
                "sequence item. Not accepting the item."
            )
            accepted = False

        # we've validated the work and publish templates. add them to the item properties
        # for use in subsequent methods
        item.properties["publish_template"] = publish_template

        return {
            "accepted": accepted,
            "checked": True
        }

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """
        # raise an exception here if something is not valid.
        # If you use the logger, warnings will appear in the validation tree.
        # You can attach callbacks that allow users to fix these warnings
        # at the press of a button.
        #
        # For example:
        #
        # self.logger.info(
        #         "Your session is not part of a maya project.",
        #         extra={
        #             "action_button": {
        #                 "label": "Set Project",
        #                 "tooltip": "Set the maya project",
        #                 "callback": lambda: mel.eval('setProject ""')
        #             }
        #         }
        #     )

        asset_path = item.properties.get("asset_path")
        asset_name = item.properties.get("asset_name")
        if not asset_path or not asset_name:
            self.logger.debug("Sequence path or name not configured.")
            return False

        # Get the configured publish template
        publish_template = item.properties.get("publish_template")
        
        # Get the context from the Publisher UI
        context = item.context
        unreal.log("context: {}".format(context))

        # Query the fields needed for the publish template from the context
        try:
            fields = context.as_template_fields(publish_template)
        except Exception:
            # We likely failed because of folder creation, trigger that
            self.parent.sgtk.create_filesystem_structure(
                context.entity["type"],
                context.entity["id"],
                self.parent.engine.instance_name
                )
            # In theory, this should now work because we've created folders and
            # updated the path cache
            fields = item.context.as_template_fields(publish_template)
        unreal.log("context fields: {}".format(fields))

        # Ensure that the current map is saved on disk
        unreal_map = unreal.EditorLevelLibrary.get_editor_world()
        unreal_map_path = unreal_map.get_path_name()

        # Transient maps are not supported, must be saved on disk
        if unreal_map_path.startswith("/Temp/"):
            self.logger.debug("Current map must be saved first.")
            return False

        # Add the map name and level sequence to fields 
        world_name = unreal_map.get_name()
        fields["world"] = world_name
        fields["level_sequence"] = asset_name

        # Stash the level sequence and map paths in properties for the render
        item.properties["unreal_asset_path"] = asset_path
        item.properties["unreal_map_path"] = unreal_map_path
        
        # Add a version number to the fields, incremented from the current asset version
        version_number = self._unreal_asset_get_version(asset_path)
        version_number = version_number + 1
        fields["version"] = version_number

        # Add today's date to the fields
        date = datetime.date.today()
        fields["YYYY"] = date.year
        fields["MM"] = date.month
        fields["DD"] = date.day

        # ensure the fields work for the publish template
        missing_keys = publish_template.missing_keys(fields)
        if missing_keys:
            error_msg = "Missing keys required for the publish template " \
                        "%s" % (missing_keys)
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        item.properties["path"] = publish_template.apply_fields(fields)
        item.properties["publish_path"] = item.properties["path"]
        item.properties["publish_type"] = "Unreal Render"
        item.properties["version_number"] = version_number
            
        return True

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # This is where you insert custom information into `item`, like the
        # path of the file being published or any dependency this publish
        # has on other publishes.

        # get the path in a normalized state. no trailing separator, separators
        # are appropriate for current os, no double separators, etc.
        
        # let the base class register the publish
        
        publish_path = item.properties.get("path")
        publish_path = os.path.normpath(publish_path)

        # Split the destination path into folder and filename
        destination_folder = os.path.split(publish_path)[0]
        movie_name = os.path.split(publish_path)[1]
        movie_name = os.path.splitext(movie_name)[0]

        # Ensure that the destination path exists before rendering the sequence
        self.parent.ensure_folder_exists(destination_folder)

        # Get the level sequence and map paths again
        unreal_asset_path = item.properties["unreal_asset_path"]
        unreal_map_path = item.properties["unreal_map_path"]
        unreal.log("movie name: {}".format(movie_name))
        # Render the movie
        self._unreal_render_sequence_to_movie(destination_folder, unreal_map_path, unreal_asset_path, movie_name)

        # Increment the version number
        self._unreal_asset_set_version(unreal_asset_path, item.properties["version_number"])

        # Publish the movie file to Shotgun
        super(UnrealMoviePublishPlugin, self).publish(settings, item)
        
        # Create a Version entry linked with the new publish
        publish_name = item.properties.get("publish_name")
        
        # Populate the version data to send to SG
        self.logger.info("Creating Version...")
        version_data = {
            "project": item.context.project,
            "code": movie_name,
            "description": item.description,
            "entity": self._get_version_entity(item),
            "sg_path_to_movie": publish_path,
            "sg_task": item.context.task
        }

        publish_data = item.properties.get("sg_publish_data")

        # If the file was published, add the publish data to the version
        if publish_data:
            version_data["published_files"] = [publish_data]

        # Log the version data for debugging
        self.logger.debug(
            "Populated Version data...",
            extra={
                "action_show_more_info": {
                    "label": "Version Data",
                    "tooltip": "Show the complete Version data dictionary",
                    "text": "<pre>%s</pre>" % (
                    pprint.pformat(version_data),)
                }
            }
        )

        # Create the version
        self.logger.info("Creating version for review...")
        version = self.parent.shotgun.create("Version", version_data)

        # Stash the version info in the item just in case
        item.properties["sg_version_data"] = version

        # On windows, ensure the path is utf-8 encoded to avoid issues with
        # the shotgun api
        upload_path = str(item.properties.get("publish_path"))
        unreal.log("upload_path: {}".format(upload_path))

        # Upload the file to SG
        self.logger.info("Uploading content...")
        self.parent.shotgun.upload(
            "Version",
            version["id"],
            upload_path,
            "sg_uploaded_movie"
        )
        self.logger.info("Upload complete!")

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        # do the base class finalization
        super(UnrealMoviePublishPlugin, self).finalize(settings, item)
        
        pass

    def _get_version_entity(self, item):
        """
        Returns the best entity to link the version to.
        """
        if item.context.entity:
            return item.context.entity
        elif item.context.project:
            return item.context.project
        else:
            return None

    def _unreal_asset_get_version(self, asset_path):
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        version_number = 0
        
        if not asset:
            return version_number
            
        engine = sgtk.platform.current_engine()
        tag = engine.get_metadata_tag("version_number")
        
        metadata = unreal.EditorAssetLibrary.get_metadata_tag(asset, tag)
        
        if not metadata:
            return version_number
        
        try:
            version_number = int(metadata)
        except ValueError:
            pass
            
        return version_number

    def _unreal_asset_set_version(self, asset_path, version_number):
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        
        if not asset:
            return
            
        engine = sgtk.platform.current_engine()
        tag = engine.get_metadata_tag("version_number")
        
        unreal.EditorAssetLibrary.set_metadata_tag(asset, tag, str(version_number))
        unreal.EditorAssetLibrary.save_loaded_asset(asset)
        
        # The save will pop up a progress bar that will bring the editor to the front thus hiding the publish app dialog
        # Workaround: Force all Shotgun dialogs to be brought to front
        engine = sgtk.platform.current_engine()
        for dialog in engine.created_qt_dialogs:
            dialog.raise_()

        
    def _unreal_render_sequence_to_movie(self, destination_path, unreal_map_path, sequence_path, movie_name):
        """
        Renders a given sequence in a given level to a movie file
        
        :param destination_path: Destionation folder where to generate the movie file
        :param unreal_map_path: Path of the Unreal map in which to run the sequence
        :param sequence_path: Content Browser path of sequence to render
        :param movie_name: Filename of the movie that will be generated
        :returns: True if a movie file was generated, False otherwise
                  string representing the path of the generated movie file
        """
        # First, check if there's a file that will interfere with the output of the Sequencer
        # Sequencer can only render to avi file format
        output_filename = "{}.avi".format(movie_name)
        output_filepath = os.path.join(destination_path, output_filename)

        if os.path.isfile(output_filepath):
            # Must delete it first, otherwise the Sequencer will add a number in the filename
            try:
                os.remove(output_filepath)
            except OSError as e:
                self.logger.debug("Couldn't delete {}. The Sequencer won't be able to output the movie to that file.".format(output_filepath))
                return False, None

        # Render the sequence to a movie file using the following command-line arguments
        cmdline_args = []
        
        # Note that any command-line arguments (usually paths) that could contain spaces must be enclosed between quotes
        unreal_exec_path = '"{}"'.format(sys.executable)

        # Get the Unreal project to load
        unreal_project_filename = "{}.uproject".format(unreal.SystemLibrary.get_game_name())
        unreal_project_path = os.path.join(unreal.SystemLibrary.get_project_directory(), unreal_project_filename)
        unreal_project_path = '"{}"'.format(unreal_project_path)

        # Important to keep the order for these arguments
        cmdline_args.append(unreal_exec_path)       # Unreal executable path
        cmdline_args.append(unreal_project_path)    # Unreal project
        cmdline_args.append(unreal_map_path)        # Level to load for rendering the sequence
        
        # Command-line arguments for Sequencer Render to Movie
        # See: https://docs.unrealengine.com/en-us/Engine/Sequencer/Workflow/RenderingCmdLine
        sequence_path = "-LevelSequence={}".format(sequence_path)
        cmdline_args.append(sequence_path)          # The sequence to render
        
        output_path = '-MovieFolder="{}"'.format(destination_path)
        cmdline_args.append(output_path)            # output folder, must match the work template

        movie_name_arg = "-MovieName={}".format(movie_name)
        cmdline_args.append(movie_name_arg)         # output filename
        
        cmdline_args.append("-game")
        cmdline_args.append("-MovieSceneCaptureType=/Script/MovieSceneCapture.AutomatedLevelSequenceCapture")
        cmdline_args.append("-ResX=1280")
        cmdline_args.append("-ResY=720")
        cmdline_args.append("-ForceRes")
        cmdline_args.append("-Windowed")
        cmdline_args.append("-MovieCinematicMode=yes")
        cmdline_args.append("-MovieFormat=Video")
        cmdline_args.append("-MovieFrameRate=24")
        cmdline_args.append("-MovieQuality=75")
        cmdline_args.append("-NoTextureStreaming")
        cmdline_args.append("-NoLoadingScreen")
        cmdline_args.append("-NoScreenMessages")

        unreal.log("Sequencer command-line arguments: {}".format(cmdline_args))
        
        # Send the arguments as a single string because some arguments could contain spaces and we don't want those to be quoted
        subprocess.call(" ".join(cmdline_args))

        return os.path.isfile(output_filepath), output_filepath
