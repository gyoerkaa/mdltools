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
        self.animlist = dict() # No need to retain order

        self.name           = 'UNNAMED'
        self.supermodel     = nvb.presets.null
        self.animScale      = 1.0
        self.classification = 'UNKNOWN'


    def addNode(self, newNode):
        # Resolve naming conflicts by using name+parent as key
        # names alone are not unique, but they are unique under each parent

        if newNode:
            key = newNode.parent + newNode.name
            if key in self.nodeList:
                self.nodeList[key] = newNode
            else:
                #TODO: Should probably raise an exception
                pass


    def getNode(self, id)
        if id in self.nodeList:
            return self.nodeList[id]
        else
            return False


    def addAnim(self, anim):
        pass
