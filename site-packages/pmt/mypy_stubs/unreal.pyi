class CineCameraActor(object):
    pass

class Vector(object):
    def __init__(self, x=0.0, y=0.0, z=0.0):
        pass

class Rotator(object):
    def __init__(self, roll=0.0, pitch=0.0, yaw=0.0):
        pass

def uclass():
    pass

class ShotBrowserUtility(object):
    pass

class Paths(object):
    def __init__(self, outer=None, name="None"):
        pass
    @staticmethod
    def combine(paths=[]) -> str:
        pass
    @staticmethod
    def engine_plugins_dir() -> str:
        pass

def ufunction(
    meta=None,
    ret=None,
    params=None,
    override=None,
    static=None,
    pure=None,
    getter=None,
    setter=None,
):
    pass

class UnrealWriterPythonAPI(object):
    @staticmethod
    def is_unreal_menu_item_loaded() -> bool:
        pass

def log_warning(str) -> None:
    pass