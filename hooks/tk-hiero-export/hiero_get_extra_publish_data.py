# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

class HieroGetExtraPublishData(HookBaseClass):
    """
    This class defines a hook that can be used to gather additional data
    and add it to the data dictionary that's used to register any new
    PublishedFile entities in Shotgun during the given Task's execution.
    """
    def execute(self, task, **kwargs):
        """
        Get a data dictionary for a PublishedFile to be updated in Shotgun.

        .. note:: The track item associated with this task can be accessed via
            task._item.

        :param task: The Hiero Task that is currently being processed.

        :returns: A dictionary to update the data for the PublishedFile in
            Shotgun, or None if there is no extra information to publish.
        :rtype: dict
        """
        # No extra data by default

        engine = sgtk.platform.current_engine()
        context = engine.context

        # update task (json) into the Published File entity
        return {
                'task': context.task
        }
