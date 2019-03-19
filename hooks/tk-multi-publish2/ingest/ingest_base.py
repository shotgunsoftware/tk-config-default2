# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.


import traceback
import pprint

import sgtk


HookBaseClass = sgtk.get_hook_baseclass()


class IngestBasePlugin(HookBaseClass):
    """
    Base Ingest Plugin
    """

    def _create_vendor_task(self, item, step_entity):
        """
        Creates a Vendor Task for the Entity represented by the Context.

        :param item: Item to get the context from.
        :param step_entity: Step entity to create Task against.
        """

        # construct the data for the new Task entity
        data = {
            "step": step_entity,
            "project": item.context.project,
            "entity": item.context.entity if item.context.entity else item.context.project,
            "content": "Vendor"
        }

        # create the task
        sg_result = self.sgtk.shotgun.create("Task", data)
        if not sg_result:
            self.logger.error("Failed to create new task - reason unknown!")
        else:
            self.logger.info("Created a Vendor Task.", extra={
                        "action_show_more_info": {
                            "label": "Show Task",
                            "tooltip": "Show the existing Task in Shotgun",
                            "text": "Task Entity: %s" % pprint.pformat(sg_result)
                        }
                    }
                )

    def validate(self, task_settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param task_settings: Dictionary of settings
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        # Run the context validations first.
        if not item.context.entity:
            self.logger.error("Ingestion at project level is not allowed! Please Contact TDs.")
            return False
        # context check needs to run before the other validations do.
        if not item.context.step:
            # Item doesn't contain a step entity! Intimate the user to create one, if they want to ingest.
            sg_filters = [
                ['short_name', 'is', "vendor"]
            ]

            # make sure we get the correct Step!
            # this should handle whether the Step is from Sequence/Shot/Asset
            sg_filters.append(["entity_type", "is", item.context.entity["type"]])

            fields = ['entity_type', 'code', 'id']

            # add a vendor step to all ingested files
            step_entity = self.sgtk.shotgun.find_one(
                entity_type='Step',
                filters=sg_filters,
                fields=fields
            )

            if not step_entity:
                self.logger.error("Step Entity doesn't exist. Please contact your TDs.",
                                  extra={
                                        "action_show_more_info": {
                                            "label": "Show Filters",
                                            "tooltip": "Show the filters used to query the Step.",
                                            "text": "SG Filters: %s\n"
                                                    "Fields: %s" % (pprint.pformat(sg_filters), pprint.pformat(fields))
                                        }
                                    })

                return False

            task_filters = [
                ['step', 'is', step_entity],
                ['entity', 'is', item.context.entity],
                ['content', 'is', 'Vendor']
            ]

            task_fields = ['content', 'step', 'entity']

            task_entity = self.sgtk.shotgun.find_one(
                entity_type='Task',
                filters=task_filters,
                fields=task_fields
            )

            if task_entity:
                self.logger.warning(
                    "Vendor task already exists! Please select that task.",
                    extra={
                        "action_show_more_info": {
                            "label": "Show Task",
                            "tooltip": "Show the existing Task in Shotgun",
                            "text": "Task Entity: %s" % pprint.pformat(task_entity)
                        }
                    }
                )
            else:
                self.logger.error(
                    "Item doesn't have a valid Step.",
                    extra={
                        "action_button": {
                            "label": "Crt Vendor Task",
                            "tooltip": "Creates a Vendor Task on the Entity represented by the Context.",
                            "callback": lambda: self._create_vendor_task(item, step_entity)
                        }
                    }
                )

            return False

        # rest of the validations run after the context is verified.
        status = super(IngestBasePlugin, self).validate(task_settings, item)

        return status
