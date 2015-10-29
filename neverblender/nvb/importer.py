import bpy
import os
import collections
import enum
import warnings
import math

import neverblender.nvb.mdl
import neverblender.nvb.node
import neverblender.nvb.presets
import neverblender.nvb.walkmesh
import neverblender.nvb.parser

class MalformedMdlFile(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)


class Importer():
    __debug = True

    def __init__(self,
                 imports,
                 shadingGroups,
                 uniqueTexture,
                 imageSearch,
                 minimapMode):
        self.imports = imports
        self.uniqueTexture = uniqueTexture
        self.shadingGroups = shadingGroups
        self.imageSearch   = imageSearch
        self.minimapMode   = minimapMode

        self.scene = bpy.context.scene
        

    def load(self, mdlFilepath):

        self.mdl = parseMdl(os.fsencode(mdlFilepath))
        self.walkmesh = parseWalkmesh(os.fsencode(mdlFilepath))
            
        self.mdl.convert()
        self.walkmesh.convert()

                
    def parseWalkmesh(filepath):
        if (self.mdl.classification != 'TILE'):
            if (self.mdl.classification == 'DOOR'):
                wkFilepath = os.path.join(os.path.dirname(filepath),
                                          os.path.splitext(os.path.basename(filepath))[0] + '.dwk')
                try:
                    return parseDwk(os.fsencode(wkFilepath))
                except IOError:
                    warnings.warn("WARNING: Unable to open walkmesh: " + wkFilepath)
            else
                # Try looking for a placeable walkmesh
                wkFilepath = os.path.join(os.path.dirname(filepath),
                                          os.path.splitext(os.path.basename(filepath))[0] + '.pwk')
                try:
                    return parsePwk(os.fsencode(wkFilepath))
                except IOError:
                    # Doesn't exist, but that's ok
                    pass
                    
        return nvb.mdl.Mdl()
        

    def parseDwk(filepath):
        pass


    def parsePwk(filepath):
        pass


    def parseMdl(filepath):
        '''
        Loads the contents of an ascii mdl file into the
        container self.mdl
        '''
        
        lines = [line.strip().split() for line in open(filepath, 'r')]
        
        mdl = nvb.mdl.Mdl()
        
        nodeList = collections.OrderedDict()
        animList = dict() # No need to retain order
        nodeStart = -1
        animStart = -1

        State = enum.Enum('State', 'START READHEAD READGEOM READGEOMNODE READANIM')
        cs = State.START
        for idx, line in enumerate(lines):
            try:
                label = line[0]
            except IndexError:
                # Probably empty line or whatever, just skip it
                continue

            if (cs == State.START):
                if (label == 'newmodel'):
                    try:
                        self.mdl.name = line[1]
                    except IndexError:
                        warnings.warn("WARNING: Unable to read model name. Using default value: " + self.mdl.name)
                    cs = State.READHEAD

            if (cs == State.READHEAD):
                if (label == 'beginmodelgeom')
                    # After this, a list of nodes has to follow
                    cs == State.READGEOM
                elif (label == 'setsupermodel'):
                    try:
                       # line should be ['setsupermodel', modelname, supermodelname]
                       self.mdl.supermodel = line[2]
                    except IndexError:
                       warnings.warn("WARNING: Unable to read supermodel. Using default value: " + self.mdl.supermodel)
                elif (label == 'classification'):
                    try:
                        self.mdl.classification = line[1].upper()
                    except IndexError:
                        warnings.warn("WARNING: Unable to read classification. Using default value: " + self.mdl.classification)
                elif (label == 'setanimationscale'):
                    try:
                        self.mdl.animScale = line[1]
                    except IndexError:
                        warnings.warn("WARNING: Unable to read animationscale. Using default value: " + self.mdl.animScale)

            elif (cs == State.READGEOM):
                if (label == 'node'):
                    nodeStart = idx
                    cs = State.READGEOMNODE
                if (label == 'endmodelgeom'):
                    # Aftert his, either animations or eof
                    cs = State.READANIM

            elif (cs == State.READGEOMNODE):
                if (label == 'endnode'):
                    nodeList.append((nodeStart, idx))
                    nodeStart = -1
                    cs = State.READGEOM
                elif (label == 'node'):
                    raise MalformedMdlFile('Unexpected "endnode" at line' + idx)

            elif (cs == State.READANIM):
                if (label == 'newanim'):
                    if (nodeStart < 0):
                        nodeStart = idx
                    else:
                        raise MalformedMdlFile('Unexpected "newanim" at line' + idx)
                if (label == 'doneanim'):
                    if (nodeStart > 0):
                        nodeList.append((nodeStart, idx))
                        nodeStart = -1
                    else:
                        raise MalformedMdlFile('Unexpected "doneanim" at line' + idx)

        for boundary in nodeList:
            node = self.parseGeomNode(lines[boundary[0]:boundary[1]])
            mdl.insertNode(node)

        for boundary in animList:
            anim = self.parseAnim(lines[boundary[0]:boundary[1]])
            mdl.addAnim(anim)

        return mdl


    def parseGeomNode(self, asciiNode):
        if asciiNode is None:
            raise MalformedMdlFile('Empty Node')

        nodeType = ''
        try:
            nodeType = asciiNode[0][1].lower()
        except IndexError, AttributeError:
            raise MalformedMdlFile('Invalid node type')

        switch = {'dummy':      nvb.node.Dummy,
                  'trimesh':    nvb.node.Trimesh,
                  'danglymesh': nvb.node.Danglymesh,
                  'skin':       nvb.node.Skinmesh,
                  'emitter':    nvb.node.Emitter,
                  'light':      nvb.node.Light,
                  'aabb':       nvb.node.Aabb}
        try:
            parsedNode = switch[nodeType]()
        except KeyError:
            raise MalformedMdlFile('Invalid node type')

        parsedNode.loadAscii(asciiNode)
        return parsedNode


    def parseAnim(self, animBlock):
        pass





def import_(operator,
            context,
            filepath = '',
            imports = {'GEOMETRY', 'ANIMATION', 'WALKMESH', 'EMITTER'},
            shadingGroups = True,
            uniqueTexture = True,
            imageSearch   = False,
            minimapMode   = False):
    '''
    Called from blender ui
    '''
    importer = Importer(imports,
                        shadingGroups,
                        uniqueTexture,
                        imageSearch,
                        minimapMode)
    importer.load(filepath)

    return {'FINISHED'}
