import collections

import bpy

import neverblender.nvb.presets


class Key():
    def __init__(self):
        self.position       = []
        self.orientation    = []
        self.selfillumcolor = []
        self.alphakey       = []
        #Lights/lamps
        self.color = []
        #Emitters
        self.birthrate  = []
        self.radius     = []
        self.alphaStart = []
        self.alphaEnd   = []
        self.colorStart = []
        self.colorEnd   = []


class Node():
    def __init__(self, name = 'UNNAMED'):
        self.name   = name
        self.parent = nvb.presets.null
        self.position    = (0.0, 0.0, 0.0)
        self.orientation = (0.0, 0.0, 0.0, 0.0)
        self.scale       = 1.0

        self.key = Keys()

    def parse(self, asciiBlock):
        lfloat = float
        for idx, line in enumerate(asciiBlock):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue
            if   (label  == 'node'):
                self.name = line[2].lower()
            elif (label  == 'parent'):
                self.parent = line[1].lower()
            elif (label  == 'position'):
                self.position = (lfloat(line[1]),
                                 lfloat(line[2]),
                                 lfloat(line[3]) )
            elif (label  == 'orientation'):
                self.orientation = (lfloat(line[1]),
                                    lfloat(line[2]),
                                    lfloat(line[3]),
                                    lfloat(line[4]) )
            elif (label  == 'scale'):
                self.scale = lfloat(line[1])
            elif (label  == 'positionkey'):
                pass
            elif (label  == 'orientationkey'):
                pass
            elif (label  == 'birthratekey'):
                pass

    def cloneScene(scene):
        objCopy = objOrig.copy()
        objOrig

    def convert(self, scene):
        cloneScene(scene)




class Animation():
    def __init__(self, name = 'UNNAMED'):
        self.name      = name
        self.length    = 1.0
        self.transtime = 1.0
        self.root      = nvb.presets.null
        self.events    = []
        self.nodeList  = []

        self.isEmpty = True # We needn't try and import animations to blender

    def parse(self, asciiBlock):
        nodeBlockList  = []
        nodeBlockStart = -1
        for idx, line in enumerate(asciiBlock):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue
            if (label == 'newanim'):
                self.name = line[1]
            elif (label == 'length'):
                self.length = float(line[1])
            elif (label == 'transtime'):
                self.transtime = float(line[1])event 0.0333333 detonate
            elif (label == 'animroot'):
                self.root = line[1]
            elif (label == 'event'):
                # "event time name"
                self.events.append((float(line[1]), line[2]))
            elif (label == 'node'):
                nodeBlockStart = idx
            elif (label == 'endnode'):
                if (nodeStart < 0):
                    nodeBlockList.append((nodeStart, idx))
                    nodeBlockStart = -1
                else (label == 'node'):
                    raise MalformedMdlFile('Unexpected "endnode" at line' + idx)

        for block in nodeBlockList:
            node = Node()
            node.parse(asciiBlock(block[0]:block[1]))
            self.nodeList.append(node)

    def convert(self, scene, geomNodeList):
        # Check if there is already a scene with this animation name
        if (self.name not in bpy.data.scenes.keys()):
            scene = bpy.data.scenes.new(self.name)
        else:
            scene = bpy.data.scenes[self.name]

        scene.render.fps  = nvb.presets.renderFps

        for node in self.nodeList:
            originalNode = geomNodeList(node.parent + node.name)
            if originalNode:
                node.convert(scene, originalNode)
            else:
                #TODO Raise an error
                pass
