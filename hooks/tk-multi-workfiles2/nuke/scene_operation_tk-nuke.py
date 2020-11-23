# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import nuke
import re
import sys
import operator

import sgtk

from sgtk import TankError
from sgtk.platform.qt import QtGui

HookClass = sgtk.get_hook_baseclass()

# Set global studio scripts dirs
if "SSVFX_PIPELINE" in os.environ.keys():
    sys.path.append(os.environ["SSVFX_PIPELINE"])
    ssvfx_script_path = os.environ["SSVFX_PIPELINE"]
    nuke.tprint("Appended %s to sys path" % (os.environ["SSVFX_PIPELINE"]))
else:
    nuke.tprint("Failed to append path")

from general.file_functions import file_tester2 as ft2
ft2_instance = ft2.FileTester()
# Import Nuke Tools
from software.nuke.nuke_python import nuke_tools as nt
imp_nuke_tools = nt.NukeTools(additional_module=ft2_instance)

nuke.pluginAddPath(os.path.join(ssvfx_script_path,'software\\nuke\\nuke_shotgun'))       

class SceneOperation(HookClass):
    """
    Hook called to perform an operation with the
    current scene
    """

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
        # We need to see which mode of Nuke we're in. If this is Hiero or
        # Nuke Studio, then we have a separate scene operation routine to
        # use. We're checking that the "hiero_enabled" attribute exists
        # to ensure that this works properly with pre-v0.4.x versions of
        # the tk-nuke engine. If that one attribute exists, then we can be
        # confident that the "studio_enabled" attribute is also available,
        # so there's no need to check that.
        #
        # If there is ever a situation where Hiero- or Nuke Studio-specific
        # logic is required that doesn't also apply to the other, then this
        # conditional could be broken up between hiero_enabled and
        # studio_enabled cases that call through to Nuke Studio and Hiero
        # specific methods.
        engine = self.parent.engine
        sg = engine.shotgun     
        
        proj_name = context.project['name']
        proj_id = context.project['id']
        type_name = context.entity['type']
        step_name = context.step['name']
        step_id = context.step['id']
        entity_id = context.entity['id']
        entity_name = context.entity['name']
        color_info = None

        # Additional Shotgun information
        proj_info = sg.find_one("Project", 
                                        [["id", "is", proj_id]], 
                                        ["sg_frame_rate","sg_frame_rate", 
                                        "sg_format_width", 
                                        "sg_format_height",
                                        "sg_short_name",
                                        "sg_nuke_color_management",
                                        "sg_project_color_management"])
        

        shot_info = sg.find_one("Shot", 
                                        [["id", "is", entity_id]], 
                                        ['sg_shot_ocio',
                                        'sg_shot_lut',
                                        'sg_project_color_management_config',
                                        'sg_nuke_templates']) 

        if proj_info['sg_nuke_color_management']:

            color_info = sg.find_one("CustomNonProjectEntity16", 
                                            [["id", "is", proj_info['sg_nuke_color_management']['id']]],
                                            [
                                            'code',
                                            'sg_monitorlut',
                                            'sg_viewerprocess',
                                            'sg_floatlut',
                                            'sg_loglut',
                                            'sg_int8lut',
                                            'sg_int16lut',
                                            'sg_color_management_type',
                                            'sg_color_management_config',
                                            'sg_color_management_config_file',
                                            ]) 

        # Special call to retrieve all existing templates
        # with their ID codes and applicable pipeline steps
        template_info = sg.find("CustomNonProjectEntity05", [], ['code', 'sg_applicable_steps'])

        if hasattr(engine, "hiero_enabled") and (engine.hiero_enabled or engine.studio_enabled):
            return self._scene_operation_hiero_nukestudio(
                operation,
                file_path,
                context,
                parent_action,
                file_version,
                read_only,
                **kwargs
            )

        # If we didn't hit the Hiero or Nuke Studio case above, we can
        # continue with the typical Nuke scene operation logic.
        if file_path:
            file_path = file_path.replace("/", os.path.sep)

        if operation == "current_path":
            # return the current script path
            return nuke.root().name().replace("/", os.path.sep)

        elif operation == "open":
            # open the specified script
            nuke.scriptOpen(file_path)
            # reset any write node render paths:
            if self._reset_write_node_render_paths():
                # something changed so make sure to save the script again:
                nuke.scriptSave()

            # Check for excess SG Write Nodes
            imp_nuke_tools.sg_writenode_check()
            # Check for OCIO/LUT
            self._find_OCIO_settings(proj_info, shot_info, color_info, step_name)

            # create template menu
            self._create_template_menu(template_info)

        elif operation == "save":
            # save the current script:   
            nuke.scriptSave()

        elif operation == "save_as":
            old_path = nuke.root()["name"].value()
            try:
                # rename script:
                nuke.root()["name"].setValue(file_path)

                # reset all write nodes:
                self._reset_write_node_render_paths()

                # save script:
                nuke.scriptSaveAs(file_path, -1)
            except Exception, e:
                # something went wrong so reset to old path:
                nuke.root()["name"].setValue(old_path)
                raise TankError("Failed to save scene %s", e)

            # Check for OCIO/LUT
            self._find_OCIO_settings(proj_info, shot_info, color_info, step_name)

            # create template menu
            self._create_template_menu(template_info)

            # check for templates and prompt user for import
            self._template_prompt(shot_info, template_info, step_id)

        elif operation == "reset":
            while nuke.root().modified():
                # changes have been made to the scene
                res = QtGui.QMessageBox.question(None,
                                                 "Save your script?",
                                                 "Your script has unsaved changes. Save before proceeding?",
                                                 QtGui.QMessageBox.Yes|QtGui.QMessageBox.No|QtGui.QMessageBox.Cancel)

                if res == QtGui.QMessageBox.Cancel:
                    return False
                elif res == QtGui.QMessageBox.No:
                    break
                else:
                    nuke.scriptSave()
            

            # now clear the script:
            nuke.scriptClear()
            
            return True   

        elif operation == "prepare_new":
            
            # TODO: If BD projects is still a thing then re-implement this

            # if proj_name =="Breakdowns":
            #     sg = engine.shotgun
            #     if type_name == "Shot":               
            #         if not proj_info['sg_project_name']:
            #             nuke.tprint("No Project Name given to the shot. Please inform Production!")
            #             return
            #         else:
            #             source_proj_name = proj_info['sg_project_name']['name']
            #             if source_proj_name:
            #                 source_proj_info = sg.find_one("Project", [["name", "is", source_proj_name]], ["sg_frame_rate","sg_frame_rate", "sg_format_width", "sg_format_height","sg_short_name"])
            #                 proj_short_code = source_proj_info["sg_short_name"]
            #                 proj_fps = source_proj_info["sg_frame_rate"]
            #                 proj_format_width = source_proj_info["sg_format_width"]
            #                 proj_format_height = source_proj_info["sg_format_height"]
            #                 try:
            #                     nroot = nuke.Root()
            #                     nroot.knob('fps').setValue(float(proj_fps))
            #                     nuke.knobDefault("Root.fps", str(proj_fps)) 
            #                     nuke.addFormat('%s %s 1 %s' %(proj_format_width, proj_format_height, proj_short_code+"_"+str(proj_format_width)))
            #                     nroot.knob('format').setValue(proj_short_code+"_"+str(proj_format_width))
            #                     nuke.tprint("This project is "+source_proj_name+". Correct format set...")
            #                 except:
            #                     nuke.tprint('Problem applying format settings from source project!')   
            #             else:
            #                 nuke.tprint("Could not get source project.")
            
            all_cameras = engine.shotgun.find("Camera",
                                            [],
                                            ['sg_shots', 'sg_format_width', 'sg_format_height', 'sg_pixel_aspect_ratio', 'code'])

            shot_camera = next((cam for cam in all_cameras if context.entity in cam['sg_shots']), None)

            if shot_camera:

                format_name = shot_camera['code'].lower() + "_" + str(shot_camera['sg_format_width'])

                cam_format = nuke.addFormat("%s %s %s %s" % (str(shot_camera['sg_format_width']), 
                                                            str(shot_camera['sg_format_height']), 
                                                            str(shot_camera['sg_pixel_aspect_ratio']), 
                                                            (format_name)))

                nuke.root()['format'].setValue(format_name)

                nuke.tprint("Format set to %s" % format_name)
                nuke.tprint("Resolution: %s X %s w/ Pixel Ratio: %s" % (str(shot_camera['sg_format_width']), 
                                                        str(shot_camera['sg_format_height']), 
                                                        str(shot_camera['sg_pixel_aspect_ratio'])))
            else:
                pass
              
            if step_name == "Roto":
                self._source_roto_template(step_name, 
                                        (str(proj_info['sg_short_name'])+"_"+str(proj_info['sg_format_width'])))

            self._sync_frames_from_SG(entity_id, context)

            # create template menu
            self._create_template_menu(template_info)

    def _source_roto_template(self, step_name, proj_format):
        """
        Prompts user if they want to import the set Roto template for the New File.
        """
        if step_name == "Roto":
            roto_template = nuke.ask("Source the default Nuke template for the <i style='color:magenta'><b><br>SSVFX Roto</b></i> workflow?")
            if not roto_template:
                pass
            else:
                tk = self.parent.engine.sgtk
                roto_template_script = tk.templates["workfile_templates"]
                fields = {}
                roto_template_script_path = os.path.normpath(roto_template_script.apply_fields(fields) +"\\pipeline_task\\roto\\roto_rgb_template.nk")
                roto_template_script_path = roto_template_script_path.replace("/", os.path.sep)
                if os.path.exists(roto_template_script_path):
                    nuke.tprint("Importing Roto template:",roto_template_script_path)
                    nuke.scriptSource(roto_template_script_path)
                    nuke.zoom(0.0)
                    try:
                        nuke.Root().knob('format').setValue(proj_format)
                    except:
                        nuke.tprint("!!! No proj_format called %s" % proj_format)
     
    def _get_current_hiero_project(self):
        """
        Returns the current project based on where in the UI the user clicked
        """
        import hiero

        # get the menu selection from hiero engine
        selection = self.parent.engine.get_menu_selection()

        if len(selection) != 1:
            raise TankError("Please select a single Project!")

        if not isinstance(selection[0] , hiero.core.Bin):
            raise TankError("Please select a Hiero Project!")

        project = selection[0].project()
        if project is None:
            # apparently bins can be without projects (child bins I think)
            raise TankError("Please select a Hiero Project!")

        return project

    def _reset_write_node_render_paths(self):
        """
        Use the tk-nuke-writenode app interface to find and reset
        the render path of any Shotgun Write nodes in the current script
        """
        write_node_app = self.parent.engine.apps.get("tk-nuke-writenode")
        if not write_node_app:
            return False

        # only need to forceably reset the write node render paths if the app version
        # is less than or equal to v0.1.11
        from distutils.version import LooseVersion
        if (write_node_app.version == "Undefined"
            or LooseVersion(write_node_app.version) > LooseVersion("v0.1.11")):
            return False

        write_nodes = write_node_app.get_write_nodes()
        for write_node in write_nodes:
            write_node_app.reset_node_render_path(write_node)

        return len(write_nodes) > 0

    def _get_all_reads(self):
        if nuke.exists("root"):
            return nuke.allNodes(group=nuke.root(), 
                                 filter='Read', 
                                 recurseGroups = True)
        else:
            return []

    def _sync_frames_from_SG(self, entity_id, context):

        eng = self.parent.engine
        sg = eng.shotgun
        script_first_frame = nuke.root()["first_frame"].value()
        script_last_frame = nuke.root()["last_frame"].value()  
        script_frame_range = (int(script_first_frame), int(script_last_frame))   
        sg_frame_range = (None, None)

        if not eng:
            pass
        elif context.entity['type'] == 'Asset':
            pass
        else:
            if "tk-multi-setframerange" not in eng.apps:
                shot_info = sg.find_one("Shot", 
                                            [["id", "is", entity_id]], 
                                            ["sg_head_in",
                                            "sg_tail_out"])
                if (shot_info["sg_head_in"] and
                    shot_info["sg_tail_out"]):
                    sg_frame_range = (int(shot_info["sg_head_in"]), int(shot_info["sg_tail_out"]))

            else:
                app = eng.apps["tk-multi-setframerange"]
                sg_frame_range = app.get_frame_range_from_shotgun()

            if sg_frame_range[0] and sg_frame_range[1] != None:
                # If script frame range doesn't match SG - update.
                if script_frame_range != sg_frame_range:
                    # unlock
                    locked = nuke.root()["lock_range"].value()
                    if locked:
                        nuke.root()["lock_range"].setValue(False)
                    # set values
                    nuke.root()["first_frame"].setValue(int(sg_frame_range[0]))
                    nuke.root()["last_frame"].setValue(int(sg_frame_range[1]))
                    # and lock again
                    if locked:
                        nuke.root()["lock_range"].setValue(True)

                nuke.tprint("Correct frame range from SG: %s-%s" % (str(nuke.root()["first_frame"].value()), 
                                                                    str(nuke.root()["last_frame"].value())))
            
            nuke.root()["lock_range"].setValue(True)                                                                

    def _scene_operation_hiero_nukestudio(
        self, operation, file_path, context, parent_action, file_version, read_only, **kwargs):
        """
        Scene operation logic for Hiero and Nuke Studio modes of Nuke.

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
        import hiero

        if operation == "current_path":
            # return the current script path
            project = self._get_current_hiero_project()
            curr_path = project.path().replace("/", os.path.sep)
            return curr_path

        elif operation == "open":
            # Manually fire the kBeforeProjectLoad event in order to work around a bug in Hiero.
            # The Foundry has logged this bug as:
            #   Bug 40413 - Python API - kBeforeProjectLoad event type is not triggered
            #   when calling hiero.core.openProject() (only triggered through UI)
            # It exists in all versions of Hiero through (at least) v1.9v1b12.
            #
            # Once this bug is fixed, a version check will need to be added here in order to
            # prevent accidentally firing this event twice. The following commented-out code
            # is just an example, and will need to be updated when the bug is fixed to catch the
            # correct versions.
            # if (hiero.core.env['VersionMajor'] < 1 or
            #     hiero.core.env['VersionMajor'] == 1 and hiero.core.env['VersionMinor'] < 10:
            hiero.core.events.sendEvent("kBeforeProjectLoad", None)

            # open the specified script
            hiero.core.openProject(file_path.replace(os.path.sep, "/"))

        elif operation == "save":
            # save the current script:
            project = self._get_current_hiero_project()
            project.save()

        elif operation == "save_as":
            project = self._get_current_hiero_project()
            project.saveAs(file_path.replace(os.path.sep, "/"))

            # ensure the save menus are displayed correctly
            _update_save_menu_items(project)

        elif operation == "reset":
            # do nothing and indicate scene was reset to empty
            return True

        elif operation == "prepare_new":
            # add a new project to hiero
            hiero.core.newProject()

    def _find_OCIO_settings(self, proj_info, shot_info, color_info, step_name):
        '''
        Checks Shotgun for an OCIO file and automatically applies it if found.
        If there's supposed to be an OCIO file, but none exists, it substitutes in aces_1.0.3
        It also clears out any viewerProcess colors that are not rec709

        param: proj_info - Project information from Shotgun
        param: shot_info - Shot information from Shotgun
        param: step_name - step name identified via Shotgun

        If the step_name is Roto, no color is applied.
        '''
        if step_name == "Roto":
            nuke.tprint('Roto, No Color Applied')
        else:
            if shot_info['sg_shot_ocio'] != None:

                # Checks Shotgun project-wide settings for color specification
                if proj_info['sg_project_color_management'] == "OCIO":
                    # Checks Shotgun's shot-specific information for OCIO filess
                    nuke.tprint('Setting shot-linked OCIO')
                    nuke.Root()['colorManagement'].setValue('OCIO')
                    nuke.Root()['OCIO_config'].setValue('custom')
                    nuke.Root()['customOCIOConfigPath'].setValue(shot_info['sg_shot_ocio']['local_path_windows'].replace('\\', '/'))
                    
                    # Check for viewers and clean out the list of viewer processes
                    if len(nuke.allNodes('Viewer')) < 1:
                        temp_view = nuke.createNode('Viewer')
                        for i in nuke.ViewerProcess.registeredNames():
                            if 'rec709' not in i:
                                nuke.ViewerProcess.unregister(i)
                        nuke.delete(temp_view)
                    else:
                        for i in nuke.ViewerProcess.registeredNames():
                            if 'rec709' not in i:
                                nuke.ViewerProcess.unregister(i)            
            
            elif color_info:

                nuke.tprint('Shot has no attached OCIO. Using Project based Color Management settings')
                nuke.tprint("- Type: %s" % (color_info['sg_color_management_type']))
                nuke.tprint("- Config: %s" % (color_info['sg_color_management_config']))
                nuke.tprint("- Config File: %s" % (color_info['sg_color_management_config_file']))

                nuke.Root()['colorManagement'].setValue(color_info['sg_color_management_type'])
                nuke.Root()['OCIO_config'].setValue(color_info['sg_color_management_config'])   
                if color_info['sg_monitorlut']:
                    nuke.Root()['monitorLut'].setValue(color_info['sg_monitorlut'])
                if color_info['sg_floatlut']:
                    nuke.Root()['floatLut'].setValue(color_info['sg_floatlut'])   
                if color_info['sg_loglut']:
                    nuke.Root()['logLut'].setValue(color_info['sg_loglut'])
                if color_info['sg_int8lut']:
                    nuke.Root()['int8Lut'].setValue(color_info['sg_int8lut'])
                if color_info['sg_int16lut']:
                    nuke.Root()['int16Lut'].setValue(color_info['sg_int16lut'])

                if color_info['sg_color_management_config_file']:
                    nuke.Root()['customOCIOConfigPath'].setValue(color_info['sg_color_management_config_file'])
                else:
                    nuke.Root()['customOCIOConfigPath'].setValue("")      
                                  
                if color_info['sg_viewerprocess']:
                    try:
                        nuke.knobDefault("Viewer.viewerProcess", color_info['sg_viewerprocess'])
                        nuke.tprint("Setting default viewerProcess to %s" %(color_info['sg_viewerprocess']))
                    except:
                        nuke.tprint("Issue setting default viewerProcess. Using default...")
            # If the project does not use OCIO, default to Nuke's default color settings
            else:
                nuke.tprint('No Project Color Settings, defaulting to Nuke defaults')
                nuke.Root()['colorManagement'].setValue('Nuke')
                nuke.Root()['OCIO_config'].setValue('nuke-default')

    def _create_template_menu(self, template_info):
        # Create Template top level menu
        template_menu = nuke.menu('Nuke')
        template_top_menu = template_menu.addMenu('SSVFX/Templates')

        # Create menu items for all available templates
        for template in template_info:
            word = template['code']
            word = '\'' + word + '\''
            template_top_menu.addCommand(template['code'], "imp_nuke_tools.template_setup(%s)" % (word))

    def _template_prompt(self, shot_info, template_info, step_id):
        # Collect tank info to find the current file version
        tk = sgtk.sgtk_from_path(nuke.Root().name())
        work_template = tk.template_from_path(nuke.Root().name())
        curr_fields = work_template.get_fields(nuke.Root().name())
        fields ={
                'Shot': curr_fields['Shot'],
                'task_name': curr_fields['task_name'],
                'name': '',
                'output': '',
                'version': curr_fields['version']
        }  

        # simplified information for sanity checks
        # template_short is templates with applicable pipeline step id codes
        # shot_step is the id code of the current pipeline step
        template_short = {template['code'] : [step['id'] for step in template['sg_applicable_steps']] for template in template_info}

        # sanity check, if passed prompt to import template
        # if it is the first version of the shot
        # and there are actual templates assigned to the shot
        if fields['version'] == 1 and shot_info['sg_nuke_templates'] != []:
            for template in shot_info['sg_nuke_templates']:
                if step_id in template_short[template['name']] and template['name'] != 'test':
                    template_prompt = nuke.ask("There is a nuke script template associated with this shot.\n<i style='color:salmon'><b>It is strongly recommended that you use this.</b>")

                    if template_prompt:
                        imp_nuke_tools.template_setup(template['name'])
                    else:
                        nuke.tprint('Declined Template Import')

                else:
                    pass


def _update_save_menu_items(project):
    """
    There's a bug in Hiero when using `project.saveAs()` whereby the file menu
    text is not updated. This is a workaround for that to find the menu
    QActions and update them manually to match what Hiero should display.
    """

    import hiero

    project_path = project.path()

    # get the basename of the path without the extension
    file_base = os.path.splitext(os.path.basename(project_path))[0]

    save_action = hiero.ui.findMenuAction('foundry.project.save')
    save_action.setText("Save Project (%s)" % (file_base,))

    save_as_action = hiero.ui.findMenuAction('foundry.project.saveas')
    save_as_action.setText("Save Project As (%s)..." % (file_base,))


