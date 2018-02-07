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
from tank.util.shotgun import get_sg_connection

HookBaseClass = sgtk.get_hook_baseclass()

class TemplateKeyCustom(HookBaseClass):

    def validate(self, value, validate_transforms, **kwargs):
        """
        Test if a value is valid for this key

        :param value: Value to test
        :param validate_transforms: Bool to enable validation of transforms,
                                    such as a subset calculation
        :returns: Bool
        """
        return self.parent._validate(value, validate_transforms)

    def value_from_str(self, str_value, **kwargs):
        """
        Translates a string into an appropriate value for this key.

        If the queried field name is sg_client_name, this will return the corresponding DD name(code).
        If the queried field name is code, this will return the corresponding Client name(sg_client_name).

        :param str_value: The string to translate.
        :returns: The translated value.
        """

        keys = set(["code", "sg_client_name"])
        return_key = keys.difference([self.parent.shotgun_field_name]).pop()

        sg = get_sg_connection()

        proj_filter = sg.find_one(entity_type='Project', filters=[['name', 'is', os.getenv('DD_SHOW')]])
        filters = [['project', 'is', proj_filter], [self.parent.shotgun_field_name, "is", str_value]]

        return_entity = sg.find_one(self.parent.shotgun_entity_type, filters, [return_key])

        return return_entity[return_key]

    def str_from_value(self, value, **kwargs):
        """
        Converts a value into properly formatted string for this key.

        :param value: An object that will be converted to a string according to the
                      format specification.

        :returns: A string representing the formatted value.
        """
        return self.parent._as_string(value)
