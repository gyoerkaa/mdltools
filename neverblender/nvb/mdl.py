import os
import math
import collections
import warnings

import bpy
from bpy_extras.io_utils import unpack_list, unpack_face_list
from bpy_extras.image_utils import load_image

import neverblender.nvb.walkmesh
import neverblender.nvb.node
import neverblender.nvb.presets
import neverblender.nvb.glob

class Mdl():
    __debug = True

    def __init__(self, isWalkmesh = False):
        self.nodeList = collections.OrderedDict()
        self.animlist = dict() # No need to retain order

        self.name           = 'UNNAMED'
        self.supermodel     = nvb.presets.null
        self.animScale      = 1.0
        self.classification = 'UNKNOWN'

        self.root       = ''
        self.isWalkmesh = isWalkmesh


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
            if (node.parent == nvb.presets.null):
                if (node.name == self.name):
                    if
                    obj.auroraprops.dummytype = 'MDLROOT'
                    self.root = obj.name
                else:
                    # Node without parent and not the mdl root. Problem ?
                    warnings.warn("WARNING: " + node.name + " has no parent.")
            else:
                if node.parent in bpy.data.objects:
                    obj.parent                = bpy.data.objects[node.parent]
                    obj.matrix_parent_inverse = obj.parent.matrix_world.inverted()
                else:
                    warnings.warn("WARNING: " + obj.name + " has no parent (" + node.parent + ")")



        if not nvb.glob.minimapMode:
            for anim in self.animlist:
                anim.convert()

