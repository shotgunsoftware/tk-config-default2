# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook which chooses an environment file to use based on the current context.

"""
import sgtk
HookBaseClass = sgtk.get_hook_baseclass()

class PickEnvironment(HookBaseClass):

    def execute(self, context, **kwargs):
        """
        The default implementation assumes there are three environments, called shot, asset
        and project, and switches to these based on entity type.
        """
        if context.source_entity:
            if context.source_entity["type"] in ["Version", "PublishedFile"]:
                return "publishedfile_version"

        if context.project is None:
            # our context is completely empty!
            # don't know how to handle this case.
            return None

        if context.entity is None:
            # we have a project but not an entity
            return "project"

        if context.entity and context.step is None:
            # we have an entity but no step!
            return "project"

        if context.entity and context.step:
            # we have a step and an entity
            if context.entity["type"] == "Sequence":
                return "sequence"
            if context.entity["type"] == "Shot":
                return "shot"
            if context.entity["type"] == "Asset":
                entities_by_type = dict([(x["type"], x) for x in context.additional_entities])
                if "Shot" in entities_by_type:
                    return "shot_asset"
                if "Sequence" in entities_by_type:
                    return "sequence_asset"
                return "asset"

        return None
