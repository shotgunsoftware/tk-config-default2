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
import json
import tank
import sgtk

GLOBAL_PIPELINE_DIR = "//10.80.8.252/VFX_Pipeline"
# GLOBAL_PIPELINE_DIR = "C:/Users/rthompson/Scripts/Pipeline"
OCIO_CONFIG = '/Pipeline/external_scripts/OpenColorIO-Configs/aces_1.0.3/config.ocio'


class BeforeAppLaunch(tank.Hook):
    """
    Hook to set up the system prior to app launch.
    set's up the environment variables for Nuke, Maya, Houdini and 3DsMax
    """
    _version_config = None
    log = sgtk.LogManager.get_logger(__name__)

    def _has_envstr(self, env_paths, srch_str):
        """ searches an environment variable to check if an entry has already been added
        :param env_paths: <string>
        :param srch_str: <string>
        :return:
        """
        srch_str = os.path.normpath(srch_str)
        if not isinstance(env_paths, list):
            env_paths = env_paths.split(os.pathsep) if os.pathsep in env_paths else [env_paths]
        for env_path in env_paths:
            env_path = os.path.normpath(env_path)
            if env_path == srch_str:
                return True
        return False

    @property
    def version_config(self):
        """ Loads the pipeline_stable_config.json located in a Pipeline Root directory and loads into a dictionary.
        :return:    <dict> {ssvfx_maya: 'v003', ssvfx_houdini: 'v037}
        """
        if self._version_config is None:
            config_file = self.get_pipeline_path("pipeline_stable_config.json", check_version=False)
            if os.path.isfile(config_file):
                self.log.debug('loading stable pipeline config from %s' % config_file)
                with open(config_file) as cf:
                    self._version_config = json.load(cf)
        return self._version_config

    @staticmethod
    def get_latest_package_version(package_path):
        """ Given a path to a folder, collects and sorts all folders named {vddd} and returns the last one
        :param package_path:    <string> path to released package, f.ex Z:/Pipeline/ssvfx_maya
        :return:                <string> name of latest versions folder f.ex v03
        """
        if not package_path or not os.path.isdir(package_path):
            return None
        import re
        VERSION_REGEX = '[vV]\d{3}'
        versions = sorted([d for d in os.listdir(package_path) if re.findall(VERSION_REGEX, d, re.IGNORECASE)])
        if versions:
            return versions[-1]
        return None

    def get_pipeline_path(self, package_name, check_version=False):
        """ Checks if the user has a SSVFX_PIPELINE_DEV custom path set, if requested package is not there,
        will find it in the global pipeline directory
        :param package_name:    <string> name of package to locate
        :param check_version:   <bool>
        :return:                <string> path to package
        """
        package_path = None
        root_path = None
        package_name = os.path.normpath(package_name)
        roots = [os.getenv('SSVFX_PIPELINE_DEV'), os.getenv('SSVFX_PIPELINE')]
        if GLOBAL_PIPELINE_DIR not in roots:
            roots.append(GLOBAL_PIPELINE_DIR)
        for root_path in roots:
            if not root_path:
                continue
            package_path = os.path.join(root_path, "Pipeline", package_name)
            if os.path.exists(package_path):
                break
            package_path = os.path.join(root_path, package_name)
            if os.path.exists(package_path):
                break
            package_path = None
        if not package_path:
            self.log.error('Unable to locate %s in Pipeline' % package_name)
            return None

        # check if it's the new version structure, will have versions and ideally! entry in pipeline_stable_config.json
        if check_version and root_path != os.getenv('SSVFX_PIPELINE_DEV'):
            version = None
            if package_name in self.version_config:
                version = self.version_config.get(package_name)
                self.log.info('stable %s version set in pipeline config: %s' % (package_name, version))
                if not os.path.exists(os.path.join(package_path, version)):
                    self.log.info('requested version has not been released, falling back to latest')
                    version = None
            if not version:
                self.log.info('finding latest version..')
                version = self.get_latest_package_version(package_path)
            if version:
                return os.path.normpath(os.path.join(package_path, version))

        return os.path.normpath(package_path)

    def add_var_to_environ(self, envkey, envvar, reset=False):
        """
        :param envkey:  <str>   Environment key to variable
        :param envvar:    <str>   Path to add to environment variable
        :param reset:   <bool>  Clear the environment var and set to path only
        """
        if envvar is None:
            self.log.warning('No variable supplied to add to env %s' % envkey)
        elif reset or envkey not in os.environ.keys():
            os.environ[envkey] = envvar
            self.log.info("Setting %s to %s" % (envkey, envvar))
        elif self._has_envstr(env_paths=os.getenv(envkey), srch_str=envvar):
            self.log.info("Variable %s already in %s" % (envvar, envkey))
        else:
            os.environ[envkey] += os.pathsep + envvar
            self.log.info("Appending %s to %s" % (envvar, envkey))

    def execute(self, app_path, app_args, version, engine_name, **kwargs):
        """
        The execute function of the hook will be called prior to starting the required application

        :param app_path: (str) The path of the application executable
        :param app_args: (str) Any arguments the application may require
        :param version: (str) version of the application being run if set in the
            "versions" settings of the Launcher instance, otherwise None
        :param engine_name (str) The name of the engine associated with the
            software about to be launched.
        """
        self.log.debug(">>>>> Before app launch - %s " % str(engine_name))
        system = sys.platform
        # todo we should be clearing the local PATH and PYTHONPATHS here, to create isolated environments

        # On non-dev machines - set global path
        self.add_var_to_environ(envkey="SSVFX_PIPELINE",
                                envvar=os.path.normpath(os.path.join(GLOBAL_PIPELINE_DIR, "Pipeline")),
                                reset=True)
        self.log.debug("Setting GLOBAL Pipeline dir: %s" % (os.environ["SSVFX_PIPELINE"]))

        # all apps use ssvfx_scripts, add that first
        self.add_var_to_environ('PYTHONPATH',
                                self.get_pipeline_path(package_name='ssvfx_scripts'))
        # make sure all apps use consistent ocio
        self.add_var_to_environ("OCIO",
                                self.get_pipeline_path(
                                    "external_scripts\\OpenColorIO-Configs\\aces_1.0.3\\config.ocio"))

        if engine_name == "tk-nuke":
            """---------------------------------------------------------------
                NUKE ENGINE
            ------------------------------------------------------------------"""
            # Windows
            if system == "win32":
                # add SSVFX Nuke Pipeline
                self.add_var_to_environ('NUKE_PATH', self.get_pipeline_path(package_name='ssvfx_nuke_path'))
                # cache and tmp
                try:
                    if os.path.exists("H:\\"):
                        os.environ["NUKE_DISK_CACHE"] = "H:\\NUKE_TEMP"
                        os.environ["NUKE_TEMP_DIR"] = "H:\\NUKE_TEMP"
                except Exception as err:
                    self.log.debug("Error unable to set env paths : %s", err)
                try:
                    if not os.path.exists("H:\\NUKE_TEMP"):
                        self.log.debug("Could not locate NUKE_TEMP: creating...")
                        os.makedirs("H:\\NUKE_TEMP")
                except:
                    self.log.error("Could not create NUKE_TEMP directory")
            # Mac
            elif system == "darwin":
                pass
            # Linux OS
            else:
                pass

        elif engine_name == "tk-maya":
            """---------------------------------------------------------------
                MAYA ENGINE
            ------------------------------------------------------------------"""
            ### Global Render Preset path and Environment Variable ###
            ### Commented out but not yet deleted in case of emergency. ###
            # global_render_preset = os.path.normpath(os.path.join(os.environ["SSVFX_PIPELINE"] ,"\\Pipeline\\ssvfx_scripts\\software\\maya\\maya_presets\\light"))
            # os.environ["MAYA_RENDER_SETUP_GLOBAL_PRESETS_PATH"] = os.path.normpath(global_render_preset)

            # MAYA-81014 The QtWebEngine module might cause instabilities on all platforms 
            # in some scenarios and is not officially supported yet. 
            # On Windows, the MAYA_ENABLE_WEBENGINE environment variable needs to be set in order 
            # to use QtWebEngineWidgets module. Otherwise Maya could hang.
            self.add_var_to_environ("MAYA_ENABLE_WEBENGINE", "1")
            self.add_var_to_environ("MAYA_OPENCL_IGNORE_DRIVER_VERSION", "1")
            self.add_var_to_environ("MAYA_NO_WARNING_FOR_MISSING_DEFAULT_RENDERER", "1")
            self.add_var_to_environ("MAYA_DISABLE_CIP", "1")
            self.add_var_to_environ("MAYA_DISABLE_CER", "1")
            self.add_var_to_environ("MAYA_SCRIPT_PATH",
                                    self.get_pipeline_path("ssvfx_scripts/software/maya/maya_scripts"))
            self.add_var_to_environ("MAYA_SHELF_PATH",
                                    self.get_pipeline_path("ssvfx_scripts/software/maya/maya_shelves"))
            self.add_var_to_environ('PYTHONPATH',
                                    self.get_pipeline_path('ssvfx_maya', check_version=True))
            self.add_var_to_environ('PYTHONPATH',
                                    self.get_pipeline_path("ssvfx_scripts/software/maya"))
            # make sure all apps use consistent ocio
            self.add_var_to_environ("OCIO",
                self.get_pipeline_path(
                    "external_scripts/OpenColorIO-Configs/aces_1.0.3/config.ocio"))
            # self.add_var_to_environ('MAYA_PLUG_IN_PATH', '')
            # self.add_var_to_environ('MAYA_MODULE_PATH', '')


        elif engine_name == "tk-houdini":
            """---------------------------------------------------------------
                HOUDINI ENGINE                            
            ------------------------------------------------------------------"""
            self.log.debug(">>>>> Before app launch - %s " % str(engine_name))
            # HOUDINI_BUFFEREDSAVE -> When enabled .hip files are first 
            # saved to a memory buffer and then written to disk. 
            # This is useful when saving over the network from Windows 2000 machines, 
            # or other places where seeking to the network is expensive.
            self.add_var_to_environ("HOUDINI_BUFFEREDSAVE", "1", reset=True)
            # Allow access to Alembic's over the network
            # Method 2 simply checks the file attributes.
            self.add_var_to_environ("HOUDINI_ACCESS_MODE", "2", reset=True)
            self.add_var_to_environ("HOUDINI_NO_START_PAGE_SPLASH", "1", reset=True)
            self.add_var_to_environ("HOUDINI_NO_SPLASH", "1", reset=True)
            self.add_var_to_environ("PYTHONIOENCODING", "UTF-8", reset=True)
            # self.add_var_to_environ("HDF5_DISABLE_VERSION_CHECK", "2", reset=True)

            self.add_var_to_environ("HOUDINI_PATH",
                '//10.80.8.252/VFX_Pipeline/Pipeline/Plugins/3D/houdini;&', reset=True)

            self.add_var_to_environ("HDA", os.path.normpath(os.path.join(
                                           GLOBAL_PIPELINE_DIR, "/Pipeline/Plugins/3D/houdini/hda")), reset=True)
            self.add_var_to_environ("QLIB", "$HDA/qLib-dev", reset=True)
            self.add_var_to_environ("QOTL", "$QLIB/otls", reset=True)
            self.add_var_to_environ("TS", "$HDA/ts", reset=True)
            self.add_var_to_environ("MOPS", "$HDA/MOPS", reset=True)
            self.add_var_to_environ("HOUBG", "$HDA/hou_bg_render", reset=True)
            self.add_var_to_environ("AELIB", "$HDA/Aelib", reset=True)
            # 19/09 added variables 
            self.add_var_to_environ("HOUDINI_GALLERY_PATH", "$AELIB/gallery;&", reset=True)
            self.add_var_to_environ("HOUDINI_TOOLBAR_PATH", "$AELIB/toolbar;&", reset=True)
            self.add_var_to_environ("HOUDINI_SCRIPT_PATH", "$AELIB/scripts;&", reset=True)
            self.add_var_to_environ("HOUDINI_VEX_PATH", "$AELIB/vex/include;&", reset=True)
            self.add_var_to_environ("HOUDINI_OTLSCAN_PATH",
                                    "$QOTL/base;$QOTL/future;$QOTL/experimental;"
                                    "$TS;$MOPS/otls;$AELIB/otls;&", reset=True)

            # add root for .ass storage
            os.environ["HOUDINI_ASS_CACHES_ROOT"] = "//10.80.8.252/projects/caches"
            # self.add_var_to_environ("HOUDINI_DSO_PATH", '')

            # Arnold paths
            # htoa_root = 'path/to/htoa-win/htoa'
            # path_env = os.environ['PATH']
            # os.environ['PATH'] = os.pathsep.join([path_env, htoa_root + '/scripts/bin'])
            # self.add_var_to_environ('HOUDINI_PATH', htoa_root)

            if sys.platform == "win32":
                userprofile = os.getenv("USERPROFILE")

                temp_dir = userprofile + "\\AppData\\Local\\houdini\\Temp"
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)
                self.add_var_to_environ("HOUDINI_TEMP_DIR", os.path.normpath(temp_dir), reset=True)

                backup_dir = userprofile + "\\AppData\\Local\\houdini\\Backup\\"
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)
                self.add_var_to_environ("HOUDINI_BACKUP_DIR", os.path.normpath(backup_dir), reset=True)

                # HOU_VERSION = '17.5'

                # HOUDINI_USER_PREF_DIR crucila for the houdini.env file
                # houdini_user_pref = userprofile + "\\Documents\\houdini16.5\\"
                # self.add_var_to_environ("HOUDINI_USER_PREF_DIR", os.path.normpath(houdini_user_pref), reset=True)

                deadline_submitter_path = os.path.normpath(userprofile + "\\AppData\\Local\\Thinkbox\\Deadline10\\submitters\\HoudiniSubmitter;&")
                # houdini_path_buff = os.getenv("HOUDINI_PATH").replace('&', '').replace(r'\r\n', '')
                # houdini_path = houdini_path_buff + deadline_submitter_path
                # self.log.debug(">>>>> Updated HOUDINI_PATH to include Deadline.\nHOUDINI_PATH %s" % str(houdini_path))

                # Deadline Menu Script Path and Submission Script Path
                # deadline_clientcmd_path = "\\Documents\\houdini{hou_version}\\python2.7libs;".format(
                #     hou_version=HOU_VERSION)
                # Deadline clientcmd path
                # deadlinecmd = os.path.normpath(
                #     userprofile + deadline_clientcmd_path)
                # pypath = os.getenv("PYTHONPATH")
                # os.environ["PYTHONPATH"] = os.pathsep.join([pypath, deadlinecmd])

                houdini_menu_path_buff = os.getenv("HOUDINI_MENU_PATH") or "$HOUDINI_MENU_PATH;"
                houdini_menu_path = houdini_menu_path_buff + deadline_submitter_path
                self.add_var_to_environ("HOUDINI_MENU_PATH", os.path.normpath(houdini_menu_path), reset=True)

                DEADLINE_REPO = "//10.80.8.206/DeadlineRepository10/submission/Houdini/Main"
                if DEADLINE_REPO not in sys.path:
                    self.log.debug(">>>>> Adding Deadline Repo sys Path")
                    sys.path.append(os.path.normpath(DEADLINE_REPO))
        else:
            """---------------------------------------------------------------
                UNSUPPORTED ENGINE                           
            ------------------------------------------------------------------"""
            self.log.info("Engine %s is unsupported in before_app_launch" % str(engine_name))
