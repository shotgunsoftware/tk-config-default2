# Copyright (c) 2021 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
import alias_api


HookBaseClass = sgtk.get_hook_baseclass()


class PublishAnnotationsPlugin(HookBaseClass):
    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        self.logger.info("Publishing annotations")

        if not self._is_batch_publish():
            item.properties["alias_annotations"] = alias_api.get_annotation_locators()

        else:

            # Links, the note will be attached to published file by default
            # if a version is created the note will be attached to this too
            publish_data = item.properties["sg_publish_data"]
            version_data = item.properties.get("sg_version_data")

            note_links = [publish_data]
            if version_data is not None:
                note_links.append(version_data)

            batch_data = []
            for annotation in item.properties["alias_annotations"]:
                note_data = {
                    "project": item.context.project,
                    "user": item.context.user,
                    "subject": "Alias Annotation",
                    "content": annotation,
                    "note_links": note_links,
                }
                if item.context.task:
                    note_data["tasks"] = [item.context.task]
                batch_data.append(
                    {"request_type": "create", "entity_type": "Note", "data": note_data}
                )

            if batch_data:
                self.parent.shotgun.batch(batch_data)
