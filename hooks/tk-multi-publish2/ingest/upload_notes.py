# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# in-built modules
import os
import re
import traceback
import copy

# external modules
from xml.dom import minidom

# package modules
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class UploadNotesPlugin(HookBaseClass):
    """
    Inherits from PublishFilesPlugin
    """

    @property
    def settings_schema(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default_value": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts
        as part of its environment configuration.
        """
        schema = super(UploadNotesPlugin, self).settings_schema

        ingest_schema = {
            "entity_identifiers": {
                "type": "dict",
                "values": {
                    "type": "dict",
                    "values": {
                        "type": "template",
                        "description": "",
                        "fields": ["context", "version", "[output]", "[name]", "*"]
                    },
                },
                "default_value": {},
                "description": (
                    "Dictionary of Identifier to figure out which type should be mapped how "
                    "If you use @key:relation@ it will just use that as a filter for querying the SG entity, "
                    "If you use #sg_field:relation:template# "
                    "it will resolve the value of the template from fields and use that value to query SG entity."
                    "If you use !template_for_fields:sg_field:relation:template_for_value! "
                    "it will resolve the fields that were derived using the first template and use these to generate value from second template to query SG entity."
                )
            },
            "ignored_identifiers": {
                "type": "dict",
                "values": {
                    "type": "list",
                    "values": {
                        "type": "str",
                        "description": "Strings to ignore when found for this key."
                    },
                },
                "default_value": {},
                "description": (
                    "Dictionary of Identifiers to ignore in the manifest's linked entities"
                    "for eg. 'name': ['cmp'] will ignore all values of name field that contain 'cmp' "
                )
            },
        }

        # add tags also to publish files
        schema["Item Type Settings"]["values"]["items"].update(ingest_schema)

        schema["Item Type Filters"]["default_value"] = ["notes.entity.*"]
        return schema

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        return """
        Plugin to process Client Notes, that come as a part of the manifest, after validating that the entities Notes,
        wants to link to exists. It will create a note entity and upload the attachments (if any).
        """

    def validate(self, task_settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param task_settings: Dictionary of settings
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        fields = item.properties.fields
        status = True

        entity_identifiers = task_settings.get("entity_identifiers").value
        ignored_identifiers = task_settings.get("ignored_identifiers").value
        # resolve the dicts in this list to SG entities.
        note_links = fields["note_links"]

        item.properties.resolved_linked_entities = list()

        for note_link in note_links:
            entity_type = note_link.get("type")

            ignored_list = list(set(note_link.keys()).intersection(ignored_identifiers.keys()))
            is_ignored = False
            ignored_value = None

            for ignored_key in ignored_list:
                value = note_link[ignored_key]
                ignored_values = ignored_identifiers[ignored_key]

                is_ignored = any(re.match(ignore_regex, value) for ignore_regex in ignored_values)

                if is_ignored:
                    ignored_value = value
                    break

            if entity_type in entity_identifiers and not is_ignored:
                identifier_mapping = entity_identifiers[entity_type]
                for key, value in identifier_mapping.iteritems():

                    # add project as default filter
                    entity_filter = [["project", "is", item.context.project]]

                    # key substitution match
                    key_substituion_match = re.match("%(\w+):(\w+)%", value)
                    # template value match
                    template_value_match = re.match("#(\w+):(\w+):(\w+)#", value)
                    # fields resolution and template value match
                    fields_resolution_template_value_match = re.match("!(\w+):(\w+):(\w+):(\w+)!", value)

                    if key_substituion_match:
                        groups = key_substituion_match.groups()
                        sg_field_name = groups[0]
                        relation = groups[1]

                        # construct the filter
                        field_filter = [sg_field_name, relation, note_link[key]]
                        entity_filter.append(field_filter)

                    if template_value_match:
                        groups = template_value_match.groups()
                        sg_field_name = groups[0]
                        relation = groups[1]
                        template_for_value = self.tank.templates[groups[2]]

                        # create a copy of fields for resolving this template
                        processed_fields = copy.deepcopy(fields)
                        processed_fields.update(item.context.as_template_fields(template_for_value))

                        # get the value of the template
                        template_value = template_for_value.apply_fields(processed_fields)

                        # construct the filter
                        field_filter = [sg_field_name, relation, template_value]
                        entity_filter.append(field_filter)

                    if fields_resolution_template_value_match:
                        groups = fields_resolution_template_value_match.groups()

                        template_for_fields = self.tank.templates[groups[0]]
                        sg_field_name = groups[1]
                        relation = groups[2]
                        template_for_value = self.tank.templates[groups[3]]

                        # get the fields from template
                        fields_from_template = template_for_fields.validate_and_get_fields(note_link[key])
                        processed_fields = copy.deepcopy(fields)
                        # let's keep our item fields first
                        processed_fields.update(item.context.as_template_fields(template_for_value))
                        # then the fields from template
                        processed_fields.update(fields_from_template)

                        # get the value of the template
                        template_value = template_for_value.apply_fields(processed_fields)

                        # construct the filter
                        field_filter = [sg_field_name, relation, template_value]
                        entity_filter.append(field_filter)

                    try:
                        queried_entity = self.tank.shotgun.find_one(entity_type, entity_filter)
                    except:
                        status = False
                        self.logger.error(
                            "Couldn't find %s entity" % entity_type,
                            extra={
                                "action_show_more_info": {
                                    "label": "Show Error",
                                    "tooltip": "Show Error while querying entity",
                                    "text": traceback.format_exc()
                                }
                            }
                        )
                        queried_entity = None

                    if queried_entity:
                        item.properties.resolved_linked_entities.append(queried_entity)
                    else:
                        status = False
                        self.logger.error(
                            "Couldn't find %s entity" % entity_type,
                            extra={
                                "action_show_more_info": {
                                    "label": "Show Filters",
                                    "tooltip": "Show Filters user for querying entity",
                                    "text": entity_filter
                                }
                            }
                        )

            elif is_ignored:
                status = True
                self.logger.warning(
                    "Ignoring the value of %s for %s entity." % (ignored_value, entity_type),
                    extra={
                        "action_show_more_info": {
                            "label": "Show Identifiers",
                            "tooltip": "Show Ignored identifiers",
                            "text": ignored_identifiers
                        }
                    }
                )

            else:
                status = False
                self.logger.error(
                    "Couldn't find %s in entity_identifiers." % entity_type,
                    extra={
                        "action_show_more_info": {
                            "label": "Show Identifiers",
                            "tooltip": "Show Entity identifiers",
                            "text": entity_identifiers
                        }
                    }
                )

        if status:
            self.logger.info(
                "Note entity will be created for %s" % item.name,
                extra={
                    "action_show_more_info": {
                        "label": "Show Entities",
                        "tooltip": "Show Resolved linked entities",
                        "text": item.properties.resolved_linked_entities
                    }
                }
            )

        return status

    def _upload_attachments(self, task_settings, item):
        """
        Uploads any generic file attachments to Shotgun, parenting
        them to the Note entity.

        :param task_settings:   The Note entity to attach the files to in SG.
        :param item:              A Shotgun API handle.
        """
        for file_path in item.properties.fields.get("attachments", []):
            if os.path.exists(file_path):
                self._upload_file(task_settings, item, file_path)
            else:
                self.logger.warning(
                    "File does not exist and will not be uploaded: %s" % file_path
                )

    def _upload_file(self, task_settings, item, file_path):
        """
        Uploads any generic file attachments to Shotgun, parenting
        them to the Note entity.

        :param task_settings:   The Note entity to attach the files to in SG.
        :param item:              A Shotgun API handle.
        :param file_path:       The path to the file to upload to SG.
        """
        self.logger.info(
            "Uploading attachments (%s bytes)..." % os.path.getsize(file_path)
        )
        # upload to the notes entity
        self.tank.shotgun.upload(item.properties.sg_note_data["type"],
                                 item.properties.sg_note_data["id"],
                                 str(file_path))
        self.logger.info("Upload complete!")

    def publish(self, task_settings, item):
        """
        Executes the publish logic for the given item and task_settings.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publisher = self.parent

        note_links = []
        note_tasks = []

        sg = self.tank.shotgun

        for entity_link in item.properties.resolved_linked_entities:

            if entity_link["type"] == "Version":
                # if we are adding a note to a version, link it with the version
                # and the entity that the version is linked to.
                # if the version has a task, link the task to the note too.
                sg_version = sg.find_one(
                    "Version",
                    [["id", "is", entity_link["id"]]],
                    ["entity", "sg_task", "cached_display_name", "project"]
                )

                # first make a sg link to the current entity - this to ensure we have a name key present
                note_links += [{"id": entity_link["id"],
                                "type": entity_link["type"],
                                "name": sg_version["cached_display_name"]}]

                # and now add the linked entity, if there is one
                if sg_version["entity"]:
                    note_links += [sg_version["entity"]]

                if sg_version["sg_task"]:
                    note_tasks += [sg_version["sg_task"]]

            elif entity_link["type"] == "Task":
                # if we are adding a note to a task, link the note to the entity that is linked to the
                # task. The link the task to the note via the task link.
                sg_task = sg.find_one(
                    "Task",
                    [["id", "is", entity_link["id"]]],
                    ["entity", "project"]
                )

                if sg_task["entity"]:
                    # there is an entity link from this task
                    note_links += [sg_task["entity"]]

                # lastly, link the note's task link to this task
                note_tasks += [entity_link]

            else:
                # no special logic. Just link the note to the current entity.
                # note that because we don't have the display name for the entity,
                # we need to retrieve this
                sg_entity = sg.find_one(entity_link["type"],
                                        [["id", "is", entity_link["id"]]],
                                        ["cached_display_name", "project"])
                note_links += [{"id": entity_link["id"],
                                "type": entity_link["type"],
                                "name": sg_entity["cached_display_name"]}]

        # this is an entity - so create a note and link it
        item.properties.sg_note_data = sg.create("Note", {"content": item.properties.fields["content"],
                                                          "subject": item.properties.fields["snapshot_name"],
                                                          "project": item.context.project,
                                                          "note_links": note_links,
                                                          "tasks": note_tasks,
                                                          "sg_note_type": "Client" if "sg_note_type" not in
                                                                                      item.properties.fields else
                                                          item.properties.fields["sg_note_type"]
                                                          })

        self._upload_attachments(task_settings, item)

    def finalize(self, task_settings, item):
        """
        Execute the finalization pass. This pass executes once
        all the publish tasks have completed, and can for example
        be used to version up files.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        if "sg_note_data" in item.properties:

            # get the data for the publish that was just created in SG
            sg_note_data = item.properties.sg_note_data

            self.logger.info(
                "Note created for: %s" % item.name,
                extra={
                    "action_show_in_shotgun": {
                        "label": "Show Note",
                        "tooltip": "Open the Note in Shotgun.",
                        "entity": sg_note_data
                    }
                }
            )
