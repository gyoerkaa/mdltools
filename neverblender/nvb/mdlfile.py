import os
import math
import collections

import bpy

#import neverblender.nvb.walkmesh
import neverblender.nvb.node

class MalformedMdlFile(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)


class Mdlfile():
    __debug = True

    def __init__(self):
        self.nodelist = collections.OrderedDict()
        self.animlist = dict() # No need to retain order
        
        # in {'unknown', 'tile', 'character', 'door', 'effect', 'gui', 'item'}
        self.classification = 'unknown'
        self.supermodel     = 'null'
        self.animationscale = 1.0 # Unused ?
        
    def addNode(self, node):
        pass
    
    def import_(self, 
               filepath = '',
               importObjects = {'GEOMETRY', 'ANIMATION', 'WALKMESH'},
               duplicateTextures = False,
               imageSearch       = False,
               skipFadingObj     = False):
        
        self.filepath = os.fsencode(filepath)
        self.filename = os.path.splitext(os.path.basename(filepath))[0]
        self.filedir  = os.path.dirname(filepath)
        
        # Import options (WHAT to import)
        self.imports = importObjects;
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

        #newmodel X
        #    beginmodelgeom X
        #        node G      
        #        endnode G
        #        node H
        #        endnode H
        #    endmodelgeom X
        #    newanim A
        #    doneanim A
        #    newanim B
        #    doneanim B
        #donemodel X          
        geomBlockStart = None
        animBlockStart = None       
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
                    # Trying to start a 2nd geometry block (only 1 allowed)
                    raise MalformedMdlFile('Unexpected "beginmodelgeom"')
                geomBlockStart = idx;
            elif (line[0] == 'endmodelgeom'):
                if not geomBlockStart:
                    # Trying to end a geometry block before starting one
                    raise MalformedMdlFile('Unexpected "endmodelgeom"')
                parseAsciiGeomBlock(lines[geomBlockStart:idx]) 
            elif (line[0] == 'newanim'):
                if animBlockStart:
                    # Trying to start a new anim before ending one
                    raise MalformedMdlFile('Unexpected "newanim"') 
                animBlockStart = idx                    
            elif (line[0] == 'doneanim'):
                if not animBlockStart:
                    # Trying to end an anim before starting one
                    raise MalformedMdlFile('Unexpected "doneanim"') 
                parseAsciiAnimBlock(lines[animBlockStart:idx])
                # Reset back to None, as there can be more than one anim block
                animBlockStart = None

    def parseAsciiGeomBlock(self, geomBlock):
        """
        Returns an ordered list of geometry nodes.
        Nodes are orderered "parent-first", i.e. a child will never come before
        its parent.   
        """
        nodeList = collections.OrderedDict()

        if geomBlock is None:
            return nodeList
        
        # For nodes, whose parents haven't been inserted yet
        geomQueue = collection.deque()
        
        nodeStart = None
        for idx, line in enumerate(geomBlock):
            if line[0] = 'node':
                if nodeStart:
                    # Trying to start a new node before ending one
                    raise MalformedMdlFile('Unexpected "node"')
                nodeStart = idx;
            elif line[0] = 'endnode':
                if not nodeStart:
                    # Trying to end a node before starting one
                    raise MalformedMdlFile('Unexpected "endnode"')
                nodeList.append(parseGeomNode(geomBlock[nodeStart:idx]))
                nodeStart = None


    def parseAsciiGeomNode(self, asciiNode):
        """
        Parse a single geometry node  
        """
        if asciiNode is None:
            raise MalformedMdlFile('Empty Node')
        
        type = ''
        try:
            type = asciiNode[0][1].lower()
        except IndexError, AttributeError:
            raise MalformedMdlFile('Invalid node type')
        
        switch={'dummy':      nvb.node.Dummy, 
                'trimesh':    nvb.node.Trimesh,
                'danglymesh': nvb.node.Danglymesh,
                'skin':       nvb.node.Skinmesh,
                'emitter':    nvb.node.Emitter,
                'light':      nvb.node.Light,
                'aabb':       nvb.node.Aabb}
        try:
            node = switch[type]()
        except KeyError:
            raise MalformedMdlFile('Invalid node type')
        
        node.from_ascii(asciiNode)
        return node


    def parseAsciiAnimBlock(self, animBlock):
        pass


    def parseAsciiAnimNode(self, animNode):
        pass