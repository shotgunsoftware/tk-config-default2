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
import sgtk
import alias_api


HookBaseClass = sgtk.get_hook_baseclass()


class AliasPublishVariantsPlugin(HookBaseClass):
    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        self.logger.info("Publishing variants")

        if not self._is_batch_publish():
            variant_list = []
            for variant in alias_api.get_variants():
                variant_list.append((variant.name, variant.path))
            item.properties["alias_variants"] = variant_list

        else:

            publisher = self.parent
            version_data = item.properties.get("sg_version_data")
            publish_data = item.properties["sg_publish_data"]

            # Links, the note will be attached to published file by default
            # if a version is created the note will be attached to this too
            note_links = [publish_data]

            if version_data is not None:
                note_links.append(version_data)

            for variant in item.properties["alias_variants"]:
                data = {
                    "project": item.context.project,
                    "user": item.context.user,
                    "subject": "Alias Variant",
                    "content": variant[0],
                    "note_links": note_links,
                }
                if item.context.task:
                    data["tasks"] = [item.context.task]

                note = publisher.shotgun.create("Note", data)
                publisher.shotgun.upload_thumbnail(
                    entity_type="Note", entity_id=note.get("id"), path=variant[1]
                )

                publisher.shotgun.upload(
                    entity_type="Note",
                    entity_id=note.get("id"),
                    path=variant[1],
                    field_name="attachments",
                    display_name="Variant Image",
                )
