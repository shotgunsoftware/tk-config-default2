# Copyright (c) 2021 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# the path to output all built .py files to
$UI_PYTHON_PATH="../python/tk_multi_progress/ui"

# the paths to where the PySide binaries are installed
$PYTHON_UIC="B:/Softwares/Autodesk/Shotgun/Python/Scripts/pyside-uic.exe"
$PYTHON_RCC="B:/Softwares/Autodesk/Shotgun-1.5.9/Python/Lib/site-packages/PySide/pyside-rcc.exe"

function Build-Ui {

    Param($name)

    echo " > Building interface for $name"
    $dst = resolve-path(Join-Path ($PSScriptRoot) $UI_PYTHON_PATH)
    $cmd = "& '$PYTHON_UIC' --from-imports '$PSScriptRoot\$name.ui' > '$dst\$name.py'"
    Invoke-Expression $cmd

    (Get-Content "$dst\$name.py").replace("from PySide import", "from sgtk.platform.qt import") | Set-Content "$dst\$name.py"

}

function Build-Rcc {

    Param($name)

    echo " > Building resources for $name"
    $dst = resolve-path(Join-Path ($PSScriptRoot) $UI_PYTHON_PATH)
    $cmd = "& '$PYTHON_RCC' -py3 '$PSScriptRoot\$name.qrc' > '$dst\$($name)_rc.py'"
    Invoke-Expression $cmd

    (Get-Content "$dst\$($name)_rc.py").replace("from PySide import", "from sgtk.platform.qt import") | Set-Content "$dst\$($name)_rc.py"

}

# build UI's
echo "building user interfaces..."
Build-Ui("dialog")

# build resources
echo "building resources..."
Build-Rcc("resources")
