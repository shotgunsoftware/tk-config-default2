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


class IngestFilesPlugin(HookBaseClass):
    """
    Inherits from PublishFilesPlugin
    """

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        desc = super(IngestFilesPlugin, self).description

        return desc + "<br><br>" + """
        After Ingesting the file a publishedFile gets created. The publishedFile will also be linked to a Plate entity.
        """

    def publish(self, task_settings, item):
        """
        Executes the publish logic for the given item and task_settings.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        super(IngestFilesPlugin, self).publish(task_settings, item)

        # create a plate entity after the publish has went through successfully.
        plate_entity = self._create_plate_entity(item)

        # let's create ingest_plate_data within item properties,
        # so that we can link the version created to plate entity as well.
        item.properties["ingest_plate_data"] = plate_entity

        # link the publish file to our plate entity.
        self._link_published_files_to_plate_entity(plate_entity, item)
        self.logger.info("Plate entity registered and Publish file is linked!")

    def finalize(self, task_settings, item):
        """
        Execute the finalization pass. This pass executes once
        all the publish tasks have completed, and can for example
        be used to version up files.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        super(IngestFilesPlugin, self).finalize(task_settings, item)

        # get the data for the plate that was just created in SG
        plate_data = item.properties["ingest_plate_data"]

        path = item.properties["path"]

        self.logger.info(
            "Plate created for file: %s" % (path,),
            extra={
                "action_show_in_shotgun": {
                    "label": "Show Plate",
                    "tooltip": "Open the Publish in Shotgun.",
                    "entity": plate_data
                }
            }
        )

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

    def _get_frame_range(self, item):
        publisher = self.parent

        # Determine if this is a sequence of paths
        if item.properties["is_sequence"]:
            first_frame = publisher.util.get_frame_number(item.properties["sequence_paths"][0])
            last_frame = publisher.util.get_frame_number(item.properties["sequence_paths"][-1])
        else:
            first_frame = last_frame = 0

        return first_frame, last_frame

    def _create_plate_entity(self, item):
        sg = get_sg_connection()
        plate_entity = self._validate_plate_entity(item)
        frange = self._get_frame_range(item)

        data = dict(
            code=item.properties["publish_name"],
            sg_client_name=item.name,
        )

        data["cut_in"] = frange[0]
        data["cut_out"] = frange[1]

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
            self.logger.info("Updated Plate entity...")
            self.logger.debug(
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
            plate_entity = sg.create(entity_type='Element', data=data)
            self.logger.info("Created Plate entity...")
            self.logger.debug(
                "Created Plate entity...",
                extra={
                    "action_show_more_info": {
                        "label": "Plate Data",
                        "tooltip": "Show the complete Plate data dictionary",
                        "text": "<pre>%s</pre>" % (pprint.pformat(data),)
                    }
                }
            )

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
