# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import ast

from tank import Hook
import tank.templatekey


class HieroTranslateTemplate(Hook):
    """
    This class implements a hook that's responsible for translating a Toolkit
    template object into a Hiero export string.
    """
    def execute(self, template, output_type, **kwargs):
        """
        Takes a Toolkit template object as input and returns a string
        representation which is suitable for Hiero exports. The Hiero export
        templates contain tokens, such as {shot} or {clip}, which are replaced
        by the exporter. This hook should convert a template object with its
        special custom fields into such a string. Depending on your template
        setup, you may have to do different steps here in order to fully
        convert your template. The path returned will be validated to check
        that no leftover template fields are present, and that the returned
        path is fully understood by Hiero.

        :param template: The Toolkit template object to be translated.
        :param str output_type: The output type associated with the template.

        :returns: A Hiero-compatible path.
        :rtype: str
        """
        # first convert basic fields
        mapping = {
            "{Sequence}": "{sequence}",
            "{Shot}": "{shot}",
            "{name}": "{project}",
            "{output}": "{clip}",
            "{version}": "{tk_version}",
            "{extension}": "{ext}"
        }

        # see if we have a value to use for Step
        try:
            task_filter = self.parent.get_setting("default_task_filter", "[]")
            task_filter = ast.literal_eval(task_filter)
            for (field, op, value) in task_filter:
                if field == "step.Step.short_name":
                    mapping["{Step}"] = value
        except ValueError:
            # continue without Step
            self.parent.log_error("Invalid value for 'default_task_filter'")

        # get the string representation of the template object
        template_str = template.definition

        # simple string to string replacement
        # the nuke script name is hard coded to ensure a valid template
        if output_type == 'script':
            template_str = template_str.replace('{output}', 'scene')

        for (orig, repl) in mapping.iteritems():
            template_str = template_str.replace(orig, repl)

        # replace {SEQ} style keys with their translated string value
        for (name, key) in template.keys.iteritems():
            if isinstance(key, tank.templatekey.SequenceKey):
                # this is a sequence template, for example {SEQ}
                # replace it with ####
                template_str = template_str.replace("{%s}" % name, key.str_from_value("FORMAT:#"))

        return template_str
