"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

Hook which chooses an environment file to use based on the current context.
This file is almost always overridden by a standard config.

"""

from tank import Hook

class PickEnvironment(Hook):

    def execute(self, context, **kwargs):
        """
        The default implementation assumes there are three environments, called shot, asset 
        and project, and switches to these based on entity type.
        """
        
        if context.project is None:
            # our context is completely empty! 
            # don't know how to handle this case.
            return None
        
        if context.project and context.entity is None:
            # project-only context
            return "project"
        elif context.entity["type"] == "Shot":
            return "shot"
        elif context.entity["type"] == "Asset":
            return "asset"

        return None
