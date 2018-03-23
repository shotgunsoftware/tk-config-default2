# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.


import traceback
import pprint

import sgtk


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

        return """
        Ingests the file to the location specified by the publish_path_template for this item and
        creates a <b>PublishedFile</b> entity in Shotgun, which will include a
        reference to the file's published path on disk.

        After the <b>PublishedFile</b> is created successfully, a <b>Plate</b> entity is also created.
        The <b>PublishedFile</b> is then linked to it's corresponding <b>Plate</b> entity for other users to use.
        Once the ingestion is complete these files can be accessed using the Loader window within each DCC.
        """

    def validate(self, task_settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param task_settings: Dictionary of settings
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        # this has to run first so that item properties are populated.
        # Properties are used to find a plate entity.
        status = super(IngestFilesPlugin, self).validate(task_settings, item)

        # ---- this check will only run if the status of the published files is true.
        # ---- check for matching plate of this path with a status.

        plate_fields = ["sg_status_list"]
        plate = self._find_plate_entity(item, plate_fields)

        if plate and status and plate["sg_status_list"] is not None:
            conflict_info = (
                "If you continue, this matching plate will be updated to use a new PublishedFile"
                "<pre>%s</pre>" % (pprint.pformat(plate),)
            )
            self.logger.warning(
                "Found a matching plate entity in Shotgun for item %s" % item.name,
                extra={
                    "action_show_more_info": {
                        "label": "Show Plate",
                        "tooltip": "Show the matching plate in Shotgun",
                        "text": conflict_info
                    }
                }
            )

        return status

    def publish(self, task_settings, item):
        """
        Executes the publish logic for the given item and task_settings.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # create a plate entity after the publish has gone through successfully.
        plate_entity = self._create_plate_entity(item)

        # let's create ingest_plate_data within item properties,
        # so that we can link the version created to plate entity as well.
        item.properties["ingest_plate_data"] = plate_entity

        if item.properties.get("ingest_plate_data"):
            # publish the file
            super(IngestFilesPlugin, self).publish(task_settings, item)

            if item.properties.get("sg_publish_data"):
                # link the publish file to our plate entity.
                updated_plate = self._link_published_files_to_plate_entity(item)

                if updated_plate:
                    # clear the status list of the plate
                    self._clear_plate_status_list(item)
                    self.logger.info("Plate entity registered and PublishedFile linked for %s" % item.name)
                else:
                    # undo the plate creation
                    self.undo(task_settings, item)
                    # undo the parent publish
                    super(IngestFilesPlugin, self).undo(task_settings, item)
                    self.logger.error("Failed to link the PublishedFile and the Plate entity for %s!" % item.name)
            else:
                self.logger.error("PublishedFile not created successfully for %s!" % item.name)
        else:
            self.logger.error("Failed to create a Plate entity for %s!" % item.name)

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

        if "ingest_plate_data" in item.properties:
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

    def undo(self, task_settings, item):
        """
        Execute the undo method. This method will
        delete the plate entity that got created due to the publish.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        plate_data = item.properties.get("ingest_plate_data")

        if plate_data:
            try:
                self.sgtk.shotgun.delete(plate_data["type"], plate_data["id"])
            except Exception:
                self.logger.error(
                    "Failed to delete Plate Entity for %s" % item.name,
                    extra={
                        "action_show_more_info": {
                            "label": "Show Error Log",
                            "tooltip": "Show the error log",
                            "text": traceback.format_exc()
                        }
                    }
                )

    def _clear_plate_status_list(self, item):
        """
        Sets the status list on the plate to None.
        Once the plate has been completely linked to it's PublishedFile entity.

        :param item:  item to get the plate entity from
        """
        try:
            self.sgtk.shotgun.update(
                entity_type=item.properties["ingest_plate_data"]["type"],
                entity_id=item.properties["ingest_plate_data"]["id"],
                data={"sg_status_list": None},
            )
        except Exception:
            self.logger.error(
                "clear_plate_status_list failed for item: %s" % item.name,
                extra={
                    "action_show_more_info": {
                        "label": "Show Error Log",
                        "tooltip": "Show the error log",
                        "text": traceback.format_exc()
                    }
                }
            )

    def _find_plate_entity(self, item, fields=list()):
        """
        Finds a plate entity corresponding to the item's context.
        Name of the Element Entity is governed by "publish_name" of the item.
        Further filters it down if the context is from shot/sequence.

        :param item: item to find the plate entity for.
        :return: plate entity or None if not found.
        """
        sg_filters = [
            ['project', 'is', item.context.project],
            ['code', 'is', item.properties["publish_name"]]
        ]
        if item.context.entity:
            if item.context.entity["type"] == "Shot":
                sg_filters.append(['sg_shot', 'is', item.context.entity])
            elif item.context.entity["type"] == "Sequence":
                sg_filters.append(['sg_sequence', 'is', item.context.entity])

        fields.extend(['shots', 'code', 'id'])

        result = self.sgtk.shotgun.find_one(
            entity_type='Element',
            filters=sg_filters,
            fields=fields
        )
        return result

    def _get_frame_range(self, item):
        """
        Frame range for the item.

        :param item: item to get the frame range for.
        :return: A tuple of first_frame, last_frame
        """
        publisher = self.parent

        # Determine if this is a sequence of paths
        if item.properties["is_sequence"]:
            first_frame = publisher.util.get_frame_number(item.properties["sequence_paths"][0])
            last_frame = publisher.util.get_frame_number(item.properties["sequence_paths"][-1])
        else:
            first_frame = last_frame = 0

        return first_frame, last_frame

    def _create_plate_entity(self, item):
        """
        Creates a plate entity if it doesn't exist for a given item, or updates it if it already exists.
        Sets the status of the plate entity to "ip"

        :param item: item to create the plate entity for.
        :return: Plate entity for the given item.
        """
        try:
            plate_entity = self._find_plate_entity(item)
        except Exception:
            self.logger.error(
                "find_plate_entity failed for item: %s" % item.name,
                extra={
                    "action_show_more_info": {
                        "label": "Show Error Log",
                        "tooltip": "Show the error log",
                        "text": traceback.format_exc()
                    }
                }
            )
            return

        frange = self._get_frame_range(item)

        data = dict(
            code=item.properties["publish_name"],
            sg_client_name=item.name,
            sg_status_list="ip"
        )

        data["head_in"] = frange[0]
        data["head_out"] = frange[1]

        if item.context.entity:
            if item.context.entity["type"] == "Shot":
                # data["shots"] = [item.context.entity]
                data["sg_shot"] = item.context.entity
            elif item.context.entity["type"] == "Sequence":
                data["sg_sequence"] = item.context.entity

        try:
            if plate_entity:
                plate_entity = self.sgtk.shotgun.update(
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
                plate_entity = self.sgtk.shotgun.create(entity_type='Element', data=data)
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

            return plate_entity
        except Exception:
            self.logger.error(
                "create_plate_entity failed for item: %s" % item.name,
                extra={
                    "action_show_more_info": {
                        "label": "Show Error Log",
                        "tooltip": "Show the error log",
                        "text": traceback.format_exc()
                    }
                }
            )
            return

    def _link_published_files_to_plate_entity(self, item):
        """
        Link the plate entity to its corresponding publish files.

        :param item: item to get the publish files(sg_publish_data) and plate entity(ingest_plate_data)
        :return: Updated plate entity.
        """

        try:
            result = self.sgtk.shotgun.update(
                entity_type='Element',
                entity_id=item.properties["ingest_plate_data"]["id"],
                data=dict(sg_published_files=[item.properties["sg_publish_data"]]),
            )
            return result
        except Exception:
            self.logger.error(
                "link_published_files_to_plate_entity failed for item: %s" % item.name,
                extra={
                    "action_show_more_info": {
                        "label": "Show Error Log",
                        "tooltip": "Show the error log",
                        "text": traceback.format_exc()
                    }
                }
            )
            return
