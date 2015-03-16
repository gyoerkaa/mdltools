# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


import bpy
import os
import math
import mathutils
import collections
from datetime import datetime
from . import amt_utils
from . import amt_presets

###########################################################
## Variables
###########################################################


glob_mdl_filepath     = ''
glob_mdl_filename     = ''
glob_mdl_filepath     = ''
glob_export_selection = 'ALL'
glob_sourcefile       = 'unknown'
glob_export_walkmesh  = True
glob_triangulate      = True
glob_apply_modifiers  = True
glob_export_shadgr    = False


glob_mdl_classification   = 'CHARACTER'
glob_walkmesh_type        = 'NONE'
glob_modelname            = 'unnamed'
glob_supermodel           = 'NULL'
glob_mdl_animationscale   = 1.0
glob_ascii_aabb_node      = [] # Needed for mdl and walkmesh
glob_export_scene         = None
glob_mdl_object_name_list = [] # Needed for skinmeshes and animations


glob_gen_digits    = 4
glob_angle_digits  = 4
glob_weight_digits = 3
glob_color_digits  = 3
glob_aabb_digits   = 2


###########################################################
## Helpers
###########################################################


def get_aurora_node_type(aurora_object):
    
    if (aurora_object.type == 'MESH'):
        node_type = aurora_object.auroraprops.meshtype.lower()
    elif (aurora_object.type == 'EMPTY'):
        node_type = 'dummy'
    elif (aurora_object.type == 'LAMP'):
        node_type = 'light'
    else:
        node_type = 'dummy'
    
    return node_type


def write_to_file(mdl_file, line_list):
    for line in line_list:
        mdl_file.write(line + '\n')


def add_child_objects(object, object_list):
    '''
    Note: An object can have only one parent, so we don't have to check for duplicates
    (which would otherwise lead to endless loops)
    '''
    
    # Lamps first
    for child in object.children:
        if (child.type == 'LAMP'):
            object_list.append(child)
            # Add the children of the current child
            add_child_objects(child, object_list)
    
    # Other objects second
    for child in object.children:
        if (child.type != 'LAMP'):
            object_list.append(child)
            # Add the children of the current child
            add_child_objects(child, object_list)
    
    return object_list


def get_export_objects():
    '''
    Get a list of objects to export depending on the
    selected mode (All objects, selected objects or active layers only)
    '''
    global glob_mdl_classification
    global glob_modelname
    global glob_supermodel
    global glob_mdl_animationscale
    
    # Search for the mdl base object (take the first found root object)    
    if (glob_export_selection == 'SELECTION'):
        # Search for mdl base in the current selection
        for object in glob_export_scene.objects:
            if (object.select):
                if (amt_utils.getIsMdlBase(object)):
                    mdlbase_object = object
                    break
    
    elif (glob_export_selection == 'LAYER'):
        # Search for mdl base in the active layers of the current scene
        for object in glob_export_scene.objects:
            # Check if the object is on an active layer
            is_active = False
            i = 0
            while (i < len(glob_export_scene.layers)):
                is_active = (glob_export_scene.layers[i] == True) and (object.layers[i] == True)
                i += 1
            
            if (is_active):
                if (amt_utils.getIsMdlBase(object)):
                    mdlbase_object = object
                    break
    
    else:
        # Is the currently selected object a mdl base ?
        # If so, take that one
        if (amt_utils.getIsMdlBase(bpy.context.object)):
            mdlbase_object = bpy.context.object         
        else:           
            # Search for mdl base in the current scene
            for object in glob_export_scene.objects:
                if (amt_utils.getIsMdlBase(object)):
                    mdlbase_object = object
                    break
    
    # Get all child objects. 
    # We do not care for the export setting while adding the child objects
    # The root object is the only object, where the settings matter
    object_list = []
    try:
        # Save some general model data for later use
        glob_mdl_classification = mdlbase_object.auroraprops.classification
        glob_modelname          = mdlbase_object.name
        if mdlbase_object.auroraprops.supermodel:
            glob_supermodel         = mdlbase_object.auroraprops.supermodel        
        glob_mdl_animationscale = mdlbase_object.auroraprops.animationscale
        
        object_list.append(mdlbase_object)
        add_child_objects(mdlbase_object, object_list)
    except NameError:
        print('ERROR: No mdl base object. Model export Failed')
    
    return object_list

 
def get_walkmesh_objects():
    '''
    Get a list of objects to export depending on the
    selected mode (All objects, selected objects or active layers only)
    '''
    global glob_walkmesh_type
    
    # Search for the root object (take the first found root object)
    if (glob_export_selection == 'SELECTION'):
        # Export selected objects only
        for object in glob_export_scene.objects:
            if (not object.parent) and (object.select):
                if (object.type == 'EMPTY'):
                    if (object.auroraprops.dummytype == 'PWKBASE'):
                        base_object = object
                        glob_walkmesh_type = 'PWK'
                        break
                    elif (object.auroraprops.dummytype == 'DWKBASE'):
                        base_object = object
                        glob_walkmesh_type = 'DWK'
                        break
    
    elif (glob_export_selection == 'LAYER'):
        # Export all objects from active layers in current scene
        for object in glob_export_scene.objects:
            # Check if the object is on an active layer
            is_active = False
            i = 0
            while (i < len(glob_export_scene.layers)):
                is_active = (glob_export_scene.layers[i] == True) and (object.layers[i] == True)
                i += 1
            
            if (not object.parent) and (is_active):
                if (object.type == 'EMPTY'):
                    if (object.auroraprops.dummytype == 'PWKBASE'):
                        base_object = object
                        glob_walkmesh_type = 'PWK'
                        break
                    elif (object.auroraprops.dummytype == 'DWKBASE'):
                        base_object = object
                        glob_walkmesh_type = 'DWK'
                        break
    
    else:
        # Export everything in current scene
        for object in glob_export_scene.objects:
            if (not object.parent):
                if (object.type == 'EMPTY'):
                    if (object.auroraprops.dummytype == 'PWKBASE'):
                        base_object = object
                        glob_walkmesh_type = 'PWK'
                        break
                    elif (object.auroraprops.dummytype == 'DWKBASE'):
                        base_object = object
                        glob_walkmesh_type = 'DWK'
                        break
    
    # Get all child objects. 
    # We do not care for the export setting while adding the child objects
    # The root object is the only object, where the settings matter
    object_list = []
    try:
        object_list.append(base_object)
        add_child_objects(base_object, object_list)
    except NameError:
        print('WARNING: No walkmesh base object. Walkmesh export failed')
    
    return object_list


def add_to_tvert_list(new_tvert, tvert_list):
    ''' 
    We want texture vertices to be unique
    The tvert list should behave like an ordered set.
    When an element is inserted, the index of the element should be returned
    '''  
    loc = -1
    for idx, tvert in enumerate(tvert_list):
        if (tvert[0] == new_tvert[0]) and (tvert[1] == new_tvert[1]):
            loc = idx
            break
    
    if (loc>=0):
        return loc
    else:      
        tvert_list.append(new_tvert)
        return (len(tvert_list)-1)


def get_walkmesh_filepath():
    ''' 
    
    '''
    walkmesh_filepath = ''
    
    if (glob_mdl_classification == 'TILE'):
        walkmesh_filepath = os.fsencode(os.path.join(glob_mdl_filedir, glob_mdl_filename + '.wok'))
    elif (glob_mdl_classification == 'CHARACTER'):
        # Could be placeable
        walkmesh_filepath = os.fsencode(os.path.join(glob_mdl_filedir, glob_mdl_filename + '.pwk'))
    elif (glob_mdl_classification == 'DOOR'):
        walkmesh_filepath = os.fsencode(os.path.join(glob_mdl_filedir, glob_mdl_filename + '.dwk'))
    
    return walkmesh_filepath


###########################################################
## Walkmesh generation
###########################################################


