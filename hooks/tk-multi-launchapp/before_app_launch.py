# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Before App Launch Hook

This hook is executed prior to application launch and is useful if you need
to set environment variables or run scripts as part of the app initialization.
"""

import os
import tank


class BeforeAppLaunch(tank.Hook):
    """
    Hook to set up the system prior to app launch.
    """

    def execute(self, app_path, app_args, version, engine_name, **kwargs):
        """
        The execute functon of the hook will be called prior to starting the required application

        :param app_path: (str) The path of the application executable
        :param app_args: (str) Any arguments the application may require
        :param version: (str) version of the application being run if set in the
            "versions" settings of the Launcher instance, otherwise None
        :param engine_name (str) The name of the engine associated with the
            software about to be launched.

        """

        # accessing the current context (current shot, etc)
        # can be done via the parent object
        #
        # > multi_launchapp = self.parent
        # > current_entity = multi_launchapp.context.entity

        # you can set environment variables like this:
        # os.environ["MY_SETTING"] = "foo bar"

        self.logger.debug("[CBFX] engine name: %s" % engine_name)

        current_context = self.parent.context
        self.logger.debug("[CBFX] current context: %s" % current_context)


        # if engine_name == "tk-nuke":
        #     os.environ['NUKE_PATH'] = os.environ['NUKE_PATH'].replace('S:\\Tools\\Nuke;', 'P:\\_pipe\\nuke;')
        #
        # if engine_name == "tk-hiero":
        #     env_vars = {
        #         # "HIERO_PLUGIN_PATH": "R:\\code\\work\\anthony.kramer\\hiero\\cbfx-hiero-tools",
        #         "HIERO_PLUGIN_PATH": "S:\\tools\\hiero\\cbfx\\current",
        #     }
        #     for k, v in env_vars.iteritems():
        #         tank.util.append_path_to_env_var(k, v)
        #         self.logger.debug("[CBFX] added environ %s=%s" % (k, v))

        # Sets the current task to in progress
        if self.parent.context.task:
            task_id = self.parent.context.task['id']
            task = self.parent.sgtk.shotgun.find_one("Task", filters=[["id", "is", task_id]], fields=["sg_status_list"])
            self.logger.debug("[CBFX] task %s status is %s" % (task_id, task['sg_status_list']))
            if task['sg_status_list'] == 'rdy':
                data = {
                    'sg_status_list': 'ip'
                }
                self.parent.shotgun.update("Task", task_id, data)
                self.logger.debug("[CBFX] changed task status to 'ip'")
