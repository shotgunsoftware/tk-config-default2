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

class HieroUpdateVersionData(HookBaseClass):
    """
    This class implements a hook that can be used to customize the data
    dictionary for a Version entity that is going to be created by the
    export process.
    """
    def execute(self, version_data, task, **kwargs):
        """
        Updates the version_data dictionary to change the data for the Version
        that will be created in Shotgun. Updating the given version_data
        dictionary in place will ensure your customizations are used when
        creating the new Version entity.

        :param dict version_data: The data dictionary that will be used by
            the export process to create a new Version entity in Shotgun.
        :param task: The Hiero export task being processed.
        """

        engine = sgtk.platform.current_engine()
        context = engine.context

        # update task into the Version entity
        version_data['sg_task'] = context.task
