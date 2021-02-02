"""
This script asks the user for an Unreal Engine Project location.
It then copies the Imaginary Spaces UE plug-ins to the project, in the right 
location
"""
import os
from PySide.QtGui import QApplication, QFileDialog, QMessageBox
import shutil


_PLUGINS_TO_COPY = [
    "site-packages/pmt/writers/UnrealWriter",
    "site-packages/UnrealMenuItem",
]

# Mandatory Application
app = QApplication("")

# options for either browse type
options = [
    QFileDialog.DontResolveSymlinks,
    QFileDialog.DontUseNativeDialog,
    QFileDialog.ShowDirsOnly,
]

# browse folders specifics
caption = "Select an Unreal Engine Project Directory"
file_mode = QFileDialog.Directory

# create the dialog
file_dialog = QFileDialog(
    parent=QApplication.instance().activeWindow(), caption=caption
)
file_dialog.setLabelText(QFileDialog.Accept, "Select")
file_dialog.setLabelText(QFileDialog.Reject, "Cancel")
file_dialog.setFileMode(file_mode)

# set the appropriate options
for option in options:
    file_dialog.setOption(option)

# browse!
if file_dialog.exec_():
    ue_project_dir = file_dialog.selectedFiles()[0]
    plugins_dir = os.path.join(ue_project_dir, "Plugins")
    plugins_dir = os.path.normpath(plugins_dir)

    # Create the Plugins directory
    try:
        os.mkdir(plugins_dir)
    except OSError:
        # Directory already exists
        pass

    config_path = os.environ["TK_CONFIG_PATH"]

    for plugin_path in _PLUGINS_TO_COPY:
        src = os.path.join(config_path, plugin_path)
        src = os.path.normpath(src)

        plugin_name = os.path.split(plugin_path)[-1]

        dst = os.path.join(plugins_dir, plugin_name)
        if os.path.exists(dst):
            # Should we overwrite?
            reply = QMessageBox.question(
                None,
                "Warning",
                "The {} plugin already exists in your Unreal Engine Project "
                "({}). Do you want to overwrite it?".format(
                    plugin_name, ue_project_dir
                ),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                shutil.rmtree(dst)
            else:
                exit(0)

        shutil.copytree(src, dst)
