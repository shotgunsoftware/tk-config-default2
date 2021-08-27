# Copyright 2021 Autodesk, Inc.  All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license agreement
# provided at the time of installation or download, or which otherwise accompanies
# this software in either electronic or hard copy form.

import os

import alias_api
import sgtk
from sgtk.platform.qt import QtGui, QtCore
from sgtk.util.filesystem import ensure_folder_exists

HookClass = sgtk.get_hook_baseclass()


class AliasLayersPublishPlugin(HookClass):
    """
    Plugin for publishing layers to Shotgun
    """

    LAYER_EXCLUDE_LIST = ["DefaultLayer"]
    ASSET_TYPE = {"Exterior": "Zone", "Interior": "Zone", "Zone": "Part"}

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Publish Layers to Shotgun"

    @property
    def description(self):
        return ""

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

        base_settings = super(AliasLayersPublishPlugin, self).settings or {}

        plugin_settings = {
            "Layer List": {
                "type": "dict",
                "default": None,
                "description": "Dictionary to store the layer list where the key is the layer name and the value "
                "is a boolean to indicate is whether or not the layer is already created in SG.",
            },
            "Task Templates": {
                "type": "dict",
                "default": None,
                "description": "Dictionary where the key is the Step Name and the value the associated Task Template"
                "This Task Template will be used when creating a new asset in SG and can be different "
                "depending on the step of the current item context",
            },
        }

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
        return ["alias.session"]

    # -----------------------------------------------------------------------------------
    # Widget management
    # -----------------------------------------------------------------------------------

    def create_settings_widget(self, parent, items=None):
        """
        Creates a Qt widget, for the supplied parent widget (a container widget
        on the right side of the publish UI)

        :param parent:  The parent to use for the widget being created
        :param items:   A list of PublishItems the selected publish tasks are parented to
        :returns:       A QtGui.QWidget
        """
        widget = LayersWidget(parent=parent)

        for layer in alias_api.get_layers():
            if layer.name in self.LAYER_EXCLUDE_LIST:
                continue
            in_sg = True if layer.name in items[0].properties.sub_assets else False
            widget.add_layer(layer.name, in_sg)

        return widget

    def get_ui_settings(self, widget, items=None):
        """
        Invoked by the publisher when the selection changes so the new templates
        can be applied on the previously selected tasks.

        The widget argument is the widget that was previously created by
        `create_settings_widget`.

        The method returns an dictionary, where the key is the name of a
        setting that should be updated and the value is the new value of that
        setting. Note that it is not necessary to return all the values from
        the UI. This is to allow the publisher to update a subset of templates
        when multiple tasks have been selected.

        Example::

            {
                 "setting_a": "/path/to/a/file"
            }

        :param widget: The widget that was created by `create_settings_widget`
        :param items:  A list of PublishItems the selected publish tasks are parented to
        """
        return {"Layer List": widget.get_layers_state()}

    def set_ui_settings(self, widget, settings, items=None):
        """
        Allows the custom UI to populate its fields with the templates from the
        currently selected tasks.

        The widget is the widget created and returned by
        `create_settings_widget`.

        A list of templates dictionaries are supplied representing the current
        values of the templates for selected tasks. The templates dictionaries
        correspond to the dictionaries returned by the templates property of the
        hook.

        Example::

            templates = [
            {
                 "seeting_a": "/path/to/a/file"
                 "setting_b": False
            },
            {
                 "setting_a": "/path/to/a/file"
                 "setting_b": False
            }]

        The default values for the templates will be the ones specified in the
        environment file. Each task has its own copy of the templates.

        When invoked with multiple templates dictionaries, it is the
        responsibility of the custom UI to decide how to display the
        information. If you do not wish to implement the editing of multiple
        tasks at the same time, you can raise a ``NotImplementedError`` when
        there is more than one item in the list and the publisher will inform
        the user than only one task of that type can be edited at a time.

        :param widget: The widget that was created by `create_settings_widget`
        :param settings: a list of dictionaries of templates for each selected
            task.
        :param items:  A list of PublishItems the selected publish tasks are parented to
        """

        if len(settings) > 1:
            raise NotImplementedError()

        widget.set_layers_state(settings[0]["Layer List"])

    # -----------------------------------------------------------------------------------

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

        # do not accept this plugin if the only layer is the Default one
        alias_layers = alias_api.get_layers()
        if len(alias_layers) <= 1:
            self.logger.debug(
                "The scene must contain at least one layer in addition to the default layer."
            )
            return {"accepted": False}

        # reject the plugin if the current asset is a Model
        asset_data = self.get_asset_data(item)
        if asset_data.get("sg_asset_type") == "Model":
            self.logger.debug("Current asset is a model: rejecting this plugin.")
            return {"accepted": False}

        # in order to gain performance, query the sub-assets here to avoid doing it each time we need to build the
        # publish widget
        sg_assets = self.parent.shotgun.find(
            "Asset", [["parents", "is", item.context.entity]], ["code"]
        )
        asset_names = [a["code"] for a in sg_assets]
        item.properties.sub_assets = asset_names

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

        # check that we have a valid publish template
        publish_template = self.get_publish_template(settings, item)
        if not publish_template:
            self.logger.error(
                "Couldn't find a valid template to publish the layers to SG."
            )
            return False

        # get the list of the layers to publish and check is whether or not they're empty as we don't want to publish
        # empty layers
        layer_validation = True
        layers_to_publish = self.get_layers_to_publish(settings, item)

        # we need at least one layer to publish
        if len(layers_to_publish) == 0:
            self.logger.warning(
                "No layer can be published, please ensure to select at least one."
            )
            return False

        layers_to_create = False
        for layer, in_sg in layers_to_publish:
            if layer.is_empty():
                layer_validation = False
                self.logger.warning(
                    "Layer {} is empty, please unselect it in the UI".format(layer.name)
                )
            if not in_sg:
                layers_to_create = True

        # Task Template validation
        task_templates = settings["Task Templates"].value
        if not task_templates:
            self.logger.error(
                "You must define at least ine Task Template in the configuration"
            )
            return False
        task_template_name = task_templates.get(item.context.step["name"])
        if not task_template_name:
            self.logger.error(
                "Couldn't find a Task Template associated to the step {}".format(
                    item.context.step["name"]
                )
            )
            return False

        sg_task_template = self.parent.shotgun.find_one(
            "TaskTemplate", [["code", "is", task_template_name]]
        )
        if not sg_task_template:
            self.logger.error(
                "Couldn't find a Task Template named '{}' in SG".format(
                    task_template_name
                )
            )
            return False
        item.properties.task_template = sg_task_template

        # get the task name to be use when publishing the layers
        sg_task = self.parent.shotgun.find_one(
            "Task",
            [
                ["task_template", "is", sg_task_template],
                [
                    "step.Step.code",
                    "is",
                    "Class-A",
                ],  # For now, we're forcing the publish on the Class-A Step
            ],
            ["content"],
        )
        if not sg_task:
            self.logger.error(
                "Couldn't find the publish task in the {} Task Template".format(
                    task_template_name
                )
            )
            return False
        item.properties.publish_task_name = sg_task["content"]

        # Asset Type validation
        sub_asset_type = self.get_sub_asset_type(item)
        if not sub_asset_type:
            self.logger.error("Couldn't get the asset type for the SG layer creation.")
            return

        return layer_validation

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publish_template = self.get_publish_template(settings, item)

        # get the value of the "name" template field of the current alias session and use it for the layers too
        work_path = alias_api.get_current_path()
        work_template = item.properties.get("work_template")
        template_fields = work_template.get_fields(work_path)
        name_template_fields = template_fields.get("name", "")

        layers_to_publish = self.get_layers_to_publish(settings, item)

        for layer, in_sg in layers_to_publish:

            # if the layer doesn't exist in SG yet, we need to create an asset with the correct Task template
            if not in_sg:

                self.logger.info("Creating Asset {}".format(layer.name))

                asset_data = self.get_asset_data(item)
                sg_asset = self.parent.shotgun.create(
                    "Asset",
                    {
                        "project": item.context.project,
                        "code": layer.name,
                        "sg_asset_type": self.get_sub_asset_type(item),
                        "sg_exterior_interior": asset_data["sg_exterior_interior"],
                        "parents": [item.context.entity],
                        "task_template": item.properties.task_template,
                    },
                )

            # get the task which will be linked to the published file
            sg_task = self.parent.shotgun.find_one(
                "Task",
                [
                    ["content", "is", item.properties.publish_task_name],
                    ["entity.Asset.code", "is", layer.name],
                    ["project", "is", item.context.project],
                ],
            )
            if not sg_task:
                self.logger.error(
                    "Couldn't find the publish task: skip the layer {} publication".format(
                        layer.name
                    )
                )
                continue

            # make sure the Task folder is created on disk and the cache up-to-date to be able to use it as context
            self.sgtk.create_filesystem_structure("Task", sg_task["id"])
            task_ctx = self.sgtk.context_from_entity_dictionary(sg_task)
            if not task_ctx:
                self.logger.error(
                    "Couldn't get context from task: skip the layer {} publication".format(
                        layer.name
                    )
                )
                continue

            # start gathering the template fields in order to build the publish path
            template_fields = task_ctx.as_template_fields(publish_template)
            template_fields["name"] = name_template_fields

            # need to get the version number by querying the files on disk in case the layer has already been
            # published
            layer_publish_paths = self.sgtk.paths_from_template(
                publish_template, template_fields, skip_keys=["version"]
            )
            if not layer_publish_paths:
                version_number = 1
            else:
                version_number = (
                    max(
                        [
                            publish_template.get_fields(p)["version"]
                            for p in layer_publish_paths
                        ]
                    )
                    + 1
                )
            template_fields["version"] = version_number

            # finally, build the publish path now that we have all the template fields
            layer_publish_path = publish_template.apply_fields(template_fields)

            # export the layer content following the publish path
            self.logger.info(
                "Exporting layer {} content to {}".format(
                    layer.name, layer_publish_path
                )
            )
            layer_publish_folder = os.path.dirname(layer_publish_path)
            ensure_folder_exists(layer_publish_folder)
            layer.export_to_file(layer_publish_path)

            # now, we need to publish the file to SG
            self.logger.info("Publishing layer {} to SG".format(layer.name))
            publish_name = self.parent.util.get_publish_name(layer_publish_path)
            publish_data = {
                "tk": self.sgtk,
                "context": task_ctx,
                "comment": item.description,
                "path": layer_publish_path,
                "name": publish_name,
                "created_by": self.get_publish_user(settings, item),
                "version_number": version_number,
                "published_file_type": self.get_publish_type(settings, item),
            }
            if "sg_publish_data" in item.properties:
                publish_data["dependency_ids"] = [item.properties.sg_publish_data["id"]]
            sgtk.util.register_publish(**publish_data)

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        pass

    def get_layers_to_publish(self, settings, item):
        """"""

        layers_to_publish = []
        layer_list = settings["Layer List"].value

        # the widget has not been initialized, publish all the layers already created in sg
        if layer_list is None:
            for layer in alias_api.get_layers():
                if layer.name in self.LAYER_EXCLUDE_LIST:
                    continue
                if layer.name in item.properties.sub_assets:
                    layers_to_publish.append((layer, True))
        else:
            for layer_name, layer_state in layer_list.items():
                if layer_state is True:
                    alias_layer = alias_api.get_layer_by_name(layer_name)
                    in_sg = True if layer_name in item.properties.sub_assets else False
                    layers_to_publish.append((alias_layer, in_sg))

        return layers_to_publish

    def get_asset_data(self, item):
        """"""
        if item.properties.get("asset_data"):
            return item.properties.asset_data

        item.properties.asset_data = self.parent.shotgun.find_one(
            "Asset",
            [["id", "is", item.context.entity["id"]]],
            ["sg_asset_type", "sg_exterior_interior"],
        )

        return item.properties.asset_data

    def get_sub_asset_type(self, item):
        """"""
        asset_data = self.get_asset_data(item)
        return self.ASSET_TYPE.get(asset_data.get("sg_asset_type"))


