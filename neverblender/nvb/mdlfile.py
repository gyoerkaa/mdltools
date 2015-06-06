import bpy
import os
import math
import collections

#import neverblender.nvb.walkmesh

class Mdlfile():
    __debug = True
    
    def __init__(self, filepath = None):
        if filepath:
           open()
      
      
    def open(self, 
             filepath = '',
             import_objects = {'GEOMETRY', 'ANIMATION', 'WALKMESH', 'LIGHT', 'SHADING_GROUP', 'EMITTER'},
             one_texture_per_image = True,
             use_image_search      = False,
             import_fading_obj     = True):
                  
        self.filepath = os.fsencode(filepath)
        self.filename = os.path.splitext(os.path.basename(filepath))[0]
        self.filedir  = os.path.dirname(filepath)
        
        # Import options (WHAT to import)
        self.import_geometry = True;
        self.import_anims    = True;
        self.import_walkmesh = True;
        self.import_light    = True;
        self.import_emitter  = True;
        # Import options (HOW to import)
        self.image_search = use_image_search
        self.one_texture  = one_texture_per_image
        self.import_fading_obj = True; # Used for minimaps
        
        # Where to put the imported stuff (additional scenes may be created for
        # animations)
        self.scene = bpy.context.scene
        
        ascii_mdl = read_ascii_mdl(self.filepath)
    
    
    def save(self,
             filepath = '',
             export_objects = {'GEOMETRY', 'ANIMATION', 'WALKMESH', 'LIGHT', 'SHADING_GROUP', 'EMITTER'},
             apply_modifiers = True):
        
        self.filepath = os.fsencode(filepath)
        self.filename = os.path.splitext(os.path.basename(filepath))[0]
        self.filedir  = os.path.dirname(filepath)

        # Exit edit mode before exporting, so current object states are exported properly
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')                
    
    
    def read_ascii_mdl(self, filepath = ''):
        '''
        Opens file in ascii format and puts its
        contents into a list    
        '''
        separated_values = []
    
        with open(filepath, 'r') as file:
            for line in file:
                line = line.strip()
                # Skip empty lines & comments
                if (line and line[0] != '#'):
                    separated_values.append(line.split())
                        
        return separated_values
    
    
    def parse_modelgeom(self, modelgeom):
        '''
        Returns an ordered list of geometry nodes.
        Nodes are orderered "parent-first", i.e. a child will never come before
        its parent.   
        '''
        
        geomnodes = collections.OrderedDict()
        
        if modegeom is None:
            return geomnodes
            
        for line in modegeom:
            if line[0] = 'node'
    
    
    def parse_geom_node(self, geomnode):
        pass
    
    
    def parse_anim(self, anim):
        pass