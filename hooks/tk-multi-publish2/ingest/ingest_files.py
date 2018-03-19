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
        Ingests the file to the location specified by the templates and
        creates a <b>PublishedFile</b> entity in Shotgun, which will include a
        reference to the file's published path on disk.

        After the <b>PublishFile</b> is created successfully, an <b>Element/Plate</b> entity is also created.
        The PublishFile is then linked to it's corresponding Element entity for other users to use.
        Other users will be able to access the published file via the plates.
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

        if "sg_publish_data" in item.properties:

            # create a plate entity after the publish has gone through successfully.
            plate_entity = self._create_plate_entity(item)

            # let's create ingest_plate_data within item properties,
            # so that we can link the version created to plate entity as well.
            item.properties["ingest_plate_data"] = plate_entity

            if item.properties.get("ingest_plate_data"):
                # link the publish file to our plate entity.
                updated_plate = self._link_published_files_to_plate_entity(item)

                if updated_plate:
                    self.logger.info("Plate entity registered and Publish file is linked to it!")
                else:
                    self.logger.error("Failed to link the Publish file and the Plate entity!")
            else:
                self.logger.error("Failed to create a plate entity!")
        else:
            self.logger.error("Publish File not created successfully!")

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

    def _find_plate_entity(self, item):
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

        result = self.sgtk.shotgun.find_one(
            entity_type='Element',
            filters=sg_filters,
            fields=['shots', 'code', 'id']
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

        :param item: item to create the plate entity for.
        :return: Plate entity for the given item.
        """
        plate_entity = self._find_plate_entity(item)
        frange = self._get_frame_range(item)

        data = dict(
            code=item.properties["publish_name"],
            sg_client_name=item.name,
        )

        data["cut_in"] = frange[0]
        data["cut_out"] = frange[1]

        if item.context.entity:
            if item.context.entity["type"] == "Shot":
                # data["shots"] = [item.context.entity]
                data["sg_shot"] = item.context.entity
            elif item.context.entity["type"] == "Sequence":
                data["sg_sequence"] = item.context.entity

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

    def _link_published_files_to_plate_entity(self, item):
        """
        Link the plate entity to its corresponding publish files.

        :param item: item to get the publish files(sg_publish_data) and plate entity(ingest_plate_data)
        :return: Updated plate entity.
        """
        result = self.sgtk.shotgun.update(
            entity_type='Element',
            entity_id=item.properties["ingest_plate_data"]["id"],
            data=dict(sg_published_files=[item.properties["sg_publish_data"]]),
        )
        return result
