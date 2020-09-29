# Netherlands Film Academy - Nuke Shotgun project plugins (init.py)
# Initialize message
print("Project config loaded")

# Project_Repository
dirname = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.join(dirname, 'project_repo')
project_dir_win = project_dir.replace(os.sep, '/')

nuke.pluginAddPath(project_dir_win)
