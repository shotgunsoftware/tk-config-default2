# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import tempfile
import uuid

import sgtk
from sgtk.platform.qt import QtCore, QtGui
from sgtk.util import LocalFileStorageManager
from sgtk.util.process import subprocess_check_output, SubprocessCalledProcessError


HookBaseClass = sgtk.get_hook_baseclass()


class PublishToLibraryPlugin(HookBaseClass):

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Publish to Library"

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
        # inherit the settings from the base publish plugin
        base_settings = super(PublishToLibraryPlugin, self).settings or {}

        library_publish_settings = {
            "Project ID": {
                "type": int,
                "default": None,
                "description": "ID of the Project we want to publish to"
            },
            "Pipeline Configuration ID": {
                "type": int,
                "default": None,
                "description": "ID of the Pipeline Configuration we want to use to get templates from"
            },
            "Plugin ID": {
                "type": str,
                "default": "basic.desktop",
                "description": "ID of the plugin we want to use"
            },
            "Library Context": {
                "type": str,
                "default": None,
                "description": "Context we want to use to publish the file to the library"
            },
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published work files. Should correspond to a template defined in "
                               "templates.yml.",
            }
        }

        base_settings.update(library_publish_settings)

        return base_settings

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["maya.session"]

    def create_settings_widget(self, parent):
        """
        Creates a Qt widget, for the supplied parent widget (a container widget
        on the right side of the publish UI)

        :param parent:  The parent to use for the widget being created
        :returns:       A QtGui.QWidget
        """

        return PublishPluginUi(self, parent)

    def get_ui_settings(self, widget):
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
        """
        return {
            "Library Context": widget.current_context
        }

    def set_ui_settings(self, widget, settings):
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
                 "seeting_a": "/path/to/a/file"
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
        """
        if len(settings) > 1:
            raise NotImplementedError()

        widget.current_context = settings[0]["Library Context"]

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

        library_project_id = settings["Project ID"].value
        if not library_project_id:
            return {"accepted": False}

        self._library_project = self.parent.shotgun.find_one("Project", [["id", "is", library_project_id]], ["name"])
        if not self._library_project:
            return {"accepted": False}

        core_root_path = self.__get_library_core_path(settings)
        if not core_root_path:
            return {"accepted": False}

        item.properties["core_root_path"] = core_root_path

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
        # first check that a context has been selected
        if not settings["Library Context"].value:
            self.logger.error("Please, select a library context to publish the file to.")
            return False

        library_ctx = sgtk.Context.deserialize(settings["Library Context"].value)
        if not library_ctx.task:
            self.logger.error("Please, select a Task in the Publish to Library widget.")
            return False
        item.properties["library_ctx"] = library_ctx

        work_template = self.parent.sgtk.template_from_path(item.properties.path)
        template_fields = work_template.get_fields(item.properties.path)

        args_file = create_parameter_file(
            dict(
                action="validate",
                entity_type=library_ctx.task["type"],
                entity_id=library_ctx.task["id"],
                publish_template=settings["Publish Template"].value,
                template_fields=template_fields
            )
        )

        try:
            self.__run_external_script(item, args_file)
        except SubprocessCalledProcessError as e:
            return False

        sgtk.util.filesystem.safe_delete_file(args_file)

        return True

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        work_template = self.parent.sgtk.template_from_path(item.properties.path)
        template_fields = work_template.get_fields(item.properties.path)

        # TODO: manage dependencies

        args_file = create_parameter_file(
            dict(
                action="publish",
                entity_type=item.properties["library_ctx"].task["type"],
                entity_id=item.properties["library_ctx"].task["id"],
                publish_template=settings["Publish Template"].value,
                work_path=item.properties.path,
                template_fields=template_fields,
                description=item.description,
                publish_name=self.get_publish_name(settings, item),
                publish_user=self.get_publish_user(settings, item),
                thumbnail_path=item.get_thumbnail_as_path(),
                publish_type=self.get_publish_type(settings, item),
            )
        )

        try:
            self.__run_external_script(item, args_file)
        except SubprocessCalledProcessError as e:
            return False

        sgtk.util.filesystem.safe_delete_file(args_file)

    def finalize(self, settings, item):
        """
        Execute the finalize logic for the given item and settings.

        This method can be used to do any type of cleanup or reporting after
        publishing is complete.

        Any raised exceptions will indicate that the finalize pass has failed
        and the publisher will stop execution.

        Simple implementation example for a Maya session item finalization:

        .. code-block:: python

            def finalize(self, settings, item):

                path = item.properties["path"]

                # get the next version of the path
                next_version_path = publisher.util.get_next_version_path(path)

                # save to the next version path
                cmds.file(rename=next_version_path)
                cmds.file(save=True, force=True)

        :param dict settings: The keys are strings, matching the keys returned
            in the :data:`settings` property. The values are
            :ref:`publish-api-setting` instances.
        :param item: The :ref:`publish-api-item` instance to finalize.
        """
        pass

    def __get_library_core_path(self, settings):
        """
        """
        # for now, make sure the Pipeline Configuration ID is mandatory
        # TODO: improve the logic to get the configuration to use if the Pipeline Configuration ID is None
        if not settings["Pipeline Configuration ID"].value:
            self.logger.error("Missing Pipeline Configuration ID value.")
            return None
        sg_pc = self.parent.shotgun.find_one(
            "PipelineConfiguration",
            [["id", "is", settings["Pipeline Configuration ID"].value]],
            ["code"]
        )
        if not sg_pc:
            self.logger.error("Couldn't find a pipeline configuration in Shotgun.")
            return None

        # create a ToolkitManager instance to retrieve the pipeline configurations associated to the library project and
        # deduce the core path
        mgr = sgtk.bootstrap.ToolkitManager()
        mgr.plugin_id = settings["Plugin ID"].value
        pipeline_configurations = mgr.get_pipeline_configurations(self._library_project)

        pipeline_configuration = None
        for pc in pipeline_configurations:
            if pc["name"] == sg_pc["code"]:
                pipeline_configuration = pc
                break

        if not pipeline_configuration:
            self.logger.error("Couldn't find a matching pipeline configuration.")
            return None

        root_path = LocalFileStorageManager.get_configuration_root(
            self.parent.shotgun.base_url,
            self._library_project["id"],
            settings["Plugin ID"].value,
            pipeline_configuration["id"],
            LocalFileStorageManager.CACHE
        )
        core_root_path = os.path.join(root_path, "cfg", "install", "core", "python")
        if not os.path.exists(core_root_path):
            self.logger.error("Couldn't find core folder on disk.")
            return None

        return core_root_path

    def __run_external_script(self, item, args_file):
        """
        """

        # find the path to the script to execute
        script = os.path.join(os.path.dirname(__file__), "external_publish_to_library_script.py")

        # get the path to the executable to use. For now, we're going to use the one defined in the configuration
        config_root_path = os.path.normpath(os.path.join(item.properties["core_root_path"], "..", "..", ".."))
        python_interpreter = sgtk.get_python_interpreter_for_config(config_root_path)

        args = [
            python_interpreter,
            script,
            item.properties["core_root_path"],
            args_file
        ]

        output = subprocess_check_output(args)


