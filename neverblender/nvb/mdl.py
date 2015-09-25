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


    def getNode(self, nodeId)
        if nodeId in self.nodeList:
            return self.nodeList[nodeId]
        else
            return False


    def addAnim(self, anim):
        pass


    def import_(self):
        for node in self.nodelist:
            nodeType = type(node)
            if nodeType == nvb.node.trimesh:
                mesh = bpy.data.meshes.new(node.name)
            
                mesh.vertices.add(len(node.verts))
                mesh.vertices.foreach_set('co', unpack_list(node.verts))
                mesh.tessfaces.add(len(node.faces))
                mesh.tessfaces.foreach_set('vertices_raw', unpack_face_list(node.faces))

                material = bpy.data.materials.new(node.name+'.mat')
                # Set material properties
                material.diffuse_color      = node.diffuse
                material.diffuse_intensity  = 1.0
                material.specular_color     = node.specular
