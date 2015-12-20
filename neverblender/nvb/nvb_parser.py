import os
import enum
import warnings

import bpy

from . import nvb_mdl
from . import nvb_node
from . import nvb_anim

class MalformedMdlFile(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)

class Parser():
    __debug = True

    def __init__(self):
        self.scene = bpy.context.scene

        self.mdl = nvb_mdl.Mdl() # Model
        self.xwk = nvb_mdl.Mdl() # Walkmesh, pwk or dwk (wok is in mdl file)

    def load(self, mdlFilepath):
        self.parseMdl(mdlFilepath)
        self.parseWalkmesh(mdlFilepath)
        self.mdl.convert(self.scene)
        #self.xwk.convert(self.scene, os.path.dirname(mdlFilepath))

        self.scene.update()

    def parseWalkmesh(self, mdlFilepath):
        if (self.mdl.classification != 'TILE'):
            # Look for the walkmesh depending on classification
            # For 'DOOR' we will look for a *.dwk file
            # For others we will try to look for a *.pwk file
            walkmeshType = 'pwk'
            if (self.mdl.classification == 'DOOR'):
                # For 'DOOR' we will look for a *.dwk file
                walkmeshType = 'dwk'

            # Construct filepath from the mdl's filepath
            (filepath, filename) = os.path.split(mdlFilepath)
            wkFilepath = os.path.join(filepath, os.path.splitext(filename)[0] + '.' + walkmeshType)

            # Try opening the walkmesh file. It may not exist which is fine
            # too.
            lines = []
            try:
                filepath = os.fsencode(wkFilepath)
                lines = [line.strip().split() for line in open(filepath, 'r')]
            except IOError:
                # Doesn't exist. We can continue without, but it's worth
                # a warning.
                warnings.warn("WARNING: Unable to open walkmesh: " + wkFilepath)
                return

            # Parse the walkmesh
            nodeBlocks  = []
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
                    if (nodeStart < 0):
                        # "endnode" befaode "node"
                        raise MalformedMdlFile('Unexpected "endnode" at line' + str(idx))
                    else:
                        nodeBlocks.append((nodeStart, idx))
                        nodeStart = -1

            # Placeable and door walkmeshes don't contain a rootdummy.
            # We need one, so we make one ourselves
            rootdummyName = self.mdl.name + '_' + walkmeshType
            self.xwk.addNode(nvb_node.Dummy(rootdummyName))
            for (nodeStart, nodeEnd) in nodeBlocks:
                asciiBlock = lines[nodeStart:nodeEnd]
                node = self.parseGeometryNode(asciiBlock)
                node.parent = rootdummyName
                self.xwk.addNode(node)


    def parseMdl(self, mdlFilepath):
        '''
        Loads the contents of an ascii mdl file into the
        container self.mdl
        '''
        filepath = os.fsencode(mdlFilepath)
        lines = [line.strip().split() for line in open(filepath, 'r')]


        State = enum.Enum('State', 'START HEADER GEOMETRY GEOMETRYNODE ANIMATION')
        cs    = State.START
        blockStart = -1
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
                    cs = State.HEADER

            elif (cs == State.HEADER):
                if (label == 'beginmodelgeom'):
                    # After this, a list of nodes has to follow
                    cs = State.GEOMETRY
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

            elif (cs == State.GEOMETRY):
                if (label == 'node'):
                    blockStart = idx
                    cs = State.GEOMETRYNODE
                if (label == 'endmodelgeom'):
                    # After this, either animations or eof
                    cs = State.ANIMATION

            elif (cs == State.GEOMETRYNODE):
                if (label == 'endnode'):
                    node = self.parseGeometryNode(lines[blockStart:idx+1])
                    self.mdl.addNode(node)
                    blockStart = -1
                    cs = State.GEOMETRY
                elif (label == 'node'):
                    raise MalformedMdlFile('Unexpected "endnode" at line' + str(idx))

            elif (cs == State.ANIMATION):
                if (label == 'newanim'):
                    if (blockStart < 0):
                        blockStart = idx
                    else:
                        raise MalformedMdlFile('Unexpected "newanim" at line' + str(idx))
                if (label == 'doneanim'):
                    if (blockStart > 0):
                        anim = self.parseAnimation(lines[blockStart:idx+1])
                        self.mdl.addAnimation(anim)
                        blockStart = -1
                    else:
                        raise MalformedMdlFile('Unexpected "doneanim" at line' + str(idx))


    def parseGeometryNode(self, asciiBlock):
        if asciiBlock is None:
            raise MalformedMdlFile('Empty Node')

        nodeType = ''
        try:
            nodeType = asciiBlock[0][1].lower()
        except (IndexError, AttributeError):
            raise MalformedMdlFile('Invalid node type')

        switch = {'dummy':      nvb_node.Dummy, \
                  'patch':      nvb_node.Patch, \
                  'reference':  nvb_node.Reference, \
                  'trimesh':    nvb_node.Trimesh,  \
                  'danglymesh': nvb_node.Danglymesh, \
                  'skin':       nvb_node.Skinmesh, \
                  'emitter':    nvb_node.Emitter, \
                  'light':      nvb_node.Light, \
                  'aabb':       nvb_node.Aabb}
        try:
            node = switch[nodeType]()
        except KeyError:
            raise MalformedMdlFile('Invalid node type')

        node.parse(asciiBlock)
        return node


    def parseAnimation(self, asciiBlock):
        if asciiBlock is None:
            raise MalformedMdlFile('Empty Animation')

        animation = nvb_anim.Animation()

        blockStart = -1
        for idx, line in enumerate(asciiBlock):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue
            if (label == 'newanim'):
                animation.name = line[1]
            elif (label == 'length'):
                animation.length = float(line[1])
            elif (label == 'transtime'):
                animation.transtime = float(line[1])
            elif (label == 'animroot'):
                animation.root = line[1]
            elif (label == 'event'):
                animation.addEvent((float(line[1]), line[2]))
            elif (label == 'node'):
                blockStart = idx
            elif (label == 'endnode'):
                if (blockStart < 0):
                    raise MalformedMdlFile('Unexpected "endnode"')
                elif (label == 'node'):
                    nodeBlocks.append((blockStart, idx))
                    node = nvb_animnode.Node()
                    node.parse(asciiBlock[nodeStart: idx+1])
                    animation.addNode(node)
                    blockStart = -1

        return animation