def generate_aabbtree(aabb_tree, face_list, rec_level = 0):
    
    if (rec_level > 100):
        print('WARNING: Error generating aabb. Recursion level exceeds 100')
        aabb_tree = []
        return
    
    if not face_list:
        # We are finished with the generation
        return
    
    # Calculate Bounding box centers and min/max coordinates
    bb_min         = mathutils.Vector(( 100000.0,  100000.0,  100000.0))
    bb_max         = mathutils.Vector((-100000.0, -100000.0, -100000.0))
    bb_avgcentroid = mathutils.Vector((0.0, 0.0, 0.0))
    for face in face_list:
        face_vertices = face[1]
        # Every vertex in the face
        for vertex in face_vertices:
            # We have to check 2x3 coordinates (min and max)
            for ax in range(3):
                # First the min
                if bb_min[ax] > vertex[ax]:
                    bb_min[ax] = vertex[ax]
                # Then the max
                if bb_max[ax] < vertex[ax]:
                     bb_max[ax] = vertex[ax]                 
        
        face_centroid = face[2]
        bb_avgcentroid = bb_avgcentroid + face_centroid
    
    bb_avgcentroid = bb_avgcentroid / len(face_list)
    
    bb_centroid = (bb_min + bb_max) /2
    
    if (len(face_list) == 1):
        # Only one face left in face list
        # This node is a leaf, save the face in the leaf
        linked_face_idx = face_list[0][0]
        aabb_treenode = [bb_min.x, bb_min.y, bb_min.z, bb_max.x, bb_max.y, bb_max.z, linked_face_idx]
        aabb_tree.append(aabb_treenode)
    else:
        # This is a node in the tree
        linked_face_idx = -1 # -1 indicates nodes
        aabb_treenode = [bb_min.x, bb_min.y, bb_min.z, bb_max.x, bb_max.y, bb_max.z, linked_face_idx]
        aabb_tree.append(aabb_treenode)
        
        # Size of bounding box
        bb_size = bb_max - bb_min
        
        # Longest axis of bounding box
        split_axis = 0 # x
        if (bb_size.y > bb_size.x):
            split_axis = 1 # y
        if (bb_size.z > bb_size.y):
            split_axis = 2 # z
        
        # Change axis in case points are coplanar with
        # the split plane
        change_axis = True
        for face in face_list:
            face_centroid = face[2]
            change_axis = change_axis and (face_centroid[split_axis] == bb_avgcentroid[split_axis])
        
        if (change_axis):
            split_axis += 1
            if (split_axis >= 3):
                split_axis = 0
        
        # Put items on the left- and rightside of the splitplane
        # into sperate lists
        face_list_left  = []
        face_list_right = []
        found_split     = False
        tested_axes     = 1
        while not found_split:
            # Sort faces by side
            face_list_left  = []
            face_list_right = [] 
            leftside        = True
            for face in face_list:
                face_centroid = face[2]
                
                leftside = (face_centroid[split_axis] < bb_avgcentroid[split_axis])
                if leftside:
                    face_list_left.append(face)
                else:
                    face_list_right.append(face)
                    
            # Try to prevent tree degeneration
            if (face_list_left) and (face_list_right):
                # Neither list is empty, this split will do just fine
                found_split = True
            else:
                # At least one of the list is empty
                # Try another axis to prevent degeneration
                tested_axes += 1
                
                split_axis  += 1
                if (split_axis >= 3):
                    split_axis = 0
                if (tested_axes >= 3):
                    # We have tried all axes, but
                    # the tree degenerates with each of them
                    # Just take the degenerate one
                    print('WARNING: Error generating aabb. Split problem.')
                    aabb_tree = []
                    return
            
        generate_aabbtree(aabb_tree, face_list_left, rec_level+1)
        generate_aabbtree(aabb_tree, face_list_right, rec_level+1)


def generate_ascii_aabbtree(walkmesh):
    
    # Grab all vertices
    vert_list = []
    for vertex in walkmesh.vertices:
        vert_list.append((vertex.co[0], vertex.co[1], vertex.co[2]))    
    
    face_list     = []
    face_idx      = 0
    for tessface in walkmesh.tessfaces:
        if (len(tessface.vertices) == 3):
            v0_idx = tessface.vertices[0]
            v1_idx = tessface.vertices[1]
            v2_idx = tessface.vertices[2]
            
            face_centroid = mathutils.Vector((walkmesh.vertices[v0_idx].co + walkmesh.vertices[v1_idx].co + walkmesh.vertices[v2_idx].co)/3)
            face_list.append((face_idx, [walkmesh.vertices[v0_idx].co, walkmesh.vertices[v1_idx].co, walkmesh.vertices[v2_idx].co], face_centroid))
            face_idx += 1
        
        elif (len(tessface.vertices) == 4):
            #Quad
            if (glob_triangulate):
                v0_idx = tessface.vertices[0]
                v1_idx = tessface.vertices[1]
                v2_idx = tessface.vertices[2]
                v3_idx = tessface.vertices[3]
                
                face_centroid = mathutils.Vector((walkmesh.vertices[v0_idx].co + walkmesh.vertices[v1_idx].co + walkmesh.vertices[v2_idx].co)/3)
                face_list.append((face_idx, [walkmesh.vertices[v0_idx].co, walkmesh.vertices[v1_idx].co, walkmesh.vertices[v2_idx].co], face_centroid))
                face_idx += 1
                
                face_centroid = mathutils.Vector((walkmesh.vertices[v2_idx].co + walkmesh.vertices[v3_idx].co + walkmesh.vertices[v0_idx].co)/3)
                face_list.append((face_idx, [walkmesh.vertices[v2_idx].co, walkmesh.vertices[v3_idx].co, walkmesh.vertices[v0_idx].co], face_centroid))
                face_idx += 1
            else:
                # This is a Quad and we are not allowed to triangulate: We are unable export this
                print('WARNING: Quad in walkmesh. Unable to generate aabb, triangulation required (manual or activate export option)')
                return []            
        else:
            # Ngon or no polygon at all (This should never be the case with tessfaces)
            print('WARNING: Ngon in walkmesh. Unable to generate aabb.')
            return []
    
    aabb_tree = []
    generate_aabbtree(aabb_tree, face_list)
    
    ascii_tree = []
    if aabb_tree:
        tree_node = aabb_tree.pop(0)
        ascii_tree.append('  aabb  ' + 
                          ' ' + 
                          str(round(tree_node[0], glob_aabb_digits)) + 
                          ' ' +
                          str(round(tree_node[1], glob_aabb_digits)) + 
                          ' ' +
                          str(round(tree_node[2], glob_aabb_digits)) + 
                          ' ' +
                          str(round(tree_node[3], glob_aabb_digits)) + 
                          ' ' +
                          str(round(tree_node[4], glob_aabb_digits)) + 
                          ' ' +
                          str(round(tree_node[5], glob_aabb_digits)) + 
                          ' ' + 
                          str(tree_node[6]) )
        for tree_node in aabb_tree:
            ascii_tree.append('    ' + 
                              str(round(tree_node[0], glob_aabb_digits)) + 
                              ' ' +
                              str(round(tree_node[1], glob_aabb_digits)) + 
                              ' ' +
                              str(round(tree_node[2], glob_aabb_digits)) + 
                              ' ' +
                              str(round(tree_node[3], glob_aabb_digits)) + 
                              ' ' +
                              str(round(tree_node[4], glob_aabb_digits)) + 
                              ' ' +
                              str(round(tree_node[5], glob_aabb_digits)) + 
                              ' ' + 
                              str(tree_node[6]) )
    
    return ascii_tree


###########################################################
## Export
###########################################################


