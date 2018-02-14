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
import copy

import sgtk
from tank.templatekey import StringKey

HookBaseClass = sgtk.get_hook_baseclass()

EDIT_TYPE = "EDIT"
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
        # since use-case of name_converter is only for modifying StringKey, copying the validations that StringKey does.
        if isinstance(self.parent, StringKey):
            return self._validate(value, validate_transforms)
        else:
            return self.parent._validate(value, validate_transforms)

    def _validate(self, value, validate_transforms, **kwargs):
        """
        Test if a value is valid for this key

        :param value: Value to test
        :param validate_transforms: Bool to enable validation of transforms,
                                    such as a subset calculation
        :returns: Bool
        """
        u_value = value
        if not isinstance(u_value, unicode):
            # handle non-ascii characters correctly by
            # decoding to unicode assuming utf-8 encoding
            u_value = value.decode("utf-8")

        if self.parent._filter_regex_u:
            # first check our std filters. These filters are negated
            # so here we are checking that there are occurances of
            # that pattern in the string
            if self.parent._filter_regex_u.search(u_value):
                self.parent._last_error = "%s Illegal value '%s' does not fit filter_by '%s'" % (self.parent, value,
                                                                                                 self.parent.filter_by)
                return False

        elif self.parent._custom_regex_u:
            # check for any user specified regexes
            if self.parent._custom_regex_u.match(u_value) is None:
                self.parent._last_error = "%s Illegal value '%s' does not fit filter_by '%s'" % (self.parent, value,
                                                                                                 self.parent.filter_by)
                return False

        # check subset regex
        if self.parent._subset_regex and validate_transforms:
            regex_match = self.parent._subset_regex.match(u_value)
            if regex_match is None:
                self.parent._last_error = "%s Illegal value '%s' does not fit " \
                                          "subset expression '%s'" % (self.parent, value, self.parent.subset)
                return False

            # validate that the formatting can be applied to the input value
            if self.parent._subset_format:
                try:
                    # perform the formatting in unicode space to cover all cases
                    self.parent._subset_format.decode("utf-8").format(*regex_match.groups())
                except Exception as e:
                    self.parent._last_error = "%s Illegal value '%s' does not fit subset '%s' with format '%s': %s" % (
                        self.parent,
                        value,
                        self.parent.subset,
                        self.parent.subset_format,
                        e
                    )
                    return False

        str_value = value if isinstance(value, basestring) else str(value)

        # We are not case sensitive
        if str_value.lower() in [str(x).lower() for x in self.parent.exclusions]:
            self.parent._last_error = "%s Illegal value: %s is forbidden for this key." % (self.parent, value)
            return False

        # to avoid the validation to fail, if the value is not defined in choices!!
        # if value is not None and self.choices:
        #     if str_value.lower() not in [str(x).lower() for x in self.choices]:
        #         self._last_error = "%s Illegal value: '%s' not in choices: %s" % (self, value, str(self.choices))
        #         return False

        if self.parent.length is not None and len(str_value) != self.parent.length:
            self.parent._last_error = ("%s Illegal value: '%s' does not have a length of "
                                       "%d characters." % (self.parent, value, self.parent.length))
            return False

        return True

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

        If the EDIT_TYPE in the choices of this template is a valid, it will apply the required "edit" on str_value.

        :param str_value: The string to translate.
        :returns: The translated value.
        """

        if isinstance(self.parent, StringKey):
            choices = copy.deepcopy(self.parent.labelled_choices)
            edit = choices.pop(EDIT_TYPE)

            # removed "pad" type edit, since that is already taken care of by 'format_spec'

            if edit in VALID_EDITS:
                if edit == "replace":
                    relevant_replaces = [replace for replace in choices if replace in str_value]
                    for replace in relevant_replaces:
                        str_value = str_value.replace(replace, choices[replace])
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
