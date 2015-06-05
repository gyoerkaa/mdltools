import bpy
import os
import math

import neverblender.nvb.walkmesh

class Mdlfile():
   
    def __init__(self, 
                 filepath = '', 
                 import_objects = {'GEOMETRY', 'ANIMATION', 'WALKMESH', 'LIGHT', 'SHADING_GROUP'},
                 one_texture_per_image = True,
                 use_image_search = False,
                 import_fading_obj = True,
                 ):
                 
        self.filepath = os.fsencode(filepath)
        self.filename = os.path.splitext(os.path.basename(filepath))[0]
        self.filedir  = os.path.dirname(filepath)
        
        # Import options (WHAT to import)
        self.import_geometry = True;
        self.import_anims    = True;
        self.import_walkmesh = True;
        self.import_lights   = True;
        
        # Import options (HOW to import)
        self.image_search = use_image_search
        self.one_texture  = one_texture_per_image
        self.import_fading_obj = True; # Used for minimaps
        
        # Where to put the imported stuff (additional scenes may be created for
        # animations)
        self.scene = bpy.context.scene
      
      
    def load_mdl():
        ascii_mdl = read_ascii_mdl()
    
    
    def read_ascii_mdl():
        '''
        Opens file in ascii format and puts its
        contents into a list    
        '''
        separated_values = []
    
        with open(self.filepath, 'r') as mdlfile:
            for line in mdlfile:
                # Make sure the current line is not a comment
                if (l[0] != '#'):
                
        # Open file
        try:
            file  = open(self.filepath, 'r')
        
            lines = file.readlines()
            # Iterate over all lines
            split_line = []
            for l in lines[0:len(lines)]:
                # Make sure the current line is not a comment
                if (l[0] != '#'):      
                    # Separate words
                    split_line = l.split()
                    # if empty, don't add to list
                    if (len(split_line) > 0):
                        separated_values.append(split_line)    
    
        except IOError:
            print('WARNING: Could not open file ' + str(self.filepath))
    
        return separated_values  