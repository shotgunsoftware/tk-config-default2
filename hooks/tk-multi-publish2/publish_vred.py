# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import os
import shutil
import subprocess

import sgtk
from sgtk.platform.qt import QtGui, QtCore

import alias_api

HookBaseClass = sgtk.get_hook_baseclass()


class AliasCreateVREDFilePlugin(HookBaseClass):
    """Plugin for creating a VRED scene from the current Alias session."""

    @property
    def name(self):
        """One line display name describing the plugin"""
        return "Create VRED Scene"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        return """
        <p>
            This plugin will create a new VRED .vpb file by importing the current Alias session file once it has been published to
            ShotGrid.<p>
            This plugin requires that you have an installation of VRED Professional on the same workstation as Alias.
            If you do not have Administrator rights to install this yourself, please contact your System Administrator to have it installed.

        </p>
        """

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
        base_settings = super(AliasCreateVREDFilePlugin, self).settings or {}

        # settings specific to this class
        plugin_settings = {
            "Work Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published work files. Should"
                "correspond to a template defined in "
                "templates.yml.",
            },
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published work files. Should"
                "correspond to a template defined in "
                "templates.yml.",
            },
            "Task Name": {
                "type": "str",
                "default": "Visualization",
                "description": "Name of the Task the VRED file(s) will be linked to.",
            },
            "Step Name": {
                "type": "str",
                "default": "Visualization",
                "description": "Name of the Step the VRED file(s) will be linked to.",
            },
            "UI Settings": {
                "type": "dict",
                "default": {},
                "description": "Python dictionary to store UI settings in order"
                "to save/restore the UI state.",
            },
        }

        # update the base settings
        base_settings.update(plugin_settings)

        return base_settings

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["alias.session.vred"]

    def create_settings_widget(self, parent, items=None):
        """
        Creates a Qt widget, for the supplied parent widget (a container widget
        on the right side of the publish UI)

        :param parent:  The parent to use for the widget being created
        :param items:   A list of PublishItems the selected publish tasks are parented to
        :returns:       A QtGui.QWidget
        """

        def __publish_app_task_manager(widget):
            """
            Recursive function to get the BackgroundTaskManager used by the Publisher App
            in order to avoid creating a new one.
            """
            parent_widget = widget.parent()
            if not parent_widget:
                return
            if hasattr(parent_widget, "_task_manager"):
                return parent_widget._task_manager
            return __publish_app_task_manager(parent_widget)

        # we need to get the BackgroundTaskManager used by the publisher app itself
        # if we create a new one, there will be conflicts between them and Alias will crash a lot
        task_manager = __publish_app_task_manager(parent)

        return CustomWidget(parent, bundle=self.parent, task_manager=task_manager)

    def get_ui_settings(self, widget, items=None):
        """
        Invoked by the publisher when the selection changes so the new settings
        can be applied on the previously selected tasks.

        The widget argument is the widget that was previously created by
        `create_settings_widget`.

        The method returns an dictionary, where the key is the name of a
        setting that should be updated and the value is the new value of that
        setting. Note that it is not necessary to return all the values from
        the UI. This is to allow the publisher to update a subset of settings
        when multiple tasks have been selected.

        Example::

            {
                 "setting_a": "/path/to/a/file"
            }

        :param widget: The widget that was created by `create_settings_widget`
        :param items:  A list of PublishItems the selected publish tasks are parented to
        """

        ui_settings = {
            "context": widget.context,
            "filename": widget.filename.text(),
            "publish_to_sg": widget.publish_to_shotgrid.isChecked(),
        }

        return {"UI Settings": ui_settings}

    def set_ui_settings(self, widget, settings, items=None):
        """
        Allows the custom UI to populate its fields with the settings from the
        currently selected tasks.

        The widget is the widget created and returned by
        `create_settings_widget`.

        A list of settings dictionaries are supplied representing the current
        values of the settings for selected tasks. The settings dictionaries
        correspond to the dictionaries returned by the settings property of the
        hook.

        Example::

            settings = [
            {
                 "setting_a": "/path/to/a/file"
                 "setting_b": False
            },
            {
                 "setting_a": "/path/to/a/file"
                 "setting_b": False
            }]

        The default values for the settings will be the ones specified in the
        environment file. Each task has its own copy of the settings.

        When invoked with multiple settings dictionaries, it is the
        responsibility of the custom UI to decide how to display the
        information. If you do not wish to implement the editing of multiple
        tasks at the same time, you can raise a ``NotImplementedError`` when
        there is more than one item in the list and the publisher will inform
        the user than only one task of that type can be edited at a time.

        :param widget: The widget that was created by `create_settings_widget`
        :param settings: a list of dictionaries of settings for each selected
            task.
        :param items:  A list of PublishItems the selected publish tasks are parented to
        """

        if len(settings) > 1:
            raise NotImplementedError()

        # initialize description widget
        widget.description_label.setText(self.description)

        # restore previous saved UI settings
        ui_settings = settings[0]["UI Settings"]

        # if no Publish template has been defined in the plugin setting, hide the publish option from the UI
        publish_template = self.get_publish_template(settings[0], items[0])
        if not publish_template:
            widget.publish_to_shotgrid.hide()
            widget.publish_to_shotgrid.setChecked(False)
        else:
            if "publish_to_sg" in ui_settings:
                widget.publish_to_shotgrid.setChecked(ui_settings["publish_to_sg"])

        # initialize context selection widget
        ctx = self.get_context(settings[0], items[0])
        widget.context_widget.set_context(ctx)

        # if the VRED template doesn't contain a "name" key, we don't want to display the filename widget
        work_template = self.get_work_template(settings[0], items[0])
        if "name" not in work_template.keys:
            widget.filename.hide()
        else:
            filename = self.get_filename(settings[0])
            if filename:
                widget.filename.setText(filename)

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

        # check for VRED PRO installation
        vred_path = self.get_vred_bin_path(item)
        if not vred_path or not os.path.exists(vred_path):
            self.logger.error(
                "Couldn't find a valid path to VRED executable. Please contact your System Administrator to "
                "install VRED on your workstation."
            )
            return {"accepted": False}
        item.properties.vred_bin_path = vred_path

        # make sure a valid work template has been defined for the VRED scene
        work_template = self.get_work_template(settings, item)
        if not work_template:
            self.logger.error("Couldn't find a valid template for VRED work file.")
            return {"accepted": False}
        item.properties.work_template = work_template

        # get the publish template for the VRED file
        publish_template_setting = settings.get("Publish Template")
        publish_template = self.parent.engine.get_template_by_name(
            publish_template_setting.value
        )
        if publish_template:
            item.local_properties["publish_template"] = publish_template

        return {"accepted": True, "checked": False}

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

        # be sure the "Publish to ShotGrid" publish plugin is also selected
        root_item = self.__get_root_item(item)
        is_plugin_checked = False
        for d in root_item.descendants:
            for t in d.tasks:
                if t.name == "Publish to ShotGrid" and t.checked:
                    is_plugin_checked = True
        if not is_plugin_checked:
            self.logger.error(
                'Please, check the "Publish to ShotGrid" publish plugin to be able to create the VRED scene'
            )
            return False

        # make sure we can build a valid work path
        work_path = self.get_work_path(settings, item)
        if not work_path:
            self.logger.error("Couldn't get a valid path for the VRED work file.")
            return False

        # if the "Publish to Shotgrid" option is selected, ensure we can build the publish path
        ui_settings = settings["UI Settings"].value
        if ui_settings.get("publish_to_sg", True):
            return super(AliasCreateVREDFilePlugin, self).validate(settings, item)

        return True

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # get the publish "mode" stored inside of the root item properties
        root_item = self.__get_root_item(item)
        bg_processing = root_item.properties.get("bg_processing", False)
        in_bg_process = root_item.properties.get("in_bg_process", False)

        if not bg_processing or (bg_processing and in_bg_process):

            # get the path to the Alias file to load in the VRED scene
            sg_publish_data = self.__get_alias_publish_data(item)
            if not sg_publish_data:
                self.logger.error("Couldn't get Alias publish data")
                return

            alias_publish_path = sg_publish_data.get("path", {}).get("local_path")
            if not alias_publish_path:
                self.logger.error("Couldn't get the path to the Alias published file")
                return

            if not os.path.exists(alias_publish_path):
                self.logger.error(
                    "The Alias file {} doesn't exist on disk".format(alias_publish_path)
                )
                return

            # build the path to the VRED file and make sure the output directory exist
            vred_work_path = self.get_work_path(settings, item)
            work_folder = os.path.dirname(vred_work_path)
            self.parent.ensure_folder_exists(work_folder)

            # build the command line to create the vred scene
            post_python_cmd = self.get_vred_python_script(
                alias_publish_path, vred_work_path
            )

            cmd = [
                self.get_vred_bin_path(item),
                "-console",
                "-hide_gui",
                "-postpython",
                post_python_cmd,
            ]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_output, _ = p.communicate()

            if p.returncode != 0:
                self.logger.error(p_output)
                return

            # now, we can publish the file is the option has been selected
            ui_settings = settings["UI Settings"].value
            if ui_settings.get("publish_to_sg", True):
                super(AliasCreateVREDFilePlugin, self).publish(settings, item)

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # get the publish "mode" stored inside of the root item properties
        root_item = self.__get_root_item(item)
        bg_processing = root_item.properties.get("bg_processing", False)
        in_bg_process = root_item.properties.get("in_bg_process", False)

        if not bg_processing or (bg_processing and in_bg_process):

            ui_settings = settings["UI Settings"].value
            if ui_settings.get("publish_to_sg", True):

                # increment the VRED work path
                self._save_to_next_version(
                    item.properties["path"],
                    item,
                    lambda p: shutil.copyfile(item.properties["path"], p),
                )

    def get_vred_bin_path(self, item):
        """
        Get the path to the VRED executable to use when creating the new scene

        :param item: Item to process
        :return: The path to the VRED executable
        """

        vred_bin_path = item.get_property("vred_bin_path")
        if vred_bin_path:
            return vred_bin_path

        launcher = sgtk.platform.create_engine_launcher(
            self.parent.sgtk, item.context, "tk-vred"
        )
        software_versions = launcher.scan_software()

        return software_versions[-1].path if software_versions else None

    def get_work_template(self, settings, item):
        """
        Get the template that will be used to build the VRED work path

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :return: VRED work template
        """

        work_template = item.get_property("work_template")
        if work_template:
            return work_template

        if settings["Work Template"] is None or settings["Work Template"].value is None:
            return None

        work_template = self.parent.engine.get_template_by_name(
            settings["Work Template"].value
        )
        if not work_template:
            return None

        return work_template

    def get_work_path(self, settings, item):
        """
        Get the path to the VRED work file.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :return: Path to the VRED work file
        """

        work_path = item.get_property("path")
        if work_path:
            return work_path

        work_template = self.get_work_template(settings, item)
        item.context = self.get_context(settings, item)
        filename = self.get_filename(settings)

        # make sure the folders are created for the selected task
        self.parent.sgtk.create_filesystem_structure(
            item.context.task["type"], item.context.task["id"], "tk-vred"
        )

        template_fields = item.context.as_template_fields(work_template)
        template_fields["name"] = filename
        # here, we initialize the version with a dummy number in order to check for missing fields
        template_fields["version"] = 0

        missing_keys = work_template.missing_keys(template_fields)
        if missing_keys:
            self.logger.error(
                "Work file '%s' missing keys required by the template: {}".format(
                    missing_keys
                )
            )
            return

        # now, we can look for the right version number
        existing_work_files = self.sgtk.paths_from_template(
            work_template, skip_keys=["version"], fields=template_fields
        )
        max_existing_version = max(
            [work_template.get_fields(p).get("version") for p in existing_work_files],
            default=0,
        )
        template_fields["version"] = max_existing_version + 1

        item.properties.path = work_template.apply_fields(template_fields)

        return item.properties.path

    def get_context(self, settings, item):
        """
        Get the context that will be used for the VRED scenes

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :return: VRED scene context
        """

        # if the user already chose a context in the UI, use it
        ui_settings = settings["UI Settings"]
        if not isinstance(ui_settings, dict):
            ui_settings = ui_settings.value

        if "context" in ui_settings and ui_settings["context"]:
            return sgtk.Context.from_dict(self.sgtk, ui_settings["context"])

        else:

            # otherwise, try to build the context from the plugin settings
            task_name = (
                settings["Task Name"].value
                if not isinstance(settings["Task Name"], str)
                else settings["Task Name"]
            )
            step_name = (
                settings["Step Name"].value
                if not isinstance(settings["Step Name"], str)
                else settings["Step Name"]
            )
            sg_task = self.parent.shotgun.find_one(
                "Task",
                [
                    ["content", "is", task_name],
                    ["step.Step.code", "is", step_name],
                    ["entity", "is", item.context.entity],
                ],
            )

            if sg_task:
                return self.parent.sgtk.context_from_entity_dictionary(sg_task)

            # finally, if the task defined in the plugin settings doesn't exist, use the current session context
            else:
                return item.context

    def get_filename(self, settings):
        """
        Get the file name that will be used for the VRED scene.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :return: The VRED file name
        """

        # if the user already defined a name in the UI, use it
        ui_settings = settings["UI Settings"]
        if not isinstance(ui_settings, dict):
            ui_settings = ui_settings.value

        if "filename" in ui_settings and ui_settings["filename"]:
            return ui_settings["filename"]

        # otherwise, try to get the file name of the current session using the template and its fields
        path = alias_api.get_current_path()
        if not path:
            return None

        work_template = self.sgtk.template_from_path(path)
        if not work_template:
            return None

        template_fields = work_template.get_fields(path)
        return template_fields.get("name")

    def get_vred_python_script(self, alias_file_path, vred_file_path):
        """
        Build the Python commands that will be used to build the VRED scene from the Alias published file.

        :param alias_file_path: Path to the Alias published file that we want to import in the scene
        :param vred_file_path: Path to the VRED file path we want to save to
        :return: The python commands used to build the VRED scene
        """

        post_python_cmd = ""
        post_python_cmd += "import vrFileIO;"
        post_python_cmd += "import vrController;"
        post_python_cmd += "vrFileIO.load(r'{}');".format(alias_file_path)
        post_python_cmd += "vrFileIO.save(r'{}');".format(vred_file_path)
        post_python_cmd += "vrController.terminateVred();"

        return post_python_cmd

    def __get_root_item(self, item):
        """
        Recursively get the publish root item

        :param item: Item to process
        : return: The publish root item
        """
        if item.is_root:
            return item
        else:
            return self.__get_root_item(item.parent)

    def __get_alias_publish_data(self, item):
        """
        Go through the publish tree to find the Alias session publish data.

        :param item: Item to process
        :return: The publish data as ShotGrid dictionary
        """

        root_item = self.__get_root_item(item)
        for i in root_item.descendants:
            if i.type_spec == "alias.session":
                return i.get_property("sg_publish_data")
        return None


