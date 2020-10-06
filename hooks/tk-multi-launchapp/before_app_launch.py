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
import sgtk
import logging
import tempfile

GLOBAL_PIPELINE_DIR = "//10.80.8.252/VFX_Pipeline"
# GLOBAL_PIPELINE_DIR = "C:/Users/rthompson/Scripts/Pipeline"

class BeforeAppLaunch(tank.Hook):
    """
    Hook to set up the system prior to app launch.
    set's up the environment variables for Nuke, Maya and 3DsMax

    """


    log = sgtk.LogManager.get_logger(__name__)
   
    def _has_envstr(self, env_paths, srch_str):
        found = False
        for idx in range(len(env_paths)):
            if (env_paths[idx] == srch_str) and (len(env_paths[idx]==len(srch_str))):
                found = True
        return found

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

        self.log.debug("Current Engine [%s]" % str(engine_name))
        system = sys.platform

        if "SSVFX_PIPELINE_DEV" in os.environ.keys():
            # Set local studio scripts dirs based on DEV env var
            self.log.debug("%s - %s" % (os.environ["SSVFX_PIPELINE_DEV"] ,"Pipeline"))
            os.environ["SSVFX_PIPELINE"] = os.path.normpath(os.path.join(os.environ["SSVFX_PIPELINE_DEV"] ,"Pipeline"))
            self.log.debug("Added DEV dir %s" %(os.environ["SSVFX_PIPELINE"]))
        else:
            # On non-dev machines - set global path
            os.environ["SSVFX_PIPELINE"] = os.path.normpath(os.path.join(GLOBAL_PIPELINE_DIR,"Pipeline"))
            self.log.debug("Added GLOBAL dir %s" %(os.environ["SSVFX_PIPELINE"]))

        if engine_name == "tk-nuke":
            """---------------------------------------------------------------
                NUKE ENGINE
            ------------------------------------------------------------------"""

            if system == "win32":
                # Windows
                # ssvfx_scripts_path = os.path.join(GLOBAL_PIPELINE_DIR, "ssvfx_scripts" )
                nuke_path= os.path.join(os.environ["SSVFX_PIPELINE"], "ssvfx_nuke_path" )

                try:
                    for i in os.environ:
                        if i == "NUKE_PATH":
                            if nuke_path not in os.getenv(i):
                                os.environ[i] += os.pathsep + nuke_path                
                    self.log.debug("Setting NUKE_PATH to %s " % (nuke_path,))
                except:
                    self.log.debug("!!! Issue setting NUKE_PATH to %s " % (nuke_path,))

                try:
                    if os.path.exists("H:\\"):
                        os.environ["NUKE_DISK_CACHE"] = "H:\\NUKE_TEMP"
                        os.environ["NUKE_TEMP_DIR"] = "H:\\NUKE_TEMP"
                except Exception, err:
                    self.log.debug("Error unable to set env paths : %s", err)

                try:
                    if not os.path.exists( "H:\\NUKE_TEMP" ):
                        self.log.debug("Could not locate NUKE_TEMP: creating...")
                        os.makedirs( "H:\\NUKE_TEMP" )
                except:
                    self.log.error( "Could not create NUKE_TEMP directory" )
            elif system == "darwin":
                # Mac
                pass
            else:
                # Linux OS
                pass

        elif engine_name == "tk-maya":
            """---------------------------------------------------------------
                MAYA ENGINE
            ------------------------------------------------------------------"""
            self.log.debug("before_app_launch - tk-maya")

            startup_path = os.path.normpath(os.path.join(os.environ["SSVFX_PIPELINE"] ,"\\Pipeline\\ssvfx_scripts\\software\\maya\\maya_startup"))
            scripts_path = os.path.normpath(os.path.join(os.environ["SSVFX_PIPELINE"] ,"\\Pipeline\\ssvfx_scripts\\software\\maya\\maya_scripts"))
            comlib_path = os.path.normpath(os.path.join(os.environ["SSVFX_PIPELINE"] ,"\\Pipeline\\ssvfx_scripts\\software\\common_lib"))
            studio_shelf_path = os.path.normpath(os.path.join(os.environ["SSVFX_PIPELINE"] ,"\\Pipeline\\ssvfx_scripts\\software\\maya\\maya_shelves"))
            ssvfx_scripts = os.path.normpath(os.path.join(os.environ["SSVFX_PIPELINE"] ,"\\Pipeline\\ssvfx_scripts\\software\\maya"))

            ocio_config = os.path.normpath(os.path.join(os.environ["SSVFX_PIPELINE"] ,"\\Pipeline\\external_scripts\\OpenColorIO-Configs\\aces_1.0.3\\config.ocio"))

            ### Global Render Preset path and Environment Variable ###
            ### Commented out but not yet deleted in case of emergency. ###
            # global_render_preset = os.path.normpath(os.path.join(os.environ["SSVFX_PIPELINE"] ,"\\Pipeline\\ssvfx_scripts\\software\\maya\\maya_presets\\light"))
            # os.environ["MAYA_RENDER_SETUP_GLOBAL_PRESETS_PATH"] = os.path.normpath(global_render_preset)

            # MAYA-81014 The QtWebEngine module might cause instabilities on all platforms 
            # in some scenarios and is not officially supported yet. 
            # On Windows, the MAYA_ENABLE_WEBENGINE environment variable needs to be set in order 
            # to use QtWebEngineWidgets module. Otherwise Maya could hang. 
            os.environ["OCIO"] = ocio_config
            os.environ["MAYA_ENABLE_WEBENGINE"] = "1"
            os.environ["MAYA_SCRIPT_PATH"] = os.path.normpath(scripts_path)+";"+os.path.normpath(comlib_path)
            os.environ["MAYA_SHELF_PATH"] = os.path.normpath(studio_shelf_path)

            # Shelf Path
            for i in os.environ:
                if i == "PYTHONPATH":
                    # module Path also in Python path
                    scripts_env = os.getenv(i)
                    if not self._has_envstr(scripts_env, ssvfx_scripts):
                        os.environ[i] += os.pathsep + ssvfx_scripts + os.pathsep + comlib_path
                        self.log.debug("PYTHONPATH has Module_path added %s " % ssvfx_scripts)
                    else:
                        self.log.debug("Module_path already in PYTHONPATH")

        elif engine_name == "tk-houdini":
            """---------------------------------------------------------------
                HOUDINI ENGINE                            
            ------------------------------------------------------------------"""
            self.log.debug(">>>>> Before app launch - %s " % str(engine_name))

            # common library path
            comlib_path = os.path.normpath(os.path.join(GLOBAL_PIPELINE_DIR,"\\Pipeline\\ssvfx_scripts\\software\\common_lib"))

            os.environ["HOUDINI_BUFFEREDSAVE"] = "1"
            # HOUDINI_BUFFEREDSAVE -> When enabled .hip files are first 
            # saved to a memory buffer and then written to disk. 
            # This is useful when saving over the network from Windows 2000 machines, 
            # or other places where seeking to the network is expensive.
            os.environ["HOUDINI_ACCESS_MODE"] = "2"
            # Allow access to Alembic's over the network
            # Method 2 simply checks the file attributes.
            os.environ["HOUDINI_NO_START_PAGE_SPLASH"] = "1"
            os.environ["HOUDINI_NO_SPLASH"] = "1"
            os.environ["HOUDINI_OTLSCAN_PATH"] = "$QOTL/base;$QOTL/future;$QOTL/experimental;$HOUDINI_OTLSCAN_PATH;$TS;$MOPS/otls;$AELIB/otls;&"
            # 19/09 added variables 
            os.environ["HOUDINI_GALLERY_PATH"] = "$AELIB/gallery;&"
            os.environ["HOUDINI_TOOLBAR_PATH"] = "$AELIB/toolbar;&"
            os.environ["HOUDINI_SCRIPT_PATH"] = "$AELIB/scripts;&"
            os.environ["HOUDINI_VEX_PATH"] = "$AELIB/vex/include;&"

            os.environ["HDA"] =  os.path.normpath(os.path.join(GLOBAL_PIPELINE_DIR,"\\Pipeline\\Plugins\\3D\\houdini\\hda"))
            os.environ["QLIB"]= "$HDA/qLib-dev"
            os.environ["QOTL"]= "$QLIB/otls"
            os.environ["TS"] = "$HDA/ts"
            os.environ["AELIB"] = "$HDA/Aelib"
            os.environ["MOPS"] = "$HDA/MOPS"
            os.environ["HOUBG"] = "$HDA/hou_bg_render"

            # set path for OCIO
            ocio_config = os.path.normpath(os.path.join(os.environ["SSVFX_PIPELINE"] ,"\\Pipeline\\external_scripts\\OpenColorIO-Configs\\aces_1.0.3\\config.ocio"))
            os.environ["OCIO"] = ocio_config

            if sys.platform == "win32":
                user_env=os.getenv("USERPROFILE")
                tempDir=user_env+"\\AppData\\Local\\houdini\\Temp"
                os.environ["HOUDINI_TEMP_DIR"] = os.path.normpath(tempDir)
                if not os.path.exists(tempDir):
                    os.makedirs(tempDir)
                backupDir=user_env+"\\AppData\\Local\\houdini\\Backup\\"
                os.environ["HOUDINI_BACKUP_DIR"] = os.path.normpath(backupDir)           
                if not os.path.exists(backupDir):
                    os.makedirs(backupDir)
                        
                # HOUDINI_USER_PREF_DIR crucila for the houdini.env file
                houdini_user_pref=user_env+"\\Documents\\houdini16.5\\"
                os.environ["HOUDINI_USER_PREF_DIR"] = os.path.normpath(houdini_user_pref)

                # Deadline Menu Script Path
                DEADLINE_SUBMITTER_PATH="\\AppData\\Local\\Thinkbox\\Deadline10\\submitters\\HoudiniSubmitter;&"
                # Deadline Submission Script Path
                DEADLINE_REPO="\\\\10.80.8.206\\DeadlineRepository10\\submission\\Houdini\\Main"
                DEADLINE_CLIENTCMD_PATH="\\Documents\\houdini16.5\\python2.7libs;"

                win_user=os.getenv("USERPROFILE")
                deadlinepath=os.path.normpath(win_user+DEADLINE_SUBMITTER_PATH)
                houdiniPathBuff=os.getenv("HOUDINI_PATH").replace('&','').replace(r'\r\n','')
                houdiniPath=houdiniPathBuff+deadlinepath+os.pathsep+comlib_path
                deadline_clientcmd_path=win_user+DEADLINE_CLIENTCMD_PATH.replace("\\","/")
                pypath=os.getenv("PYTHONPATH")
                deadlinecmd=os.path.normpath(deadline_clientcmd_path)
                # remove the carage return append deadline cmd
                os.environ["PYTHONPATH"]=pypath.replace(r'\r\n','')+os.pathsep+deadlinecmd+comlib_path
                houdiniMenuPathBuff=os.getenv("HOUDINI_MENU_PATH")
                if houdiniMenuPathBuff is not None:
                    houdiniMenuPath=houdiniMenuPathBuff+deadlinepath
                else:
                    houdiniMenuPath="$HOUDINI_MENU_PATH;"+deadlinepath
                os.environ["HOUDINI_MENU_PATH"]=os.path.normpath(houdiniMenuPath)
                self.log.debug(">>>>> Updated HOUDINI_PATH to include Deadline.\nHOUDINI_PATH %s"%str(houdiniPath))
                deadline_repo_path=DEADLINE_REPO.replace( "\\", "/" )
                deadline_clientcmd_path=win_user+DEADLINE_CLIENTCMD_PATH.replace("\\","/")
                if deadline_repo_path not in sys.path:
                    self.log.debug(">>>>> Adding Deadline Repo sys Path")
                    sys.path.append(os.path.normpath(deadline_repo_path))
                if comlib_path not in sys.path:
                    self.log.debug(">>>>> Adding ssvfx common sg lib to sys Path")
                    sys.path.append(os.path.normpath(comlib_path))
                # add root for .ass storage
                os.environ["HOUDINI_ASS_CACHES_ROOT"] = "\\10.80.8.252\\projects\\caches"
        else:
            """---------------------------------------------------------------
                UNSUPPORTED ENGINE                           
            ------------------------------------------------------------------"""
            self.log.debug("Engine %s is unsupported " % str(engine_name))
