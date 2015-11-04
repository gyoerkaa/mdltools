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

    def __init__(self):
        self.scene = bpy.context.scene

        self.mdl = nvb.mdl.Mdl() # Model
        self.xwk = nvb.mdl.Mdl() # Walkmesh


    def load(self, mdlFilepath):

        parseMdl(os.fsencode(mdlFilepath))
        parseWalkmesh(os.fsencode(mdlFilepath))
        self.mdl.convert(self.scene, os.path.dirname(mdlFilepath))
        self.xwk.convert(self.scene, os.path.dirname(mdlFilepath))

        self.scene.update()


    def parseWalkmesh(mdlFilepath):
        if (self.mdl.classification != 'TILE'):
            if (self.mdl.classification == 'DOOR'):
                # Doors should have a dwk file.
                wkFilepath = os.path.join(os.path.dirname(mdlFilepath),
                                          os.path.splitext(os.path.basename(mdlFilepath))[0] + '.dwk')
                try:
                    parseDwk(os.fsencode(wkFilepath))
                except IOError:
                    # Doesn't exist. We can continue without, but it's worth
                    # a warning.
                    warnings.warn("WARNING: Unable to open door walkmesh: " + wkFilepath)
            else
                # Could be a placeable, try looking for a pwk file.
                wkFilepath = os.path.join(os.path.dirname(mdlFilepath),
                                          os.path.splitext(os.path.basename(mdlFilepath))[0] + '.pwk')
                try:
                    parsePwk(os.fsencode(wkFilepath))
                except IOError:
                    # Doesn't exist and that's fine in this case as we can't
                    # be sure if it's a placeable.
                    pass


    def parseDwk(filepath):
        lines = [line.strip().split() for line in open(filepath, 'r')]

        nodeList = collections.OrderedDict()
        nodeStart = -1

        State = enum.Enum('State', 'READGEOM READGEOMNODE')
        cs = State.READGEOMNODE
        for idx, line in enumerate(lines):
            try:
                label = line[0]
            except IndexError:
                # Probably empty line or whatever, just skip it
                continue
            if (label == 'node'):
                nodeStart = idx
            elif (label == 'endnode'):
                if (nodeStart < 0)
                    nodeList.append((nodeStart, idx))
                    nodeStart = -1
                else:
                    raise MalformedMdlFile('Unexpected "endnode" at line' + idx)

        # dwk's don't contain a rootdummy. We need one, so we make one.
        rootname = self.mdl.name + '_dwk'
        node = nvb.node.Dummy(rootname, True)
        self.xwk.insertNode(node)
        for boundary in nodeList:
            node = self.parseGeomNode(lines[boundary[0]:boundary[1]], True)
            node.parent = rootname
            self.xwk.insertNode(node)


    def parsePwk(filepath):
        lines = [line.strip().split() for line in open(filepath, 'r')]

        nodeList = collections.OrderedDict()
        nodeStart = -1

        for idx, line in enumerate(lines):
            try:
                label = line[0]
            except IndexError:
                # Probably empty line or whatever, just skip it
                continue
            if (label == 'node'):
                nodeStart = idx
            elif (label == 'endnode'):
                if (nodeStart < 0)
                    nodeList.append((nodeStart, idx))
                    nodeStart = -1
                else:
                    raise MalformedMdlFile('Unexpected "endnode" at line' + idx)

        # pwk's don't contain a rootdummy. We need one, so we make one.
        rootname = self.mdl.name + '_pwk'
        node = nvb.node.Dummy(rootname, True)
        self.xwk.insertNode(node)
        for boundary in nodeList:
            node = self.parseGeomNode(lines[boundary[0]:boundary[1]], True)
            node.parent = rootname
            self.xwk.insertNode(node)


    def parseMdl(filepath):
        '''
        Loads the contents of an ascii mdl file into the
        container self.mdl
        '''
        lines = [line.strip().split() for line in open(filepath, 'r')]

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
            self.mdl.insertNode(node)

        for boundary in animList:
            anim = self.parseAnim(lines[boundary[0]:boundary[1]])
            self.mdl.addAnim(anim)


    def parseGeomNode(self, asciiBlock):
        if asciiBlock is None:
            raise MalformedMdlFile('Empty Node')

        nodeType = ''
        try:
            nodeType = asciiBlock[0][1].lower()
        except IndexError, AttributeError:
            raise MalformedMdlFile('Invalid node type')

        switch = {'dummy':      nvb.node.Dummy, \
                  'trimesh':    nvb.node.Trimesh,  \
                  'danglymesh': nvb.node.Danglymesh, \
                  'skin':       nvb.node.Skinmesh, \
                  'emitter':    nvb.node.Emitter, \
                  'light':      nvb.node.Light, \
                  'aabb':       nvb.node.Aabb}
        try:
            parsedNode = switch[nodeType](isWalkmesh = parseAsWalkmesh)
        except KeyError:
            raise MalformedMdlFile('Invalid node type')

        parsedNode.load(asciiBlock)
        return parsedNode


    def parseAnim(self, asciiBlock):
        if asciiBlock is None:
            raise MalformedMdlFile('Empty Animation')

        return nvb.anim.load



def import_(operator,
            context,
            filepath = '',
            imports = {'GEOMETRY', 'ANIMATION', 'WALKMESH'},
            useShadingGroups = True,
            useSingleTexture = True,
            useImgSearch = False,
            minimapMode = False):
    '''
    Called from blender ui
    '''
    nvb.glob.imports          = imports
    nvb.glob.useShadingGroups = useShadingGroups
    nvb.glob.useSingleTexture = useSingleTexture
    nvb.glob.useImgSearch     = useImgSearch
    nvb.glob.minimapMode      = minimapMode

    importer = Importer()
    importer.load(filepath)

    return {'FINISHED'}
