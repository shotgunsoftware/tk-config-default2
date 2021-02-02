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
import sys
import tank


class BeforeAppLaunch(tank.Hook):
    """
    Hook to set up the system prior to app launch.
    """

    def execute(
        self,
        app_path,
        app_args,
        version,
        engine_name,
        software_entity=None,
        **kwargs
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
        # Add this configuration `site-packages` folder to the PYTHONPATH
        # NB: Adding to sys.path (e.g. with `site.addsitepackage`) won't work,
        # this Hook is executed by Shotgun Desktop's Python interpreter, while
        # DCCs have their own Python interpreter.
        config_site_packages = os.path.join(
            self.sgtk.configuration_descriptor.get_config_folder(),
            "site-packages",
        )
        if not config_site_packages in os.environ.get("PYTHONPATH", ""):
            os.environ["PYTHONPATH"] += os.pathsep + config_site_packages

        # Make sure the right Python interpreter is used for Python scripts
        # We use the Shotgun Desktop Python interpreter
        if app_path == "python.exe":
            python_interpreter_dir = os.path.split(sys.executable)[0]
            os.environ["PATH"] = (
                python_interpreter_dir + os.pathsep + os.environ["PATH"]
            )

            # setup_ue_project needs to know where the config is
            os.environ[
                "TK_CONFIG_PATH"
            ] = self.sgtk.configuration_descriptor.get_config_folder()
