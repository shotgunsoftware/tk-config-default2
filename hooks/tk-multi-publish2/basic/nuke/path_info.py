# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
# ### OVERRIDDEN IN SSVFX_SG ###

import os
from tank.util import sgre as re
import sgtk
from ss_config.hooks.tk_multi_publish2.desktop.path_info import SsBasicPathInfo

HookBaseClass = sgtk.get_hook_baseclass()

# ---- globals

# a regular expression used to extract the version number from the file.
# this implementation assumes the version number is of the form 'v###'
# coming just before an optional extension in the file/folder name and just
# after a '.', '_', or '-'.

VERSION_REGEX = re.compile(r"(.+)([._-])v(\d+)\.?([^.]+)?\.?([^.]+)?$", re.IGNORECASE)

# a regular expression used to extract the frame number from the file.
# this implementation assumes the version number is of the form '.####'
# coming just before the extension in the filename and just after a '.', '_',
# or '-'.

FRAME_REGEX = re.compile(r"(.*)([._-])(\d+)\.([^.]+)$", re.IGNORECASE)


class BasicPathInfo(SsBasicPathInfo):
    """
    Methods for basic file path parsing.
    """

    def get_frame_sequence_path(self, path, frame_spec=None):

        return self.initial_path_info_returns( path )

    def initial_path_info_returns(self, path):
        publisher = self.parent
        logger = publisher.logger

        # logger.warning(">>>>> Collecting initial_path_info_returns...")

        from general.file_functions import path_finder
        find_path = path_finder.PathFinder( logger )

        # run path_finder
        ignore_folder_list = path.get('ignore_folder_list') or []
        seek_folder_list = path.get('seek_folder_list') or []
        path = path.get('path')

        ext = os.path.splitext(path)[-1]
        self.logger.warning(">>>>> EXT: %s" % ext)
        if ext:
            finder_path = os.path.dirname(path)
        else:
            finder_path = path

        self.logger.warning(">>>>> Collecting path: %s" % finder_path)
        path_info_returns = find_path.get_folder_contents( finder_path, ignore_folder_list, seek_folder_list, file_ext_ignore=["db"], legacy=False )
        path_info = { 'all_fields':{}, 'path_info_returns': path_info_returns }

        # for i in path_info_returns:
        #     self.logger.warning(">>>>> i: %s" % i)

        # initialize templates
        tk = sgtk.sgtk_from_path(path)
        root_template = tk.template_from_path( path )
        path_info['all_fields']['root_template'] = root_template

        for item in path_info_returns:
            if item['file_range'] == 0:
                item['single'] = True
            elif not ext:
                item['single'] = item['file_range'].split('-')[0] == item['file_range'].split('-')[-1]
            else:
                frame = re.search( r"(\d{3,10})%s$" % ext, path ).group(1)
                item['file_range'] = "%s-%s" % ( frame, frame )
                item['single'] = True

            frames = str( item['file_range'] ).split('-')

            # collect template and template fields
            tmp_path = ''
            work_template = None
            if item['single']:
                tmp_path = item['padded_file_name']
                if item['file_range'] != 0:
                    full_path = re.sub( item['hash_padding'].replace('.', ''), frames[0], tmp_path )
                else:
                    full_path = item['padded_file_name']

                work_template = tk.template_from_path( tmp_path )

                item['full_path'] = full_path
            
            elif item.get('relative_path') in [None, "."]:
                tmp_path = item['padded_file_name']
                work_template = tk.template_from_path( tmp_path )

            else:
                tmp_path = os.path.join( path, item['relative_path'] ).replace("\\", "/")
                item['directory'] = tmp_path
                work_template = tk.template_from_path( tmp_path )

            if not work_template:
                self.logger.warning( ">>>>> Could not find template for %s. Continuing..." % tmp_path )
                continue

            item['base_template'] = work_template

            curr_fields = work_template.get_fields(tmp_path)
            item['fields'] = curr_fields
            if not curr_fields.get("extension"):
                item['fields'].update( { "extension": ext } )

            # Add fields specific to shot/asset
            if "Shot" in item['fields'].keys():
                item['fields'].update( {
                        'Entity': curr_fields['Shot'],
                        'type': "Shot"
                    })

            elif "Asset" in curr_fields.keys():
                item['fields'].update({
                        'Entity': curr_fields['Asset'],
                        'type': "Asset"                        
                    })

            # set workfiles directory for any copy functions
            self._set_workfile_dir( path, item, tk )

            # set outsource/process
            item['process_plugin_info'] = self._set_process( work_template )

            # upadate all_info with any outstanding key:value pairs
            for key in item['fields'].keys():
                if not path_info['all_fields'].get(key):
                    path_info['all_fields'][key] = item['fields'][key]

        return path_info

    def _set_workfile_dir(self, path, item, tk):

        publisher = self.parent
        logger = publisher.logger

        template = item.get('base_template')

        if not template:
            logger.warning("Could not get template from %s" % ( path ) )
            return

        fields = item.get('fields')

        if template.name == "incoming_outsource_shot_version_psd":
            fields['task_name'] = fields['task_name'].lower()
            item['workfile_dir'] = tk.get_template_by_name('psd_shot_work')
        
        if template.name == "incoming_outsource_shot_version_tif":
            fields['task_name'] = fields['task_name'].lower()
            item['workfile_dir'] = tk.get_template_by_name('psd_shot_version_tif')          

        if item.get('workfile_dir'):
            item['publish_path'] = item['workfile_dir'].apply_fields(fields)
        else:
            item['workfile_dir'] = None
            item['publish_path'] = None

    def _set_process(self, template):

        process_info = {
            "outsource": False,
            "software": "Nuke",

            }

        if not template:
            return process_info

        # determine if outsource
        if template.name in [
            "incoming_outsource_shot_folder_root",
            "incoming_outsource_assets_root",
            "incoming_outsource_shot_3de_file",
            "maya_shot_outsource_work_file",
            "maya_shot_outsource_version_abc",
            "maya_asset_outsource_work_file",
            "maya_asset_outsource_version_abc",
            "incoming_outsource_shot_nuke_render",
            "incoming_outsource_shot_matchmove_render",
            "incoming_outsource_shot_undistorted",
            ]:
            
            process_info['outsource'] = True

        # determine if Maya .ma/.mb File
        if template.name in [
            "maya_shot_outsource_work_file",
            "maya_asset_outsource_work_file",
            "maya_shot_work",
            "maya_asset_work",
            ]:

            process_info['software'] = "Maya"

        # determine if alembic
        if template.name in [
            "maya_shot_outsource_work_file",
            "maya_asset_outsource_work_file",
            ]:

            process_info['process'] = "Alembic"

        return process_info

