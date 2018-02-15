# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook which chooses an environment file to use based on the current context.

"""
import os

import sgtk
from tank.templatekey import StringKey

HookBaseClass = sgtk.get_hook_baseclass()

EDIT_TYPE_KEY = "edit_type"
EDITS_KEY = "edits"
VALID_EDITS = ["replace", "lower_case", "upper_case", "underscore_to_camelcase"]


class TemplateKeyCustom(HookBaseClass):

    def validate(self, value, validate_transforms, **kwargs):
        """
        Test if a value is valid for this key

        :param value: Value to test
        :param validate_transforms: Bool to enable validation of transforms,
                                    such as a subset calculation
        :returns: Bool
        """
        return  self.parent._validate(value, validate_transforms)

    @staticmethod
    def _underscore_to_camelcase(value):
        def camelcase():
            yield str.lower
            while True:
                yield str.capitalize

        c = camelcase()
        return "".join(c.next()(x) if x else '_' for x in value.split("_"))

    def value_from_str(self, str_value, **kwargs):
        """
        Translates a string into an appropriate value for this key.

        If the EDIT_TYPE_KEY(edit_type) in the TemplateKey is valid, it will apply the required "edit" on str_value.
        You can also define a set of EDITS_KEY(edits) in the TemplateKey.
        eg. use "edits" to store the replacement mapping for "replace" type "edit".

        :param str_value: The string to translate.
        :returns: The translated value.
        """
        choices = kwargs
        if isinstance(self.parent, StringKey):
            edits = dict()
            edit = None

            if EDITS_KEY in choices:
                edits = choices[EDITS_KEY]

            if EDIT_TYPE_KEY in choices:
                edit = choices[EDIT_TYPE_KEY]

            # removed "pad" type edit, since that is already taken care of by 'format_spec'
            if edit in VALID_EDITS:
                if edit == "replace":
                    if edits:
                        relevant_replaces = [replace for replace in edits if replace in str_value]
                        for replace in relevant_replaces:
                            str_value = str_value.replace(replace, edits[replace])
                elif edit == "lower_case":
                    str_value = str_value.lower()
                elif edit == "upper_case":
                    str_value = str_value.upper()
                elif edit == "underscore_to_camelcase":
                    str_value = self._underscore_to_camelcase(str_value)

        return str_value

    def str_from_value(self, value, **kwargs):
        """
        Converts a value into properly formatted string for this key.

        :param value: An object that will be converted to a string according to the
                      format specification.

        :returns: A string representing the formatted value.
        """

        return self.parent._as_string(value)
