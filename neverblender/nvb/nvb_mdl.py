import os
import math
import collections
import warnings

import bpy

from . import nvb_node
from . import nvb_presets
from . import nvb_glob

class Mdl():
    def __init__(self):
        self.nodeList  = collections.OrderedDict()
        self.animList  = dict() # No need to retain order
        self.rootdummy = ''

        self.name           = 'UNNAMED'
        self.supermodel     = nvb_presets.null
        self.animScale      = 1.0
        self.classification = 'UNKNOWN'


    def addAsciiGeomNode(self, asciiBlock):
        pass

    def addNode(self, newNode):
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

    def addAnimation(self, anim):
        if anim:
            if anim.name in self.animList:
                #TODO: Should probably raise an exception
                pass
            else:
                self.animList[anim.name] = anim

    def convert(self, scene):
        for (nodeKey, node) in self.nodeList.items():
            obj = node.convert(scene)
            if (node.parent == nvb_presets.null):
                if (node.name == self.name):
                    obj.nvb.dummytype = 'MDLROOT'
                    self.rootdummy = obj.name
                else:
                    # Node without parent and not the mdl root. Problem ?
                    warnings.warn("WARNING: " + node.name + " has no parent.")
            else:
                if node.parent in bpy.data.objects:
                    obj.parent                = bpy.data.objects[node.parent]
                    obj.matrix_parent_inverse = obj.parent.matrix_world.inverted()
                else:
                    #TODO: Try to resolve naming conflict
                    warnings.warn("WARNING: " + obj.name + " has no parent (" + node.parent + ")")

        if not nvb_glob.minimapMode:
            for (animName, anim) in self.animList.items():
                anim.convert(scene, self.rootdummy)