class CustomWidget(QtGui.QWidget):
    """Settings widget that will be used by the Publish plugin"""

    def __init__(self, parent, bundle, task_manager):
        """
        Class constructor.

        :param parent: Parent widget
        :param bundle: The bundle (app, engine or framework) instance for the app that the calling code is associated
            with
        :param task_manager: Background Task Manager used to perform tasks without blocking the main thread
        """

        QtGui.QWidget.__init__(self, parent)

        self._bundle = bundle
        self._task_manager = task_manager

        self.context = None

        # store Toolkit framework modules in order to avoid importing them many times
        self.__modules = {
            "context_selector": self._bundle.frameworks[
                "tk-framework-qtwidgets"
            ].import_module("context_selector"),
        }

        # initialize the UI
        self.setup_ui()

    def setup_ui(self):
        """Configure the UI."""

        # description widget
        self.description_group_box = QtGui.QGroupBox(self)
        self.description_group_box.setTitle("Description:")

        self.description_label = QtGui.QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setOpenExternalLinks(True)
        self.description_label.setTextFormat(QtCore.Qt.RichText)

        self.description_layout = QtGui.QVBoxLayout()
        self.description_layout.addWidget(self.description_label)
        self.description_layout.addStretch()
        self.description_group_box.setLayout(self.description_layout)

        # context selection widget
        self.context_widget = self.__modules["context_selector"].ContextWidget(self)
        self.context_widget.set_up(self._task_manager)
        self.context_widget.restrict_entity_types_by_link("PublishedFile", "entity")
        self.context_widget.set_task_tooltip(
            "<p>The task that the selected item will be associated with "
            "the SG entity being acted upon.</p>"
        )
        self.context_widget.set_link_tooltip(
            "<p>The link that the selected item will be associated with "
            "the SG entity being acted upon.</p>"
        )
        self.context_widget.context_changed.connect(self._on_context_changed)

        # filename widget
        self.filename_label = QtGui.QLabel("File Name:")
        self.filename = QtGui.QLineEdit()
        self.filename_layout = QtGui.QHBoxLayout()
        self.filename_layout.addWidget(self.filename_label)
        self.filename_layout.addWidget(self.filename)

        # publish option
        self.publish_to_shotgrid = QtGui.QCheckBox("Publish the VRED Scene to ShotGrid")
        self.publish_to_shotgrid.setChecked(True)

        # layout the widgets
        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.description_group_box)
        self.main_layout.addItem(
            QtGui.QSpacerItem(
                20, 30, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed
            )
        )
        self.main_layout.addWidget(self.context_widget)
        self.main_layout.addItem(
            QtGui.QSpacerItem(
                20, 20, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed
            )
        )
        self.main_layout.addLayout(self.filename_layout)
        self.main_layout.addItem(
            QtGui.QSpacerItem(
                20, 30, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed
            )
        )
        self.main_layout.addWidget(self.publish_to_shotgrid)

    def _on_context_changed(self, context):
        """
        Slot called when the context is picked by the user in the UI.

        :param context: The selected context
        """
        self.context = context.to_dict()
