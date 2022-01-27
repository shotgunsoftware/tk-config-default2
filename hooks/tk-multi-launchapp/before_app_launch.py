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
import sgtk
logger = sgtk.platform.get_logger(__name__)

NUKE_DEV = "dcc/dev/nuke"
NUKE_PRIMARY = "dcc/primary/nuke"

class BeforeAppLaunch(tank.Hook):
    """
    Hook to set up the system prior to app launch.
    """

    def execute(
        self, app_path, app_args, version, engine_name, software_entity=None, **kwargs
    ):
        """
        The execute function of the hook will be called prior to starting the required application

        :param app_path: (str) The path of the application executable
        :param app_args: (str) Any arguments the application may require
        :param version: (str) version of the application being run if set in the
            "versions" settings of the Launcher instance, otherwise None
        :param engine_name (str) The name of the engine associated with the
            software about to be launched.
        :param software_entity: (dict) If set, this is the Software entity that is
            associated with this launch command.
        """

        # accessing the current context (current shot, etc)
        # can be done via the parent object
        #
        # > multi_launchapp = self.parent
        # > current_entity = multi_launchapp.context.entity

        # you can set environment variables like this:
        # os.environ["MY_SETTING"] = "foo bar"
        engine = sgtk.platform.current_engine()

        if engine_name == "tk-nuke":
            if os.environ.get("NUKE_PATH") and os.environ.get("PIPELINE_ROOT"):
                # set NUKE_PATH here rather than machine level env variables
                # as that will show operators that the are in an off-pipe Nuke, no menus
                nuke_path = os.path.join(os.environ.get("PIPELINE_ROOT"), NUKE_PRIMARY)
                if os.environ.get("PIPELINE_DEV"):
                    nuke_path = os.path.join(os.environ.get("PIPELINE_ROOT"), NUKE_DEV)
                    # Check if there is a true value for this to
                    # determine if user is a developer
                    if os.environ.get("DEV_ROOT") and os.path.exists(os.environ.get("DEV_ROOT")):
                        # DEV_ROOT is the root location of unique development work
                        # This should be set by the developer on a local level
                        nuke_path = os.path.join(os.environ.get("DEV_ROOT"), NUKE_DEV)

                logger.debug("Nuke path set is:{}".format(nuke_path))
                tank.util.append_path_to_env_var("NUKE_PATH", nuke_path)

                # Look for project-specific and relatively stored dcc tools
                for path_ in engine.context.filesystem_locations:
                    try:
                        project_pipeline_root = os.path.join(path_, 'Pipeline')
                        if os.path.exists(project_pipeline_root):
                            project_nuke_tools = os.path.join(project_pipeline_root, 'dcc', 'nuke')
                            logger.debug("Adding to NUKE_PATH:{}".format(project_nuke_tools))
                            tank.util.append_path_to_env_var("NUKE_PATH", project_nuke_tools)

                    except:
                        pass
            else:
                logger.debug("No nuke path set")