class PublishPluginUi(QtGui.QWidget):

    def __init__(self, hook_instance, parent):
        """
        """
        QtGui.QWidget.__init__(self, parent=parent)

        self.__hook_instance = hook_instance
        engine_context = sgtk.platform.current_engine().context
        self._current_context = None

        context_selector = self.__hook_instance.parent.frameworks["tk-framework-qtwidgets"].import_module(
            "context_selector")
        task_manager = self.__hook_instance.parent.frameworks["tk-framework-shotgunutils"].import_module("task_manager")
        self._shotgun_globals = self.__hook_instance.parent.frameworks["tk-framework-shotgunutils"].import_module(
            "shotgun_globals")

        self._bg_task_manager = task_manager.BackgroundTaskManager(self)
        self._shotgun_globals.register_bg_task_manager(self._bg_task_manager)

        self._project_library_widget = QtGui.QLabel(
            "Publishing to project: {}".format(self.__hook_instance._library_project["name"])
        )

        self._context_widget = context_selector.ContextWidget(self, project=self.__hook_instance._library_project)
        self._context_widget.set_up(self._bg_task_manager)
        self._context_widget.setFixedWidth(280)

        # self._context_widget.restrict_entity_types_by_link("PublishedFile", "entity")
        self._context_widget.restrict_entity_types([engine_context.entity["type"]])
        self._context_widget.context_changed.connect(self._on_item_context_change)

        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self._project_library_widget)
        self.main_layout.addWidget(self._context_widget)
        self.main_layout.addStretch()

    @property
    def current_context(self):
        return self._current_context.serialize() if self._current_context else None

    @current_context.setter
    def current_context(self, ctx):
        self._current_context = sgtk.Context.deserialize(ctx) if ctx else None
        if self._current_context:
            self._context_widget.set_context(self._current_context)

    def __del__(self):
        """
        Executed when the main dialog is closed.
        All worker threads and other things which need a proper shutdown
        need to be called here.
        """
        try:
            self._bg_task_manager.shut_down()
        except Exception:
            pass
        finally:
            self._shotgun_globals.unregister_bg_task_manager(self._bg_task_manager)

    def _on_item_context_change(self, context):
        """
        """
        self._current_context = context


def create_parameter_file(data):
    """
    Pickles and dumps out a temporary file containing the provided data structure.

    :param data: The data to serialize to disk.
    :returns: File path to a temporary file
    :rtype: str
    """
    param_file = os.path.join(tempfile.gettempdir(), "sgtk_%s.cmd" % uuid.uuid4().hex)

    with open(param_file, "wb") as fh:
        sgtk.util.pickle.dump(data, fh)

    return param_file
