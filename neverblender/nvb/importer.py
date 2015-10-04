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


class MalformedMdlFile(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)


class Parser():
    __debug = True

    def __init__(self,
                 filepath,
                 imports,
                 uniqueTexture       = False,
                 importShadingGroups = False,
                 imageSearch         = False,
                 minimapMode         = False,
                 ):
        self.filepath = os.fsencode(filepath)
        self.filename = os.path.splitext(os.path.basename(filepath))[0]
        self.filedir  = os.path.dirname(filepath)

        self.imports = imports
        self.uniqueTexture       = uniqueTexture
        self.importShadingGroups = importShadingGroups
        self.imageSearch         = imageSearch
        self.minimapMode         = minimapMode

        self.scene = bpy.context.scene
        self.mdl   = nvb.mdl.Mdl()


    def load(self, filepath):
        self.filepath = os.fsencode(filepath)
        self.filename = os.path.splitext(os.path.basename(filepath))[0]
        self.filedir  = os.path.dirname(filepath)
        
        parseMdl();


    def parseMdl():
        lines = [line.strip().split() for line in open(filepath, 'r')]

        nodeList = collections.OrderedDict()
        nodeStart = -1
        animList = dict() # No need to retain order
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
                        warnings.warn("WARNING: Unable to read model name. Default value: " + self.mdl.name)
                    cs = State.READHEAD

            if (cs == State.READHEAD):
                if (label == 'beginmodelgeom')
                    cs == State.READGEOM
                elif (label == 'setsupermodel'):
                    try:
                       self.mdl.supermodel = line[1]
                    except IndexError:
                       warnings.warn("WARNING: Unable to read supermodel. Default value: " + self.mdl.supermodel)
                elif (label == 'classification'):
                    try:
                        self.mdl.classification = line[1]
                    except IndexError:
                        warnings.warn("WARNING: Unable to read classification. Default value: " + self.mdl.classification)
                elif (label == 'setanimationscale'):
                    try:
                        self.mdl.animScale = line[1]
                    except IndexError:
                        warnings.warn("WARNING: Unable to read animationscale. Default value: " + self.mdl.animScale)

            elif (cs == State.READGEOM):
                if (label == 'node'):
                    nodeStart = idx
                    cs = State.READGEOMNODE
                if (label == 'endmodelgeom'):
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

        for lineRange in nodeList:
            node = self.parseGeomNode(lines[lineRange[0]:lineRange[1]])
            self.mdl.insertNode(node)

        for lineRange in animList:
            anim = self.parseAnim(lines[lineRange[0]:lineRange[1]])
            self.mdl.addAnim(anim)


    def parseGeomNode(self, geomBlock):
        if asciiNode is None:
            raise MalformedMdlFile('Empty Node')

        nodeType = ''
        try:
            nodeType = asciiNode[0][1].lower()
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
            nodeType = switch[label]()
        except KeyError:
            raise MalformedMdlFile('Invalid node type')

        node.fromAscii(asciiNode)
        return node


    def parseAnim(self, animBlock):
        pass



def import_(operator,
            context,
            filepath = '',
            imports = {'GEOMETRY', 'ANIMATION', 'WALKMESH', 'EMITTER'},
            uniqueTexture       = False,
            importShadingGroups = False,
            imageSearch         = False,
            minimapMode         = False,
            ):
    '''
    Called from blender ui
    '''
    parser = Parser(imports,
                    uniqueTexture,
                    importShadingGroups,
                    imageSearch,
                    minimapMode)
    parser.load(filepath)

    return {'FINISHED'}