def get_ascii_emitter(mesh_object):
    ascii_emitter = []
    
    particle_system = mesh_object.particle_systems.active
    ps_settings     = particle_system.settings
    
    ascii_emitter.append('  xSize ' + str(round(mesh_object.dimensions[0]*100, glob_gen_digits)))
    ascii_emitter.append('  ySize ' + str(round(mesh_object.dimensions[1]*100, glob_gen_digits)))
    
    ascii_emitter.append('  birthrate ' + str(ps_settings.auroraprops.birthrate)) 
    ascii_emitter.append('  frameStart ' + str(int(ps_settings.frame_start)))    
    ascii_emitter.append('  frameEnd ' + str(int(ps_settings.frame_end)))    
    ascii_emitter.append('  lifeExp ' + str(round(ps_settings.auroraprops.lifeexp, glob_gen_digits)))
    ascii_emitter.append('  mass ' + str(round(ps_settings.mass, 1)))
    ascii_emitter.append('  velocity ' + str(round(ps_settings.normal_factor, glob_gen_digits)))
    ascii_emitter.append('  randvel ' + str(round(ps_settings.factor_random, glob_gen_digits)))
    tmp = '1' if (ps_settings.effector_weights.wind > 0.001) else '0'
    ascii_emitter.append('  affectedByWind ' + tmp)    
    tmp = '1' if (ps_settings.effector_weights.drag > 0.001) else '0'
    ascii_emitter.append('  drag ' + tmp)
    tmp = '1' if (ps_settings.effector_weights.gravity > 0.001) else '0'
    ascii_emitter.append('  grav ' + tmp)
    
    # Inheritance props
    tmp = '1' if (ps_settings.auroraprops.inherit) else '0'
    ascii_emitter.append('  inherit ' + tmp) 
    tmp = '1' if (ps_settings.auroraprops.inherit_vel) else '0'
    ascii_emitter.append('  inheritvel ' + tmp)
    tmp = '1' if (ps_settings.auroraprops.inherit_local) else '0'
    ascii_emitter.append('  inherit_local ' + tmp)
    tmp = '1' if (ps_settings.auroraprops.inherit_part) else '0'
    ascii_emitter.append('  inherit_part ' + tmp)    
    
    # Spawntype
    if (ps_settings.auroraprops.blend == 'NORMAL'):
        tmp = 'Normal'
    elif (ps_settings.auroraprops.blend == 'TRAIL'):
        tmp = 'Trail'
    else:
        tmp = 'Normal'
    ascii_emitter.append('  spawntype ' + tmp)
    
    # Update type
    if (ps_settings.auroraprops.update == 'FOUNTAIN'):
        tmp = 'Fountain'
    elif (ps_settings.auroraprops.update == 'SINGLE'):
        tmp = 'Single'
    elif (ps_settings.auroraprops.update == 'EXPLOSION'):
        tmp = 'Explosion'
    elif (ps_settings.auroraprops.update == 'LIGHTNING'):
        tmp = 'Lightning'        
    else:
        tmp = 'Fountain'
    ascii_emitter.append('  update ' + tmp)
    
    # Render type
    if (ps_settings.auroraprops.render == 'NORMAL'):
        tmp = 'Normal'
    elif (ps_settings.auroraprops.render == 'LINKED'):
        tmp = 'Linked'
    elif (ps_settings.auroraprops.render == 'BB2LZ'):
        tmp = 'Billboard_to_Local_Z'
    elif (ps_settings.auroraprops.render == 'BB2WZ'):
        tmp = 'Billboard_to_World_Z'
    elif (ps_settings.auroraprops.render == 'AL2WZ'):
        tmp = 'Aligned_to_World_Z'
    elif (ps_settings.auroraprops.render == 'AL2PD'):
        tmp = 'Aligned_to_Particle_Dir'
    elif (ps_settings.auroraprops.render == 'MOBLUR'):
        tmp = 'Motion_Blur'        
    else:
        tmp = 'Normal'
    ascii_emitter.append('  render ' + tmp)
    
    # Blend type
    if (ps_settings.auroraprops.blend == 'NORMAL'):
        tmp = 'Normal'
    elif (ps_settings.auroraprops.blend == 'PUNCH-THROUGH'):
        tmp = 'Punch-Through'
    elif (ps_settings.auroraprops.blend == 'LIGHTEN'):
        tmp = 'Lighten'
    else:
        tmp = 'Normal'
    ascii_emitter.append('  blend ' + tmp)
    
    #Texture
    tmp = 'NULL'
    # Check if this object has a material assigned to it
    active_mat = mesh_object.active_material
    if active_mat:
        # Check if this material has a texture assigned
        active_tex = active_mat.active_texture
        if active_tex:
            # The texture should be an image texture
            if (active_tex.type == 'IMAGE'):
                # There should be an image assigned
                if (active_tex.image):
                    tmp = amt_utils.get_image_filename(active_tex.image)
    ascii_emitter.append('  texture ' + tmp)
    tmp = ps_settings.billboard_uv_split
    ascii_emitter.append('  xgrid ' + str(tmp))
    ascii_emitter.append('  ygrid ' + str(tmp))
    
    # Blast props
    ascii_emitter.append('  blastRadius ' + str(round(ps_settings.auroraprops.blastradius, glob_gen_digits)))
    ascii_emitter.append('  blastLength ' + str(round(ps_settings.auroraprops.blastlength, glob_gen_digits)))
    
    # Animation props
    ascii_emitter.append('  colorStart ' + str(round(ps_settings.auroraprops.colorstart[0], glob_color_digits)) + ' ' + 
                                           str(round(ps_settings.auroraprops.colorstart[1], glob_color_digits)) + ' ' + 
                                           str(round(ps_settings.auroraprops.colorstart[2], glob_color_digits))  )
    ascii_emitter.append('  colorEnd ' + str(round(ps_settings.auroraprops.colorstart[0], glob_color_digits)) + ' ' + 
                                         str(round(ps_settings.auroraprops.colorstart[1], glob_color_digits)) + ' ' + 
                                         str(round(ps_settings.auroraprops.colorstart[2], glob_color_digits))  )                                         
    ascii_emitter.append('  alphaStart ' + str(round(ps_settings.auroraprops.alphastart, glob_gen_digits)))
    ascii_emitter.append('  alphaEnd ' + str(round(ps_settings.auroraprops.alphaend, glob_gen_digits)))
    ascii_emitter.append('  sizeStart ' + str(round(ps_settings.auroraprops.sizestart, glob_gen_digits)))
    ascii_emitter.append('  sizeEnd ' + str(round(ps_settings.auroraprops.sizeend, glob_gen_digits)))
    ascii_emitter.append('  sizeStart_y ' + str(round(ps_settings.auroraprops.sizestart_y, glob_gen_digits)))
    ascii_emitter.append('  sizeEnd_y ' + str(round(ps_settings.auroraprops.sizeend_y, glob_gen_digits)))
    
    # Misc props
    tmp = '1' if (ps_settings.auroraprops.splat ) else '0'
    ascii_emitter.append('  splat ' + tmp)     
    tmp = '1' if (ps_settings.auroraprops.istinted) else '0'
    ascii_emitter.append('  m_istinted ' + tmp) 
    tmp = '1' if (ps_settings.auroraprops.bounce) else '0'
    ascii_emitter.append('  bounce ' + tmp)
    tmp = '1' if (ps_settings.auroraprops.random) else '0'
    ascii_emitter.append('  random ' + tmp) 
    ascii_emitter.append('  bounce_co ' + str(round(ps_settings.auroraprops.bounce_co, glob_gen_digits)))
    ascii_emitter.append('  spread ' + str(round(ps_settings.auroraprops.spread, glob_gen_digits)))
    ascii_emitter.append('  particleRot ' + str(round(ps_settings.auroraprops.particlerot, glob_gen_digits)))    
    ascii_emitter.append('  fps ' + str(ps_settings.auroraprops.fps))
    ascii_emitter.append('  blurLength ' + str(round(ps_settings.auroraprops.blurlength, glob_gen_digits)))
    tmp = ps_settings.auroraprops.chunkname
    if (tmp != ''):
        ascii_emitter.append('  chunkname ' + tmp)
    tmp = '1' if (ps_settings.auroraprops.loop) else '0'
    ascii_emitter.append('  loop ' + tmp)
    ascii_emitter.append('  renderorder ' + str(ps_settings.auroraprops.renderorder))
    ascii_emitter.append('  deadspace ' + str(round(ps_settings.auroraprops.deadspace, glob_gen_digits)))
    tmp = '1' if (ps_settings.auroraprops.twosidedtex) else '0'
    ascii_emitter.append('  twosidedtex ' + tmp)   
    
    # Lightning props
    ascii_emitter.append('  lightningDelay ' + str(round(ps_settings.auroraprops.lightningdelay, glob_gen_digits)))
    ascii_emitter.append('  lightningRadius ' + str(round(ps_settings.auroraprops.lightningradius, glob_gen_digits)))
    ascii_emitter.append('  lightningSubDiv ' + str(ps_settings.auroraprops.lightningsubdiv))
    ascii_emitter.append('  lightningScale ' + str(round(ps_settings.auroraprops.lightningscale, glob_gen_digits)))

    # p2p props
    ascii_emitter.append('  p2p ' + str(ps_settings.auroraprops.p2p))
    if (ps_settings.auroraprops.p2p == 'BEZIER'):
        tmp = '1'
    elif (ps_settings.auroraprops.p2p == 'GRAVITY'):
        tmp = '2'
    else:
        tmp = '1'
    ascii_emitter.append('  p2p_sel ' + tmp)
    ascii_emitter.append('  p2p_bezier2 ' + str(round(ps_settings.auroraprops.p2p_bezier2, glob_gen_digits)))
    ascii_emitter.append('  p2p_bezier3 ' + str(round(ps_settings.auroraprops.p2p_bezier3, glob_gen_digits)))
    ascii_emitter.append('  threshold ' + str(round(ps_settings.auroraprops.threshold, glob_gen_digits)))
    ascii_emitter.append('  combinetime ' + str(round(ps_settings.auroraprops.combinetime, glob_gen_digits)))
    
    return ascii_emitter

    
def get_face_shadinggr(tface, mesh_object):
    '''
    A face belongs to a shading/vertex group, if all of
    its vertices belong to a shading/vertex group
    If it belongs to more than one group, the first found group
    will be used.
    Takes an object and one of its tessfaces ans parameters
    '''
    
    shadegr_id = 1
    if (not glob_export_shadgr):
        return shadegr_id
        
    # Set of vertex groups common to all vertices of the 
    # face. There should be only one, if there are more
    # we just pick one
    common_vgroups = set(mesh_object.vertex_groups.keys())
    
    if common_vgroups:
        # Iterate over vertex indices of the face
        for vertex_idx in tface.vertices:
            # Get actual vertex from the mesh object
            vertex = mesh_object.data.vertices[vertex_idx]
            # Vertex groups of the vertex
            vertex_vgroups = set([])
            for vgroup_element in vertex.groups:
                vgroup = mesh_object.vertex_groups[vgroup_element.group]
                if amt_utils.get_is_shadinggr(vgroup):
                    vertex_vgroups.add(vgroup.name)
            common_vgroups = common_vgroups & vertex_vgroups
    
    
        if common_vgroups:        
            # Get an element from the set and get its shading
            # group id
            
            try:
                shadegr_id = int(common_vgroups.pop().replace(amt_presets.shading_group_name,''))
            except:
                print('WARNING: Unable to get shading group.')
            
    return shadegr_id

    
