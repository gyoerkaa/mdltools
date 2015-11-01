import os
import math
import collections

import bpy
from bpy_extras.io_utils import unpack_list, unpack_face_list
from bpy_extras.image_utils import load_image

import neverblender.nvb.walkmesh
import neverblender.nvb.node
import neverblender.nvb.presets
import neverblender.nvb.glob

class Mdl():
    __debug = True

    def __init__(self):
        self.nodeList = collections.OrderedDict()
        self.animlist = dict() # No need to retain order

        self.name           = 'UNNAMED'
        self.supermodel     = nvb.presets.null
        self.animScale      = 1.0
        self.classification = 'UNKNOWN'

        self.root = ''


    def insertNode(self, newNode):
        # Blender requires unique object names. In mdl names are only
        # unique for a parent, i.e. another object with the same name
        # with a different parent may exist.
        # We'd need to save all names starting from root to resolve
        # this, but that's too much effort.
        # Name + ParentName should be enough.

        if newNode:
            key = newNode.parent + newNode.name
            if key in self.nodeList:
                #TODO: Should probably raise an exception
                pass
            else:
                self.nodeList[key] = newNode


    def getNode(self, nodeId)
        if nodeId in self.nodeList:
            return self.nodeList[nodeId]
        else
            return False


    def addAnim(self, anim):
        pass


    def convert(self, scene, filepath = ''):

        for node in self.nodelist:
            obj = node.convert(scene, filepath)
            if (node.parent == nvb.presets.null) and
               (node.name == self.name)
                obj.auroraprops.dummytype = 'MDLROOT'
                self.root = obj.name

        if not nvb.glob.minimapMode:
            for anim in self.animlist:
                anim.convert()

