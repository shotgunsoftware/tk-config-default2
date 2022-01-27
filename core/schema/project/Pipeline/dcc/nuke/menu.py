###### Project specific settings
# SG Nuke will include this file as part of the startup process
# Change settings as required as per the Projects specs
# Update the  project_icon24x24.pngto a Project specific icon
m = nuke.menu('Nodes')
eggMenu = m.addMenu('ProjectTools', icon='project_icon24x24.png')

# Add any project based commands here
eggMenu.addCommand('Shots/Shot tool', 'print("Shot tool")', '', icon='', index=1, shortcutContext=2)