def get_ascii_geometry(mesh_object, textured = True):
    ascii_geometry = []
    
    try:
        mesh = mesh_object.to_mesh(glob_export_scene, glob_apply_modifiers, 'PREVIEW')
    except RuntimeError:
        printf('WARNING: Error exporting geometry from ' + mesh_object.name)
        mesh = None
    
    if mesh is not None:
        # We need only to scale (rotation & location will be stored in the model)
        scale_matrix = mathutils.Matrix([[mesh_object.scale.x,0,0,0],
                                         [0,mesh_object.scale.y,0,0],
                                         [0,0,mesh_object.scale.z,0],
                                         [0,0,0,1]])
        trans_matrix = mesh_object.matrix_parent_inverse.copy()*scale_matrix 
        mesh.transform(trans_matrix)
        
        vert_list       = [] # Vertex coordinates
        face_list       = [] # Indices of 3 verts pointing to the tvert_list
        tvert_list      = [] # Texture coordinates with no duplicates
        
        # Grab all vertices
        for vertex in mesh.vertices:
            vert_list.append((vertex.co[0], vertex.co[1], vertex.co[2]))
        
        # Grab all faces and corresponding tverts
        tessfaces_uvs = mesh.tessface_uv_textures.active
        tessfaces     = mesh.tessfaces
        for idx in range(len(tessfaces)):
            face              = tessfaces[idx]
            face_shadegr      = get_face_shadinggr(face, mesh_object)
            face_material_idx = face.material_index
            
            if (len(face.vertices) == 3):
                #Triangle
                uv1_idx = 0
                uv2_idx = 0
                uv3_idx = 0
                if (tessfaces_uvs is not None):
                    # No uv data means no texture
                    face_uv = tessfaces_uvs.data[idx]
                    uv1_idx = add_to_tvert_list(face_uv.uv1, tvert_list)
                    uv2_idx = add_to_tvert_list(face_uv.uv2, tvert_list)
                    uv3_idx = add_to_tvert_list(face_uv.uv3, tvert_list)
                
                face_list.append([face.vertices[0], face.vertices[1], face.vertices[2], face_shadegr, uv1_idx, uv2_idx, uv3_idx, face_material_idx])
            
            elif (len(face.vertices) == 4):
                #Quad
                if (glob_triangulate):
                    uv1_idx = 0
                    uv2_idx = 0
                    uv3_idx = 0
                    uv4_idx = 0                 
                    if (tessfaces_uvs is not None):
                        # No uv data means no texture
                        face_uv = tessfaces_uvs.data[idx]
                        uv1_idx = add_to_tvert_list(face_uv.uv1, tvert_list)
                        uv2_idx = add_to_tvert_list(face_uv.uv2, tvert_list)
                        uv3_idx = add_to_tvert_list(face_uv.uv3, tvert_list)
                        uv4_idx = add_to_tvert_list(face_uv.uv4, tvert_list)
                    
                    face_list.append([face.vertices[0], face.vertices[1], face.vertices[2], face_shadegr, uv1_idx, uv2_idx, uv3_idx, face_material_idx])
                    face_list.append([face.vertices[2], face.vertices[3], face.vertices[0], face_shadegr, uv3_idx, uv4_idx, uv1_idx, face_material_idx])                 
                else:
                    # This is a Quad and we are not allowed to triangulate: We are unable export this
                    print('WARNING: Quad in ' + mesh_object.name + '. Unable to export, triangulation required (manual or activate export option)')
                    return []
            else:
                # Ngon or no polygon at all (This should never be the case with tessfaces)
                print('WARNING: Ngon in ' + mesh_object.name + '. Unable to export.')
                return []
        
        ascii_geometry.append('  verts ' + str(len(vert_list)))
        for vert in vert_list:
            ascii_geometry.append('    ' + str(round(vert[0], glob_gen_digits)) + ' ' +
                                           str(round(vert[1], glob_gen_digits)) + ' ' +
                                           str(round(vert[2], glob_gen_digits)) )
        
        if (textured):
            ascii_geometry.append('  faces ' + str(len(face_list)))
            for face in face_list:
                ascii_geometry.append('    ' + str(face[0]) + ' '  + # Vertex index
                                               str(face[1]) + ' '  + # Vertex index
                                               str(face[2]) + '  ' + # Vertex index
                                               str(face[3]) + '  ' + # Smoth group/Shading group (whatever)
                                               str(face[4]) + ' '  + # Texture vertex index
                                               str(face[5]) + ' '  + # Texture vertex index
                                               str(face[6]) + '  ' + # Texture vertex index
                                               str(face[7]) )        # Misc
            
            ascii_geometry.append('  tverts ' + str(len(tvert_list)))  
            for tvert in tvert_list:
                ascii_geometry.append('    ' + str(round(tvert[0], glob_gen_digits)) + ' ' +
                                               str(round(tvert[1], glob_gen_digits)) + ' ' +
                                               '0' )
        
        else:
            ascii_geometry.append('  faces ' + str(len(face_list)))
            for face in face_list:
                ascii_geometry.append('    ' + str(face[0]) + ' '  + # Vertex index
                                               str(face[1]) + ' '  + # Vertex index
                                               str(face[2]) + '  ' + # Vertex index
                                               str(face[3]) + '  ' + # Smoth group/Shading group (whatever)
                                               str(0)       + ' '  + # Texture vertex index
                                               str(0)       + ' '  + # Texture vertex index
                                               str(0)       + '  ' + # Texture vertex index
                                               str(face[7]) )        # Misc
        
        bpy.data.meshes.remove(mesh)
    
    return ascii_geometry

 
def get_ascii_constraints(mesh_object):
    '''
    For danglymeshes.
    Actually these are vertex weights in the danglegroup
    '''
    ascii_constraints = []
    
    # Check if there is actually a danglegroup
    danglegroup_name = mesh_object.auroraprops.danglegroup
    try:
        danglegroup = mesh_object.vertex_groups[danglegroup_name]
    except:
        print('WARNING: Invalid danglegroup for ' + mesh_object.name)
        return []
    
    num_vertices = len(mesh_object.data.vertices)
    ascii_constraints.append('  constraints ' + str(num_vertices))
    for vertex_idx, vertex in enumerate(mesh_object.data.vertices):
        try:
            ascii_constraints.append('    ' + str(round(danglegroup.weight(vertex_idx)*255, glob_weight_digits)))
        except:
            # Vertex is not part of this group
            ascii_constraints.append('    ' + '0.0')
    
    return ascii_constraints


def get_ascii_weights(mesh_object, export_object_list = []):
    '''
    For skins
    Values of the skingroups
    '''   
    
    # Get a list of skingroups for this object:  
    # To find out if a group is a skingroup check for objects
    # in the mdl list with the same name
    skingroup_list = []    
    for export_object in export_object_list:
        if export_object.name in mesh_object.vertex_groups:
            skingroup_list.append(mesh_object.vertex_groups[export_object.name])
    
    vertex_weight_list = [] 
    for vertex_idx, vertex in enumerate(mesh_object.data.vertices):
        weight_list = []
        for skingroup in skingroup_list:
            try:
                weight_list.append([skingroup.name, skingroup.weight(vertex_idx)])
            except:
                # Vertex not part of this group
                pass
        vertex_weight_list.append(weight_list)
    
    ascii_weights = []    
    if (len(vertex_weight_list) > 0):
        num_vertices = len(mesh_object.data.vertices)
        ascii_weights.append('  weights ' + str(num_vertices))
        for weight_list in vertex_weight_list:
            line = '    '
            if weight_list:
                for weight in weight_list:
                    line += weight[0] + ' ' + str(round(weight[1], glob_weight_digits)) + ' '
            else:
                # No weights for this vertex ... this is a problem
                print('WARNING: Missing vertex weight')
                line = 'ERROR: no weight'
            ascii_weights.append(line)
    
    return ascii_weights  


def get_ascii_aabb_tree(walkmesh_object):
    ascii_aabb_tree = []
    
    try:
        walkmesh = walkmesh_object.to_mesh(glob_export_scene, glob_apply_modifiers, 'PREVIEW')
    except RuntimeError:
        printf('WARNING: Error exporting geometry from ' + mesh_object.name)
        walkmesh = None
    
    if walkmesh is not None:
        # We need only to scale (no rotation or location)
        scale_matrix = mathutils.Matrix([[walkmesh_object.scale.x,0,0,0],
                                          [0,walkmesh_object.scale.y,0,0],
                                          [0,0,walkmesh_object.scale.z,0],
                                          [0,0,0,1]])
        trans_matrix = walkmesh_object.matrix_parent_inverse.copy()*scale_matrix 
        walkmesh.transform(trans_matrix)
        
        ascii_aabb_tree = generate_ascii_aabbtree(walkmesh)
    
    return ascii_aabb_tree


