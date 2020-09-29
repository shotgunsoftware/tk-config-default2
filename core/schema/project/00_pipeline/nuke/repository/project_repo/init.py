"""spin tools nuke startup module.

recursively adds all subfolders to plugin path.
"""

# python
import os

# nuke
import nuke

curdir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.join(dirname, 'project_repo')
project_dir_win = project_dir.replace(os.sep, '/')

for root, dirs, files in os.walk(project_dir_win):
    nuke.pluginAddPath(root)
