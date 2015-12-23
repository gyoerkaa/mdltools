import os
import enum
import warnings

import bpy

from . import nvb_mdl
from . import nvb_node
from . import nvb_anim


class Parser():
    __debug = True

    def __init__(self):
        self.scene = bpy.context.scene

        self.mdl = nvb_mdl.Mdl() # Model
        self.xwk = nvb_mdl.Mdl() # Walkmesh, pwk or dwk (wok is in mdl file)

    def load(self, mdlFilepath):
        self.parseMdl(mdlFilepath)
        self.parseWalkmesh(mdlFilepath)
        self.mdl.addMdlToScene(self.scene)
        self.xwk.addMdlToScene(self.scene)

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
                # a message.
                print("Neverblender: Unable to open walkmesh: " + wkFilepath)
                return

            # Placeable and door walkmeshes don't contain a rootdummy.
            # We need one, so we make one ourselves
            rootDummyName = self.mdl.name + '_' + walkmeshType
            rootDummy = nvb_node.Dummy(rootDummyName)
            if walkmeshType == 'dwk':
                rootDummy.setDummyType('DWKROOT')
            else:
                rootDummy.setDummyType('PWKROOT')
            self.xwk.addNode(rootDummy)

            # Parse the walkmesh
            blockStart = -1
            for idx, line in enumerate(lines):
                try:
                    label = line[0]
                except IndexError:
                    # Probably empty line or whatever, just skip it
                    continue
                if (label == 'node'):
                    blockStart = idx
                elif (label == 'endnode'):
                    if (blockStart > 0):
                        self.xwk.addAsciiNode(lines[blockStart:idx+1])
                        blockStart = -1
                    else:
                        # "endnode" before "node"
                        raise nvb_def.MalformedMdlFile('Unexpected "endnode" at line' + str(idx))


    def parseMdl(self, mdlFilepath):
        '''
        Get the geometry block and the animation blocks.
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
                    #node = self.parseGeometryNode(lines[blockStart:idx+1])
                    self.mdl.addAsciiNode(lines[blockStart:idx+1])
                    blockStart = -1
                    cs = State.GEOMETRY
                elif (label == 'node'):
                    raise nvb_def.MalformedMdlFile('Unexpected "endnode" at line' + str(idx))

            elif (cs == State.ANIMATION):
                if (label == 'newanim'):
                    if (blockStart < 0):
                        blockStart = idx
                    else:
                        raise nvb_def.MalformedMdlFile('Unexpected "newanim" at line' + str(idx))
                if (label == 'doneanim'):
                    if (blockStart > 0):
                        self.mdl.addAsciiAnimation(lines[blockStart:idx+1])
                        blockStart = -1
                    else:
                        raise nvb_def.MalformedMdlFile('Unexpected "doneanim" at line' + str(idx))
