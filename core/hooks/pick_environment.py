# Copyright (c) 2018 Shotgun Software Inc.
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

from tank import Hook, TankError


class PickEnvironment(Hook):
    def execute(self, context, **kwargs):
        """
        The default implementation assumes there are three environments, called shot, asset
        and project, and switches to these based on entity type.
        """
        if getattr(context, "flow_project_id", None):
            return self._pick_flowam_environment(context)

        if context.source_entity:
            if context.source_entity["type"] == "Version":
                return "version"
            elif context.source_entity["type"] == "PublishedFile":
                return "publishedfile"
            elif context.source_entity["type"] == "Playlist":
                return "playlist"

        if context.project is None:
            # Our context is completely empty. We're going into the site context.
            return "site"

        if context.entity is None:
            # We have a project but not an entity.
            return "project"

        if context.entity and context.step is None:
            # We have an entity but no step.
            if context.entity["type"] == "Shot":
                return "shot"
            if context.entity["type"] == "Asset":
                return "asset"
            if context.entity["type"] == "Sequence":
                return "sequence"

        if context.entity and context.step:
            if context.entity["type"] == "Shot":
                return "shot_step"
            if context.entity["type"] == "Asset":
                return "asset_step"

        return None

    def _pick_flowam_environment(self, context):
        """
        Picks the environment of a FlowAM project.

        :returns: The FlowAM environment name.
        :raises TankError: If the context has no supported FlowAM environment.
        """
        if context.entity is None:
            return "flowam/project"

        if context.entity["type"] == "Asset" and context.step:
            return "flowam/asset_step"

        raise TankError(
            "You are in a Flow Asset Management project, and the environment for "
            "your current context (%s) is not supported at this moment." % context
        )
