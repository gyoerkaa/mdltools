import os
import math
import collections

import bpy

import neverblender.nvb.walkmesh
import neverblender.nvb.node
import neverblender.nvb.presets

class Mdl():
    __debug = True

    def __init__(self):
        self.nodeList = collections.OrderedDict()
        self.tmpnodes = collections.OrderedDict()
        self.animlist = dict() # No need to retain order
        
        self.name           = 'UNNAMED'
        self.supermodel     = nvb.presets.null
        self.animScale      = 1.0
        self.classification = 'UNKNOWN'
    
    
    def addNode(self, newNode):
        if newNode:
            if (newNode.parent == nvb.presets.null) or 
               (newNode.parent in self.nodeList):
                # try to resolve naming conflicts (blender requires unique names)
                if newNode.name in self.nodeList:
                    newNode.name = newNode.parent + newNode.name
                self.nodeList[newNode.name] = newNode
                if newNode.name in self:
                    
            else:
                self.tmpnodes[newNode.parent] = newNode
    
    
    def getNode(self, id)
        if id in self.nodeList:
            return self.nodeList[id]
        else
            return False
    
    
    def addAnim(self, anim):
        pass