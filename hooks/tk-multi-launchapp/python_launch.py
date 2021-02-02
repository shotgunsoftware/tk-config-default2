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
App Launch Hook
This hook is executed to launch the applications.
"""

import os
import tank
import sys


class PythonLaunch(tank.Hook):
    """
    Hook to run an application.
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
        The execute function of the hook will be called to start the required application
        :param app_path: (str) The path of the application executable
        :param app_args: (str) Any arguments the application may require
        :param version: (str) version of the application being run if set in the
            "versions" settings of the Launcher instance, otherwise None
        :param engine_name (str) The name of the engine associated with the
            software about to be launched.
        :param software_entity: (dict) If set, this is the Software entity that is
            associated with this launch command.
        :returns: (dict) The two valid keys are 'command' (str) and 'return_code' (int).
        """

        # Make sure the right Python interpreter is used for Python scripts
        # We use the Shotgun Desktop Python interpreter
        if app_path != "python.exe":
            raise KeyError(
                "The PythonLaunch hook can only be used when executing a Python script"
            )
        python_interpreter_dir = os.path.split(sys.executable)[0]
        os.environ["PATH"] = (
            python_interpreter_dir + os.pathsep + os.environ["PATH"]
        )

        # setup_ue_project needs to know where the config is
        os.environ[
            "TK_CONFIG_PATH"
        ] = self.sgtk.configuration_descriptor.get_config_folder()

        # Expand the app_args in case {config_path} is present
        app_args = app_args.format(
            config_path=self.sgtk.configuration_descriptor.get_config_folder()
        )

        # Uploaded pipeline configs (zipped) get copied to the %APPDATA% area,
        # where spaces can get in the full path name. Surround the argument with
        # quotes
        app_args = '"{}"'.format(app_args)

        if tank.util.is_linux():
            # on linux, we just run the executable directly
            cmd = "%s %s &" % (app_path, app_args)

        elif tank.util.is_macos():
            # If we're on OS X, then we have two possibilities: we can be asked
            # to launch an application bundle using the "open" command, or we
            # might have been given an executable that we need to treat like
            # any other Unix-style command. The best way we have to know whether
            # we're in one situation or the other is to check the app path we're
            # being asked to launch; if it's a .app, we use the "open" command,
            # and if it's not then we treat it like a typical, Unix executable.
            if app_path.endswith(".app"):
                # The -n flag tells the OS to launch a new instance even if one is
                # already running. The -a flag specifies that the path is an
                # application and supports both the app bundle form or the full
                # executable form.
                cmd = 'open -n -a "%s"' % (app_path)
                if app_args:
                    cmd += " --args %s" % app_args
            else:
                cmd = "%s %s &" % (app_path, app_args)

        else:
            # on windows, we run the start command in order to avoid
            # any command shells popping up as part of the application launch.
            cmd = 'start /B "App" "%s" %s' % (app_path, app_args)

        # run the command to launch the app
        exit_code = os.system(cmd)

        return {"command": cmd, "return_code": exit_code}