# -----------------------------------------------------------------------------------
# WIDGETS
# -----------------------------------------------------------------------------------


class LayersWidget(QtGui.QWidget):
    def __init__(self, parent):
        """
        Class constructor.
        """

        QtGui.QWidget.__init__(self, parent=parent)

        self._ui = Ui_Form()
        self._ui.setupUi(self)

        self.__layers = {}

    def add_layer(self, layer_name, in_sg=True):
        """
        Add a new layer to the UI in the right widget depending if the layer already exists in SG or not

        :param layer_name:  Name of the layer to add
        :param in_sg:  True if the layer already exists in SG, False otherwise
        """
        layer_box = QtGui.QCheckBox(layer_name)
        if in_sg:
            self._ui.in_sg_layout.addWidget(layer_box)
            layer_box.setCheckState(QtGui.Qt.Checked)
        else:
            self._ui.not_in_sg_layout.addWidget(layer_box)
        self.__layers[layer_name] = layer_box

    def set_layers_state(self, layer_list):
        """"""
        if layer_list is not None:
            for layer_name, layer_box in self.__layers.items():
                if layer_name not in layer_list.keys():
                    continue
                layer_box.setChecked(layer_list[layer_name])

    def get_layers_state(self):
        """"""
        layer_list = {}
        for layer_name, layer_box in self.__layers.items():
            layer_list[layer_name] = layer_box.isChecked()
        return layer_list


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(400, 300)
        self.verticalLayout = QtGui.QVBoxLayout(Form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.in_sg_group = QtGui.QGroupBox(Form)
        self.in_sg_group.setObjectName("in_sg_group")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.in_sg_group)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.scrollArea = QtGui.QScrollArea(self.in_sg_group)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.in_sg_widget = QtGui.QWidget()
        self.in_sg_widget.setGeometry(QtCore.QRect(0, 0, 360, 103))
        self.in_sg_widget.setObjectName("in_sg_widget")
        self.in_sg_layout = QtGui.QVBoxLayout(self.in_sg_widget)
        self.in_sg_layout.setObjectName("in_sg_layout")
        self.scrollArea.setWidget(self.in_sg_widget)
        self.verticalLayout_2.addWidget(self.scrollArea)
        self.verticalLayout.addWidget(self.in_sg_group)
        self.not_in_sg_group = QtGui.QGroupBox(Form)
        self.not_in_sg_group.setObjectName("not_in_sg_group")
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.not_in_sg_group)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.scrollArea_2 = QtGui.QScrollArea(self.not_in_sg_group)
        self.scrollArea_2.setWidgetResizable(True)
        self.scrollArea_2.setObjectName("scrollArea_2")
        self.not_in_sg_widget = QtGui.QWidget()
        self.not_in_sg_widget.setGeometry(QtCore.QRect(0, 0, 360, 103))
        self.not_in_sg_widget.setObjectName("not_in_sg_widget")
        self.not_in_sg_layout = QtGui.QVBoxLayout(self.not_in_sg_widget)
        self.not_in_sg_layout.setObjectName("not_in_sg_layout")
        self.scrollArea_2.setWidget(self.not_in_sg_widget)
        self.verticalLayout_3.addWidget(self.scrollArea_2)
        self.verticalLayout.addWidget(self.not_in_sg_group)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(
            QtGui.QApplication.translate(
                "Form", "Form", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.in_sg_group.setTitle(
            QtGui.QApplication.translate(
                "Form", "Layers already in SG", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.not_in_sg_group.setTitle(
            QtGui.QApplication.translate(
                "Form", "Layers not in SG yet", None, QtGui.QApplication.UnicodeUTF8
            )
        )
