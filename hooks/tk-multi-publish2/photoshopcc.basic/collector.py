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
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class PhotoshopCCSceneCollector(HookBaseClass):
    """
    Collector that operates on the photoshop cc active document. Should inherit
    from the basic collector.
    """

    def process_current_session(self, parent_item):
        """
        Analyzes the open documents in Photoshop and creates publish items
        parented under the supplied item.

        :param parent_item: Root item instance
        """

        # go ahead and build the path to the icon for use by any documents
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "photoshop.png"
        )

        engine = self.parent.engine

        # get the active document name
        try:
            active_doc_name = engine.adobe.app.activeDocument.name
        except RuntimeError:
            engine.logger.debug("No active document found.")
            active_doc_name = None

        # iterate over all open documents and add them as publish items
        for document in engine.adobe.app.documents:

            # create a publish item for the document
            document_item = parent_item.create_item(
                "photoshop.document",
                "Photoshop Image",
                document.name
            )

            document_item.set_icon_from_path(icon_path)

            # disable thumbnail creation for photoshop documents. for the
            # default workflow, the thumbnail will be auto-updated after the
            # version creation plugin runs
            document_item.thumbnail_enabled = False

            # add the document object to the properties so that the publish
            # plugins know which open document to associate with this item
            document_item.properties["document"] = document

            doc_name = document.name

            self.logger.info("Collected Photoshop document: %s" % (doc_name))

            # enable the active document and expand it. other documents are
            # collapsed and disabled.
            if active_doc_name and doc_name == active_doc_name:
                document_item.expanded = True
                document_item.checked = True
            elif active_doc_name:
                # there is an active document, but this isn't it. collapse and
                # disable this item
                document_item.expanded = False
                document_item.checked = False

            path = _document_path(document)

            if path:
                # try to set the thumbnail for display. won't display anything
                # for psd/psb, but others should work.
                document_item.set_thumbnail_from_path(path)



def _document_path(document):
    """
    Returns the path on disk to the supplied document. May be ``None`` if the
    document has not been saved.
    """

    try:
        path = document.fullName.fsName
    except RuntimeError:
        path = None

    return path