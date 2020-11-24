# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
from tank.util import sgre as re

import sgtk

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


class BasicPathInfo(HookBaseClass):
    """
    Methods for basic file path parsing.
    """

    def get_publish_name(self, path, sequence=False):
        """
        Given a file path, return the display name to use for publishing.

        Typically, this is a name where the path and any version number are
        removed in order to keep the publish name consistent as subsequent
        versions are published.

        Example::

            # versioned file. remove the version
            in: /path/to/the/file/scene.v001.ma
            out: scene.ma

            # image sequence. replace the frame number with #s
            in: /path/to/the/file/my_file.001.jpg
            out: my_file.###.jpg

        :param path: The path to a file, likely one to be published.
        :param sequence: If True, treat the path as a sequence name and replace
            the frame number with placeholder

        :return: A publish display name for the provided path.
        """

        publisher = self.parent

        logger = publisher.logger
        logger.debug("Getting publish name for path: %s ..." % (path,))

        path_info_returns = publisher.util.get_file_path_components(path)
        filename = path_info_returns["filename"]

        version_pattern_match = re.search(VERSION_REGEX, filename)
        frame_pattern_match = re.search(FRAME_REGEX, filename)

        if version_pattern_match:
            # found a version number, use the other groups to remove it
            prefix = version_pattern_match.group(1)
            extension = version_pattern_match.group(4) or ""
            if extension:
                publish_name = "%s.%s" % (prefix, extension)
            else:
                publish_name = prefix
        elif frame_pattern_match and sequence:
            # found a frame number, meplace it with #s
            prefix = frame_pattern_match.group(1)
            frame_sep = frame_pattern_match.group(2)
            frame = frame_pattern_match.group(3)
            display_str = "#" * len(frame)
            extension = frame_pattern_match.group(4) or ""
            publish_name = "%s%s%s.%s" % (prefix, frame_sep, display_str, extension)
        else:
            publish_name = filename

        logger.debug("Returning publish name: %s" % (publish_name,))
        return publish_name

    def get_version_number(self, path):
        """
        Extract a version number from the supplied path.

        This is used by plugins that need to know what version number to
        associate with the file when publishing.

        :param path: The path to a file, likely one to be published.

        :return: An integer representing the version number in the supplied
            path. If no version found, ``None`` will be returned.
        """

        publisher = self.parent

        logger = publisher.logger
        logger.debug("Getting version number for path: %s ..." % (path,))

        path_info_returns = publisher.util.get_file_path_components(path)
        filename = path_info_returns["filename"]

        # default if no version number detected
        version_number = None

        # if there's a version in the filename, extract it
        version_pattern_match = re.search(VERSION_REGEX, filename)

        if version_pattern_match:
            version_number = int(version_pattern_match.group(3))

        logger.debug("Returning version number: %s" % (version_number,))
        return version_number

    def get_frame_sequence_path(self, path, frame_spec=None):

        return self.initial_path_info_returns( path )
        # """
        # Given a path with a frame number, return the sequence path where the
        # frame number is replaced with a given frame specification such as
        # ``{FRAME}`` or ``%04d`` or ``$F``.

        # :param path: The input path with a frame number
        # :param frame_spec: The frame specification to replace the frame number
        #     with.

        # :return: The full frame sequence path
        # """

        # publisher = self.parent
        # path_info_returns = publisher.util.get_file_path_components(path)

        # # see if there is a frame number
        # frame_pattern_match = re.search(FRAME_REGEX, path_info_returns["filename"])

        # if not frame_pattern_match:
        #     # no frame number detected. carry on.
        #     return None

        # prefix = frame_pattern_match.group(1)
        # frame_sep = frame_pattern_match.group(2)
        # frame_str = frame_pattern_match.group(3)
        # extension = frame_pattern_match.group(4) or ""

        # # make sure we maintain the same padding
        # if not frame_spec:
        #     padding = len(frame_str)
        #     frame_spec = "%%0%dd" % (padding,)

        # seq_filename = "%s%s%s" % (prefix, frame_sep, frame_spec)

        # if extension:
        #     seq_filename = "%s.%s" % (seq_filename, extension)

        # # build the full sequence path
        # return os.path.join(path_info_returns["folder"], seq_filename)

    def get_frame_sequences(self, folder, extensions=None, frame_spec=None):
        """
        Given a folder, inspect the contained files to find what appear to be
        files with frame numbers.

        :param folder: The path to a folder potentially containing a sequence of
            files.

        :param extensions: A list of file extensions to retrieve paths for.
            If not supplied, the extension will be ignored.

        :param frame_spec: A string to use to represent the frame number in the
            return sequence path.

        :return: A list of tuples for each identified frame sequence. The first
            item in the tuple is a sequence path with the frame number replaced
            with the supplied frame specification. If no frame spec is supplied,
            a python string format spec will be returned with the padding found
            in the file.


            Example::

            get_frame_sequences(
                "/path/to/the/folder",
                ["exr", "jpg"],
                frame_spec="{FRAME}"
            )

            [
                (
                    "/path/to/the/supplied/folder/key_light1.{FRAME}.exr",
                    [<frame_1_path>, <frame_2_path>, ...]
                ),
                (
                    "/path/to/the/supplied/folder/fill_light1.{FRAME}.jpg",
                    [<frame_1_path>, <frame_2_path>, ...]
                )
            ]
        """

        publisher = self.parent
        logger = publisher.logger

        logger.debug("Looking for sequences in folder: '%s'..." % (folder,))

        # list of already processed file names
        processed_names = {}

        # examine the files in the folder
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)

            if os.path.isdir(file_path):
                # ignore subfolders
                continue

            # see if there is a frame number
            frame_pattern_match = re.search(FRAME_REGEX, filename)

            if not frame_pattern_match:
                # no frame number detected. carry on.
                continue

            prefix = frame_pattern_match.group(1)
            frame_sep = frame_pattern_match.group(2)
            frame_str = frame_pattern_match.group(3)
            extension = frame_pattern_match.group(4) or ""

            # filename without a frame number.
            file_no_frame = "%s.%s" % (prefix, extension)

            if file_no_frame in processed_names:
                # already processed this sequence. add the file to the list
                processed_names[file_no_frame]["file_list"].append(file_path)
                continue

            if extensions and extension not in extensions:
                # not one of the extensions supplied
                continue

            # make sure we maintain the same padding
            if not frame_spec:
                padding = len(frame_str)
                frame_spec = "%%0%dd" % (padding,)

            seq_filename = "%s%s%s" % (prefix, frame_sep, frame_spec)

            if extension:
                seq_filename = "%s.%s" % (seq_filename, extension)

            # build the path in the same folder
            seq_path = os.path.join(folder, seq_filename)

            # remember each seq path identified and a list of files matching the
            # seq pattern
            processed_names[file_no_frame] = {
                "sequence_path": seq_path,
                "file_list": [file_path],
            }

        # build the final list of sequence paths to return
        frame_sequences = []
        for file_no_frame in processed_names:

            seq_info = processed_names[file_no_frame]
            seq_path = seq_info["sequence_path"]

            logger.debug("Found sequence: %s" % (seq_path,))
            frame_sequences.append((seq_path, seq_info["file_list"]))

        return frame_sequences

    def get_version_path(self, path, version):
        """
        Given a path without a version number, return the path with the supplied
        version number.

        If a version number is detected in the supplied path, the path will be
        returned as-is.

        :param path: The path to inject a version number.
        :param version: The version number to inject.

        :return: The modified path with the supplied version number inserted.
        """

        publisher = self.parent

        logger = publisher.logger
        logger.debug("Getting version %s of path: %s ..." % (version, path))

        path_info_returns = publisher.util.get_file_path_components(path)
        filename = path_info_returns["filename"]

        # see if there's a version in the supplied path
        version_pattern_match = re.search(VERSION_REGEX, filename)

        if version_pattern_match:
            # version number already in the path. return the original path
            return path

        (basename, ext) = os.path.splitext(filename)

        # construct the new filename with the version number inserted
        version_filename = "%s.%s%s" % (basename, version, ext)

        # construct the new, full path
        version_path = os.path.join(path_info_returns["folder"], version_filename)

        logger.debug("Returning version path: %s" % (version_path,))
        return version_path

    def get_next_version_path(self, path):
        """
        Given a file path, return a path to the next version.

        This is typically used by auto-versioning logic in plugins that need to
        save the current work file to the next version number.

        If no version can be identified in the supplied path, ``None`` will be
        returned, indicating that the next version path can't be determined.

        :param path: The path to a file, likely one to be published.

        :return: The path to the next version of the supplied path.
        """

        publisher = self.parent

        logger = publisher.logger
        logger.debug("Getting next version of path: %s ..." % (path,))

        # default
        next_version_path = None

        path_info_returns = publisher.util.get_file_path_components(path)
        filename = path_info_returns["filename"]

        # see if there's a version in the supplied path
        version_pattern_match = re.search(VERSION_REGEX, filename)

        if version_pattern_match:
            prefix = version_pattern_match.group(1)
            version_sep = version_pattern_match.group(2)
            version_str = version_pattern_match.group(3)
            extension = version_pattern_match.group(4) or ""

            # make sure we maintain the same padding
            padding = len(version_str)

            # bump the version number
            next_version_number = int(version_str) + 1

            # create a new version string filled with the appropriate 0 padding
            next_version_str = "v%s" % (str(next_version_number).zfill(padding))

            new_filename = "%s%s%s" % (prefix, version_sep, next_version_str)
            if extension:
                new_filename = "%s.%s" % (new_filename, extension)

            # build the new path in the same folder
            next_version_path = os.path.join(path_info_returns["folder"], new_filename)

        logger.debug("Returning next version path: %s" % (next_version_path,))
        return next_version_path

    def initial_path_info_returns(self, path):
        publisher = self.parent
        logger = publisher.logger

        # logger.warning(">>>>> Collecting initial_path_info_returns...")

        from general.file_functions import path_finder
        find_path = path_finder.PathFinder()

        # run path_finder
        ignore_folder_list = path.get('ignore_folder_list') or []
        seek_folder_list = path.get('seek_folder_list') or []
        path = path.get('path')

        ext = os.path.splitext(path)[-1]
        if ext:
            finder_path = os.path.dirname(path)
        else:
            finder_path = path

        logger.warning(">>>>> Collecting path: %s" % finder_path)
        path_info_returns = find_path.get_folder_contents( finder_path, ignore_folder_list, seek_folder_list )
        path_info = { 'all_fields':{}, 'path_info_returns': path_info_returns }

        # initialize templates
        tk = sgtk.sgtk_from_path(path)

        for item in path_info_returns:
            if not ext:
                item['single'] = item['file_range'].split('-')[0] == item['file_range'].split('-')[-1]
            else:
                frame = re.search( r"(\d{3,10})%s$" % ext, path ).group(1)
                item['file_range'] = "%s-%s" % ( frame, frame )
                item['single'] = True

            frames = item['file_range'].split('-')

            # collect template and template fields
            tmp_path = ''
            work_template = None
            if item['single']:
                tmp_path = item['padded_file_name']
                full_path = re.sub( item['hash_padding'].replace('.', ''), frames[0], tmp_path )
                work_template = tk.template_from_path( tmp_path )

                item['full_path'] = full_path
            
            elif item.get('relative_path') in [None, "."]:
                tmp_path = item['padded_file_name']
                work_template = tk.template_from_path( tmp_path )

            else:
                tmp_path = os.path.join( path, item['relative_path'] )
                item['directory'] = tmp_path
                work_template = tk.template_from_path( tmp_path )

            item['base_template'] = work_template

            if item.get('base_template'):
                curr_fields = work_template.get_fields(tmp_path)
                item['fields'] = curr_fields

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

            # upadate all_info with any outstanding key:value pairs
            for key in item['fields'].keys():
                if not path_info['all_fields'].get(key):
                    path_info['all_fields'][key] = item['fields'][key]
                else:
                    pass

        # set pipeline root for Deadline processes
        script_file = "\\\\10.80.8.252\\VFX_Pipeline\\Pipeline\\ssvfx_scripts\\thinkbox\\draft\\draft_process_submit.py"
        path_info['all_fields']['script_file'] = script_file

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