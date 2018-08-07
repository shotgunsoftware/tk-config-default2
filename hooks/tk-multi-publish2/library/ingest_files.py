# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.



import pprint
import sgtk

from sgtk import context


HookBaseClass = sgtk.get_hook_baseclass()


class IngestLibraryFilesPlugin(HookBaseClass):

    @property
    def settings_schema(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default_value": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts
        as part of its environment configuration.
        """
        schema = super(IngestLibraryFilesPlugin, self).settings_schema

        # library ingest produces Element entities by default.
        ingest_schema = {
            "snapshot_type_settings": {
                "default_value": {"*": "Element",
                                  self.parent.settings["default_snapshot_type"]:
                                      self.parent.settings["default_entity_type"]}
            }
        }

        schema["Item Type Settings"]["values"]["items"].update(ingest_schema)

        return schema

    def validate(self, task_settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param task_settings: Dictionary of settings
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        publisher = self.parent

        # this has to run first so that item properties are populated.
        # Properties are used to find a linked entity.
        status = super(IngestLibraryFilesPlugin, self).validate(task_settings, item)

        linked_entity = self._find_linked_entity(item, task_settings)


        if linked_entity:
            publishes = publisher.util.get_conflicting_publishes(
                # look for publish files linked to this entity
                context.from_entity(publisher.sgtk, linked_entity["type"], linked_entity["id"]),
                item.properties["publish_path"],
                item.properties["publish_name"],
            )

            if publishes:
                conflict_info = (
                        "Cannot continue, Since this library element already exists as a publish:<br>"
                        "<pre>%s</pre>" % (pprint.pformat(publishes),)
                )
                self.logger.error(
                    "Found %s conflicting publishes in Shotgun" %
                    (len(publishes),),
                    extra={
                        "action_show_more_info": {
                            "label": "Show Conflicts",
                            "tooltip": "Show the conflicting publishes in Shotgun",
                            "text": conflict_info
                        }
                    }
                )
                return False

        return status

