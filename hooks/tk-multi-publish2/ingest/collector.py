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
import datetime

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class IngestCollectorPlugin(HookBaseClass):
    """
    Collector that operates on the current set of ingestion files. Should
    inherit from the basic collector hook.
    """

    def _resolve_work_path_template(self, properties, path):
        """
        Resolve work_path_template from the properties.
        The signature uses properties, so that it can resolve the template even if the item object hasn't been created.

        :param properties: properties that have/will be used to build item object.
        :param path: path to be used to get the templates, using template_from_path,
         in this class we use os.path.basename of the path.
        :return: Name of the template.
        """

        # using file name for resolving templates
        path = os.path.basename(path)

        work_path_template = super(IngestCollectorPlugin, self)._resolve_work_path_template(properties, path)
        return work_path_template

    def _get_item_context_from_path(self, parent_item, properties, path):
        """Updates the context of the item from the work_path_template/template, if needed.

        :param properties: properties of the item.
        :param path: path to build the context from, in this class we use os.path.basename of the path.
        """

        # using file name for resolving templates and context
        path = os.path.basename(path)

        item_context = super(IngestCollectorPlugin, self)._get_item_context_from_path(parent_item, properties, path)
        return item_context

    def _get_template_fields_from_path(self, item, template_name, path):
        """
        Get the fields by parsing the input path using the template derived from
        the input template name.
        """

        # using file name for resolving templates and context
        path = os.path.basename(path)

        fields = super(IngestCollectorPlugin, self)._get_template_fields_from_path(item, template_name, path)

        # adding a description to item
        item.description = "Created by shotgun_ingest on %s" % str(datetime.date.today())
        return fields
