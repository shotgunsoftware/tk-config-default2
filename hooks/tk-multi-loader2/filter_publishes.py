# Copyright (c) 2015 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os,sys

import sgtk
from sgtk import Hook

class FilterPublishes(Hook):
    """
    Hook that can be used to filter the list of publishes returned from Shotgun for the current
    location
    """
    
    def execute(self, publishes, **kwargs):
        """
        Main hook entry point
        
        :param publishes:    List of dictionaries 
                             A list of  dictionaries for the current location within the app.  Each
                             item in the list is a Dictionary of the form:
                             
                             {
                                 "sg_publish" : {Shotgun entity dictionary for a Published File entity}
                             }
                             
                                                         
        :return List:        The filtered list of dictionaries of the same form as the input 'publishes' 
                             list
        """
        app = self.parent

        eng = sgtk.platform.current_engine()

        # test for current engine
        if eng.name == "tk-nuke":
            import nuke

            # list that contains all items that pass the filters
            revised_publishes = []
            # filter out non-complete, non-final versions and 3D Render publishes
            for item in publishes:
                try:
                    # 3d publishes
                    if item['sg_publish']['published_file_type']['id'] == 4:
                        if (item['sg_publish']['version'] == None 
                            and item['sg_publish']['sg_status_list'] == "cmpt"):

                                revised_publishes.append(item)

                        elif (item['sg_publish']['sg_status_list'] == "lwv" 
                                and (item['sg_publish']['version.Version.sg_status_list'] == "fin" or
                                item['sg_publish']['version.Version.sg_status_list'] == "rfc" )):

                                revised_publishes.append(item)
                        else:
                            pass
                    elif item['sg_publish']['sg_status_list'] == "efl":
                        nuke.tprint("Excluding %s from loader. Based on Publish File status." %(item['sg_publish']['code']))
                        pass
                    else:
                        revised_publishes.append(item)
                except:
                    # Published File needs Published File Type! Don't Add
                    pass
            
            # final decision on what to submit to the loader
            return self.compare_publish_lists(publishes, revised_publishes)

        elif eng.name == "tk-maya":

            # list that contains all items that pass the filters
            revised_publishes = []

            # filter out non-complete, non-final versions and 3D Render publishes
            for item in publishes:
                try:
                    if item['sg_publish']['published_file_type']['id'] != 5:
                        revised_publishes.append(item)
                    elif item['sg_publish']['sg_status_list'] == "cmpt":
                        revised_publishes.append(item)
                    else:
                        pass
                except:
                    # Published File needs Published File Type! Don't Add
                    pass
            
            # final decision on what to submit to the loader
            return self.compare_publish_lists(publishes, revised_publishes)

        # return all publised files with no filtering
        else:
            return publishes

    def compare_publish_lists(self, publishes, revised_publishes):

        if publishes == revised_publishes:
            return publishes
        else:
            return revised_publishes
