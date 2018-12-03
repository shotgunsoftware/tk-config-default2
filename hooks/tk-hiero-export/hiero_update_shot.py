# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class HieroUpdateShot(HookBaseClass):

    def update_shotgun_shot_entity(self, entity_type, entity_id, entity_data, preset_properties):

        """
        Handles updating the Shot entity in Shotgun with the new data produced
        during the export. The preset properties dictionary is provided to
        allow for the lookup of any custom properties that might have been
        defined in other hooks, like can be achieved when using the
        hiero_customize_export_ui hook.

        :param str entity_type: The entity type to update.
        :param int entity_id: The id of the entity to update.
        :param dict entity_data: The new data to update the entity with.
        :param dict preset_properties: The export preset's properties
            dictionary.
        """

        # apparently shotgun utility 'sync frame range' within Maya uses 'sg_head_in' and 'sg_tail_out'
        start_frame = entity_data['sg_cut_in']

        entity_data['sg_head_in'] = start_frame
        entity_data['sg_tail_out'] = entity_data['sg_head_in'] + entity_data['sg_cut_duration']

        self.parent.logger.debug(
            "Updating info for %s %s: %s" % (entity_type, entity_id, entity_data)
        )
        self.parent.sgtk.shotgun.update(entity_type, entity_id, entity_data)