def get_material_properties(mesh_object):
    ascii_props = []
    
    # Check if this object has a material assigned to it
    active_mat = mesh_object.active_material
    if active_mat:
        if (active_mat.use_transparency):
            alpha_val = 1-active_mat.alpha
            ascii_props.append('  alpha ' + str(round(alpha_val, 1)))
        else:
            ascii_props.append('  alpha 1.0')
        
        ascii_props.append('  ambient ' + str(round(mesh_object.auroraprops.ambientcolor[0], glob_color_digits)) + ' ' + 
                                          str(round(mesh_object.auroraprops.ambientcolor[1], glob_color_digits)) + ' ' + 
                                          str(round(mesh_object.auroraprops.ambientcolor[2], glob_color_digits))  )
                                              
        ascii_props.append('  diffuse ' + str(round(active_mat.diffuse_color[0], glob_color_digits)) + ' ' + 
                                          str(round(active_mat.diffuse_color[1], glob_color_digits)) + ' ' + 
                                          str(round(active_mat.diffuse_color[2], glob_color_digits))  )
        
        ascii_props.append('  specular ' + str(round(active_mat.specular_color[0], glob_color_digits)) + ' ' + 
                                           str(round(active_mat.specular_color[1], glob_color_digits)) + ' ' + 
                                           str(round(active_mat.specular_color[2], glob_color_digits))  )
        
        ascii_props.append('  shininess ' + str(mesh_object.auroraprops.shininess))  
        
        # Check if this material has a texture assigned
        active_tex = active_mat.active_texture
        image_name = 'NULL'
        if active_tex:
            # The texture should be an image texture
            if (active_tex.type == 'IMAGE'):
                # There should be an image assigned
                if (active_tex.image):
                    image_name = amt_utils.get_image_filename(active_tex.image)
        ascii_props.append('  bitmap ' + image_name)
    else:
        # No material, set some default values
        ascii_props.append('  alpha 1.0')
        ascii_props.append('  ambient 1.0 1.0 1.0')
        ascii_props.append('  diffuse 1.0 1.0 1.0')
        ascii_props.append('  specular 0.0 0.0 0.0')
        ascii_props.append('  shininess 1')     
        ascii_props.append('  bitmap NULL')
    
    return ascii_props


def lamp2lightnode(lamp_object):
    ascii_node = []
    
    ascii_node.append('node light ' + lamp_object.name)
    
    tmp = 'NULL'
    if lamp_object.parent:
        tmp = lamp_object.parent.name
    ascii_node.append('  parent ' + tmp) 
    
    ascii_node.append('  position ' + str(round(lamp_object.location[0], glob_gen_digits)) + ' ' + 
                                      str(round(lamp_object.location[1], glob_gen_digits)) + ' ' + 
                                      str(round(lamp_object.location[2], glob_gen_digits)) )
    
    tmp = amt_utils.getRotationAurora(lamp_object)
    ascii_node.append('  orientation ' + str(round(tmp[0], glob_angle_digits)) + ' ' +
                                         str(round(tmp[1], glob_angle_digits)) + ' ' +
                                         str(round(tmp[2], glob_angle_digits)) + ' ' +
                                         str(round(tmp[3], glob_angle_digits)) )
    
    ascii_node.append('  wirecolor ' + str(round(lamp_object.auroraprops.wirecolor[0], glob_color_digits)) + ' ' + 
                                       str(round(lamp_object.auroraprops.wirecolor[1], glob_color_digits)) + ' ' + 
                                       str(round(lamp_object.auroraprops.wirecolor[2], glob_color_digits))  )
    
    ascii_node.append('  radius ' +  str(lamp_object.data.distance))
    
    ascii_node.append('  multiplier ' +  str(lamp_object.data.energy))
    
    ascii_node.append('  color ' + str(round(lamp_object.data.color[0], glob_color_digits)) + ' ' + 
                                   str(round(lamp_object.data.color[1], glob_color_digits)) + ' ' + 
                                   str(round(lamp_object.data.color[2], glob_color_digits)) )
    
    tmp = '0' if (lamp_object.data.use_diffuse) else '1'
    ascii_node.append('  ambientonly ' + tmp)
    
    tmp = '1' if (lamp_object.auroraprops.isdynamic) else '0'
    ascii_node.append('  nDynamicType ' + tmp)
    
    tmp = '1' if (lamp_object.auroraprops.affectdynamic) else '0'
    ascii_node.append('  affectDynamic ' + tmp)
    
    tmp = '1' if (lamp_object.auroraprops.shadow) else '0'
    ascii_node.append('  shadow ' + tmp)
    
    ascii_node.append('  lightpriority ' + str(lamp_object.auroraprops.lightpriority))
    
    tmp = '1' if (lamp_object.auroraprops.fadinglight) else '0'
    ascii_node.append('  fadingLight ' + tmp)
    
    ascii_node.append('endnode')
    
    return ascii_node


