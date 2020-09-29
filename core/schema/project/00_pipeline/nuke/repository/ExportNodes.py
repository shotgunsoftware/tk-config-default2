import nuke
import nukescripts
import os


def main():
    # Getting current location
    dirname = os.path.dirname(os.path.abspath(__file__))

    # Saving selected nodes for export
    selection = nuke.selectedNodes()
    if selection == []:
        nuke.message("There are no nodes selected.")
    else:

        # Creating Template creation menu
        class TemplateCreation(nukescripts.PythonPanel):
            def __init__(self, node):

                nukescripts.PythonPanel.__init__(self, 'Template creation')
                self.tcNode = node
                self.typeKnob = nuke.Enumeration_Knob('exporttype', 'Export selected node(s) as', ['Node', 'Template'])
                self.elementKnob = nuke.String_Knob('expname', 'Name')
                for k in (self.typeKnob, self.elementKnob):
                    self.addKnob(k)

        # Activating menu
        tc = TemplateCreation(selection)
        if tc.showModalDialog():
            # Getting values from menu
            exptype = tc.typeKnob.value()
            expname = tc.elementKnob.value()

            if expname == '':
                nuke.message('There was no name specified.')
            else:
                # Template export settings
                if exptype == 'Template':
                    # Creating export paths
                    expfile = expname + '.nk'
                    exploc = os.path.join(dirname, "project_repo","Templates", expfile)

                    # Fixing windows slashes functionality
                    exploc_win = exploc.replace(os.sep, '/')

                    # Exporting as Nuke file
                    try:
                        nuke.nodeCopy(exploc_win)

                        # Creating menu to add recent created node
                        toolbar = nuke.toolbar("Nodes")
                        prj_repo = toolbar.addMenu("Project repository", icon ="project_repository.png")

                        # Creating command to import node when artist asks
                        prj_repo.addCommand("Templates/" + expname,"nuke.nodePaste(" + "\"" + exploc_win + "\")")

                        # Giving artist success message
                        nuke.message("Exporting " + expname + " as template was successful.")

                    except:
                        nuke.message("An exception occurred")
                # Node export settings
                if exptype == 'Node':
                    # Creating export paths
                    expfile = expname + '.nk'
                    exploc = os.path.join(dirname, "project_repo", "Nodes", expfile)

                    # Fixing windows slashes functionality
                    exploc_win = exploc.replace(os.sep, '/')

                    # Exporting as Nuke file
                    try:
                        nuke.nodeCopy(exploc_win)

                        # Creating menu to add recent created node
                        toolbar = nuke.toolbar("Nodes")
                        prj_repo = toolbar.addMenu("Project repository", icon ="project_repository.png")

                        # Creating command to import node when artist asks
                        prj_repo.addCommand("Nodes/" + expname,"nuke.nodePaste(" + "\"" + exploc_win + "\")")

                        # Giving artist success message
                        nuke.message("Exporting " + expname + " as node was successful.")

                    except:
                        nuke.message("An exception occurred")
