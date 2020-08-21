# Netherlands Film Academy - Nuke standard plugins (init.py)
# Initialize message
print("Project config loaded")

# NFA_Repository
dirname = os.path.dirname(os.path.abspath(__file__))
nuke.pluginAddPath(os.path.join(dirname, 'project_repo'))