def mesh2meshnode(mesh_object, export_object_list = []):
    '''
    '''
    global glob_ascii_aabb_node
    
    ascii_node = []
    
    mesh_type = mesh_object.auroraprops.meshtype
    if (mesh_type == 'AABB') and (glob_mdl_classification != 'TILE'):
        # We return an empty list, as walkmeshes are stored in a separate file
        # (with the exception of tile models)
        return []
    
    tmp = mesh_type.lower()
    ascii_node.append('node ' + tmp + ' ' + mesh_object.name)
    
    # Stuff common to all nodes and classifications
    if mesh_object.parent:
        tmp = mesh_object.parent.name
    else:
        tmp = 'NULL'
    ascii_node.append('  parent ' + tmp)
     
    ascii_node.append('  position ' + str(round(mesh_object.location[0], glob_gen_digits)) + ' ' + 
                                      str(round(mesh_object.location[1], glob_gen_digits)) + ' ' + 
                                      str(round(mesh_object.location[2], glob_gen_digits)) )
    
    tmp = amt_utils.getRotationAurora(mesh_object)
    ascii_node.append('  orientation ' + str(round(tmp[0], glob_angle_digits)) + ' ' + 
                                         str(round(tmp[1], glob_angle_digits)) + ' ' + 
                                         str(round(tmp[2], glob_angle_digits)) + ' ' + 
                                         str(round(tmp[3], glob_angle_digits)) )
    
    if (mesh_type == 'TRIMESH'):
        ascii_node.append('  wirecolor ' + str(round(mesh_object.auroraprops.wirecolor[0], glob_color_digits)) + ' ' + 
                                           str(round(mesh_object.auroraprops.wirecolor[1], glob_color_digits)) + ' ' + 
                                           str(round(mesh_object.auroraprops.wirecolor[2], glob_color_digits))  )
        
        ascii_node.extend(get_material_properties(mesh_object))
        
        tmp = '1.0'
        ascii_node.append('  scale ' + tmp)
        
        tmp = '1' if (mesh_object.auroraprops.render) else '0'
        ascii_node.append('  render ' + tmp)  
        
        tmp = '1' if (mesh_object.auroraprops.shadow) else '0'
        ascii_node.append('  shadow ' + tmp)
        
        tmp = str(mesh_object.auroraprops.transparencyhint)
        ascii_node.append('  transparencyhint ' + tmp)
        
        # For tiles only
        if (glob_mdl_classification == 'TILE'): 
            tmp = '1' if (mesh_object.auroraprops.tilefade) else '0'
            ascii_node.append('  tilefade ' + tmp)
            
            tmp = '1' if (mesh_object.auroraprops.rotatetexture) else '0'
            ascii_node.append('  rotatetexture ' + tmp)
        
        tmp = '1' if (mesh_object.auroraprops.beaming) else '0'
        ascii_node.append('  beaming ' + tmp)
        
        tmp = '1' if (mesh_object.auroraprops.inheritcolor) else '0'
        ascii_node.append('  inheritcolor ' + tmp)
        
        ascii_node.append('  selfillumcolor ' + str(round(mesh_object.auroraprops.selfillumcolor [0], glob_color_digits)) + ' ' + 
                                                str(round(mesh_object.auroraprops.selfillumcolor [1], glob_color_digits)) + ' ' + 
                                                str(round(mesh_object.auroraprops.selfillumcolor [2], glob_color_digits))  )        
        
        ascii_node.extend(get_ascii_geometry(mesh_object))
    
    elif (mesh_type == 'DANGLYMESH'):
        ascii_node.append('  wirecolor ' + str(round(mesh_object.auroraprops.wirecolor[0], glob_color_digits)) + ' ' + 
                                           str(round(mesh_object.auroraprops.wirecolor[1], glob_color_digits)) + ' ' + 
                                           str(round(mesh_object.auroraprops.wirecolor[2], glob_color_digits))  )
        
        ascii_node.extend(get_material_properties(mesh_object))
        
        tmp = '1.0'
        ascii_node.append('  scale ' + tmp)
        
        tmp = '1' if (mesh_object.auroraprops.render) else '0'
        ascii_node.append('  render ' + tmp)  
        
        tmp = '1' if (mesh_object.auroraprops.shadow) else '0'
        ascii_node.append('  shadow ' + tmp)
        
        tmp = str(mesh_object.auroraprops.transparencyhint)
        ascii_node.append('  transparencyhint ' + tmp)
        
        # For tiles only
        if (glob_mdl_classification == 'TILE'):
            tmp = '1' if (mesh_object.auroraprops.tilefade) else '0'
            ascii_node.append('  tilefade ' + tmp)
            
            tmp = '1' if (mesh_object.auroraprops.rotatetexture) else '0'
            ascii_node.append('  rotatetexture ' + tmp)
        
        tmp = '1' if (mesh_object.auroraprops.beaming) else '0'
        ascii_node.append('  beaming ' + tmp)
        
        tmp = '1' if (mesh_object.auroraprops.inheritcolor) else '0'
        ascii_node.append('  inheritcolor ' + tmp)
         
        ascii_node.append('  selfillumcolor ' + str(round(mesh_object.auroraprops.selfillumcolor [0], glob_color_digits)) + ' ' + 
                                                str(round(mesh_object.auroraprops.selfillumcolor [1], glob_color_digits)) + ' ' + 
                                                str(round(mesh_object.auroraprops.selfillumcolor [2], glob_color_digits))  )
        
        tmp = str(mesh_object.auroraprops.period)
        ascii_node.append('  period ' + tmp)
        
        tmp = str(mesh_object.auroraprops.tightness)
        ascii_node.append('  tightness ' + tmp)        
        
        tmp = str(mesh_object.auroraprops.displacement)
        ascii_node.append('  displacement ' + tmp)
        
        ascii_node.extend(get_ascii_geometry(mesh_object))
        ascii_node.extend(get_ascii_constraints(mesh_object))
    
    elif (mesh_type == 'SKIN'):
        ascii_node.append('  wirecolor ' + str(round(mesh_object.auroraprops.wirecolor[0], glob_color_digits)) + ' ' + 
                                           str(round(mesh_object.auroraprops.wirecolor[1], glob_color_digits)) + ' ' + 
                                           str(round(mesh_object.auroraprops.wirecolor[2], glob_color_digits))  )
        
        ascii_node.extend(get_material_properties(mesh_object))
        
        tmp = '1.0'
        ascii_node.append('  scale ' + tmp)
        
        tmp = '1' if (mesh_object.auroraprops.render) else '0'
        ascii_node.append('  render ' + tmp)  
        
        # No shadows on skinmeshes
        #tmp = '1' if (mesh_object.auroraprops.shadow) else '0'
        #ascii_node.append('  shadow ' + tmp)
        
        tmp = str(mesh_object.auroraprops.transparencyhint)
        ascii_node.append('  transparencyhint ' + tmp)
        
        # For tiles only
        if (glob_mdl_classification == 'TILE'):
            tmp = '1' if (mesh_object.auroraprops.tilefade) else '0'
            ascii_node.append('  tilefade ' + tmp)
            
            tmp = '1' if (mesh_object.auroraprops.rotatetexture) else '0'
            ascii_node.append('  rotatetexture ' + tmp)
        
        tmp = '1' if (mesh_object.auroraprops.beaming) else '0'
        ascii_node.append('  beaming ' + tmp)
        
        tmp = '1' if (mesh_object.auroraprops.inheritcolor) else '0'
        ascii_node.append('  inheritcolor ' + tmp)
        
        ascii_node.append('  selfillumcolor ' + str(round(mesh_object.auroraprops.selfillumcolor [0], glob_color_digits)) + ' ' + 
                                                str(round(mesh_object.auroraprops.selfillumcolor [1], glob_color_digits)) + ' ' + 
                                                str(round(mesh_object.auroraprops.selfillumcolor [2], glob_color_digits))  )
        
        ascii_node.extend(get_ascii_geometry(mesh_object))
        ascii_node.extend(get_ascii_weights(mesh_object, export_object_list))
    
    elif (mesh_type == 'AABB'):
        ascii_node.append('  wirecolor ' + str(round(mesh_object.auroraprops.wirecolor[0], glob_color_digits)) + ' ' + 
                                           str(round(mesh_object.auroraprops.wirecolor[1], glob_color_digits)) + ' ' + 
                                           str(round(mesh_object.auroraprops.wirecolor[2], glob_color_digits))  )
        ascii_node.append('  ambient 0.0 0.0 0.0')
        ascii_node.append('  diffuse 0.5 0.5 0.5')
        ascii_node.append('  specular 0.0 0.0 0.0')
        ascii_node.append('  shininess 10') 
        ascii_node.append('  bitmap NULL')
        
        ascii_node.extend(get_ascii_geometry(mesh_object, False)) # No tverts for walkmeshes
        ascii_node.extend(get_ascii_aabb_tree(mesh_object))
        glob_ascii_aabb_node = ascii_node # Save aabb node for later use
    
    elif (mesh_type == 'EMITTER'):
        ascii_node.extend(get_ascii_emitter(mesh_object))
    
    ascii_node.append('endnode')
    
    return ascii_node


def mesh2walkmeshmeshnode(mesh_object):
    '''
    '''   
    ascii_node = []

    mesh_type = mesh_object.auroraprops.meshtype
    if (glob_mdl_classification == 'TILE'):
        # We return an empty list, as tile walkmeshes/aabb nodes are created elsewhere
        # (with the exception of tile models)
        return []
    
    tmp = 'trimesh' # Everything is a trimesh here
    ascii_node.append('node ' + tmp + ' ' + mesh_object.name)
    
    # Stuff common to all nodes and classifications
    if mesh_object.parent:
        tmp = mesh_object.parent.name
    else:
        tmp = 'NULL'
    ascii_node.append('  parent ' + tmp)
    
    ascii_node.append('  position ' + str(round(mesh_object.location[0], glob_gen_digits)) + ' ' + 
                                      str(round(mesh_object.location[1], glob_gen_digits)) + ' ' + 
                                      str(round(mesh_object.location[2], glob_gen_digits)) )
    
    tmp = amt_utils.getRotationAurora(mesh_object)
    ascii_node.append('  orientation ' + str(round(tmp[0], glob_angle_digits)) + ' ' + 
                                         str(round(tmp[1], glob_angle_digits)) + ' ' + 
                                         str(round(tmp[2], glob_angle_digits)) + ' ' + 
                                         str(round(tmp[3], glob_angle_digits)) )
    
    ascii_node.append('  wirecolor ' + str(round(mesh_object.auroraprops.wirecolor[0], glob_color_digits)) + ' ' + 
                                       str(round(mesh_object.auroraprops.wirecolor[1], glob_color_digits)) + ' ' + 
                                       str(round(mesh_object.auroraprops.wirecolor[2], glob_color_digits))  )
    
    ascii_node.append('  bitmap NULL')
    
    ascii_node.extend(get_ascii_geometry(mesh_object, False))
    
    ascii_node.append('endnode')
    
    return ascii_node

  
def empty2dummynode(empty_object):
    ascii_node = []
    
    ascii_node.append('node dummy ' + empty_object.name)
    
    tmp = 'NULL'
    if empty_object.parent:
        tmp = empty_object.parent.name
    ascii_node.append('  parent ' + tmp)
    
    if (empty_object.auroraprops.dummytype == 'MDLBASE'):
        # Root dummy, no additional data here
        pass
    else:
        ascii_node.append('  position ' + str(round(empty_object.location[0], glob_gen_digits)) + ' ' + 
                                          str(round(empty_object.location[1], glob_gen_digits)) + ' ' + 
                                          str(round(empty_object.location[2], glob_gen_digits)) )
        
        tmp = amt_utils.getRotationAurora(empty_object)
        ascii_node.append('  orientation ' + str(round(tmp[0], glob_angle_digits)) + ' ' + 
                                             str(round(tmp[1], glob_angle_digits)) + ' ' + 
                                             str(round(tmp[2], glob_angle_digits)) + ' ' + 
                                             str(round(tmp[3], glob_angle_digits)) ) 
        
        ascii_node.append('  wirecolor ' + str(round(empty_object.auroraprops.wirecolor[0], glob_color_digits)) + ' ' + 
                                           str(round(empty_object.auroraprops.wirecolor[1], glob_color_digits)) + ' ' + 
                                           str(round(empty_object.auroraprops.wirecolor[1], glob_color_digits))  )
    
    ascii_node.append('endnode')
    
    return ascii_node


