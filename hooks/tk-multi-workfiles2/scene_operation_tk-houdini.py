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
import shutil
import filecmp
import hou
import toolutils

import sgtk

HookClass = sgtk.get_hook_baseclass()


class SceneOperation(HookClass):
    """
    Hook called to perform an operation with the current scene
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

        if operation == "current_path":
            return str(hou.hipFile.name())

        elif operation == "open":
            # give houdini forward slashes
            file_path = file_path.replace(os.path.sep, '/')
            hou.hipFile.load(file_path.encode("utf-8"))
            
            self.set_envs(file_path)
            self.confirm_defaults()

        elif operation == "save":
            hou.hipFile.save()

        elif operation == "save_as":
            # give houdini forward slashes
            file_path = file_path.replace(os.path.sep, '/')
            hou.hipFile.save(str(file_path.encode("utf-8")))

        elif operation == "reset":
            hou.hipFile.clear()
            return True

        elif operation == "prepare_new":
            hou.hipFile.clear()
            self.confirm_defaults()

    def set_envs(self, file_path):

        # setup Shotgun base functions
        eng = sgtk.platform.current_engine()
        tk = sgtk.sgtk_from_path(file_path)

        fields_template = tk.template_from_path(file_path)
        entity_type = eng.context.entity.get('type')
        root_template = None

        # determine context and get templates
        if entity_type:
            if entity_type in ['shot', 'Shot', 'SHOT']:
                root_template = tk.templates['houdini_shot_render_step_ver']
                cache_root = tk.templates['houdini_shot_cache_root']
                flip_root = tk.templates['houdini_shot_playblast_root']
                alembic_root = tk.templates['houdini_shot_alembic_root']
            elif entity_type in ['asset', 'Asset', 'ASSET']:
                root_template = tk.templates['houdini_asset_render_step_ver']
                cache_root = tk.templates['houdini_asset_cache_root']
                flip_root = tk.templates['houdini_asset_playblast_root']
                alembic_root = tk.templates['houdini_asset_alembic_root']

        # generate output roots for renders/caches/flipbooks
        curr_fields = fields_template.get_fields(file_path)

        output_root = root_template.apply_fields(curr_fields)
        cache_output = cache_root.apply_fields(curr_fields)
        flip_output = flip_root.apply_fields(curr_fields)
        alembic_output = alembic_root.apply_fields(curr_fields)

        hou.putenv("RENDER_ROOT", output_root.replace(os.path.sep, '/') )
        hou.putenv("CACHE_ROOT", cache_output.replace(os.path.sep, '/') )
        hou.putenv("FLIP_ROOT", flip_output.replace(os.path.sep, '/') )
        hou.putenv("ALEMBIC_ROOT", alembic_output.replace(os.path.sep, '/') )

        # create variables for filename output
        filename_base = "%s_%s_" % ((curr_fields.get('Asset') or curr_fields.get('Shot') ), curr_fields.get('task_name') )
        filename_version = "_v%s" % str(curr_fields.get('version')).zfill(4)
        hou.putenv("FILENAME_ROOT", filename_base)
        hou.putenv("FILENAME_VER", filename_version)

    def confirm_defaults(self):

        # set ssvfx aux file directory
        ssvfx_presets = r"\\10.80.8.252\VFX_Pipeline\Pipeline\ssvfx_scripts\software\houdini\houdini_node_presets"

        # get user preferences directory
        user_prefs = hou.getenv("HOUDINI_USER_PREF_DIR")
        preset_dir = os.path.join("presets", "Driver")
        driver_dir = os.path.join(user_prefs, preset_dir).replace("/", "\\")

        if not os.path.exists(driver_dir):
            os.makedirs(driver_dir)

        # set base path that should be in all templates
        flipbook_path = r"$FLIP_ROOT/$hipname/$OS/$hipname.$F4.exr"
        render_path = r"$RENDER_ROOT/$hipname/$OS/$FILENAME_ROOT$OS$FILENAME_VER"
        path_with_frames = r"$RENDER_ROOT/$hipname/$OS/$FILENAME_ROOT$OS$FILENAME_VER.$F4.exr"

        # check for the ssvfx defaults in local directory
        for preset in os.listdir(ssvfx_presets):
            ssvfx_item = os.path.join(ssvfx_presets, preset)
            local_item = os.path.join(driver_dir, preset)

            if not os.path.exists(local_item):
                print(">>>>> Copying Preset for: %s" % str(preset) )
                shutil.copy2(ssvfx_item, local_item)
                print(">>>>> Preset copied")
                continue

            print(">>>>> Existing default found. Checking for conflicts...")
            ### SANITY CHECKS ###
            # see if the files are already identical
            if filecmp.cmp(ssvfx_item, local_item, shallow=False):
                print(">>>>> No conflicts in existing preset")
                continue

            # since idx files contain bisary, they can't be edited or read directly
            # so a copy is made to run tests
            print(">>>>> Defaults mismatch, checking path value...")
            file_item = open(local_item)
            file_copy = file_item.read()
            file_item.close()
            
            # set up some lists of nodes with their primary jobs
            frame_renders = ["ifd.idx", "arnold.idx"]
            flip_renders = ["opengl.idx"]

            # check for a render path in the file copy
            # determined by the job type lists
            if preset in frame_renders:
                if path_with_frames in file_copy:
                    print(">>>>> No conflicts with existing frame preset path")
                    continue
            elif preset in flip_renders:
                if flipbook_path in file_copy:
                    print(">>>>> No conflicts with existing flip preset path")
                    continue
            else:
                if render_path in file_copy:
                    print(">>>>> No conflicts with existing preset path")
                    continue
            
            preset_name = preset
            if preset == "ifd.idx":
                preset_name = "mantra.idx"

            confirmation = hou.ui.displayMessage("The ROP default path for %s has been changed\nWould you like to replace your current default with the SSVFX default?\n\nWARNING: THIS WILL COMPLETELY OVERWRITE YOUR EXISTING SAVED DEFAULT FOR THIS NODE" % preset_name, 
                                                    buttons=('Yes', 'No'), 
                                                    default_choice=1,
                                                    close_choice=1,
                                                    title="Retrieve ROP Default",
                                                )

            if confirmation == 1:
                print(">>>>> Reversion rejected")
                continue
            else:
                print(">>>>> Restoring SSVFX default")
                shutil.copy2(ssvfx_item, local_item)

    # def set_flip_path(self):
    #     # Instance flipbookSettings for editing
    #     # node path = "$FLIP_ROOT/$hipname/$OS/$hipname.$F4.exr"
    #     flipbook_options = toolutils.sceneViewer().flipbookSettings()

    #     flipbook_options.output(r"$FLIP_ROOT/$hipname/$hipname.$F4.exr")
