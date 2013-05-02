"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

Hook which chooses an environment file to use based on the current context.

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
        
        if context.entity is None:
            # we have a project but not an entity
            return "project"
        
        if context.entity and context.step is None:
            # we have an entity but no step!
            # this is convered by a single environment
            return "shot_and_asset"
            
        if context.entity and context.step:
            # we have a step and an entity
            if context.entity["type"] == "Shot":
                return "shot_step"
            if context.entity["type"] == "Asset":
                return "asset_step"            

        return None
