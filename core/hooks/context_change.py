# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
This hook gets executed before and after the context changes in Toolkit.
"""
import os
from tank import get_hook_baseclass


def resolve_template(context, template, fields=None):
    """Resolves sgtk templates.

    Uses the current context to resolve an sgtk template.

    :param str template: template name defined in templates.yml
    :param dict fields: extra fields that cannot be resolved by context alone.
    :return: A resolved sgtk template
    :rtype: str
    """
    tmpl = context.sgtk.templates[template]
    flds = context.as_template_fields(tmpl)

    if fields is not None:
        flds.update(flds)

    return tmpl.apply_fields(flds)


def first_file(path):
    """Returns the first file found in the given.

    Returns the first file found in the given path. Useful if you're only
    expecting to find one file.

    :param str path: The directory to search.
    :return: The full path to the found file.
    :rtype: str
    """
    try:
        file = next(os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)))
        return file
    except StopIteration:
        return None


def shot_cc_file(context):
    try:
        lut_area = resolve_template(context, "lut_shot")
        lut_file = first_file(lut_area)
        return lut_file
    except:
        return None


def sequence_cc_file(context):
    try:
        lut_area = resolve_template(context, "lut_seq")
        lut_file = first_file(lut_area)
        return lut_file
    except:
        return None


def project_cc_file(context):
    try:
        lut_area = resolve_template(context, "lut_root")
        lut_file = first_file(lut_area)
        return lut_file
    except:
        return None


class ContextChange(get_hook_baseclass()):
    """
    - If an engine **starts up**, the ``current_context`` passed to the hook
      methods will be ``None`` and the ``next_context`` parameter will be set
      to the context that the engine is starting in.

    - If an engine is being **reloaded**, in the context of an engine restart
      for example, the ``current_context`` and ``next_context`` will usually be
      the same.

    - If a **context switch** is requested, for example when a user switches
      from project to shot mode in Nuke Studio, ``current_context`` and ``next_context``
      will contain two different context.

    .. note::

       These hooks are called whenever the context is being set in Toolkit. It is
       possible that the new context will be the same as the old context. If
       you want to trigger some behavior only when the new one is different
       from the old one, you'll need to compare the two arguments using the
       ``!=`` operator.
    """

    def pre_context_change(self, current_context, next_context):
        """
        Executed before the context has changed.

        The default implementation does nothing.

        :param current_context: The context of the engine.
        :type current_context: :class:`~sgtk.Context`
        :param next_context: The context the engine is switching to.
        :type next_context: :class:`~sgtk.Context`
        """
        pass

    def post_context_change(self, previous_context, current_context):
        """
        Executed after the context has changed.

        The default implementation does nothing.

        :param previous_context: The previous context of the engine.
        :type previous_context: :class:`~sgtk.Context`
        :param current_context: The current context of the engine.
        :type current_context: :class:`~sgtk.Context`
        """
        if previous_context != current_context:

            self.logger.debug("Current self.parent is: {}".format(self.parent))

            if current_context:
                env_vars = {
                    "PROJECT": None,
                    "SHOT": None,
                    "SEQUENCE": None,
                    "PROJECT_CC": None,
                    "SHOT_CC": None,
                    "SEQUENCE_CC": None
                }

                if current_context.project:
                    id = current_context.project['id']
                    self.logger.debug("Current context project id: {}".format(id))
                    entity = current_context.sgtk.shotgun.find_one('Project', [['id', 'is', id]], ['code'])
                    self.logger.debug("Current context project entity: {}".format(entity))
                    env_vars["PROJECT"] = entity['code']
                    self.logger.debug("Set env var PROJECT = {}".format(entity['code']))
                    env_vars["PROJECT_CC"] = project_cc_file(current_context)
                    self.logger.debug("Set env var PROJECT_CC = {}".format(project_cc_file(current_context)))

                if current_context.entity:
                    type = current_context.entity['type']
                    id = current_context.entity['id']
                    entity = current_context.sgtk.shotgun.find_one(type, [['id', 'is', id]], ['code', 'sg_sequence'])
                    if type == "Shot" or type == "Sequence":
                        env_vars["SEQUENCE"] = entity.get('sg_sequence').get('name')
                        env_vars["SEQUENCE_CC"] = sequence_cc_file(current_context)
                    if type == "Shot":
                        env_vars["SHOT"] = entity.get("code")
                        env_vars["SHOT_CC"] = shot_cc_file(current_context)

                for key, value in env_vars.iteritems():
                    if not value:
                        if os.environ.get(key):
                            os.environ.pop(key)
                    else:
                        os.environ[key] = value
