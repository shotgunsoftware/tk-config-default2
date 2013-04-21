"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

The after_project_create file is executed as part of creating a new project.
If your starter config needs to create any data in shotgun or do any other
special configuration, you can add it to this file.

The create() method will be executed as part of the setup and is passed
the following keyword arguments:

* sg -         A shotgun connection
* project_id - The shotgun project id that is being setup
* log -        A logger instance to which progress can be reported via
               standard logger methods (info, warning, error etc)

"""

def create(sg, project_id, log, **kwargs):
    """
    Insert post-project code here
    """
    # the default config does not require any post-session stuff.
    pass

