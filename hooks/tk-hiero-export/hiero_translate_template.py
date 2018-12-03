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
import sgtk

import hiero.core
import hiero.ui

HookBaseClass = sgtk.get_hook_baseclass()


class HieroTranslateTemplate(HookBaseClass):
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
        # First add in any relevant fields from the context
        fields = self.parent.context.as_template_fields(template)
        # Substitute the variables that Hiero will inject during export
        hiero_fields = {
            "Sequence": "{sequence}",
            "Shot": "{shot}",
            "name": "{project}",
            "output": "{clip}",
            "width": "{width}",
            "height": "{height}",
            "version": "{tk_version}",
            "extension": "{ext}"
        }
        fields.update(hiero_fields)

        # Update field name from work_template in tk-multi-workfiles2 app
        workfiles_app = self.parent.engine.apps.get("tk-multi-workfiles2")
        if not workfiles_app:
            self.parent.logger.error("Unable to get the 'name' field. The tk-multi-workfiles2 app isn't loaded!")
        else:
            work_template = workfiles_app.get_work_template()

            # from selected project
            view = hiero.ui.activeView()
            if hasattr(view, 'selection'):
                selection = view.selection()

                if isinstance(view, hiero.ui.BinView):
                    item = selection[0]

                    # iterate until you get project
                    while hasattr(item, 'parentBin') and item != isinstance(item.parentBin(), hiero.core.Project):
                        item = item.parentBin()

                project_path = item.path()
                if not work_template.get_fields(project_path):
                    self.parent.logger.error("Unable to get the 'name' field. The selected Project '%s' does not match the work template '%s'" % (item.name(), str(work_template)))
                else:
                    tmpl_fields = work_template.get_fields(project_path)
                    if "name" in tmpl_fields:
                        fields["name"] = tmpl_fields["name"]

        for name, key in template.keys.iteritems():
            if isinstance(key, sgtk.templatekey.SequenceKey):
                fields[name] = "FORMAT:#"

        # simple string to string replacement
        # the nuke script name is hard coded to ensure a valid template
        if output_type == 'script':
            fields["output"] = "scene"

        # Nuke Studio project string has version number which is an issue when we have to resolve template by path
        # so replacing {name} with 'plate' string
        # and stripping {output} to simplify template to {Sequence}_{Shot}_{Step}_{name}.v{tk_version}.mov
        # engine specific template would have been useful here (as could update only for nuke studio)
        if output_type == "plate":
            fields["name"] = "plate"
            del fields['output']

        template_str = template.apply_fields(fields, ignore_types=hiero_fields.keys())

        return template_str
