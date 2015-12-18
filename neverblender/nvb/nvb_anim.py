import collections

import bpy

from . import nvb_presets
from . import nvb_animnode

class MalformedMdlFile(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)

class Animation():
    def __init__(self, name = 'UNNAMED'):
        self.name      = name
        self.length    = 1.0
        self.transtime = 1.0
        self.root      = nvb_presets.null
        self.eventList = []
        self.nodeList  = collections.OrderedDict()

    def addNode(self, newNode):
        if newNode:
            key = newNode.parent + newNode.name
            if key in self.nodeList:
                #TODO: Should probably raise an exception
                pass
            else:
                self.nodeList[key] = newNode

    def addEvent(self, event):
        pass

    def parse(self, asciiBlock):
        nodeBlocks = []
        blockStart = -1
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
                self.transtime = float(line[1])
            elif (label == 'animroot'):
                self.root = line[1]
            elif (label == 'event'):
                # "event time name"
                #event 0.0333333 detonate
                self.eventList.append((float(line[1]), line[2]))
            elif (label == 'node'):
                blockStart = idx
            elif (label == 'endnode'):
                if (blockStart < 0):
                    raise MalformedMdlFile('Unexpected "endnode"')
                elif (label == 'node'):
                    nodeBlocks.append((blockStart, idx))
                    blockStart = -1

        for (nodeStart, nodeEnd) in nodeBlocks:
            node = nvb_animnode.Node()
            node.parse(asciiBlock[nodeStart:nodeEnd])
            self.addNode(node)

    def convert(self, scene, originalNodeList):
        # Check if there is already a scene with this animation name
        if (self.name not in bpy.data.scenes.keys()):
            animScene = bpy.data.scenes.new(self.name)
        else:
            animScene = bpy.data.scenes[self.name]

        animScene.render.fps  = nvb_presets.renderFps

        for (nodeKey, node) in self.nodeList.items():
            if nodeKey in originalNodeList:
                # This node is animated. We'll need to add animations
                originalNode = riginalNodeList(nodeKey)
                node.convert(animScene, originalNode)
            else:
                # The node in the animation doesn't exist in the model
                raise MalformedMdlFile('Node ' + node.name + ' in animation '+ self.name +' but not present in model.')

    def cloneScene(scene):
        objCopy = objOrig.copy()
