import os
import math
import collections

import bpy
from bpy_extras.io_utils import unpack_list, unpack_face_list
from bpy_extras.image_utils import load_image

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


    def insertNode(self, newNode):
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


    def createObjects(self):
        for node in self.nodelist:
            #nodeType = type(node)
            nodeName = node.name
            if isinstance(node, nvb.node.Trimesh):
                # Create mesh
                mesh = bpy.data.meshes.new(nodeName)
                mesh.vertices.add(len(node.verts))
                mesh.vertices.foreach_set('co', unpack_list(node.verts))
                mesh.tessfaces.add(len(node.faces))
                mesh.tessfaces.foreach_set('vertices_raw', unpack_face_list(node.faces))

                # Create material
                material = bpy.data.materials.new(nodeName+'.mat')
                material.diffuse_color      = node.diffuse
                material.diffuse_intensity  = 1.0
                material.specular_color     = node.specular
                texName = node.bitmap
                if (texName != nvb.presets.null):
                    texture = material.texture_slots.add()
                    # Make sure textures are unique
                    if (texName in bpy.data.textures)):
                        texture.texture = bpy.data.textures[texName]
                    else:
                        pass
                        
                mesh.materials.append(material)
    
                # Add the texture coordinates 
                # Check if bitmap is NULL. Some jokers put in texture
                # coordinates whithout textures, which results
                # in an error
                if ( len(node.tverts) > 0 and
                     mesh.tessfaces and
                     texName != nvb.presets.null ):   
                    uv_name = nodeName+'_uv'
                    node_uv = node_mesh.tessface_uv_textures.new(uv_name)
                    node_mesh.tessface_uv_textures.active = node_uv

                    for i in range(len(pnode['faces_tverts'])):
                        blender_face = mesh.tessfaces[i] # New Face
                        
                        blender_face.material_index = 0
                        # Get a tessface
                        blender_tface = node_mesh.tessface_uv_textures[0].data[i]
                        
                        # Get the indices of the tverts for this face
                        tvert_idx = parsed_node['faces_tverts'][i]
                        
                        # Get the indices of the verts (for eekadoodle fix)
                        tvert_idx  = node.faces[i]
                        
                        # BUG - Evil eekadoodle problem where faces that have vert index 0 at location 3 are shuffled.
                        if tvert_idx[2] == 0:
                            tvert_idx = tvert_idx[1], tvert_idx[2], tvert_idx[0]
                        # END EEEKADOODLE FIX    
                        
                        # Add uv coordinates to face
                        blender_tface.uv1 = node.tverts[tvert_idx[0]]
                        blender_tface.uv2 = node.tverts[tvert_idx[1]]
                        blender_tface.uv3 = node.tverts[tvert_idx[2]]
                        # Link texture to face
                        blender_tface.image = node_mat.texture_slots[0].texture.image
    
                # After calling update() tessfaces become inaccessible
                #node_mesh.validate()    
                mesh.update()
            elif isinstance(node, nvb.node.Light):
                pass
            elif isinstance(node, nvb.node.Emitter):
                pass