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
            # return the "site" configuration.
            return "site"

        if context.step is None:
            # we aren't in a Task context so return the base env
            return "base"

        if context.entity is None:
            # we have a project but not an entity
            return "project"
        else:
            # we have an entity
            entity_type = context.entity["type"]
            if entity_type == "Sequence":
                return "sequence"
            elif entity_type == "Shot":
                return "shot"
            else:
                addl_entity_types = [x["type"] for x in context.additional_entities]
                if "Shot" in addl_entity_types:
                    return "shot_%s" % entity_type.lower()
                if "Sequence" in addl_entity_types:
                    return "sequence_%s" % entity_type.lower()
                return "project_%s" % entity_type.lower()

        return None