def empty2walkmeshdummynode(empty_object):
    ascii_node = []
    
    if (empty_object.auroraprops.dummytype in {'PWKBASE', 'DWKBASE', 'MDLBASE'}):
        # Base dummys will not be written into the walkmesh file
        pass
    else:
        ascii_node.append('node dummy ' + empty_object.name)
        
        tmp = 'NULL'
        if empty_object.parent:
            tmp = empty_object.parent.name
        ascii_node.append('  parent ' + tmp)
        
        ascii_node.append('  position ' + str(round(empty_object.location[0], glob_gen_digits)) + ' ' + 
                                          str(round(empty_object.location[1], glob_gen_digits)) + ' ' + 
                                          str(round(empty_object.location[2], glob_gen_digits)) )
        
        tmp = amt_utils.getRotationAurora(empty_object)
        ascii_node.append('  orientation ' + str(round(tmp[0], glob_angle_digits)) + ' ' + 
                                             str(round(tmp[1], glob_angle_digits)) + ' ' + 
                                             str(round(tmp[2], glob_angle_digits)) + ' ' + 
                                             str(round(tmp[3], glob_angle_digits)) )  
        
        ascii_node.append('  wirecolor ' + str(round(empty_object.auroraprops.wirecolor[0], glob_color_digits)) + ' ' + 
                                           str(round(empty_object.auroraprops.wirecolor[1], glob_color_digits)) + ' ' + 
                                           str(round(empty_object.auroraprops.wirecolor[1], glob_color_digits))  )
        
        ascii_node.append('endnode')
    
    return ascii_node


def animdata2asciikeys(anim_object, anim_scene):
    
    animation_keys = {}
    scene_fps = anim_scene.render.fps
    
    # Get action for the object
    try:
        anim_action = anim_object.animation_data.action
    except:
        anim_action = None
    
    # Custom prop keys behave strangely, they may not be 
    # accessible from the object/material
    if anim_action is None:
        try:
            anim_action = bpy.data.actions[anim_scene.name+'.'+anim_object.name]
        except:
            anim_action = None
    
    if anim_action is not None:
        action_fcurves = anim_action.fcurves
        for fcurve in action_fcurves:
            if fcurve.data_path not in animation_keys:
                animation_keys[fcurve.data_path] = collections.OrderedDict()
            
            key_dict = animation_keys[fcurve.data_path]
            
            axis = fcurve.array_index
            for keyframe_point in fcurve.keyframe_points:
                # We just round the x coord of the keyframe point to get 
                # the frame number
                # Yes, this could result in duplicate points, but I won't
                # use float keys
                frame_idx = int(round(keyframe_point.co[0]))
                
                # See if there is already an entry in the dict
                if frame_idx in key_dict:  
                    values = key_dict[frame_idx]
                else:
                    values = [0.0, 0.0, 0.0, 0.0] # 4 dims should be enough
                
                values[axis] = values[axis] + keyframe_point.co[1]
                key_dict[frame_idx] = values
    
    # Get action for the material
    try:
        anim_action = anim_object.active_material.animation_data.action 
    except:
        anim_action = None
    # Custom prop keys behave strangely, they may not be 
    # accessible from the object/material
    if anim_action is None:
        try:
            material_name = anim_object.active_material.name
            anim_action   = bpy.data.actions[anim_scene.name + '.' + material_name]
        except:
            anim_action = None            
    
    if anim_action is not None:
        action_fcurves = anim_action.fcurves
        for fcurve in action_fcurves:
            if fcurve.data_path not in animation_keys:
                animation_keys[fcurve.data_path] = collections.OrderedDict()
            
            key_dict = animation_keys[fcurve.data_path]
            
            axis = fcurve.array_index
            for keyframe_point in fcurve.keyframe_points:
                # We just round the x coord of the keyframe point to get 
                # the frame number
                # Yes, this could result in duplicate points, but I won't
                # use float keys
                frame_idx = int(round(keyframe_point.co[0]))
                
                # See if there is already an entry in the dict
                if frame_idx in key_dict:  
                    values = key_dict[frame_idx]
                else:
                    values = [0.0, 0.0, 0.0, 0.0] # 4 dims should be enough
                
                values[axis] = values[axis] + keyframe_point.co[1]
                key_dict[frame_idx] = values

    # Get action for the particle system settings
    try:
        anim_action = anim_object.particle_systems.active.settings.animation_data.action 
    except:
        anim_action = None
    # Custom prop keys behave strangely, they may not be 
    # accessible from the object/material
    if anim_action is None:
        try:
            partsys_name  = anim_object.particle_systems.active.name
            anim_action   = bpy.data.actions[anim_scene.name + '.' + partsys_name]
        except:
            anim_action = None            
    
    if anim_action is not None:
        action_fcurves = anim_action.fcurves
        for fcurve in action_fcurves:
            if fcurve.data_path not in animation_keys:
                animation_keys[fcurve.data_path] = collections.OrderedDict()
            
            key_dict = animation_keys[fcurve.data_path]
            
            axis = fcurve.array_index
            for keyframe_point in fcurve.keyframe_points:
                # We just round the x coord of the keyframe point to get 
                # the frame number
                # Yes, this could result in duplicate points, but I won't
                # use float keys
                frame_idx = int(round(keyframe_point.co[0]))
                
                # See if there is already an entry in the dict
                if frame_idx in key_dict:  
                    values = key_dict[frame_idx]
                else:
                    values = [0.0, 0.0, 0.0, 0.0] # dim 4 should be enough
                
                values[axis] = values[axis] + keyframe_point.co[1]
                key_dict[frame_idx] = values
                    
    # Generate ascii keys from animation_key dict
    nwnprop_dict = {'rotation_euler'             : ['orientation', glob_angle_digits, 4],
                    'rotation_axis_angle'        : ['orientation', glob_angle_digits, 4],
                    'location'                   : ['position', glob_gen_digits, 3],
                    'scale'                      : ['scale', glob_gen_digits, 3],
                    'auroraprops.selfillumcolor' : ['selfillumcolor', glob_color_digits, 3],
                    'color'                      : ['color', glob_color_digits, 3],
                    'alpha'                      : ['alpha', glob_color_digits, 1],
                    'auroraprops.birthrate'      : ['birthrate', glob_color_digits, 1] }
    
    ascii_keys = []
    for blend_name, nwnprop in nwnprop_dict.items():
        if (blend_name in animation_keys):
            key_dict = animation_keys[blend_name]
            
            rnd_digs = nwnprop[1]
            num_vals = nwnprop[2]
            if (len(key_dict) == 1):
                nwn_name = nwnprop[0]
                values   = list(key_dict.values())[0]
                str_vals = ''
                if (blend_name == 'rotation_euler'):
                    nwrot = amt_utils.euler2nwangle(values)
                    str_vals = ( str(round(nwrot[0], rnd_digs)) +
                                 ' ' +
                                 str(round(nwrot[1], rnd_digs)) +
                                 ' ' +
                                 str(round(nwrot[2], rnd_digs)) +
                                 ' ' +
                                 str(round(nwrot[3], rnd_digs)) )
                if (blend_name == 'rotation_axis_angle'):
                    str_vals = ( str(round(values[1], rnd_digs)) +
                                 ' ' +
                                 str(round(values[2], rnd_digs)) +
                                 ' ' +
                                 str(round(values[3], rnd_digs)) +
                                 ' ' +
                                 str(round(values[0], rnd_digs)) )                                 
                elif (blend_name == 'alpha'):
                    str_vals = str(round(values[0], rnd_digs))
                else:
                    str_vals = ( str(round(values[0], rnd_digs)) +
                                 ' ' +
                                 str(round(values[1], rnd_digs)) +
                                 ' ' +
                                 str(round(values[2], rnd_digs)) )
                
                ascii_keys.append('    ' + nwn_name + ' ' + str_vals)
            elif (len(key_dict) > 1):
                nwn_name = nwnprop[0]+'key'
                ascii_keys.append('    ' + nwn_name )#+ ' ' + str(len(key_dict)))
                for frame_idx, values in key_dict.items():
                    str_vals = ''
                    if (blend_name == 'rotation_euler'):
                        nwrot = amt_utils.euler2nwangle(values)
                        str_vals = ( str(round(nwrot[0], rnd_digs)) +
                                     ' ' +
                                     str(round(nwrot[1], rnd_digs)) +
                                     ' ' +
                                     str(round(nwrot[2], rnd_digs)) +
                                     ' ' +
                                     str(round(nwrot[3], rnd_digs)) )
                    if (blend_name == 'rotation_axis_angle'):
                        str_vals = ( str(round(values[1], rnd_digs)) +
                                    ' ' +
                                    str(round(values[2], rnd_digs)) +
                                    ' ' +
                                    str(round(values[3], rnd_digs)) +
                                    ' ' +
                                    str(round(values[0], rnd_digs)) )                                      
                    elif (blend_name == 'auroraprops.birthrate'):
                        str_vals = str(int(values[0]))                                     
                    elif (blend_name == 'alpha'):
                        str_vals = str(round(values[0], rnd_digs))                                    
                    else:
                        str_vals = ( str(round(values[0], rnd_digs)) +
                                     ' ' +
                                     str(round(values[1], rnd_digs)) +
                                     ' ' +
                                     str(round(values[2], rnd_digs)) )
                    
                    ascii_keys.append('      ' + 
                                      str(amt_utils.frame2nwtime(frame_idx, scene_fps)) + 
                                      ' ' + 
                                      str_vals)
                ascii_keys.append('    ' + 'endlist')
    return ascii_keys


