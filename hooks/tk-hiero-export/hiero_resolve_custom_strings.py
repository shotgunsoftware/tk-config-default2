# Copyright (c) 2014 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from tank import Hook
import hiero


class HieroResolveCustomStrings(Hook):
    """
    This class implements a hook that is used to resolve custom tokens into
    their concrete value when paths are being processed during the export.
    """
    RESOLUTION_TOKEN_NAMES = ("width", "height")

    # Cache of shots that have already been pulled from shotgun
    _sg_lookup_cache = {}

    def execute(self, task, keyword, **kwargs):
        """
        The default implementation of the custom resolver simply looks up
        the keyword from the Shotgun Shot entity dictionary. For example,
        to pull the shot code, you would simply specify 'code'. To pull
        the sequence code you would use 'sg_sequence.Sequence.code'.

        :param task: The export task being processed.
        :param str keyword: The keyword token that needs to be resolved.

        :returns: The resolved keyword value to be replaced into the
            associated string.
        :rtype: str
        """
        # strip off the leading and trailing curly brackets
        keyword = keyword[1:-1]

        self.parent.log_debug("Attempting to resolve custom keyword: %s" % keyword)
        if keyword in self.RESOLUTION_TOKEN_NAMES:
            result = getattr(self, "get_{}".format(keyword))(task)
            self.parent.log_debug("Custom resolver: %s -> %s" % (keyword, result))

        else:
            shot_code = task._item.name()

            # grab the shot from the cache, or the get_shot hook if not cached
            sg_shot = self._sg_lookup_cache.get(shot_code)
            if sg_shot is None:
                fields = [ctf['keyword'] for ctf in self.parent.get_setting('custom_template_fields')]
                sg_shot = self.parent.execute_hook(
                    "hook_get_shot",
                    task=task,
                    item=task._item,
                    data=self.parent.preprocess_data,
                    fields=fields,
                    upload_thumbnail=False,
                )

                self._sg_lookup_cache[shot_code] = sg_shot

            if sg_shot is None:
                raise RuntimeError("Could not find shot for custom resolver: %s" % keyword)

            result = sg_shot.get(keyword, "")
            self.parent.log_debug("Custom resolver: %s[%s] -> %s" % (shot_code, keyword, result))

        return result

    def get_height(self, task):
        """
        """
        # First check if a reformat has been defined
        if "reformat" in task._preset.properties():
            if "height" in task._preset.properties()["reformat"]:
                return task._preset.properties()["reformat"]["height"]

        # Next check if there is a sequence format definition
        if isinstance(task._item, hiero.core.Sequence):
            return task._sequence.format().height()

        # Else get the source height
        return task._source.height()

    def get_width(self, task):
        """
        """
        # First check if a reformat has been defined
        if "reformat" in task._preset.properties():
            if "width" in task._preset.properties()["reformat"]:
                return task._preset.properties()["reformat"]["width"]

        # Next check if there is a sequence format definition
        if isinstance(task._item, hiero.core.Sequence):
            return task._sequence.format().width()

        # Else get the source width
        return task._source.width()
