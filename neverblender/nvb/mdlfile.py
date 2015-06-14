import os
import math
import collections

import bpy

#import neverblender.nvb.walkmesh
#import neverblender.nvb.node

class MalformedMdlFile(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)


class Mdlfile():
    __debug = True
    
    def __init__(self):
        pass
      
    def import_(self, 
               filepath = '',
               importObjects = {'GEOMETRY', 'ANIMATION', 'WALKMESH', 'LIGHT', 'EMITTER', 'SHADINGGROUP'},
               duplicateTextures = False,
               imageSearch       = False,
               skipFadingObj     = False):
                  
        self.filepath = os.fsencode(filepath)
        self.filename = os.path.splitext(os.path.basename(filepath))[0]
        self.filedir  = os.path.dirname(filepath)
        
        # Import options (WHAT to import)
        self.importGeometry  = 'GEOMETRY'     in importObjects;
        self.importAnims     = 'ANIMATION'    in importObjects;
        self.importWalkmesh  = 'WALKMESH'     in importObjects;
        self.importLight     = 'LIGHT'        in importObjects;
        self.importEmitter   = 'EMITTER'      in importObjects;
        self.importShadingGr = 'SHADINGGROUP' in importObjects;
        # Import options (HOW to import)
        self.duplicateTextures = duplicateTextures # use 1 texture for each img
        self.imageSearch       = imageSearch # search in subfolders
        self.skipFadingObj     = skipFadingObj; # for minimaps
        
        # Where to put the imported stuff (additional scenes may be created for
        # animations)
        self.scene = bpy.context.scene
        
        self.nodelist = collections.OrderedDict()
        self.animlist = dict() # No need to retain order
        parseAsciiMdl(self.filepath)
    
    def export_(self,
                filepath = '',
                exportObjects = {'GEOMETRY', 'ANIMATION', 'WALKMESH', 'LIGHT', 'SHADING_GROUP', 'EMITTER'},
                applyModifiers = True):
        
        self.filepath = os.fsencode(filepath)
        self.filename = os.path.splitext(os.path.basename(filepath))[0]
        self.filedir  = os.path.dirname(filepath)

        # Exit edit mode before exporting, so current object states are exported properly
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')                
        
    def writeAsciiMdl(self, filepath = ''):
        pass
       
    def parseAsciiMdl(self, filepath = ''):
        """
        Opens file in ascii format and puts its nodes into lists 
        (one for geometry & aninms each)
        """
        lines = [line.strip().split() for line in open(filepath, 'r')]

        # Read some metadata frist
        geomBlockStart = None
        geomBlockEnd   = None
        animBlockStart = None 
        animBlockEnd   = None
        animBlockList  = []
        for idx, line in enumerate(lines):
            if (line[0] == 'newmodel'):
                try:
                    self.modelname = line[1]
                except IndexError:
                    self.modelname = 'UNKNOWN'
            elif (line[0] == 'setsupermodel'): 
                try:
                   self.supermodel = line[1]
                except IndexError:
                   self.supermodel = 'NULL'
            elif (line[0] == 'classification'):
                try:
                    self.classification = line[1]
                except IndexError:
                    self.classification = 'UNKNOWN'
            elif (line[0] == 'setanimationscale'):
                try:
                    self.animScale = line[1]
                except IndexError:
                    self.animScale = 1.0
            elif (line[0] == 'beginmodelgeom'):
                if (geomBlockStart):
                     # There can only be one
                    raise MalformedMdlFile('Unexpected "beginmodelgeom"')
                geomBlockStart = idx;                   
            elif (line[0] == 'endmodelgeom'):
                if (geomBlockEnd):
                    # There can only be one
                    raise MalformedMdlFile('Unexpected "endmodelgeom"')
                geomBlockEnd = idx; 
            elif (line[0] == 'newanim'):               
                if animBlockStart:
                    # Trying to start a new anim before finishing the old
                    raise MalformedMdlFile('Unexpected "newanim"') 
                animBlockStart = idx                    
            elif (line[0] == 'doneanim'):               
                if not animBlockStart:
                    # Trying to end an anim before starting one
                    raise MalformedMdlFile('Unexpected "doneanim"') 
                animBlockEnd = idx
                animBlockList.append((animBlockStart, animBlockEnd))
                animBlockStart = None
                animBlockEnd   = None
        
        # Parse Geometry
        parseGeomBlock(geomBlockStart,geomBlockEnd)
        
        # Parse Animations
        for anim in animBlockList:
            pass
        
              
    def parseGeomBlock(self, geomBlockStart, geomBlockEnd):
        """
        Returns an ordered list of geometry nodes.
        Nodes are orderered "parent-first", i.e. a child will never come before
        its parent.   
        """
        
        geomNodes = collections.OrderedDict()

        if geomBlock is None:
            return geomNodes
            
        # For nodes, whose parents haven't been inserted yet
        geomQueue = collection.deque()
        
        for line in modelGeom:
            if line[0] = 'node':
                pass
                    
    def parseGeomNode(self, geomNode):
        pass
    
    def parseAnimBlock(self, animBlock):
        pass
     
    def parseAnimNode(self, animNode):
        pass