def get_animation_data(export_object_list):
    animation_data = {}
    
    # Loop thorugh all scenes and check if they contain a root dummy
    # Each scene with a rootdummy is an scene
    if (export_object_list):
        # Mdl base comes first in export list
        mdl_base_name = export_object_list[0].name
        for scene in bpy.data.scenes:
            # Don't export animations from base scene
            if (scene == glob_export_scene):
                continue
            anim_name = scene.name
            # Name of the mdl base in the animation scene
            anim_mdl_base_name = mdl_base_name + '.' + anim_name
            if anim_mdl_base_name in scene.objects:
                # We have a mdl base in this scene
                anim_mdl_base = scene.objects[anim_mdl_base_name]
                # This scene is an animation, so add an animation to 
                # the animation dict
                ascii_anim = []
                
                ascii_anim.append('newanim ' + 
                                  anim_name + 
                                  ' ' + 
                                  glob_modelname)
                
                ascii_anim.append('  length '    + str(amt_utils.frame2nwtime(scene.frame_end, scene.render.fps)))
                ascii_anim.append('  transtime ' + str(anim_mdl_base.auroraprops.transtime))
                ascii_anim.append('  animroot '  + glob_modelname)
                
                # Search for copies of objects
                for export_object in export_object_list:
                    aurora_node_type = get_aurora_node_type(export_object)
                    ascii_anim.append('  node '        + 
                                      aurora_node_type + 
                                      ' '              + 
                                      export_object.name)
                    
                    parent_name = ''
                    try:
                        parent_name = export_object.parent.name
                    except:
                        parent_name = 'NULL'  
                    ascii_anim.append('    parent ' + parent_name)
                    
                    anim_object_name = export_object.name + '.' + anim_name
                    if anim_object_name in scene.objects:
                        # We have found a object, it could contain an action
                        anim_object = scene.objects[anim_object_name]
                        ascii_anim.extend(animdata2asciikeys(anim_object, scene))
                    else:
                        # This object is not in the animation scene
                        # We just treat it like it has no action 
                        # assigned, i.e do nothing :-)
                        pass
                    ascii_anim.append('  endnode')
                
                ascii_anim.append('doneanim ' + 
                                  anim_name + 
                                  ' ' + 
                                  glob_modelname)
                animation_data[anim_name] = ascii_anim
    
    return animation_data


def generate_ascii_node(node_object, export_object_list = []):
    ascii_node = []
    
    if (node_object.type == 'EMPTY'):
        # Emptys become dummys
        ascii_node = empty2dummynode(node_object)
    
    elif (node_object.type == 'MESH'):
        # Could be danglymesh, skinmesh or trimesh
        ascii_node = mesh2meshnode(node_object, export_object_list)
    
    elif (node_object.type == 'LAMP'):
        # Lamps become lights
        ascii_node = lamp2lightnode(node_object)
    
    else:
        # Everything else won't be exported
        pass
    
    return ascii_node


def generate_walkmesh_node(walkmesh_object):
    walkmesh_node = []
    if (walkmesh_object.type == 'EMPTY'):
        # Emptys become dummys
        walkmesh_node = empty2walkmeshdummynode(walkmesh_object)
    
    elif (walkmesh_object.type == 'MESH'):
        # Could be danglymesh, skinmesh or trimesh 
        # (but will be exported as trimesh anyway)
        walkmesh_node = mesh2walkmeshmeshnode(walkmesh_object)
    
    else:
        # Everything else won't be exported
        pass    
    
    return walkmesh_node


def generate_mdl_header():
    header = []
    
    current_time = datetime.now()
    
    header.append('# Exported from blender at ' + current_time.strftime('%A, %Y-%m-%d %H:%M'))
    header.append('# ')
    header.append('filedependancy'    + ' ' + glob_sourcefile)
    header.append('newmodel'          + ' ' + glob_modelname)
    header.append('setsupermodel'     + ' ' + glob_modelname + ' ' + glob_supermodel)
    header.append('classification'    + ' ' + glob_mdl_classification)
    header.append('setanimationscale' + ' ' + str(round(glob_mdl_animationscale, 2)))
    
    return header  


def generate_mdl_geometry(export_object_list):
    ascii_geometry = []
    
    ascii_geometry.append('beginmodelgeom' + ' ' + glob_modelname)
    
    # Each object is a node 
    for object in export_object_list:
        ascii_node = generate_ascii_node(object, export_object_list)
        ascii_geometry.extend(ascii_node)
    
    ascii_geometry.append('endmodelgeom' + ' ' + glob_modelname)
    
    return ascii_geometry


def generate_mdl_animations(export_object_list):
    
    #
    animation_data = get_animation_data(export_object_list)
    
    # Only write animation blocks, if there are animations present
    ascii_anim_list = []
    ascii_anim_list.append('')
    for anim_name, ascii_anim in animation_data.items():
        ascii_anim_list.extend(ascii_anim)
        ascii_anim_list.append('')
    return ascii_anim_list


def generate_mdl_footer():
    footer = []
    
    footer.append('donemodel' + ' ' + glob_modelname)
    
    return footer


def generate_walkmesh_header():
    header = []
    
    current_time = datetime.now()
    
    header.append('# Exported from blender at ' + current_time.strftime('%A, %Y-%m-%d %H:%M'))
    header.append('# ')
    header.append('filedependancy' + ' ' + glob_sourcefile)
    
    return header


def generate_walkmesh(object_list, ascii_aabb_tree = []):
    walkmesh = []
    
    if (glob_mdl_classification == 'TILE'):
        # Just the aabb tree for Tiles 
        walkmesh.append('beginwalkmeshgeom '+ glob_modelname)
        walkmesh.extend(ascii_aabb_tree)
        walkmesh.append('endwalkmeshgeom '+ glob_modelname)
    else:
        # Each object is a node
        for object in object_list:
            walkmesh_node = generate_walkmesh_node(object)
            walkmesh.extend(walkmesh_node)
    
    return walkmesh


def generate_walkmesh_footer():
    footer = []
    
    return footer


def save_mdl():
    # Exit edit mode before exporting, so current object states are exported properly
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    
    export_object_list = get_export_objects()
    
    if export_object_list:
        with open(glob_mdl_filepath, 'w') as mdl_file:
            write_to_file(mdl_file, generate_mdl_header())
            
            write_to_file(mdl_file, generate_mdl_geometry(export_object_list))
            
            write_to_file(mdl_file, generate_mdl_animations(export_object_list))
            
            write_to_file(mdl_file, generate_mdl_footer())
        
        if (glob_export_walkmesh):
            if (glob_mdl_classification == 'TILE'):
                walkmesh_object_list = []
                walkmesh_filepath    = get_walkmesh_filepath()
                if (walkmesh_filepath != ''):
                    try:
                        with open(walkmesh_filepath, 'w') as walkmesh_file:
                            write_to_file(walkmesh_file, generate_walkmesh_header())
                            
                            write_to_file(walkmesh_file, generate_walkmesh(walkmesh_object_list, glob_ascii_aabb_node))
                            
                            write_to_file(walkmesh_file, generate_walkmesh_footer())
                    except IOError:
                        print('ERROR: Could not create walkmesh file ' + str(walkmesh_filepath))
            else:
                walkmesh_object_list = get_walkmesh_objects()
                walkmesh_filepath    = get_walkmesh_filepath()
                if (walkmesh_filepath != '') and (walkmesh_object_list):
                    try:
                        with open(walkmesh_filepath, 'w') as walkmesh_file:
                            write_to_file(walkmesh_file, generate_walkmesh_header())
                            
                            write_to_file(walkmesh_file, generate_walkmesh(walkmesh_object_list, glob_ascii_aabb_node))
                            
                            write_to_file(walkmesh_file, generate_walkmesh_footer())
                    except IOError:
                        print('ERROR: Could not create walkmesh file ' + str(walkmesh_filepath))


###########################################################
## Called by blender
###########################################################


def save(operator,
         context, 
         filepath = '',
         export_selection = 'ALL',
         export_walkmesh = False,
         apply_modifiers = True,
         export_shading_groups = False,
         ):
    
    global glob_mdl_filepath
    global glob_mdl_filename
    global glob_mdl_filedir
    global glob_export_selection
    global glob_export_walkmesh
    global glob_apply_modifiers
    
    global glob_sourcefile
    global glob_export_scene
    
    glob_mdl_filepath     = os.fsencode(filepath)
    glob_mdl_filename     = os.path.splitext(os.path.basename(filepath))[0]
    glob_mdl_filedir      = os.path.dirname(filepath)
    glob_export_selection = export_selection
    glob_export_walkmesh  = export_walkmesh
    glob_apply_modifiers  = apply_modifiers
    glob_export_shadgr    = export_shading_groups
    
    glob_sourcefile       = os.path.basename(bpy.data.filepath)
    if (glob_sourcefile == ''):
        glob_sourcefile = 'unknown'
    glob_export_scene     = bpy.context.scene
    
    save_mdl()
    
    return {'FINISHED'}
