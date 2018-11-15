from dd.runtime import api
api.load('openimageio')

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

# Stub class to allow api.load of openimageio package
class FileDDCollectorPlugin(HookBaseClass):
    pass
