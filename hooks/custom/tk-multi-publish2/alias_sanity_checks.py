# Copyright 2021 Autodesk, Inc.  All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license agreement
# provided at the time of installation or download, or which otherwise accompanies
# this software in either electronic or hard copy form.

import alias_api
import sgtk
from sgtk.platform.qt import QtGui, QtCore

HookBaseClass = sgtk.get_hook_baseclass()


class AliasCheckPlugin(HookBaseClass):
    """
    Plugin for publishing an open alias session.

    This hook relies on functionality found in the base file publisher hook in
    the publish2 app and should inherit from it in the configuration. The hook
    setting for this plugin should look something like this::

        hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_session.py"

    """

    # NOTE: The plugin icon and name are defined by the base file plugin.

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
        base_settings = super(AliasCheckPlugin, self).settings or {}

        # settings specific to this class
        alias_check_settings = {
            "Check List": {
                "type": "list",
                "default": [],
                "description": "List of dictionaries to describe all the checks we'd like to perform before "
                "publishing the file.",
            }
        }

        # update the base settings
        base_settings.update(alias_check_settings)

        return base_settings

    def create_settings_widget(self, parent, items=None):
        """
        Creates a Qt widget, for the supplied parent widget (a container widget
        on the right side of the publish UI)

        :param parent:  The parent to use for the widget being created
        :param items:   A list of PublishItems the selected publish tasks are parented to
        :returns:       A QtGui.QWidget
        """

        widget = QtGui.QWidget(parent)
        widget.main_layout = QtGui.QVBoxLayout()
        widget.setLayout(widget.main_layout)

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

        check_list = []

        for check in widget.checks:
            check_data = check.data
            check_data["checked"] = check.isChecked()
            check_list.append(check_data)

        return {"Check List": check_list}

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

        check_list = settings[0]["Check List"]
        widget.checks = []

        for check_data in check_list:

            check_box = QtGui.QCheckBox(check_data["name"])
            check_box.data = check_data
            check_box.setToolTip(check_data["description"])

            is_checked = check_data.get("checked", True)
            check_state = QtCore.Qt.Unchecked if not is_checked else QtCore.Qt.Checked
            check_box.setCheckState(check_state)

            if not check_data["function"]:
                check_box.setCheckState(QtCore.Qt.Unchecked)
                check_box.setEnabled(False)

            widget.main_layout.addWidget(check_box)
            widget.checks.append(check_box)

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

        # perform the checks
        for check_data in settings["Check List"].value:

            # if not function is associated to the check, skip it
            if not check_data["function"]:
                continue

            # if the check has not been selected by the user, skip it
            is_checked = check_data.get("checked", True)
            if not is_checked:
                continue

            # check that the Alias api has access to the function
            if not hasattr(alias_api, check_data["function"]):
                self.logger.error(
                    "Couldn't find Alias operation for {} in the API.".format(
                        check_data["function"]
                    )
                )
                continue

            self.logger.info("Executing {}".format(check_data["name"]))
            callback = getattr(alias_api, check_data["function"])
            callback()

        # let the base class handle the other validations
        return super(AliasCheckPlugin, self).validate(settings, item)
