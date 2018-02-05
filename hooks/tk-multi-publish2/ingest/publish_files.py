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
import copy
import glob
import pprint
import traceback

import sgtk
from sgtk import TankError

from tank.util.shotgun import get_sg_connection

HookBaseClass = sgtk.get_hook_baseclass()


class IngestPublishFilesPlugin(HookBaseClass):
    """
    Inherits from PublishFilesPlugin
    """

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        desc = super(IngestPublishFilesPlugin, self).description

        return desc + "<br><br>" + """
        After publishing, if the file type is render(sequences) or image(sequences).
        Plate entities will also be created for them, and published files will be linked to the plate entities.
        """


    def validate(self, task_settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param task_settings: Dictionary of settings
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        publisher = self.parent

        # ---- ensure that work file(s) exist on disk to be published

        if item.properties["is_sequence"]:
            if not item.properties["sequence_paths"]:
                self.logger.warning("File sequence does not exist: %s" % item.properties["path"])
                return False
        else:
            if not os.path.exists(item.properties["path"]):
                self.logger.warning("File does not exist: %s" % item.properties["path"])
                return False

        # ---- validate the settings required to publish

        attr_list = ("publish_type", "publish_path", "publish_name", "publish_version")
        for attr in attr_list:
            try:
                method = getattr(self, "_get_%s" % attr)
                item.properties[attr] = method(item, task_settings)
            except Exception:
                self.logger.error(
                    "Unable to determine '%s' for item: %s" % (attr, item.name),
                    extra={
                        "action_show_more_info": {
                            "label": "Show Error Log",
                            "tooltip": "Show the error log",
                            "text": traceback.format_exc()
                        }
                    }
                )
                return False

        # ---- check for conflicting publishes of this path with a status

        # Note the name, context, and path *must* match the values supplied to
        # register_publish in the publish phase in order for this to return an
        # accurate list of previous publishes of this file.
        publishes = publisher.util.get_conflicting_publishes(
            item.context,
            item.properties["publish_path"],
            item.properties["publish_name"],
            filters=["sg_status_list", "is_not", None]
        )

        if publishes:
            conflict_info = (
                "If you continue, these conflicting publishes will no longer "
                "be available to other users via the loader:<br>"
                "<pre>%s</pre>" % (pprint.pformat(publishes),)
            )
            self.logger.warning(
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

        # ---- ensure the published file(s) don't already exist on disk

        conflict_info = None
        if item.properties["is_sequence"]:
            seq_pattern = publisher.util.get_path_for_frame(item.properties["publish_path"], "*")
            seq_files = [f for f in glob.iglob(seq_pattern) if os.path.isfile(f)]

            if seq_files:
                conflict_info = (
                    "The following files already exist!<br>"
                    "<pre>%s</pre>" % (pprint.pformat(seq_files),)
                )
        else:
            if os.path.exists(item.properties["publish_path"]):
                conflict_info = (
                    "The following file already exists!<br>"
                    "<pre>%s</pre>" % (item.properties["publish_path"],)
                )

        if conflict_info:
            self.logger.error(
                "Version '%s' of this file already exists on disk." %
                    (item.properties["publish_version"],),
                extra={
                    "action_show_more_info": {
                        "label": "Show Conflicts",
                        "tooltip": "Show the conflicting published files",
                        "text": conflict_info
                    }
                }
            )
            return False

        self.logger.info(
            "A Publish will be created for item '%s'." %
                (item.name,),
            extra={
                "action_show_more_info": {
                    "label": "Show Info",
                    "tooltip": "Show more info",
                    "text": "Publish Name: %s" % (item.properties["publish_name"],) + "\n" +
                            "Publish Path: %s" % (item.properties["publish_path"],)
                }
            }
        )

        return True


    def publish(self, task_settings, item):
        """
        Executes the publish logic for the given item and task_settings.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publisher = self.parent

        # Get item properties populated by validate method
        publish_name     = item.properties["publish_name"]
        publish_path     = item.properties["publish_path"]
        publish_type     = item.properties["publish_type"]
        publish_version  = item.properties["publish_version"]

        # handle copying of work to publish
        self._copy_files(publish_path, item)

        # if the parent item has a publish path, include it in the list of
        # dependencies
        dependency_paths = item.properties.get("publish_dependencies", [])
        if "sg_publish_path" in item.parent.properties:
            dependency_paths.append(item.parent.properties["sg_publish_path"])

        # get any additional_publish_fields that have been defined
        sg_fields = {}
        additional_fields = task_settings.get("additional_publish_fields", {})
        for template_key, sg_field in additional_fields.iteritems():
            if template_key in item.properties["fields"]:
                sg_fields[sg_field] = item.properties["fields"][template_key]

        # arguments for publish registration
        self.logger.info("Registering publish...")
        publish_data= {
            "tk": publisher.sgtk,
            "context": item.context,
            "comment": item.description,
            "path": publish_path,
            "name": publish_name,
            "version_number": publish_version,
            "thumbnail_path": item.get_thumbnail_as_path() or "",
            "published_file_type": publish_type,
            "dependency_paths": dependency_paths,
            "sg_fields": sg_fields
        }

        # log the publish data for debugging
        self.logger.debug(
            "Populated Publish data...",
            extra={
                "action_show_more_info": {
                    "label": "Publish Data",
                    "tooltip": "Show the complete Publish data dictionary",
                    "text": "<pre>%s</pre>" % (pprint.pformat(publish_data),)
                }
            }
        )

        # create the publish and stash it in the item properties for other
        # plugins to use.
        item.properties["sg_publish_data"] = sgtk.util.register_publish(
            **publish_data)

        if item.type.startswith("file.image") or item.type.startswith("file.render"):
            # create a plate entity after the publish has went through successfully.
            plate_entity = self._create_plate_entity(item)
            self._link_published_files_to_plate_entity(plate_entity, item)
            self.logger.info("Plate entity registered and Publish file is linked!")
        else:
            self.logger.info("Publish registered!")


    @staticmethod
    def _validate_plate_entity(item):
        sg = get_sg_connection()
        sg_filters = [
            ['project', 'is', item.context.project],
            ['code', 'is', item.properties["publish_name"]]
        ]
        if item.context.entity:
            if item.context.entity["type"] == "Shot":
                sg_filters.append(['shots', 'is', item.context.entity])
            elif item.context.entity["type"] == "Sequence":
                sg_filters.append(['sg_sequence', 'is', item.context.entity])

        result = sg.find_one(
            entity_type='Element',
            filters=sg_filters,
            fields=['shots', 'code', 'id']
        )
        return result

    def _create_plate_entity(self, item):
        sg = get_sg_connection()
        plate_entity = self._validate_plate_entity(item)
        data = dict(
            code=item.properties["publish_name"],
            sg_client_name=item.name
        )
        if item.context.entity:
            if item.context.entity["type"] == "Shot":
                data["shots"] = [item.context.entity]
                data["sg_shot"] = item.context.entity
            elif item.context.entity["type"] == "Sequence":
                data["sg_sequence"] = item.context.entity

        if plate_entity:
            plate_entity = sg.update(
                entity_type='Element',
                entity_id=plate_entity['id'],
                data=data,
                multi_entity_update_modes=dict(shots='add'),
            )
            self.logger.info(
                "Updated Plate entity...",
                extra={
                    "action_show_more_info": {
                        "label": "Plate Data",
                        "tooltip": "Show the complete Plate data dictionary",
                        "text": "<pre>%s</pre>" % (pprint.pformat(data),)
                    }
                }
            )
        else:
            data["project"] = item.context.project
            self.logger.info(
                "Created Plate entity...",
                extra={
                    "action_show_more_info": {
                        "label": "Plate Data",
                        "tooltip": "Show the complete Plate data dictionary",
                        "text": "<pre>%s</pre>" % (pprint.pformat(data),)
                    }
                }
            )
            plate_entity = sg.create(entity_type='Element', data=data)

        return plate_entity

    @staticmethod
    def _link_published_files_to_plate_entity(plate_entity, item):
        """
        Create a plate entity for the corresponding publish and link the publish files
        :param plate_entity:
        :param item:
        :return:
        """
        sg = get_sg_connection()
        result = sg.update(
            entity_type='Element',
            entity_id=plate_entity['id'],
            data=dict(sg_published_files=[item.properties["sg_publish_data"]]),
        )
        return result
