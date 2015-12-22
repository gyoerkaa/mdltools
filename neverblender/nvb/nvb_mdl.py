import os
import math
import collections
import warnings

import bpy

from . import nvb_node
from . import nvb_anim
from . import nvb_def
from . import nvb_glob


class Mdl():
    def __init__(self):
        self.nodeList  = collections.OrderedDict()
        self.animList  = dict() # No need to retain order
        self.rootdummy = ''

        self.name           = 'UNNAMED'
        self.supermodel     = nvb_def.null
        self.animScale      = 1.0
        self.classification = 'UNKNOWN'


    def addAsciiNode(self, asciiBlock):
        if asciiBlock is None:
            raise nvb_def.MalformedMdlFile('Empty Node')

        nodeType = ''
        try:
            nodeType = asciiBlock[0][1].lower()
        except (IndexError, AttributeError):
            raise nvb_def.MalformedMdlFile('Invalid node type')

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
            raise nvb_def.MalformedMdlFile('Invalid node type')

        node.parse(asciiBlock)
        self.addNode(node)


    def addAsciiAnimation(self, asciiBlock):
        if asciiBlock is None:
            raise nvb_def.MalformedMdlFile('Empty Animation')

        animation = nvb_anim.AnimationBlock()
        animation.getAnimFromAscii(asciiBlock)

        self.addAnimation(animation)


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
            if (node.parent == nvb_def.null):
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
                anim.addAnimToScene(scene, self.rootdummy)


    def toAscii(self, rootDummyName = ''):
        pass
