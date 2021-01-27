# UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.
import sequence_utility
import unreal

if unreal.UnrealWriterPythonAPI.is_unreal_menu_item_loaded():
    import imgspc
    import scripts.script_to_UE

    # Creating toolbar button and menu using the Python Toolbar Button and Menu Creator plugin
    try:
        imgspc.make_menu_item(
            "ImgSpc", icon_path="UnrealWriter/Resources/imgspc-logo-toolbar.png"
        )
        imgspc.make_menu_item(
            "ImgSpc/Convert Script text file to Sequence",
            callback="scripts.script_to_UE.main()",
            tooltip="Convert a script text file to sequencer assets",
        )
    except Exception as e:
        unreal.log_warning(type(e))
        unreal.log_warning(e.args)
