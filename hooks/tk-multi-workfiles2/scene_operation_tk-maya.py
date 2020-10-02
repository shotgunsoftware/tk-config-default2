# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import os, sys
import shutil, glob
import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm
import re
import sgtk

from sgtk import TankError
from sgtk.platform.qt import QtCore, QtGui
import logging

HookClass = sgtk.get_hook_baseclass()

# Detect Dev environment variable
# If detected, run scripts from local location
# Otherwise run scripts from global location
if "SSVFX_PIPELINE" in os.environ.keys():
    sys.path.append(os.environ["SSVFX_PIPELINE"])
    ssvfx_script_path = os.environ["SSVFX_PIPELINE"]
    print("Appended %s to sys path" % (os.environ["SSVFX_PIPELINE"]))
    try:
        from ssvfx_scripts.software.maya.maya_python import maya_tools as mt
    except Exception, err:
        cmds.error("Could not load external ssvfx maya modules. Error %s" % err)
    
else:
    print("Failed to append path")
    try:
        from maya_python import maya_tools as mt
    except Exception, err:
        cmds.error("Could not load external ssvfx maya modules. Error %s" % err)

class SceneOperation(HookClass):
    """
    Hook called to perform an operation with the
    current scene
    """
    # set engine context for class
    eng = sgtk.platform.current_engine()

    # LOCAL BACKUP CONSTANTS
    LOC_BKP_USE_DEFAULT = "USE_DEFAULT_PATH"

    # The Temp path gets cleaned by CC Cleaner
    LOC_BKP_REL_PATH = "/Downloads/Maya_Scene_AutoBkp/"
    LOC_BKP_ENV_VAR_AUTOSAVE = "SSVFX_MAYA_AUTOSAVE"


    def execute(self, operation, file_path, context, parent_action, file_version, read_only, **kwargs):
        """
        Main hook entry point

        :param operation:       String
                                Scene operation to perform

        :param file_path:       String
                                File path to use if the operation
                                requires it (e.g. open)

        :param context:         Context
                                The context the file operation is being
                                performed in.

        :param parent_action:   This is the action that this scene operation is
                                being executed for.  This can be one of:
                                - open_file
                                - new_file
                                - save_file_as
                                - version_up

        :param file_version:    The version/revision of the file to be opened.  If this is 'None'
                                then the latest version should be opened.

        :param read_only:       Specifies if the file should be opened read-only or not

        :returns:               Depends on operation:
                                'current_path' - Return the current scene
                                                 file path as a String
                                'reset'        - True if scene was reset to an empty
                                                 state, otherwise False
                                all others     - None
        """
        # set logger
        self.log = sgtk.LogManager.get_logger(__name__)

        # instance maya_tools
        try:
            mtools = mt.MayaTools()
        except:
            sys.stdout.write(">>>>> Maya_Tools Exception")

        # Shotgun Search to retrieve basic information about the project
        proj_id = context.project['id']
        
        sg_info = self.eng.shotgun.find_one("Project", 
                                            [["id", "is", proj_id]], 
                                            ["sg_frame_rate",
                                            "sg_format_width",
                                            "sg_format_height",
                                            "sg_3d_settings",
                                            "sg_project_color_management"])

        # package CustomEntity03 fields into sg_info
        for index,key in enumerate(sg_info['sg_3d_settings']):
            render_engine = self.eng.shotgun.find_one("CustomNonProjectEntity03", 
                                                    [["id", "is", sg_info['sg_3d_settings'][index]['id']]], 
                                                    ['sg_primary_render_layer', 'sg_render_engine'])
            
            for k in render_engine:
                sg_info['sg_3d_settings'][index].update({k : render_engine[k]})

        if file_path:
            self.log.debug(">>>>> Maya current path %s" % str(file_path))
            file_path = file_path.replace("/", os.path.sep)

        if operation == "current_path":
            # return the current scene path
            return cmds.file(query=True, sceneName=True)

        elif operation == "open":
            # do new scene as Maya doesn't like opening
            # the scene it currently has open!
            try:
                cmds.file(new=True, force=True)
                cmds.file(file_path, open=True, force=True)

                mel.eval('addRecentFile("%s", "%s");' % (file_path,"mayaAscii" if file_path.endswith(".ma") else "mayaBinary"))

                file_path = os.path.normpath(file_path)
                file_path = file_path.replace('\\', '/')

                # Maya root project location
                self.log.debug(">>>>> open - opened file saving workspace Settings")
                self.root_dir = cmds.workspace(q=True, rd=True)

                # Set project/render paths and sync framerate
                self._set_maya_proj_paths(file_path)
                mtools.sync_framerate_SG(sg_info)
                
                # revise render output filename
                self._create_render_prefix()

            except Exception, err:
                self.log.error("Error unable to open Maya file properly %s"%(err))

        elif operation == "save":
            # save the current scene:
            self.log.debug(">>>>> save")
            cmds.file(save=True)

        elif operation == "save_as":
            # first rename the scene as file_path:
            cmds.file(rename=file_path)

            # set proj paths
            self.log.debug(">>>>> save_as - Settings Proj paths: %s" % str(file_path))

            self.root_dir = cmds.workspace(q=True, rd=True)
            self._set_maya_proj_paths(file_path)

            # Maya can choose the wrong file type so
            # we should set it here explicitely based
            # on the extension
            maya_file_type = None
            if file_path.lower().endswith(".ma"):
                maya_file_type = "mayaAscii"
            elif file_path.lower().endswith(".mb"):
                maya_file_type = "mayaBinary"

            # save the scene:
            if maya_file_type:
                cmds.file(save=True, force=True, type=maya_file_type)
            else:
                cmds.file(save=True, force=True)

            # Backup Scene to local storage if activated
            self._backup_save()

            # revise render output filename
            self._create_render_prefix()

        elif operation == "reset":
            """
            Reset the scene to an empty state
            """
            self.log.debug(">>>>> reset")
            while cmds.file(query=True, modified=True):
                # changes have been made to the scene
                res = QtGui.QMessageBox.question(None,
                                                 "Save your scene?",
                                                 "Your scene has unsaved changes. Save before proceeding?",
                                                 QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.Cancel)

                if res == QtGui.QMessageBox.Cancel:
                    return False
                elif res == QtGui.QMessageBox.No:
                    break
                else:
                    scene_name = cmds.file(query=True, sn=True)
                    if not scene_name:
                        cmds.SaveSceneAs()
                    else:
                        cmds.file(save=True)

            # do new file:
            cmds.file(newFile=True, force=True)

            return True

        elif operation == "prepare_new":

            self.log.debug(">>>>> prepare new file")

            # critical Shotgun information
            proj_name = context.project['name']
            type_name = context.entity['type']
            step_name = context.entity['name']
            entity_id = context.entity['id']
            
            # wipe file paths from project window
            cmds.workspace(fileRule=['images', ""])
            cmds.workspace(fileRule=['Alembic', ""])
            cmds.workspace(fileRule=['alembicCache', ""])

            # set famerate
            mtools.sync_framerate_SG(sg_info)
            
            # set resolution
            mtools.maya_resolution_setup(sg_info)
            
            # set frame range
            mtools.sync_frames_from_SG(context.entity)

            # Set initial render options         
            mtools.set_default_renderer(sg_info)
            self._initial_scene_operations()

            # cant set proj paths as file path is empty
            self.log.debug(">>>>> prepare_new proj_name: %s type:%s step:%s entity:%s" % (
                proj_name, type_name, step_name, entity_id))

    def _get_render_fullpath(self, file_path):
        """
        _get_render_path
        Args:
         file_path (path): os Path to resolve templates from
        """
        #tk = self.eng.tank
        sg_project = self.eng.context.project
        sg_proj_path = self.eng.sgtk.project_path
        ctx_id = self.eng.context.entity['id']
        ctx_entity = self.eng.context.entity['type']


        render_root_tmpl = None
        render_path = None
        try:
            if ctx_entity == "Shot":
                render_root_tmpl = self.eng.sgtk.templates['maya_shot_render_stub']
                curr_work_tmpl = self.eng.sgtk.templates['maya_shot_work']
            if ctx_entity == "Asset":
                render_root_tmpl = self.eng.sgtk.templates['maya_asset_renders_stub']
                curr_work_tmpl = self.eng.sgtk.templates['maya_asset_work']
            if render_root_tmpl:
                curr_fields = curr_work_tmpl.get_fields(file_path)
                self.log.debug(">>>>> path fields %s" % curr_fields)
                render_path = os.path.normpath(
                    render_root_tmpl.apply_fields(curr_fields))
        except Exception as err:
            self.log.error("Error: Unable to resolve render path %s" % err)
        return (render_path)

    def _get_render_relpath(self, file_path):
        """
        get render_relpath
        Args:
            file_path (path): os file path to resolve from.
        """
        render_relpath=None
        try:
            # Strip root name to get relative path
            render_path = self._get_render_fullpath(file_path)
            self.log.debug("fullpath %s"%render_path)
            render_relpath = os.path.relpath(render_path, self.root_dir)
            self.log.debug("render relpath %s"%render_relpath)
            #render_relpath = os.path.split(render_relpath)[0]
        except Exception as err:
            self.log.error("Error getting relative renderpath %s",err)
        return (render_relpath)

    def _get_scene_path(self, file_path):
        """
        getter for sg_scene_path
        Args:
            file_path (str): file path
        Returns:
            scene_path (path): scene path
        """
        scene_root_tmpl = None
        ctx_entity = self.eng.context.entity['type']
        if ctx_entity == 'Shot':
            scene_root_tmpl = self.eng.sgtk.templates['maya_shot_work']
        elif ctx_entity == 'Asset':
            scene_root_tmpl = self.eng.sgtk.templates['maya_asset_work']
        if scene_root_tmpl:
            fields = self.eng.context.as_template_fields(scene_root_tmpl)
            scene_path = os.path.normpath(scene_root_tmpl.apply_fields(fields))
        return (scene_path)

    def _get_ncache_path(self, file_path):
        """
        getter for sg_cache_path root path set to maya's workspace
        Args:
            file_path (str): file path
        Returns:
            ncache_path (str): ncache path
        """

        ctx_entity = self.eng.context.entity['type']
        ncache_path = None
        if ctx_entity == 'Shot':
            curr_work_tmpl = self.eng.sgtk.templates['maya_shot_work']
            curr_fields = curr_work_tmpl.get_fields(file_path)
            self.log.debug(">>>>>>> ncache curr fields %s" % str(curr_fields))
            ncache_tmpl = self.eng.sgtk.templates['maya_shot_cache_geo']
            fields = self.eng.context.as_template_fields(ncache_tmpl)
            self.log.debug(">>>>>>> ncache fields %s" % str(fields))
            ncache_path = ncache_tmpl.apply_fields(fields)
            #ncache_path = self._get_template(self.root_dir, file_path, "maya_shot_work", "maya_shot_cache_geo")
            self.log.debug(">>>>>>> ncache_path %s" % str(ncache_path))
        if ctx_entity == 'Asset':
            #ncache_path = self._get_template(self.root_dir, file_path, "maya_asset_work", "maya_asset_cache_geo")
            self.log.debug("ncache_path rel:%s " % str(ncache_path))
        return ncache_path

    def _get_alembic_path(self, file_path):
        """ Get alembic file path
        This is the workspace path
        Args:
            file_path (str): string with the current path.
        """
        #tk = self.eng.tank
        sg_project = self.eng.context.project
        sg_proj_path = self.eng.sgtk.project_path
        ctx_id = self.eng.context.entity['id']
        ctx_entity = self.eng.context.entity['type']

        # ../../../../renders/ maya/anm/version/0400_0000_0010_anm_v002
        # //10.80.8.251/projects/pipeline/shots/0400_0000_0010/pipeline_task/anm/work

        alembic_root_tmpl = None
        alembic_path = None
        self.log.debug(">>>>>> Getting alembic_cache_path ")
        try:
            if ctx_entity == "Shot":
                alembic_root_tmpl = self.eng.sgtk.templates['maya_shot_cache_alembic']
                curr_work_tmpl = self.eng.sgtk.templates['maya_shot_work']
            if ctx_entity == "Asset":
                alembic_root_tmpl = self.eng.sgtk.templates['maya_asset_cache_alembic']
                curr_work_tmpl = self.eng.sgtk.templates['maya_asset_work']
            if alembic_root_tmpl:
                curr_fields = curr_work_tmpl.get_fields(file_path)
                self.log.debug(">>>>>> path alembic fields %s" % curr_fields)
                alembic_path = os.path.normpath(
                    alembic_root_tmpl.apply_fields(curr_fields))
        except Exception as err:
            self.log.error("Error: Unable to resolve alembic path %s" % err)
        return (alembic_path)

    def _get_alembic_relpath(self, file_path):
        """
        get alembic relative path from the root dir
        Args: 
            file_path (str): os fule path to resole from
        """
        abc_path = None
        try:
            # Strip root name to get relative path
            alembic_path = self._get_alembic_path(file_path)
            self.log.debug(">>>>> get_alembic_relpath %s"%alembic_path)
            abc_path = os.path.relpath(alembic_path, self.root_dir)
            self.log.debug(">>>>> set alembic relpath %s"%abc_path)
           # abc_path = os.path.split(alembic_path)[0]
        except Exception as err:
            self.log.error("Error getting alembic relative path %s"%err)
        return (abc_path)

    def _set_maya_proj_paths(self, file_path):
        """
        _set_maya_proj_paths :
        Args:
            file_path (str): file_path 
        """
        try:
            # generate render path
            maya_render_path = self._get_render_relpath(file_path)
            self.log.debug(">>>> set maya proj %s", str(maya_render_path))
            
            if maya_render_path is not None:
                curr_renderer = cmds.getAttr('defaultRenderGlobals.currentRenderer')
                cmds.workspace(fileRule=['images', maya_render_path])
               
            # get alembic-specific path
            alembic_path = self._get_alembic_path(file_path)
            
            if alembic_path is not None:
                cmds.workspace(fileRule=['Alembic', alembic_path])
                cmds.workspace(fileRule=['alembicCache', alembic_path])

            self.log.debug(">>>>> save maya proj paths render[%s] abc[%s]" % (
                maya_render_path, alembic_path))

            # save workspace
            cmds.workspace(saveWorkspace=True)

        except Exception as err:
            self.log.error("Error: Unable to set maya proj paths %s" % err)

    def _get_template(self, root_dir, file_path, current_work_template_name, output_template):
        """ 
        get_template determines the render path base on root_dir and template dir

        Args:
            root_dir (str): root path

            file_path (str): file path

            current_work_template_name (str): work template

            output_template (str): output template

        """
        # Get sgtk to find template eng.tank depreicated points to eng.sgtk
        tk = self.eng.sgtk
        maya_type_work = tk.templates[current_work_template_name]
        fields = maya_type_work.get_fields(file_path)
        # ["maya_shot_render_exr"]
        render_template = tk.templates[output_template]
        render_path = os.path.normpath(render_template.apply_fields(fields))

        # Strip root name to get relative path
        render_path_rel = os.path.relpath(render_path, root_dir)
        render_path_rel = os.path.split(render_path_rel)[0]

        return render_path_rel

    def _get_AutoSave_Dir(self):
        """
        _get_AutoSave_Dir() return the destination scene for backing up
        Returns (str): A string with the AutoSave Path
        """
        # if it has a path use it. if it's undefined use "DEFAULT_PATH"
        auto_save=os.getenv(self.LOC_BKP_ENV_VAR_AUTOSAVE) or "" # self.LOC_BKP_USE_DEFAULT

        # If its set to OFF or not set skip
        if ((auto_save.upper() == "OFF") or (len(auto_save)<=3)):
            return None
        
        mayaLocalPath = os.getenv('MAYA_AUTOSAVE_FOLDER')
        if mayaLocalPath is not None:
            return mayaLocalPath
        
        # if it does have a path or is Empty use default 
        if auto_save == self.LOC_BKP_USE_DEFAULT:
            if sys.platform == "win32":
                # Windows Local Path
                win_user = os.getenv('USERPROFILE')
                autoSaveFolder = os.path.join(win_user + self.LOC_BKP_REL_PATH)

                # check the directory exists if not make it
                # c:\User\<user>\AppData\Local\Maya_Scene_Bkp\
                try:
                    if not os.path.exists(autoSaveFolder):
                        os.makedirs(autoSaveFolder)
                except OSError, err:
                    self.log.debug("Unable Access Scene_Bkp directory %s"%err)
            else:
                # Linux tmp save 
                autoSaveFolder=os.path.join("/usr/local/tmp/")
            return autoSaveFolder
        
        if os.path.exists(auto_save) :
            # check if WINDOWS path is valid no wild card chars
            if re.match(r'^(([a-zA-Z]\:)|(\\))(\\{1}|((\\{1})[^\\]([^:*?&<>"|]*))+)$', auto_save):
                autoSaveFolder=os.path.join(auto_save, '')
            else:
                cmds.error("Environment Path looks invalid!")
                autoSaveFolder=None
        else:
            self.log.debug("AutoSave Configured path does not exist")
            autoSaveFolder=None

        # return configured folder
        return autoSaveFolder

    def _local_auto_save(self):
        """
        Local Temp scene save should the server storage fail
        does not backup references and textures just the scene
        """
        try:
            autoSaveFolder=self._get_AutoSave_Dir()
            if autoSaveFolder is not None:
                cmds.warning("AutoSaving Local copy to %s",autoSaveFolder)
                pm.autoSave(p=True,dst=True,folder=autoSaveFolder,lim=True,max=3,int=3600,en=False)
            else:
                self.log.debug("AutoSave Directory not set backup not processed.")
        except Exception, err:
            # Maya package located in Python\Lib\site-packages\maya\app\general
            cmds.error("Unable to make a local Scene backup. Error %s" % err)

    def _fullscene_backup_save(self):
        """            
            Backup scene, textures and de-reference

            Returns:
                None: if autoSaveFolder is not configured

                dst (dict): destination file and path
        """
        try: 
            # import maya's native File->Archive_Scene lib;  
            import maya.app.general.zipScene as bkpScene      

            autoSaveFolder = self._get_AutoSave_Dir()
            if autoSaveFolder is None:
                self.log.debug("autoSave Folder not set backup not processed")
                return

            # call Maya Archive scene 
            bkpScene.zipScene(True)

            # current path + file name
            src_filepath=cmds.file(query=True, l=True)[0]

            # add backup zip extension
            src_bkpfile=src_filepath+".zip"

            # split returned path + filename
            sceneName = os.path.split(src_bkpfile)[1]
            dst=os.path.join(autoSaveFolder + sceneName)

            # local backup with reference and textures
            src=os.path.normpath(src_bkpfile)
            dst=os.path.normpath(dst)
            cmds.warning("\nMaking local backup from: \nSRC: %s\nDEST: %s\n"%(src,dst))

            # move it to the local drive 
            shutil.move(src,dst)

            #return destination save
            return dst
        except Exception, err:
            # Maya package located in Python\Lib\site-packages\maya\app\general
            cmds.error("Unable to make a local Scene backup. Error %s" % err)
    
    def _backup_save(self):
        """
        _backup_save:   save scene all textures, import references, 
                        keep latest 2 zip copies
        """
        try:
            # current path and filename
            curr_filepath = cmds.file(query=True, l=True)[0]

            # current filename minus path
            # curr_fileName = os.path.split(curr_filepath)[1]

            # get AutoSave Folder
            autoSaveFolder = self._get_AutoSave_Dir()

            # if its not set return            
            if autoSaveFolder is None:
                self.log.debug("AutoSave Folder not set")
                return

            # Back current scene and import references
            curfile=self._fullscene_backup_save()

            # slice up file name for 
            file_name_ext=os.path.split(curfile)[1]
            file_name=file_name_ext.rsplit('.',1)[0]
            filename_no_ver=file_name.rsplit('_v',1)[0]

            # find all the local backup's sort reverse order v41,v40
            local_names_ext = glob.glob(autoSaveFolder + filename_no_ver + "*.zip")
            local_names_ext.sort(reverse=True)

            # rotation of the oldest zip to save local diskspace
            for idx in range(0,len(local_names_ext)):
                if idx > 0:
                    roll=local_names_ext[idx]
                    #dst_file=roll.rsplit('.zip')[0]
                    cmds.warning("Recycling file :%s\n"%roll)
                    # no special chars in name
                    #if re.match(r'^(([^*?&<>;"|]*)+)$', roll):
                    os.remove(roll)
        except Exception, err:
            cmds.warning("Unable to save a backup %s"%err)

    def _initial_scene_operations(self):
        """
        Initial scene configurations, including frame range, frame rate, and resolution
        """
        # Set file naming format to fileName.frameNumber.ext
        cmds.setAttr("defaultRenderGlobals.animation", True)
        cmds.setAttr("defaultRenderGlobals.putFrameBeforeExt", True)

        # Set color management default setting to ACEScg
        try:
            cmds.colorManagementFileRules("Default", edit = True, colorSpace = "ACES - ACEScg")
        except:
            cmds.colorManagementFileRules("Default", edit = True, colorSpace = "ACEScg")

        #Set view transform default setting to Rec.709
        try:
            cmds.colorManagementPrefs(edit = True, viewTransformName = "Rec.709 (ACES)")
        except:
            cmds.colorManagementPrefs(edit = True, viewTransformName = "sRGB (ACES)")

        # Determine current render engine
        curr_renderer = cmds.getAttr('defaultRenderGlobals.currentRenderer')

        if curr_renderer == "arnold":
            # Creates instance of Arnold's defaultSettings node, which is essential
            # for executing Arnold-specific functions without opening the menu
            from mtoa.core import createOptions
            createOptions()

            # # set file naming convention
            # cmds.setAttr("defaultRenderGlobals.imageFilePrefix", "<Scene>_<RenderLayer>/<Scene>_<RenderLayer>", type = "string")
            # set MergeAOVs to True
            cmds.setAttr('defaultArnoldDriver.mergeAOVs', 1)

        elif curr_renderer == "vray":
            cmds.setAttr("vraySettings.animType", 1)
            cmds.setAttr("vraySettings.imageFormatStr", 5)
        else:
            pass

    def _create_render_prefix(self):
        """
        create a token to place in the renderSetup filename prefix
        """
        
        path = cmds.file(query = True, sceneName = True)
        tk = sgtk.sgtk_from_path(path)

        work_template = tk.template_from_path(path)
        curr_fields = work_template.get_fields(path)

        eng = sgtk.platform.current_engine()

        # entity name with space-to-dash conversion
        entity = eng.context.entity.get('name')
        entity = entity.replace(" ", "-")

        # task name
        task = eng.context.task.get('name')

        # version number
        version = "v" + str(curr_fields.get('version')).zfill(3)

        # internal Maya key for layer name
        layer = "<RenderLayer>"

        name_token = "%s_%s_%s_%s" % (entity, task, layer, version)

        cmds.setAttr("defaultRenderGlobals.imageFilePrefix", "<RenderLayer>/" + name_token, type = "string")
