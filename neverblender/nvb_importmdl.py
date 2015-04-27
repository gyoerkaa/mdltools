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
from bpy_extras.io_utils import unpack_list, unpack_face_list
from bpy_extras.image_utils import load_image
from . import nvb_utils
from . import nvb_presets

###########################################################
## Globals
###########################################################


# User Settings
glob_mdl_filedir           = ''
glob_mdl_filename          = ''
glob_mdl_filepath          = ''
glob_import_items          = {'GEOMETRY', 'ANIMATIONS'}
glob_import_walkmesh       = True
glob_import_shading_groups = False
glob_use_image_search      = False
glob_one_tex_per_image     = True
glob_import_lights         = True
glob_import_fading_obj     = True


# Will be read from file
glob_modelname          = 'unnamed'
glob_classification     = 'UNKNOWN'
glob_supermodel         = 'NULL'
glob_animationscale     = 1.0


# 
glob_import_scene = None


###########################################################
## Helpers
###########################################################


def get_tilelight_type(node_lamp):
    name = node_lamp.name
    if (name == glob_modelname+'ml1'):
        return 'MAINLIGHT1'
    elif (name == glob_modelname+'ml2'):
        return 'MAINLIGHT2'
    elif (name == glob_modelname+'sl1'):
        return 'SOURCELIGHT1'
    elif (name == glob_modelname+'sl2'):
        return 'SOURCELIGHT2'
    else:
        return 'NONE'


def get_mdl_classification():
    '''
    Matches the classification the model with
    the available ones and returns it
    Writes a warning to the logfile if there is a 
    unknown classification an sets it to unknown
    '''
    if (glob_classification.lower() in {'unknown', 'tile', 'character', 'door', 'effect', 'gui', 'item'}):
        return glob_classification.upper()
    else:
        printf('WARNING: Invalid Classification')
        return 'UNKNOWN'


def is_numeric(str):
    '''
    Check if the string is a number or not
    We need this, as models exported from nwmax do not
    always give the vertex-, face- and especially
    key count (afaik it ever gives key count)
    '''
    try:
        float(str)
        return True
    except ValueError:
        return False


def read_ascii_mdl(filepath):
    '''
    Opens a mdl file in ascii format and puts its
    contents into a list    
    '''
    separated_values = []
    
    # Open file
    try:
        file  = open(filepath, 'r')
        
        lines = file.readlines()
        # Iterate over all lines
        split_line = []
        for l in lines[0:len(lines)]:
            # Make sure the current line is not a comment
            if (l[0] != '#'):      
                # Separate words
                split_line = l.split()
                # if empty, don't add to list
                if (len(split_line) > 0):
                    separated_values.append(split_line)    
    
    except IOError:
        print('WARNING: Could not open file ' + str(filepath))
    
    return separated_values            


def find_line(str, ascii_mdl, start):
    '''
    Returns the number of the line beginning with the string 
    str
    '''
    for pos in range(start,len(ascii_mdl)):
        if (ascii_mdl[pos][0] == str):
            return pos
     
    return start


def load_material_image(filename, fileext = '.tga'):
    '''
    Load the specified image. Just a convenience function
    '''
    image = load_image(filename + fileext, glob_mdl_filedir, recursive=glob_use_image_search, place_holder=False, ncase_cmp=False)
    if (image is None):
        image = bpy.data.images.new(filename, 512, 512)
    else:
        image.name = filename
    
    return image


###########################################################
## Import
###########################################################


def add_particle_system(node_object, parsed_node):

    modifier        = node_object.modifiers.new(node_object.name + '.' + 'AuroraEmit', 'PARTICLE_SYSTEM')
    particle_system = modifier.particle_system
    ps_settings     = particle_system.settings
    
    particle_system.name = node_object.name +  '.emit'
    
    ps_settings.name          = node_object.name + '.emset'
    ps_settings.frame_start   = parsed_node['framestart']
    ps_settings.frame_end     = parsed_node['frameend']
    ps_settings.lifetime      = parsed_node['lifeexp']
    ps_settings.mass          = parsed_node['mass']
    ps_settings.normal_factor = parsed_node['velocity']
    ps_settings.factor_random = parsed_node['randvel']
    
    ps_settings.effector_weights.wind    = float(parsed_node['affectedbywind'])
    ps_settings.effector_weights.drag    = float(parsed_node['drag'])
    ps_settings.effector_weights.gravity = float(parsed_node['grav'])
     
    ps_settings.auroraprops.birthrate = int(parsed_node['birthrate'])
     
    # Inheritance props
    ps_settings.auroraprops.inherit       = (parsed_node['inherit'] == 1)
    ps_settings.auroraprops.inherit_vel   = (parsed_node['inheritvel'] == 1)
    ps_settings.auroraprops.inherit_local = (parsed_node['inherit_local'] == 1)
    ps_settings.auroraprops.inherit_part  = (parsed_node['inherit_part'] == 1)
    ps_settings.auroraprops.splat         = (parsed_node['splat'] == 1)
    
    # Spawntype
    if (parsed_node['spawntype'] == 1):
        ps_settings.auroraprops.spawntype = 'NORMAL'
    elif (parsed_node['spawntype'] == 2):
        ps_settings.auroraprops.spawntype = 'TRAIL'
    
    # Update type
    if (parsed_node['update'] == 1):
        ps_settings.auroraprops.update = 'FOUNTAIN'
    elif (parsed_node['update'] == 2):
        ps_settings.auroraprops.update = 'SINGLE'
    elif (parsed_node['update'] == 2):
        ps_settings.auroraprops.update = 'EXPLOSION'
    elif (parsed_node['update'] == 4):
        ps_settings.auroraprops.update = 'LIGHTNING'
    
    # Render type
    if (parsed_node['render'] == 1):
        ps_settings.auroraprops.render = 'NORMAL'
    elif (parsed_node['render'] == 2):
        ps_settings.auroraprops.render = 'LINKED'
    elif (parsed_node['render'] == 3):
        ps_settings.auroraprops.render = 'BB2LZ'
    elif (parsed_node['render'] == 4):
        ps_settings.auroraprops.render = 'BB2WZ'
    elif (parsed_node['render'] == 5):
        ps_settings.auroraprops.render = 'AL2WZ'
    elif (parsed_node['render'] == 6):
        ps_settings.auroraprops.render = 'AL2PD'
    elif (parsed_node['render'] == 7):
        ps_settings.auroraprops.render = 'MOBLUR'        
    
    # Blend type
    if (parsed_node['blend'] == 1):
        ps_settings.auroraprops.blend = 'NORMAL'
    elif (parsed_node['blend'] == 2):
        ps_settings.auroraprops.blend = 'PUNCH-THROUGH'
    elif (parsed_node['blend'] == 3):
        ps_settings.auroraprops.blend = 'LIGHTEN'
    
    # Texture
    if (parsed_node['texture'].lower() != 'null'):
        ps_settings.render_type = 'BILLBOARD'
        #ps_settings.billboard_align = 'VIEW' # TODO
        ps_settings.billboard_uv_split = max([parsed_node['xgrid'], parsed_node['ygrid']])
         
    # Blast props
    ps_settings.auroraprops.blastradius = parsed_node['blastradius']
    ps_settings.auroraprops.blastlength = parsed_node['blastlength']
    
    # Animation props
    ps_settings.auroraprops.colorstart  = parsed_node['colorstart']
    ps_settings.auroraprops.colorend    = parsed_node['colorend']
    ps_settings.auroraprops.alphastart  = parsed_node['alphastart']
    ps_settings.auroraprops.alphaend    = parsed_node['alphaend']
    ps_settings.auroraprops.sizestart   = parsed_node['sizestart']
    ps_settings.particle_size           = parsed_node['sizestart']/10
    ps_settings.auroraprops.sizeend     = parsed_node['sizeend']
    ps_settings.auroraprops.sizestart_y = parsed_node['sizestart_y']
    ps_settings.auroraprops.sizeend_y   = parsed_node['sizeend_y']

    # Misc props
    ps_settings.auroraprops.lifeexp     = parsed_node['lifeexp']
    ps_settings.auroraprops.istinted    = (parsed_node['m_istinted'] == 1)
    ps_settings.auroraprops.bounce      = (parsed_node['bounce'] == 1)
    ps_settings.auroraprops.random      = (parsed_node['random'] == 1)
    ps_settings.auroraprops.bounce_co   = parsed_node['bounce_co']
    ps_settings.auroraprops.spread      = parsed_node['spread']
    ps_settings.auroraprops.particlerot = parsed_node['particlerot']
    ps_settings.auroraprops.fps         = parsed_node['fps']
    ps_settings.auroraprops.blurlength  = parsed_node['blurlength']    
    ps_settings.auroraprops.chunkname   = parsed_node['chunkname']
    ps_settings.auroraprops.loop        = (parsed_node['loop'] == 1)
    ps_settings.auroraprops.deadspace   = parsed_node['deadspace']    
    ps_settings.auroraprops.renderorder = parsed_node['renderorder']
    ps_settings.auroraprops.twosidedtex = (parsed_node['twosidedtex'] == 1)
    ps_settings.auroraprops.opacity     = parsed_node['opacity']
    
    # Lighting props
    ps_settings.auroraprops.lightningdelay  = parsed_node['lightningdelay']
    ps_settings.auroraprops.lightningradius = parsed_node['lightningradius']
    ps_settings.auroraprops.lightningsubdiv = parsed_node['lightningsubdiv']
    ps_settings.auroraprops.lightningscale  = parsed_node['lightningscale']

    # p2p props
    ps_settings.auroraprops.p2p          = parsed_node['p2p']
    if (parsed_node['p2p_sel'] == 1):
        ps_settings.auroraprops.p2p_sel = 'BEZIER'
    elif (parsed_node['p2p_sel'] == 2): 
        ps_settings.auroraprops.p2p_sel = 'GRAVITY'
    ps_settings.auroraprops.p2p_bezier2  = parsed_node['p2p_bezier2']
    ps_settings.auroraprops.p2p_bezier3  = parsed_node['p2p_bezier3']
    ps_settings.auroraprops.threshold    = parsed_node['threshold']
    ps_settings.auroraprops.combinetime  = parsed_node['combinetime']     
   
    
def add_danglegroup(node_object, parsed_node):
    '''
    Creates a vertex group for the object to contain the vertex
    weights for the danglymesh. The weights are called "constraints" 
    in NWN are in [0.0, 255.0] as oppossed to [0.0, 1.0] in Blender
    '''
    
    vert_group = node_object.vertex_groups.new(nvb_presets.danglymesh_group_name)
    for vert_num, nw_constraint in enumerate(parsed_node['constraints']):
        vert_weight = nw_constraint/255
        vert_group.add([vert_num], vert_weight, 'REPLACE')
    
    return vert_group


def add_shading_groups(node_object, parsed_node):
    
    if not glob_import_shading_groups:
        return
    
    # Create a dictionary of shading groups with group id's as keys
    # and a vertex lists as values
    shading_groups_dict = {}
    for face_id, face_info in enumerate(parsed_node['faces_info']):
        group_id = face_info[0] # face_info[0] = shading group id this face belongs to
        if group_id not in shading_groups_dict: 
            shading_groups_dict[group_id] = []
         
        shading_groups_dict[group_id].append(parsed_node['faces'][face_id][0])
        shading_groups_dict[group_id].append(parsed_node['faces'][face_id][1])
        shading_groups_dict[group_id].append(parsed_node['faces'][face_id][2])
    
    # Add vertices to previously created vertex groups
    for group_id, group_members in shading_groups_dict.items():
        vert_group = node_object.vertex_groups.new(nvb_presets.shading_group_name + str(group_id))
        vert_group.add(group_members, 1.0, 'REPLACE')    


def add_skingroups(node_object, parsed_node):
    
    skin_groups_dict = {}
    for vertex_id, vertex_memberships in enumerate(parsed_node['weights']):
        for membership in vertex_memberships:
            if membership[0] in skin_groups_dict:
                skin_groups_dict[membership[0]].add([vertex_id], membership[1], 'REPLACE') 
            else:
                vert_group = node_object.vertex_groups.new(membership[0])
                skin_groups_dict[membership[0]] = vert_group
                vert_group.add([vertex_id], membership[1], 'REPLACE') 


def create_mesh_material(parsed_node):
    '''
    Creates a material from a parsed ascii node
    '''   
    node_mat = bpy.data.materials.new(parsed_node['name']+'.mat')
    
    # Set material properties
    node_mat.diffuse_color      = parsed_node['diffuse']
    node_mat.diffuse_intensity  = 1.0
    node_mat.specular_color     = parsed_node['specular']
    
    # Set alpha values. Note: Texture alpha_factor needs to be set too
    if (parsed_node['alpha'] >= 0.99999):
        node_mat.alpha            = 0.0
        node_mat.use_transparency = True
    elif (parsed_node['alpha'] >= 0.00001):
        node_mat.alpha            = 1-parsed_node['alpha']
        node_mat.use_transparency = True   
    else:
        node_mat.use_transparency = False
    
    # Set the texture, if there is one
    texture_name = parsed_node['bitmap'].lower()
    if (texture_name != 'null'):
        node_tex = node_mat.texture_slots.add()
        # Check if this texture was created previously
        if (glob_one_tex_per_image and (texture_name in bpy.data.textures)):
            node_tex.texture = bpy.data.textures[texture_name]
        else:
            node_tex.texture = bpy.data.textures.new(texture_name, type='IMAGE')
        node_tex.texture_coords        = 'UV'
        node_tex.use_map_color_diffuse = True
        
        # Texture alpha should fully control alpha
        if (parsed_node['alpha'] >= 0.00001):
            node_tex.alpha_factor   = 1.0
            node_tex.use_map_alpha = True
            
        # Check if this image was loaded previously
        if (parsed_node['bitmap'] in bpy.data.images):
            image = bpy.data.images[parsed_node['bitmap']]
            node_tex.texture.image = image  
        else:
            image = load_material_image(parsed_node['bitmap'],'.tga')
            if image:
                node_tex.texture.image = image
                # Alpha settings
                if (parsed_node['alpha'] >= 0.00001):
                    node_tex.alpha_factor = 1.0
                    node_tex.use_map_alpha = True
                    #################################
                    # Blender 2.60 - 2.66
                    try:
                        image.use_premultiply = True
                    except:
                        pass # just do nothing
                    #################################
                    # Blender 2.67 - XXX
                    try:
                        image.alpha_mode = 'PREMUL'
                        image.use_alpha = True
                    except:
                        pass # just do nothing                        
                    #################################               
                
    
    return node_mat


def create_emitter_material(parsed_node):
    '''
    Creates a material from a parsed ascii node
    '''   
    node_mat = bpy.data.materials.new(parsed_node['name']+'.mat')
    
    # Set material properties
    node_mat.diffuse_color     = (1.0, 1.0, 1.0)
    node_mat.diffuse_intensity = 1.0
    node_mat.specular_color    = (0.0, 0.0, 0.0)
    
    # Set alpha values. Note: Texture alpha_factor needs to be set too
    node_mat.alpha            = 0.0
    node_mat.use_transparency = True
     
    # Set the texture
    texture_name = parsed_node['texture'].lower()
    if (texture_name != 'null'):
        node_tex = node_mat.texture_slots.add()
        if (glob_one_tex_per_image and (texture_name in bpy.data.textures)):
            node_tex.texture = bpy.data.textures[texture_name]
        else:
            node_tex.texture = bpy.data.textures.new(texture_name, type='IMAGE')     
        node_tex.texture_coords        = 'UV'
        node_tex.use_map_color_diffuse = True
        
        # Texture alpha should fully control alpha
        node_tex.alpha_factor   = 1.0
        node_tex.use_map_alpha = True
        
        if (parsed_node['texture'] in bpy.data.images):
            image = bpy.data.images[parsed_node['texture']]
        else:        
            image = load_material_image(parsed_node['texture'],'.tga')

        if image:
            node_tex.texture.image = image
    
    return node_mat


def animnode2partsysaction(parsed_node, partsys_name = ''):
    '''
    Creates an action from a parsed animation node
    The animations are rendered at 30 fps, so 0.3333 sec are one frame
    '''
    
    # Return a None object, if there is no animation data
    if not parsed_node['birthratekey']:
        return None
    print('adding birthratekey')
    action_name               = parsed_node['anim_name'] + '.' + partsys_name
    node_action               = bpy.data.actions.new(name=action_name)
    node_action.use_fake_user = True # We want this action to be saved, even if it isn't attached to an object
    
    # Set birthrate channels if there are birthrate keys
    # This should influence the birthrate value
    curve = node_action.fcurves.new(data_path='auroraprops.birthratekey')     
        
    for i, key in enumerate(parsed_node['birthratekey']):
        curve.keyframe_points.insert(nvb_utils.nwtime2frame(key[0], nvb_presets.render_fps), key[1])   
            
    return node_action


def animnode2mataction(parsed_node, mat_name = ''):
    '''
    Creates an action from a parsed animation node
    The animations are rendered at 30 fps, so 0.3333 sec are one frame
    '''
    
    # Return a None object, if there is no animation data
    if not parsed_node['alphakey']:
        return None
    
    action_name               = parsed_node['anim_name'] + '.' + mat_name 
    node_action               = bpy.data.actions.new(name=action_name)
    node_action.use_fake_user = True # We want this action to be saved, even if it isn't attached to an object
    
    # Set alpha channels
    # This should influence the material alpha value
    curve = node_action.fcurves.new(data_path='alpha')     
        
    for i, key in enumerate(parsed_node['alphakey']):
        curve.keyframe_points.insert(nvb_utils.nwtime2frame(key[0], nvb_presets.render_fps), key[1])   
            
    return node_action


def animnode2objectaction(parsed_node):
    '''
    Creates an action from a parsed animation node
    The animations are rendered at 30 fps, so 0.3333 sec are one frame
    '''   
    
    # Return a None object, if there is no animation data
    if not (parsed_node['orientationkey'] or 
            ('orientation' in parsed_node) or 
            parsed_node['positionkey'] or 
            ('position' in parsed_node) or 
            parsed_node['scalekey'] or 
            parsed_node['colorkey'] or
            parsed_node['selfillumcolorkey']):
        return None    
    
    action_name               = parsed_node['anim_name'] + '.' + parsed_node['object_name']
    node_action               = bpy.data.actions.new(name=action_name)
    node_action.use_fake_user = True # We want this action to be saved, even if it isn't attached to an object
    
    # Set rotation channels if rotation keys exist
    if (parsed_node['orientationkey']):
        
        ######################################
        # Euler
        ######################################
        # convert nwn format(axis-angle) to euler       
        #euler_rotations = []
        #for key in parsed_node['orientationkey']:
        #    euler_rotations.append(nvb_utils.nwangle2euler((key[1], key[2], key[3], key[4])))
        
        # for each axis
        #for c in range(3):
        #    curve = node_action.fcurves.new(data_path='rotation_euler', index=c)
        #    for i in range(len(parsed_node['orientationkey'])):
        #        curve.keyframe_points.insert(nvb_utils.nwtime2frame(parsed_node['orientationkey'][i][0], nvb_presets.render_fps), euler_rotations[i][c])
        ######################################
        # Euler
        ######################################
        
        ######################################
        # Axis angle
        ######################################        
        # Set angle
        # In mdl format the angle is the last value, in 
        # blender it must the first
        curve = node_action.fcurves.new(data_path='rotation_axis_angle', index=0)
        for i in range(len(parsed_node['orientationkey'])):
            curve.keyframe_points.insert(nvb_utils.nwtime2frame(parsed_node['orientationkey'][i][0], nvb_presets.render_fps), parsed_node['orientationkey'][i][4])
                
        # Now set the axes
        for c in range(1,4):
            curve = node_action.fcurves.new(data_path='rotation_axis_angle', index=c)
            for i in range(len(parsed_node['orientationkey'])):
                curve.keyframe_points.insert(nvb_utils.nwtime2frame(parsed_node['orientationkey'][i][0], nvb_presets.render_fps), parsed_node['orientationkey'][i][c])
        ######################################
        # Axis Angle
        ######################################    
    
    # This means that there is only one orientation key (presumably)
    elif ('orientation' in parsed_node):
        # convert nwn format(axis-angle) to euler
        euler_rotation = nvb_utils.nwangle2euler((parsed_node['orientation'][0], parsed_node['orientation'][1], parsed_node['orientation'][2], parsed_node['orientation'][3]))
        
        # for each axis (too lazy to check if there is actually a rotation for every axis)
        for c in range(3):
            curve = node_action.fcurves.new(data_path='rotation_euler', index=c) 
            curve.keyframe_points.insert(0, euler_rotation[c])
    
    # Set location channels if there are location keys
    if (parsed_node['positionkey']):
        # for each axis
        for c in range(3):
            curve = node_action.fcurves.new(data_path='location', index=c)
            
            for i, key in enumerate(parsed_node['positionkey']):
                curve.keyframe_points.insert(nvb_utils.nwtime2frame(key[0], nvb_presets.render_fps), key[c+1])
    
    # This means that there is only one position key (presumably)
    elif ('position' in parsed_node):
         for c in range(3):
            curve = node_action.fcurves.new(data_path='location', index=c) 
            curve.keyframe_points.insert(0, parsed_node['position'][c])       
    
    # Set scale channels if there are scale keys
    if (parsed_node['scalekey']):
        # for each axis
        for c in range(3):
            curve = node_action.fcurves.new(data_path='scale', index=c)     
            
            for i, key in enumerate(parsed_node['scalekey']):
                curve.keyframe_points.insert(nvb_utils.nwtime2frame(key[0], nvb_presets.render_fps), key[c+1])   
    
    # Set color channels if there are color keys
    if (parsed_node['colorkey']):
        # for each axis
        for c in range(3):
            curve = node_action.fcurves.new(data_path='color', index=c)     
            
            for i, key in enumerate(parsed_node['colorkey']):
                curve.keyframe_points.insert(nvb_utils.nwtime2frame(key[0], nvb_presets.render_fps), key[c+1])      
    
    # Set alpha channels if there are alpha keys
    if (parsed_node['selfillumcolorkey']):
        # for each axis
        for c in range(3):
            curve = node_action.fcurves.new(data_path='auroraprops.selfillumcolor', index=c)     
            for i, key in enumerate(parsed_node['selfillumcolorkey']):
                curve.keyframe_points.insert(nvb_utils.nwtime2frame(key[0], nvb_presets.render_fps), key[c+1])
    
    return node_action


def emitternode2mesh(parsed_node, override_name = ''):
    '''
    Creates a plane, as aurora emitters are planes
    '''
    if (override_name == ''):
        mesh_name = parsed_node['name']+'.mesh'
    else:
        mesh_name = override_name
    # Create n new (empty) mesh
    emitter_mesh = bpy.data.meshes.new(mesh_name)
    
    xsize = parsed_node['xsize']/100
    ysize = parsed_node['ysize']/100
    
    emitter_mesh.vertices.add(4)
    emitter_mesh.vertices[0].co = ( xsize/2,  ysize/2, 0.0)
    emitter_mesh.vertices[1].co = ( xsize/2, -ysize/2, 0.0)
    emitter_mesh.vertices[2].co = (-xsize/2, -ysize/2, 0.0)
    emitter_mesh.vertices[3].co = (-xsize/2,  ysize/2, 0.0)
    
    emitter_mesh.tessfaces.add(1)
    emitter_mesh.tessfaces.foreach_set('vertices_raw', [0, 1, 2, 3])  
    
    # Create a material/texture
    emitter_mat = create_emitter_material(parsed_node)
    
    # Append the material to the mesh
    emitter_mesh.materials.append(emitter_mat)
    
    # Add simple uv layer
    if (parsed_node['texture'].lower() != 'null'):
        uv_name = parsed_node['name']+'_uv'
        emitter_uv = emitter_mesh.tessface_uv_textures.new(uv_name)
        emitter_mesh.tessface_uv_textures.active = emitter_uv

        blender_face = emitter_mesh.tessfaces[0] # We created one face above
        # Apply material to face
        blender_face.material_index = 0
        # Get the tessface
        blender_tface = emitter_mesh.tessface_uv_textures[0].data[0]
        # Add uv coordinates to face
        blender_tface.uv1 = ( xsize/2,  ysize/2)
        blender_tface.uv2 = ( xsize/2, -ysize/2)
        blender_tface.uv3 = (-xsize/2, -ysize/2)
        blender_tface.uv4 = (-xsize/2,  ysize/2)
        # Apply texture to face
        blender_tface.image = emitter_mat.texture_slots[0].texture.image
            
    # After calling update() tessfaces become inaccessible
    emitter_mesh.validate()    
    emitter_mesh.update()
    
    return emitter_mesh


def woknode2mesh(parsed_node, override_name = ''):
    '''
    Creates a mesh from a parsed ascii node
    '''
    if (override_name == ''):
        mesh_name = parsed_node['name']+'.mesh'
    else:
        mesh_name = override_name    
    # Create n new (empty) mesh
    node_mesh = bpy.data.meshes.new(parsed_node['name']+'.mesh')
    
    # Add the vertices
    node_mesh.vertices.add(len(parsed_node['verts']))
    node_mesh.vertices.foreach_set('co', unpack_list(parsed_node['verts']))
    
    # Add the faces
    node_mesh.tessfaces.add(len(parsed_node['faces']))
    node_mesh.tessfaces.foreach_set('vertices_raw', unpack_face_list(parsed_node['faces'])) 
    
    # Create walkmesh materials
    for i in range(len(nvb_presets.wok_materials)):
    
        mat_name = nvb_presets.wok_materials[i][0] +'.mat'
        
        # Walkmesh materials should be shared across multiple walkmesh objects
        if mat_name in bpy.data.materials.keys():
            node_mat = bpy.data.materials[mat_name]
        else:
            node_mat = bpy.data.materials.new(mat_name)
        
            node_mat.diffuse_color      = nvb_presets.wok_materials[i][1]
            node_mat.diffuse_intensity  = 1.0 
            node_mat.specular_color     = (0.0,0.0,0.0)
            node_mat.specular_intensity = nvb_presets.wok_materials[i][2]
        
        node_mesh.materials.append(node_mat)
    
    # Apply the walkmesh materials
    for i in range(len(parsed_node['faces_info'])):
        # Get a face
        blender_face = node_mesh.tessfaces[i]
          
        # Apply material to face
        blender_face.material_index = parsed_node['faces_info'][i][1]        
    
    # After calling update() tessfaces become inaccessible
    node_mesh.validate()    
    node_mesh.update()
    
    return node_mesh


def lightnode2lamp(parsed_node, override_name = ''):
    '''
    Creates a lamp from a parsed ascii light node
    '''   
    if (override_name == ''):
        lamp_name = parsed_node['name']+'_lamp'
    else:
        lamp_name = override_name    
    # Get light type
    node_lamp = bpy.data.lamps.new(lamp_name, 'POINT')
    
    
    node_lamp.use_diffuse = (parsed_node['ambientonly'] == 0)
    node_lamp.color       = parsed_node['color']
    node_lamp.energy      = parsed_node['multiplier']
    node_lamp.distance    = parsed_node['radius']
    #node_lamp_use_negative = parsed_node['negative']
    #node_lamp.use_sphere  = True # Doesn't really matter
    
    return node_lamp


def trimeshnode2mesh(parsed_node, override_name = ''):
    '''
    Creates a mesh from a parsed ascii trimesh node
    '''
    if (override_name == ''):
        mesh_name = parsed_node['name']+'.mesh'
    else:
        mesh_name = override_name    
    # Create n new (empty) mesh
    node_mesh = bpy.data.meshes.new(mesh_name)
    
    # Add the vertices
    node_mesh.vertices.add(len(parsed_node['verts']))
    node_mesh.vertices.foreach_set('co', unpack_list(parsed_node['verts']))
    
    # Add vertex groups
    
    # Add the faces
    node_mesh.tessfaces.add(len(parsed_node['faces']))
    node_mesh.tessfaces.foreach_set('vertices_raw', unpack_face_list(parsed_node['faces']))
    
    # Create a material/texture
    node_mat = create_mesh_material(parsed_node)
    
    # Append the material to the mesh
    node_mesh.materials.append(node_mat)
    
    # Add the texture coordinates 
    # ( Also check if bitmap is NULL, some joker put in texture coordinates while the texture is null, wich results in an error)
    if ( (len(parsed_node['tverts']) > 0) and (node_mesh.tessfaces) and (parsed_node['bitmap'].lower() != 'null') ):   
        uv_name = parsed_node['name']+'_uv'
        node_uv = node_mesh.tessface_uv_textures.new(uv_name)
        node_mesh.tessface_uv_textures.active = node_uv

        for i in range(len(parsed_node['faces_tverts'])):
            # Get a face
            blender_face = node_mesh.tessfaces[i]
            
            # Apply material to face
            blender_face.material_index = 0
            
            # Get a tessface
            blender_tface = node_mesh.tessface_uv_textures[0].data[i]
            
            # Get the indices of the tverts for this face
            tvert_indices = parsed_node['faces_tverts'][i]
            
            # Get the indices of the verts (for eekadoodle fix)
            vert_indices  = parsed_node['faces'][i]
            
            # BUG - Evil eekadoodle problem where faces that have vert index 0 at location 3 are shuffled.
            if vert_indices[2] == 0:
                tvert_indices = tvert_indices[1], tvert_indices[2], tvert_indices[0]
            # END EEEKADOODLE FIX    
            
            # Add uv coordinates to face
            blender_tface.uv1 = parsed_node['tverts'][tvert_indices[0]]
            blender_tface.uv2 = parsed_node['tverts'][tvert_indices[1]]
            blender_tface.uv3 = parsed_node['tverts'][tvert_indices[2]]
            
            # Apply texture to face
            blender_tface.image = node_mat.texture_slots[0].texture.image
    
    # After calling update() tessfaces become inaccessible
    #node_mesh.validate()    
    node_mesh.update()
    
    return node_mesh


def danglymeshnode2mesh(parsed_node, override_name = ''):
    '''
    Creates a mesh from a parsed ascii node
    '''
    
    # Don't tell anyone, but this is just the same
    node_mesh = trimeshnode2mesh(parsed_node, override_name)
    
    return node_mesh


def skinmeshnode2mesh(parsed_node, override_name = ''):
    '''
    Creates a mesh from a parsed ascii node
    '''
    
    # Don't tell anyone, but this is just the same
    node_mesh = trimeshnode2mesh(parsed_node, override_name)
    
    return node_mesh


def parse_geom_node(ascii_node):
    '''
    Grab the node data from the ascii node an return it in the form of a
    dictionary.
    '''
    
    # The returned node will be a dictionary
    parsed_node = {}
    
    # Set some default values
    parsed_node['type']             = 'dummy'
    parsed_node['name']             = 'unnamed'
    parsed_node['parent']           = 'null'
    parsed_node['position']         = (0.0, 0.0, 0.0)
    parsed_node['orientation']      = (0.0, 0.0, 0.0, 0.0)
    parsed_node['wirecolor']        = (0.0, 0.0, 0.0)
    parsed_node['tilefade']         = 0
    parsed_node['scale']            = 1.0
    parsed_node['render']           = 1
    parsed_node['shadow']           = 0
    parsed_node['beaming']          = 0
    parsed_node['inheritcolor']     = 0
    parsed_node['rotatetexture']    = 0
    parsed_node['alpha']            = 1.0
    parsed_node['transparencyhint'] = 0
    parsed_node['selfillumcolor']   = (0.0, 0.0, 0.0)
    parsed_node['ambient']          = (0.8, 0.8, 0.8)
    parsed_node['diffuse']          = (0.5, 0.5, 0.5)
    parsed_node['specular']         = (0.5, 0.5, 0.5)
    parsed_node['shininess']        = 0
    parsed_node['center']           = (0.0, 0.0, 0.0)
    parsed_node['bitmap']           = 'NULL'
    # For lights 
    parsed_node['radius']           = 5.0
    parsed_node['multiplier']       = 1
    parsed_node['color']            = (0.0, 0.0, 0.0)
    parsed_node['ambientonly']      = 1
    parsed_node['ndynamictype']     = 0
    parsed_node['isdynamic']        = 0
    parsed_node['affectdynamic']    = 0
    parsed_node['lightpriority']    = 5
    parsed_node['fadinglight']      = 1
    parsed_node['flareradius']      = 1
    # For danglymeshes
    parsed_node['period']           = 1.0
    parsed_node['tightness']        = 1.0
    parsed_node['displacement']     = 1.0
    # Misc
    parsed_node['verts']            = []
    parsed_node['faces']            = []
    parsed_node['tverts']           = []
    parsed_node['constraints']      = []
    parsed_node['weights']          = []
    # For Emitters
    parsed_node['affectedbywind']   = 0.0
    parsed_node['m_istinted']       = 1
    parsed_node['bounce']           = 0
    parsed_node['random']           = 0
    parsed_node['inherit']          = 1
    parsed_node['inheritvel']       = 0
    parsed_node['inherit_local']    = 0
    parsed_node['inherit_part']     = 0
    parsed_node['splat']            = 0
    parsed_node['renderorder']      = 0
    parsed_node['spawntype']        = 1
    parsed_node['update']           = 1
    #parsed_node['render']           = 0 # same as for meshes
    parsed_node['blend']            = 1
    parsed_node['texture']          = 'NULL'
    parsed_node['chunkname']        = ''
    parsed_node['xgrid']            = 5
    parsed_node['ygrid']            = 5
    parsed_node['loop']             = 0
    parsed_node['deadspace']        = 0.0
    parsed_node['twosidedtex']      = 0
    parsed_node['blastradius']      = 0
    parsed_node['blastlength']      = 0
    parsed_node['colorstart']       = (1.0, 1.0, 1.0)
    parsed_node['colorend']         = (1.0, 1.0, 1.0)
    parsed_node['alphastart']       = 1.0
    parsed_node['alphaend']         = 1.0
    parsed_node['sizestart']        = 1.0
    parsed_node['sizeend']          = 1.0
    parsed_node['sizestart_y']      = 0.0
    parsed_node['sizeend_y']        = 0.0
    parsed_node['framestart']       = 0
    parsed_node['frameend']         = 30
    parsed_node['birthrate']        = 10
    parsed_node['lifeexp']          = 3.0
    parsed_node['mass']             = 0.0
    parsed_node['spread']           = 1.0
    parsed_node['particlerot']      = 0.0  
    parsed_node['velocity']         = 1.0
    parsed_node['randvel']          = 0.0
    parsed_node['fps']              = 10
    parsed_node['xsize']            = 100
    parsed_node['ysize']            = 100
    parsed_node['bounce_co']        = 0.0
    parsed_node['blurlength']       = 10.0
    parsed_node['lightningdelay']   = 0.0
    parsed_node['lightningradius']  = 0.0
    parsed_node['lightningsubdiv']  = 0
    parsed_node['lightningscale']   = 0.0 
    parsed_node['combinetime']      = 0.0
    parsed_node['drag']             = 0.0
    parsed_node['grav']             = 0.0 
    parsed_node['threshold']        = 0.0
    parsed_node['p2p']              = 0
    parsed_node['p2p_sel']          = 1
    parsed_node['p2p_bezier2']      = 0.0
    parsed_node['p2p_bezier3']      = 0.0
    
    # Get node type first
    line = []
    pos = 0
    while (pos < len(ascii_node)):
        line       = ascii_node[pos]
        first_word = line[0].lower()
        if (first_word == 'node'): 
            parsed_node['type'] = line[1].lower()
            parsed_node['name'] = line[2]
            pos = len(ascii_node)+1
        pos += 1
    
    # Gather the actual node properties 
    line = []
    pos = 0
    while (pos < len(ascii_node)):
        line       = ascii_node[pos]
        first_word = line[0].lower()
        if (first_word == 'node'):
            pass # We already have this 
        
        elif (first_word == 'parent'):
            parsed_node['parent']    = line[1]
        
        elif (first_word == 'position'): 
            parsed_node['position'] = ( float(line[1]), 
                                        float(line[2]), 
                                        float(line[3]) )  
        
        elif (first_word == 'orientation'): 
            parsed_node['orientation'] = ( float(line[1]), 
                                           float(line[2]), 
                                           float(line[3]), 
                                           float(line[4]) )
        
        elif (first_word == 'wirecolor'):
            parsed_node['wirecolor'] = ( float(line[1]), 
                                         float(line[2]), 
                                         float(line[3]) )
        
        elif (first_word == 'tilefade'): 
            parsed_node['tilefade'] = int(line[1])
         
        elif (first_word == 'scale'): 
            parsed_node['scale'] = float(line[1])
        
        elif (first_word == 'render'):
            if (is_numeric(line[1])):
                parsed_node['render'] = int(line[1])
            else:
                if (line[1].lower() == 'normal'): # Also for meshes
                    parsed_node['render'] = 1                    
                elif (line[1].lower() == 'linked'):
                    parsed_node['render'] = 2
                elif (line[1].lower() == 'billboard_to_local_z'):
                    parsed_node['render'] = 3
                elif (line[1].lower() == 'billboard_to_world_z'):
                    parsed_node['render'] = 4
                elif (line[1].lower() == 'aligned_to_world_z'):
                    parsed_node['render'] = 5
                elif (line[1].lower() == 'aligned_to_particle_dir'):
                    parsed_node['render'] = 6
                elif (line[1].lower() == 'motion_blur'):
                    parsed_node['render'] = 7                     
                else:
                    parsed_node['render'] = 0            
                
        elif (first_word == 'shadow'):
            parsed_node['shadow'] = int(line[1])
        
        elif (first_word == 'beaming'):
            parsed_node['beaming'] = int(line[1])
        
        elif (first_word == 'inheritcolor '):
            parsed_node['inheritcolor '] = int(line[1])
        
        elif (first_word == 'rotatetexture'):
             parsed_node['rotatetexture'] = int(line[1])  
        
        elif (first_word == 'alpha'): 
            parsed_node['alpha'] = float(line[1])
        
        elif (first_word == 'transparencyhint'):
             parsed_node['transparencyhint'] = int(line[1])
        
        elif (first_word == 'selfillumcolor'): # Self illumination color
            parsed_node['selfillumcolor'] = ( float(line[1]), 
                                              float(line[2]), 
                                              float(line[3]) )
        
        elif (first_word == 'ambient'): 
            parsed_node['ambient'] = ( float(line[1]), 
                                       float(line[2]), 
                                       float(line[3]) )
           
        elif (first_word == 'diffuse'): 
            parsed_node['diffuse'] = ( float(line[1]), 
                                       float(line[2]), 
                                       float(line[3]) )  
        
        elif (first_word == 'specular'):   
            parsed_node['specular'] = ( float(line[1]), 
                                        float(line[2]), 
                                        float(line[3]) )
        
        elif (first_word == 'shininess'): 
            parsed_node['shininess'] = int(float(line[1]))
        
        elif (first_word == 'center'):
            if is_numeric(line[1]):
                parsed_node['center'] = ( float(line[1]), 
                                          float(line[2]), 
                                          float(line[3]) ) 
        
        elif (first_word == 'bitmap'): 
            parsed_node['bitmap'] = line[1] 
        
        elif (first_word == 'radius'): # lights only
            parsed_node['radius'] = float(line[1])
        
        elif (first_word == 'multiplier'): # lights only
            parsed_node['multiplier'] = float(line[1])
        
        elif (first_word == 'color'): # lights only
            parsed_node['color'] = ( float(line[1]), 
                                     float(line[2]), 
                                     float(line[3]) ) 
        
        elif (first_word == 'ambientonly'): # lights only
            parsed_node['ambientonly'] = int(line[1])
        
        elif (first_word == 'ndynamictype'): # lights only
            parsed_node['ndynamictype'] = int(line[1])
        
        elif (first_word == 'isdynamic'): # lights only
            parsed_node['isdynamic'] = int(line[1]) 
        
        elif (first_word == 'flareradius'): # lights only
            parsed_node['flareradius'] = int(line[1])  
        
        elif (first_word == 'affectdynamic'): # lights only
            parsed_node['affectdynamic'] = int(line[1])  
        
        elif (first_word == 'lightpriority'): # lights only
            parsed_node['lightpriority'] = int(line[1])
        
        elif (first_word == 'fadinglight'): # lights only
            parsed_node['fadinglight'] = int(line[1])
         
        elif (first_word == 'displacement'): # danglymeshes only
            parsed_node['displacement'] = float(line[1])
        
        elif (first_word == 'period'): # danglymeshes only
            parsed_node['period'] = float(line[1])
        
        elif (first_word == 'tightness'): # danglymeshes only
            parsed_node['tightness'] = float(line[1])
        
        elif (first_word == 'verts'): 
            # We expect numeric values (floats) in the next few lines
            vert_list = []
            
            pos += 1 # next line (current line does not contain any verts) 
            numeric = True
            while (pos < len(ascii_node)) and (numeric): 
                line = ascii_node[pos]
                
                numeric = is_numeric(line[0])
                if (numeric):                                
                    vert_list.append( (float(line[0]), 
                                       float(line[1]), 
                                       float(line[2])) )
                    pos += 1 # continue counting lines
             
            pos -= 1 # We have counted one line too far
             
            parsed_node['verts'] = vert_list
         
        elif (first_word == 'faces'):
            # We expect numeric values (integers) in the next few lines
            face_list       = []
            face_tvert_list = []
            face_info_list  = []
            
            pos += 1 # next line (current line does not contain any faces) 
            numeric = True
            while (pos < len(ascii_node)) and (numeric):             
                line = ascii_node[pos]
                
                numeric = is_numeric(line[0])
                if (numeric):                  
                    face_list.append( (int(line[0]), 
                                       int(line[1]), 
                                       int(line[2])) )
                    face_tvert_list.append( (int(line[4]), 
                                             int(line[5]),
                                             int(line[6])) )
                    face_info_list.append( [int(line[3]), int(line[7])] )
                    pos += 1 # continue counting lines
            
            pos -= 1 # We have counted one line too far
            
            parsed_node['faces']        = face_list
            parsed_node['faces_tverts'] = face_tvert_list
            parsed_node['faces_info']   = face_info_list
         
        elif (first_word == 'tverts'):                        
            # We expect numeric values (floats) in the next few lines
            tvert_list  = []
            
            pos += 1 # next line (current line does not contain any tverts)
            numeric = True
            while (pos < len(ascii_node)) and (numeric):
                line = ascii_node[pos] 
                
                numeric = is_numeric(line[0])
                if (numeric):                
                    # We throw away line[2], it is always 0 anyway
                    tvert_list.append( (float(line[0]), float(line[1])) ) 
                    pos += 1 # continue counting lines
            
            pos -= 1 # We have counted one line too far
            
            parsed_node['tverts'] = tvert_list
         
        elif (first_word == 'constraints'): 
            # For danglymeshes, these will be weights in a vertex group
            constraint_list  = []
            
            pos += 1 # next line (current line does not contain any values) 
            numeric = True
            while (pos < len(ascii_node)) and (numeric):
                line = ascii_node[pos]
                
                numeric = is_numeric(line[0])
                if (numeric):
                    constraint_list.append( float(line[0]) )
                    pos += 1            
            
            pos -= 1 # We have counted one line too far
            
            parsed_node['constraints'] = constraint_list
         
        elif (first_word == 'weights'): # For skins
            # Cannot rely on this to be present or correct, 
            # but we have no other choice here or it will get very ugly
            weight_count      = int(line[1]) 
            vertex_skingroups = []
            
            pos += 1 # next line (current line does not contain any values) 
            while (pos < len(ascii_node)) and (weight_count > 0):
                line = ascii_node[pos]
                
                # A line looks like this 
                # [group_name, vertex_weight, group_name, vertex_weight]
                # We create a list looking like this: 
                # [[group_name, vertex_weight], [group_name, vertex_weight]]
                i = 0
                memberships = []
                while (i < len(line)):
                    memberships.append( [line[i], float(line[i+1])] )
                    i += 2
                
                vertex_skingroups.append(memberships)
                
                weight_count -= 1
                pos += 1            
            
            parsed_node['weights'] = vertex_skingroups
            
            pos -= 1 # We have counted one line too far
         
        elif (first_word == 'aabb'): 
            # For walkmeshes: Axis Aligned Bounding Box
            pass # No need to import this. Faces & verts suffice
        
        # Stuff for emitters
        elif (first_word == 'affectedbywind'):
            if (is_numeric(line[1])):
                parsed_node['affectedbywind'] = float(line[1])
            else:
                if (line[1].lower() == 'false'):
                    parsed_node['affectedbywind'] = 0.0
                else:
                    parsed_node['affectedbywind'] = 1.0
        
        elif (first_word == 'm_istinted'):
            parsed_node['m_istinted'] = int(line[1])
        
        elif (first_word == 'random'):
            parsed_node['random'] = int(line[1])
        
        elif (first_word == 'inherit'):
            parsed_node['inherit'] = int(line[1])
        
        elif (first_word == 'inheritvel'):
            parsed_node['inheritvel'] = int(line[1])
        
        elif (first_word == 'inherit_local'):
            parsed_node['inherit_local'] = int(line[1])
        
        elif (first_word == 'inherit_part'):
            parsed_node['inherit_part'] = int(line[1])
        
        elif (first_word == 'splat'):
            parsed_node['splat'] = int(line[1])
            
        elif (first_word == 'renderorder'):
            parsed_node['renderorder'] = int(line[1])
            
        elif (first_word == 'opacity'):
            parsed_node['opacity'] = float(line[1])
            
        elif (first_word == 'spawntype'):            
            if (is_numeric(line[1])):
                parsed_node['spawntype'] = int(line[1])
            else:
                if (line[1].lower() == 'normal'):
                    parsed_node['spawntype'] = 1
                elif (line[1].lower() == 'trail'):
                    parsed_node['spawntype'] = 2            
                else:
                    parsed_node['spawntype'] = 1
        
        elif (first_word == 'update'):     
            if (is_numeric(line[1])):
                parsed_node['update'] = int(line[1])
            else:
                if (line[1].lower() == 'normal'):
                    parsed_node['update'] = 1
                elif (line[1].lower() == 'linked'):
                    parsed_node['update'] = 2
                elif (line[1].lower() == 'billboard_to_local_z'):
                    parsed_node['update'] = 3
                elif (line[1].lower() == 'billboard_to_world_z'):
                    parsed_node['update'] = 4
                elif (line[1].lower() == 'aligned_to_world_z'):
                    parsed_node['update'] = 5
                elif (line[1].lower() == 'aligned_to_particle_dir'):
                    parsed_node['update'] = 6
                elif (line[1].lower() == 'motion_blur'):
                    parsed_node['update'] = 7
                else:
                    parsed_node['update'] = 1
            
        elif (first_word == 'blend'):
            if (is_numeric(line[1])):
                parsed_node['blend'] = int(line[1])
            else:
                if (line[1].lower() == 'normal'):
                    parsed_node['blend'] = 1
                elif (line[1].lower() == 'punch-through'):
                    parsed_node['blend'] = 2
                elif (line[1].lower() == 'lighten'):
                    parsed_node['blend'] = 3                    
                else:
                    parsed_node['blend'] = 1
    
        elif (first_word == 'bounce'):
            parsed_node['bounce'] = int(line[1])
            
        elif (first_word == 'texture'):
            parsed_node['texture'] = line[1]
            
        elif (first_word == 'chunkname'):
            parsed_node['chunkname'] = line[1]
        
        elif (first_word == 'xgrid'):
            parsed_node['xgrid'] = int(line[1])
        
        elif (first_word == 'ygrid'):
            parsed_node['ygrid'] = int(line[1])
            
        elif (first_word == 'loop'):
            parsed_node['loop'] = int(line[1])
        
        elif (first_word == 'deadspace'):
            parsed_node['deadspace'] = float(line[1])

        elif (first_word == 'twosidedtex'):
            parsed_node['twosidedtex'] = int(line[1])
        
        elif (first_word == 'blastradius'):
            parsed_node['blastradius'] = float(line[1])
        
        elif (first_word == 'blastlength'):
            parsed_node['blastlength'] = float(line[1])
    
        elif (first_word == 'colorstart'):
            parsed_node['colorstart'] = ( float(line[1]), 
                                          float(line[2]), 
                                          float(line[3]) )
        
        elif (first_word == 'colorend'):
            parsed_node['colorend'] = ( float(line[1]), 
                                        float(line[2]), 
                                        float(line[3]) )
        
        elif (first_word == 'alphastart'):
            parsed_node['alphastart'] = float(line[1])
            
        elif (first_word == 'alphaend'):
            parsed_node['alphaend'] = float(line[1])
            
        elif (first_word == 'sizestart'):
            parsed_node['sizestart'] = float(line[1])
        
        elif (first_word == 'sizeend'):
            parsed_node['sizeend'] = float(line[1])
            
        elif (first_word == 'sizestart_y'):
            parsed_node['sizestart_y'] = float(line[1])
            
        elif (first_word == 'sizeend_y'):
            parsed_node['sizeEnd_y'] = float(line[1])            
        
        elif (first_word == 'framestart'):
            parsed_node['framestart'] = int(line[1])
        
        elif (first_word == 'frameend'):
            parsed_node['frameend'] = int(line[1])
        
        elif (first_word == 'birthrate'):
            parsed_node['birthrate'] = int(line[1])
        
        elif (first_word == 'lifeexp'):
            parsed_node['lifeexp'] = float(line[1])
        
        elif (first_word == 'mass'):
            parsed_node['mass'] = float(line[1])
        
        elif (first_word == 'spread'):
            parsed_node['spread'] = float(line[1])
        
        elif (first_word == 'particlerot'):
            parsed_node['particlerot'] = float(line[1])
  
        elif (first_word == 'velocity'):
            parsed_node['velocity'] = float(line[1])
        
        elif (first_word == 'randvel'):
            parsed_node['randvel'] = float(line[1])
            
        elif (first_word == 'fps'):
            parsed_node['fps'] = int(line[1])
            
        elif (first_word == 'xsize'):
            parsed_node['xsize'] = float(line[1])
        
        elif (first_word == 'ysize'):
            parsed_node['ysize'] = float(line[1])
        
        elif (first_word == 'bounce_co'):
            parsed_node['bounce_co'] = float(line[1])        
        
        elif (first_word == 'blurlength'):
            parsed_node['blurlength'] = float(line[1])        
        
        elif (first_word == 'lightningdelay'):
            parsed_node['lightningdelay'] = float(line[1])
  
        elif (first_word == 'lightningradius'):
            parsed_node['lightningradius'] = float(line[1])
        
        elif (first_word == 'lightningsubdiv'):
            parsed_node['lightningsubdiv'] = int(line[1])
            
        elif (first_word == 'lightningscale'):
            parsed_node['lightningscale'] = float(line[1])
    
        elif (first_word == 'combinetime'):
            parsed_node['combinetime'] = float(line[1])
        
        elif (first_word == 'drag'):
            parsed_node['drag'] = float(line[1])
        
        elif (first_word == 'grav'):
            parsed_node['grav'] = float(line[1])
            
        elif (first_word == 'threshold'):
            parsed_node['threshold'] = float(line[1])
        
        elif (first_word == 'p2p'):
            if (is_numeric(line[1])):
                parsed_node['p2p'] = int(line[1])
            else:
                parsed_node['p2p'] = 0
        
        elif (first_word == 'p2p_sel'):
            if (is_numeric(line[1])):
                parsed_node['p2p_sel'] = int(line[1])
            else:
                parsed_node['p2p_sel'] = 1
        
        elif (first_word == 'p2p_bezier2'):
            parsed_node['p2p_bezier2'] = float(line[1])
        
        elif (first_word == 'p2p_bezier3'):
            parsed_node['p2p_bezier3'] = float(line[1])
    
        pos += 1
       
    return parsed_node


def parse_animation_node(ascii_node):
    parsed_node = {}
    
    parsed_node['object_type']       = 'dummy'
    parsed_node['object_name']       = 'null'
    parsed_node['parent']            = 'null'
    parsed_node['birthratekey']      = []
    parsed_node['orientationkey']    = []
    parsed_node['positionkey']       = []
    parsed_node['scalekey']          = []
    parsed_node['colorkey']          = []
    parsed_node['alphakey']          = []
    parsed_node['selfillumcolorkey'] = []
    parsed_node['empty']             = True    
    
    # Gather the actual node properties 
    line = []
    pos = 0
    while (pos < len(ascii_node)):
        line       = ascii_node[pos]
        first_word = line[0].lower()
        
        if (first_word == 'node'): 
            # name of the affected object/node
            parsed_node['object_type'] = line[1].lower()
            parsed_node['object_name'] = line[2]            
        elif (first_word == 'parent'):
            # usually the same as defined in the geometry
            parsed_node['parent'] = line[1]
            
        elif (first_word == 'birthratekey'):
            # We expect numeric values
            key_list = []
            parsed_node['empty'] = False
            
            pos += 1 # next line (current line does not contain any verts)
            numeric = True
            while (pos < len(ascii_node)) and (numeric):
                line = ascii_node[pos]
                 
                numeric = is_numeric(line[0])
                if (numeric):               
                    key_list.append( (float(line[0]), 
                                      float(line[1])) )
                    pos += 1 # continue counting lines
            
            pos -= 1 # We have counted one line too far
            
            # Set the data
            parsed_node['birthratekey'] = key_list            
             
        elif (first_word == 'orientationkey'):
            # We expect numeric values (4 tuples of floats)
            key_list = []
            parsed_node['empty'] = False
            
            pos += 1 # next line (current line does not contain any verts)
            numeric = True
            while (pos < len(ascii_node)) and (numeric):
                line = ascii_node[pos]
                 
                numeric = is_numeric(line[0])
                if (numeric):               
                    key_list.append( (float(line[0]), 
                                      float(line[1]), 
                                      float(line[2]), 
                                      float(line[3]), 
                                      float(line[4])) )
                    pos += 1 # continue counting lines
            
            pos -= 1 # We have counted one line too far
            
            # Set the data
            parsed_node['orientationkey'] = key_list
            
        elif (first_word == 'orientation'): 
            # It seems this is only used, if only one key is present
            parsed_node['orientation'] = ( float(line[1]), 
                                           float(line[2]), 
                                           float(line[3]), 
                                           float(line[4]) )
            parsed_node['empty'] = False
            pos += 1
        
        elif (first_word == 'positionkey'):
            # We expect numeric values (4 tuples of floats)
            key_list   = []
            parsed_node['empty'] = False
            
            pos += 1 # next line (current line does not contain any verts) 
            numeric = True
            while (pos < len(ascii_node)) and (numeric):
                line = ascii_node[pos]
                
                numeric = is_numeric(line[0])
                if (numeric):
                    key_list.append( (float(line[0]), 
                                      float(line[1]), 
                                      float(line[2]), 
                                      float(line[3])) )
                    pos += 1 # continue counting lines
            
            pos -= 1 # We have counted one line too far
            
            # Set the data
            parsed_node['positionkey'] = key_list
        
        elif (first_word == 'position'): 
            # It seems this is only used, if only one key is present
            parsed_node['position'] = ( float(line[1]), 
                                        float(line[2]), 
                                        float(line[3]) )
            parsed_node['empty'] = False
            
            pos += 1
        
        elif (first_word == 'scalekey'):
            # We expect numeric values (4 tuples of floats)
            key_list   = []
            parsed_node['empty'] = False
            
            pos += 1 # next line (current line does not contain any verts) 
            numeric = True
            while (pos < len(ascii_node)) and (numeric):
                line = ascii_node[pos]
                
                numeric = is_numeric(line[0])
                if (numeric):
                    key_list.append( (float(line[0]), 
                                      float(line[1]), 
                                      float(line[2]), 
                                      float(line[3])) )
                    pos += 1 # continue counting lines
            
            pos -= 1 # We have counted one line too far
            
            # Set the data
            parsed_node['scalekey'] = key_list
        
        elif (first_word == 'colorkey'):
            # We expect numeric values (4 tuples of floats)
            key_list   = []
            parsed_node['empty'] = False
            
            pos += 1 # next line (current line does not contain any verts) 
            numeric = True
            while (pos < len(ascii_node)) and (numeric):
                line = ascii_node[pos]
                
                numeric = is_numeric(line[0])
                if (numeric):
                    key_list.append( (float(line[0]), 
                                      float(line[1]), 
                                      float(line[2]), 
                                      float(line[3])) )
                    pos += 1 # continue counting lines
            
            pos -= 1 # We have counted one line too far
            
            # Set the data
            parsed_node['colorkey'] = key_list
        
        elif (first_word == 'alphakey'):
            # We expect numeric values (tuples of floats) in the next few lines
            #key_count  = int(line[1]) # Cannot rely on this to be present or correct
            key_list   = []
            parsed_node['empty'] = False
            
            pos += 1 # next line (current line does not contain any verts) 
            numeric = True
            while (pos < len(ascii_node)) and (numeric):
                line = ascii_node[pos]
                
                numeric = is_numeric(line[0])
                if (numeric):
                    key_list.append( (float(line[0]), float(line[1])) )
                    pos += 1 # continue counting lines
            
            pos -= 1 # We have counted one line too far
            
            # Set the data
            parsed_node['alphakey'] = key_list 
        
        elif (first_word == 'selfillumcolorkey'):
            # We expect numeric values (4 tuples of floats) in the next few lines
            #key_count  = int(line[1]) # Cannot rely on this to be present or correct
            key_list   = []
            parsed_node['empty'] = False
            
            pos += 1 # next line (current line does not contain any verts) 
            numeric = True
            while (pos < len(ascii_node)) and (numeric):
                line = ascii_node[pos]
                 
                numeric = is_numeric(line[0])
                if (numeric):
                    key_list.append( (float(line[0]), 
                                      float(line[1]), 
                                      float(line[2]), 
                                      float(line[3])) )
                    pos += 1 # continue counting lines
            
            pos -= 1 # We have counted one line too far
            
            # Set the data
            parsed_node['selfillumcolorkey'] = key_list          
        
        pos += 1
    
    return parsed_node


def parse_geometry(ascii_geom):
    '''
    Handles the actual generation of Objects/meshes
    '''
    node_list      = []
    
    # Get all the nodes from the ascii_model
    current_line    = 0
    ascii_geom_node = []
    line            = []
    for current_line in range(0, len(ascii_geom)):
        ascii_geom_node  = []
        line             = ascii_geom[current_line]
        if (line[0] == 'node'):
            # Find the end of the ascii node
            node_endline = find_line('endnode', ascii_geom, current_line)
            ascii_geom_node   = ascii_geom[current_line:node_endline]
            # Pass the ascii node to the parser
            parsed_node = parse_geom_node(ascii_geom_node)
            # Add the parsed node to the node_list
            node_list.append(parsed_node)
            # jump to the ending of the model
            current_line = node_endline
        
        else:   
            current_line += 1
    
    # Build nodes
    parent_list = {}
    object_dict = {}
    dummy_mesh = bpy.data
    for parsed_node in node_list:
        # First get the node type
        if (parsed_node['type'] == 'dummy'):    
            # Create the object (no mesh needed for a dummy)
            node_object = bpy.data.objects.new(parsed_node['name'], None)
            
            # Set properties
            nvb_utils.setRotationAurora(node_object, \
                                        parsed_node['orientation'])           
            node_object.scale    = (parsed_node['scale'], \
                                    parsed_node['scale'], \
                                    parsed_node['scale'])
            node_object.location = parsed_node['position'] 
            
            # Set additional data
            if (node_object.name == glob_modelname):
                node_object.auroraprops.dummytype      = 'MDLBASE'
                node_object.auroraprops.classification = get_mdl_classification()
                node_object.auroraprops.supermodel     = glob_supermodel
                node_object.auroraprops.animationscale = glob_animationscale
            else:
                node_object.auroraprops.dummytype = 'NONE'
            node_object.auroraprops.wirecolor = parsed_node['wirecolor']
            
            # Link object to scene
            glob_import_scene.objects.link(node_object)
            object_dict[parsed_node['name']] = [node_object, parsed_node['parent']]
            
        elif (parsed_node['type'] == 'trimesh'):           
            if (parsed_node['tilefade'] == 0) or (glob_import_fading_obj):            
                # Create the mesh
                node_mesh = trimeshnode2mesh(parsed_node) 
                
                # Create the object
                node_object = bpy.data.objects.new(parsed_node['name'], node_mesh)
                
                # Set properties
                nvb_utils.setRotationAurora(node_object, \
                                            parsed_node['orientation'])           
                node_object.scale = (parsed_node['scale'], \
                                     parsed_node['scale'], \
                                     parsed_node['scale'])
                node_object.location = parsed_node['position']
            
                # Add shading groups
                add_shading_groups(node_object, parsed_node)
            
                # Aurora properties
                node_object.auroraprops.meshtype         = 'TRIMESH'
                node_object.auroraprops.wirecolor        = parsed_node['wirecolor']
                node_object.auroraprops.tilefade         = parsed_node['tilefade']
                #node_object.auroraprops.scale            = parsed_node['scale']
                node_object.auroraprops.render           = (parsed_node['render'] == 1)
                node_object.auroraprops.shadow           = (parsed_node['shadow'] == 1)
                node_object.auroraprops.beaming          = (parsed_node['beaming'] == 1)
                node_object.auroraprops.inheritcolor     = (parsed_node['inheritcolor'] == 1)
                node_object.auroraprops.rotatetexture    = (parsed_node['rotatetexture'] == 1)
                node_object.auroraprops.transparencyhint = parsed_node['transparencyhint']
                node_object.auroraprops.selfillumcolor   = parsed_node['selfillumcolor']
                node_object.auroraprops.ambientcolor     = parsed_node['ambient']
                node_object.auroraprops.shininess        = parsed_node['shininess']
            
                # Link object to scene
                glob_import_scene.objects.link(node_object)
                object_dict[node_object.name] = [node_object, parsed_node['parent']]
        
        elif (parsed_node['type'] == 'danglymesh'):
            if (parsed_node['tilefade'] == 0) or (glob_import_fading_obj):
                # Create the mesh
                node_mesh = danglymeshnode2mesh(parsed_node)              
            
                # Create the object
                node_object = bpy.data.objects.new(parsed_node['name'], node_mesh)
            
                # Set properties
                nvb_utils.setRotationAurora(node_object, \
                                            parsed_node['orientation'])           
                node_object.scale = (parsed_node['scale'], \
                                     parsed_node['scale'], \
                                     parsed_node['scale'])
                node_object.location = parsed_node['position']
            
                # Add shading groups
                add_shading_groups(node_object, parsed_node)
            
                # Add a vertex group for the danglymesh
                danglegroup = add_danglegroup(node_object, parsed_node)
                node_object.auroraprops.danglegroup = danglegroup.name
            
                # Aurora properties
                node_object.auroraprops.meshtype         = 'DANGLYMESH'
                node_object.auroraprops.wirecolor        = parsed_node['wirecolor']
                node_object.auroraprops.tilefade         = parsed_node['tilefade']
                #node_object.auroraprops.scale            = parsed_node['scale']
                node_object.auroraprops.render           = (parsed_node['render'] == 1)
                node_object.auroraprops.shadow           = (parsed_node['shadow'] == 1)
                node_object.auroraprops.beaming          = (parsed_node['beaming'] == 1)
                node_object.auroraprops.inheritcolor     = (parsed_node['inheritcolor'] == 1)
                node_object.auroraprops.rotatetexture    = (parsed_node['rotatetexture'] == 1)
                node_object.auroraprops.transparencyhint = parsed_node['transparencyhint']
                node_object.auroraprops.selfillumcolor   = parsed_node['selfillumcolor']
                node_object.auroraprops.ambientcolor     = parsed_node['ambient']
                node_object.auroraprops.shininess        = parsed_node['shininess']
                node_object.auroraprops.period           = parsed_node['period']
                node_object.auroraprops.tightness        = parsed_node['tightness']
                node_object.auroraprops.displacement     = parsed_node['displacement']
            
                # Link object to scene
                glob_import_scene.objects.link(node_object)    
                object_dict[node_object.name] = [node_object, parsed_node['parent']]
        
        elif (parsed_node['type'] == 'skin'):
            if (parsed_node['tilefade'] == 0) or (glob_import_fading_obj):             
                # Create the mesh
                node_mesh = skinmeshnode2mesh(parsed_node) 
            
                # Create the object
                node_object = bpy.data.objects.new(parsed_node['name'], node_mesh)
            
                # Set properties
                nvb_utils.setRotationAurora(node_object, \
                                        parsed_node['orientation'])           
                node_object.scale = (parsed_node['scale'], \
                                     parsed_node['scale'], \
                                     parsed_node['scale'])
                node_object.location = parsed_node['position']
            
                # Add shading groups
                add_shading_groups(node_object, parsed_node)
            
                # Add a vertex group for the skin
                add_skingroups(node_object, parsed_node)
            
                # Aurora properties
                node_object.auroraprops.meshtype         = 'SKIN'
                node_object.auroraprops.wirecolor        = parsed_node['wirecolor']
                node_object.auroraprops.tilefade         = parsed_node['tilefade']
                #node_object.auroraprops.scale            = parsed_node['scale']
                node_object.auroraprops.render           = (parsed_node['render'] == 1)
                node_object.auroraprops.shadow           = (parsed_node['shadow'] == 1)
                node_object.auroraprops.beaming          = (parsed_node['beaming'] == 1)
                node_object.auroraprops.inheritcolor     = (parsed_node['inheritcolor'] == 1)
                node_object.auroraprops.rotatetexture    = (parsed_node['rotatetexture'] == 1)
                node_object.auroraprops.transparencyhint = parsed_node['transparencyhint']
                node_object.auroraprops.selfillumcolor   = parsed_node['selfillumcolor']
                node_object.auroraprops.ambientcolor     = parsed_node['ambient']
                node_object.auroraprops.shininess        = parsed_node['shininess']
            
                # Link object to scene
                glob_import_scene.objects.link(node_object)
                object_dict[node_object.name] = [node_object, parsed_node['parent']]
        
        elif (parsed_node['type'] == 'emitter'):
            # Create the mesh for the emitter
            node_mesh = emitternode2mesh(parsed_node) 

            # Create the object
            node_object = bpy.data.objects.new(parsed_node['name'], node_mesh)
            
            add_particle_system(node_object, parsed_node)
            
            # Set properties
            nvb_utils.setRotationAurora(node_object, \
                                        parsed_node['orientation'])           
            node_object.scale    = (parsed_node['scale'], \
                                    parsed_node['scale'], \
                                    parsed_node['scale'])
            node_object.location = parsed_node['position']
            node_object.auroraprops.wirecolor = parsed_node['wirecolor']
            
            # Aurora properties
            node_object.auroraprops.meshtype     = 'EMITTER'
            
            # Link object to scene
            glob_import_scene.objects.link(node_object)
            object_dict[node_object.name] = [node_object, parsed_node['parent']]
        
        elif (parsed_node['type'] == 'light'):
            if (glob_import_lights):
                # Create the lamp
                node_lamp = lightnode2lamp(parsed_node)
            
                # Create the object
                node_object = bpy.data.objects.new(parsed_node['name'], node_lamp)
            
                # Set properties
                nvb_utils.setRotationAurora(node_object, \
                                            parsed_node['orientation']) 
                node_object.location = parsed_node['position']  
            
                # Aurora properties
                node_object.auroraprops.tilelight     = get_tilelight_type(node_object)
                node_object.auroraprops.shadow        = (parsed_node['shadow'] == 1) 
                node_object.auroraprops.wirecolor     = parsed_node['wirecolor']
                node_object.auroraprops.lightpriority = parsed_node['lightpriority']
                node_object.auroraprops.fadinglight   = (parsed_node['fadinglight'] == 1)
                node_object.auroraprops.isdynamic     = (parsed_node['ndynamictype'] == 1) or (parsed_node['isdynamic'] == 1)
                node_object.auroraprops.affectdynamic = (parsed_node['affectdynamic'] == 1)
            
                # Link object to scene
                glob_import_scene.objects.link(node_object)
                object_dict[node_object.name] = [node_object, parsed_node['parent']]
        
        elif (parsed_node['type'] == 'aabb'): # Walkmesh
            if (glob_import_walkmesh):
                # Create the walkmesh
                node_mesh = woknode2mesh(parsed_node, node_object.name)
                
                # Create the object
                node_object = bpy.data.objects.new(parsed_node['name'], node_mesh)
                
                # Set properties
                nvb_utils.setRotationAurora(node_object, \
                                            parsed_node['orientation']) 
                node_object.location = parsed_node['position']
                
                # Aurora properties
                node_object.auroraprops.meshtype         = 'AABB'
                node_object.auroraprops.wirecolor        = parsed_node['wirecolor']
                node_object.auroraprops.tilefade         = parsed_node['tilefade']
                #node_object.auroraprops.scale            = parsed_node['scale']
                node_object.auroraprops.render           = (parsed_node['render'] == 1)
                node_object.auroraprops.shadow           = (parsed_node['shadow'] == 1)
                #node_object.auroraprops.beaming          = (parsed_node['beaming'] == 1)
                #node_object.auroraprops.inheritcolor     = (parsed_node['inheritcolor'] == 1)            
                #node_object.auroraprops.rotatetexture    = (parsed_node['rotatetexture'] == 1)
                node_object.auroraprops.transparencyhint = parsed_node['transparencyhint']
                #node_object.auroraprops.selfillumcolor   = parsed_node['selfillumcolor']
                
                # Link object to scene
                glob_import_scene.objects.link(node_object)
                object_dict[node_object.name] = [node_object, parsed_node['parent']]
    
    # Set parents
    for node_name, node_info in object_dict.items():
        node_object = node_info[0]
        parent_name = node_info[1]
        if (parent_name.lower() != 'null'):
            if parent_name in object_dict:
                node_object.parent                = object_dict[parent_name][0]
                node_object.matrix_parent_inverse = object_dict[parent_name][0].matrix_world.inverted()
            else:
                print('WARNING: Object ' + node_name + ' has no parent ' +  parent_name)
    
    glob_import_scene.update()


def parse_animation_scene(ascii_anim):
    animation_dict = {}
    
    animation_dict['anim_name']      = 'nameless'    
    animation_dict['anim_transtime'] = 0.25
    animation_dict['anim_length']    = 1.00
    animation_dict['anim_root']      = 'null'
    
    # Get some general data
    current_line    = 0
    line            = []    
    for current_line in range(0, len(ascii_anim)):
        line             = ascii_anim[current_line]
        first_word       = line[0].lower()
        if (first_word == 'newanim'):
            animation_dict['anim_name']      = line[1]
        elif (first_word == 'length'):
            animation_dict['anim_length']    = float(line[1])
        elif (first_word == 'transtime'):
            animation_dict['anim_transtime'] = float(line[1])
        elif (first_word == 'animroot'):
            animation_dict['anim_root']      = line[1]            
        current_line += 1
    
    # Parse all the nodes from the animation
    parsed_nodes_dict = {}
    for line_idx, line in enumerate(ascii_anim):
        ascii_anim_node = []
        first_word      = line[0].lower()
        if (first_word == 'node'):
            # Find the end of the ascii node
            node_endline    = find_line('endnode', ascii_anim, line_idx)
            ascii_anim_node = ascii_anim[line_idx:node_endline]
            # Pass the ascii node to the parser
            parsed_node = parse_animation_node(ascii_anim_node)
            # if an empty node is returned, this node contains no keys and is therefore omitted
            if (parsed_node):
                # Fill in the additional info for this action
                parsed_node['anim_name']      = animation_dict['anim_name']
                parsed_node['anim_length']    = animation_dict['anim_length'] 
                parsed_node['anim_transtime'] = animation_dict['anim_transtime']
                parsed_node['anim_root']      = animation_dict['anim_root']
                # Append the parsed node to action list for this node 
                if (parsed_node['object_name'] in parsed_nodes_dict):
                    print('WARNING: Object ' + parsed_node['object_name'] + ' already exists for ' + parsed_node['anim_name'])
                else:
                    parsed_nodes_dict[parsed_node['object_name']] = parsed_node
    
    animation_dict['parsed_nodes'] = parsed_nodes_dict
    
    return animation_dict


def create_anims_scene(animation_dict):
    '''
    Creates a scene wnamend like the animation,
    copies all objects (shallow copy) and adds
    actions for the animation
    '''
    anim_scene = None
    parsed_animation_nodes = animation_dict['parsed_nodes']
    
    # Check if there is already a scene with this animation name
    scene_name_list = bpy.data.scenes.keys()
    if (animation_dict['anim_name'] not in scene_name_list):
        # Create the scene
        anim_scene = bpy.data.scenes.new(animation_dict['anim_name'])
    
    else:
        # There already exists a scene with this name.
        #print('INFO: Scene ' + animation_dict['anim_name'] + ' already exists')
        anim_scene = bpy.data.scenes[animation_dict['anim_name']]
    
    # Set fps    
    anim_scene.render.fps  = nvb_presets.render_fps
    
    # Now we create copies of the required objects in the scene
    anim_objects_parent = {}
    anim_objects        = {}
    for req_object_name in parsed_animation_nodes.keys():
        if req_object_name in glob_import_scene.objects:
            req_object = glob_import_scene.objects[req_object_name]
            
            object_copy        = req_object.copy()
            object_copy.parent = None
            object_copy.name   = req_object.name + '.' + animation_dict['anim_name'] 
            if req_object.parent:
                object_copy_parent_name = req_object.parent.name + '.' + animation_dict['anim_name'] 
            else:
                object_copy_parent_name = 'null'
            
            # Additional data
            if (req_object.type == 'EMPTY'):
                # We have just copied the MDL Base, set some additional data
                if (req_object.auroraprops.dummytype == 'MDLBASE'):
                    object_copy.auroraprops.in_animscene = True
                    object_copy.auroraprops.animname     = animation_dict['anim_name']
                    object_copy.auroraprops.tmpanimname  = animation_dict['anim_name']
                    object_copy.auroraprops.transtime    = animation_dict['anim_transtime']
            else:
                # Create a copy of the mesh
                if (req_object.data):
                    req_mesh  = req_object.data
                    mesh_copy = req_mesh.copy()
                    mesh_copy.name = req_mesh.name + '.' + animation_dict['anim_name']  
                    object_copy.data = mesh_copy
                    
                    # Create a copy of the material
                    if (req_object.active_material):
                        req_object_mat = req_object.active_material
                        mat_copy = req_object_mat.copy()
                        mat_copy.name = req_object_mat.name + '.' + animation_dict['anim_name']  
                        object_copy.active_material = mat_copy
                    
                    # Create a copy of the particle system
                    if (req_object.particle_systems.active):
                        #partsys_copy = req_object.particle_systems.active.copy()
                        #partsys_copy.name = animation_dict['anim_name'] + '.' + req_object.name
                        #anim_object.particle_systems.active = partsys_copy
                        
                        # Create a copy of the particle system settings
                        # We do not need to check for existence (never none)
                        req_partsys_settings = req_object.particle_systems.active.settings
                        partsys_settings_copy = req_partsys_settings.copy()
                        partsys_settings_copy.name = req_partsys_settings.name + '.' + animation_dict['anim_name'] 
                        object_copy.particle_systems.active.settings = partsys_settings_copy
                         
            # Link Object to scene
            anim_scene.objects.link(object_copy)
            # Save the copies for parenting
            anim_objects_parent[req_object_name] = object_copy_parent_name 
            anim_objects[req_object_name]        = object_copy
        else:
            pass
    
    # Set the parents
    for req_object_name, object_copy in anim_objects.items():
        parent_name = anim_objects_parent[req_object_name]
        
        if (parent_name.lower() != 'null'):
            if parent_name in anim_scene.objects:
                object_copy.parent = anim_scene.objects[parent_name]
            else:
                print('WARNING: Object ' + object_copy.name + ' has no parent ' +  parent_name)            
    
    anim_scene.update()
    
    # Create animations and link them to the scenes
    for object_name, parsed_node in parsed_animation_nodes.items():
        if not parsed_node['empty']:    
            if object_name in anim_objects.keys():    
                anim_object = anim_objects[object_name]
                
                # Add action to the object itself
                object_action = animnode2objectaction(parsed_node)
                if object_action:
                    anim_object.animation_data_create()
                    anim_object.animation_data.action = object_action
                
                # Add action to the object's material
                if anim_object.active_material:    
                    anim_mat = anim_object.active_material
                    
                    mat_action = animnode2mataction(parsed_node, anim_mat.name)
                    if mat_action:
                        anim_mat.animation_data_create()
                        anim_mat.animation_data.action = mat_action
                
                # Add action to the objects's particle system
                if anim_object.particle_systems.active:    
                    anim_partsys = anim_object.particle_systems.active.settings
                    
                    partsys_action = animnode2partsysaction(parsed_node, anim_partsys.name)
                    if partsys_action:
                        anim_partsys.animation_data_create()
                        anim_partsys.animation_data.action = partsys_action
            else:
                print('WARNING: Error assigning action. Object ' + object_name + ' not found' )
    
    # Set Scene Start/End
    anim_scene.frame_start   = 0
    anim_scene.frame_end     = nvb_utils.nwtime2frame(animation_dict['anim_length'], nvb_presets.render_fps)
    anim_scene.frame_current = 0


def parse_ascii_mdl(ascii_mdl):
    # The created object may not have the same name, as in the model
    # (in case an object with this name already exists)
    # So we keep a dictionary of (object name, object) pairs
    global glob_modelname
    global glob_supermodel
    global glob_classification
    global glob_animationscale
    
    #print('INFO: loading model')
    
    # Get general infos and settings
    for line in ascii_mdl:
        first_word = line[0].lower()
        if (first_word == 'newmodel'):
            glob_modelname = line[1]
        elif (first_word == 'setsupermodel'):
            if (len(line) >= 3):
                glob_supermodel = line[2]
            else:
                glob_supermodel = 'NULL'
        elif (first_word == 'classification'):
            glob_classification = line[1].lower()
        elif (first_word == 'setanimationscale'):
            glob_animationscale = float(line[1])
        
        # Abort loop if a 'beginmodelgeom' is found
        if (line[0] == 'beginmodelgeom'):
            break
    
    # Create geometry    
    if ('GEOMETRY' in glob_import_items):
        ascii_mdl_section = []
        current_line      = 0
        geometry_endline  = 0
        
        while (current_line < len(ascii_mdl)):
            if (ascii_mdl[current_line][0] == 'beginmodelgeom'):
                # Found the beginning of a model geometry. 
                # Now we have to find the end point and pass
                # it to the model handler
                geometry_endline = find_line('endmodelgeom', ascii_mdl, current_line)
                #print('INFO: ... processing geometry ' + ascii_mdl[current_line][1])
                ascii_mdl_section = ascii_mdl[current_line:geometry_endline]
                
                parse_geometry(ascii_mdl_section)
                
                # There should be only one 'modelgeom' block
                break 
            else:
                current_line += 1
    
    # Create the animations
    if ('ANIMATIONS' in glob_import_items):
        ascii_mdl_section = []        
        current_line      = 0 
        animation_endline = 0    
        
        # Create animations as scene:
        #   - Each animation node will be an action
        #   - Each animation gets his own scene.            
        
        while (current_line < len(ascii_mdl)):       
            animation_dict    = {}
            ascii_mdl_section = []  
            if (ascii_mdl[current_line][0] == 'newanim'):       
                # Found the beginning of an animation. 
                # Now we have to find the end point and pass
                # the anim to the animation parser
                #print('INFO: ... processing animation ' + ascii_mdl[current_line][1] + ' ' + ascii_mdl[current_line][2])
                animation_endline = find_line('doneanim', ascii_mdl, current_line)
                
                ascii_mdl_section = ascii_mdl[current_line:animation_endline]
                animation_dict    = parse_animation_scene(ascii_mdl_section)
                
                create_anims_scene(animation_dict)
                 
                current_line = animation_endline
            else:
                current_line += 1 
    
    #print('INFO: done loading model')        


def parse_ascii_walkmesh(ascii_walkmesh, walkmesh_dummy_type):
    '''
    Loads dwk or pwk from external file
    '''
    #print('INFO: loading walkmesh')
    node_list   = []
    
    # Get all the nodes from the ascii_model
    current_line    = 0
    ascii_geom_node = []
    line            = []
    for current_line in range(0, len(ascii_walkmesh)):
        ascii_geom_node  = []
        line             = ascii_walkmesh[current_line]
        if (line[0] == 'node'):
            # Find the end of the ascii node
            node_endline = find_line('endnode', ascii_walkmesh, current_line)
            ascii_geom_node   = ascii_walkmesh[current_line:node_endline]
            # Pass the ascii node to the parser
            parsed_node = parse_geom_node(ascii_geom_node)
            # Add the parsed node to the node_list
            node_list.append(parsed_node)
            # jump to the ending of the model
            current_line = node_endline
        
        else:   
            current_line += 1
    
    # Build the base node
    # For walkmeshes there is no such node present,
    # but we want to create one nonetheless
    dummy_name_ext = ''
    if (walkmesh_dummy_type == 'PWKBASE'):
        base_dummy = bpy.data.objects.new(glob_modelname+'_PWK', None)
        base_dummy.auroraprops.dummytype = walkmesh_dummy_type     
    elif (walkmesh_dummy_type == 'DWKBASE'):
        base_dummy = bpy.data.objects.new(glob_modelname+'_DWK', None)
        base_dummy.auroraprops.dummytype = walkmesh_dummy_type
    else:
        return
    
    # Link object to scene
    glob_import_scene.objects.link(base_dummy)      
    
    # Build nodes
    parent_list = {}
    object_dict = {}
    for parsed_node in node_list:
        # First get the node type
        if (parsed_node['type'] == 'dummy'):    
            # Create the object (no mesh needed for a dummy)
            node_object = bpy.data.objects.new(parsed_node['name'], None)
            # Set properties
            node_object.rotation_euler = nvb_utils.nwangle2euler(parsed_node['orientation'])
            node_object.location       = parsed_node['position'] 
            
            node_object.auroraprops.dummytype = 'NONE'
            node_object.auroraprops.wirecolor = parsed_node['wirecolor']
            
            # Link object to scene
            glob_import_scene.objects.link(node_object)       
            object_dict[parsed_node['name']] = [node_object, parsed_node['parent']]  
            
        elif (parsed_node['type'] == 'trimesh'):
            # Create the mesh
            node_mesh = trimeshnode2mesh(parsed_node)               
            # Create the object
            node_object = bpy.data.objects.new(parsed_node['name'], node_mesh)
            
            # Set properties
            node_object.scale          = (parsed_node['scale'], parsed_node['scale'], parsed_node['scale'])
            node_object.rotation_euler = nvb_utils.nwangle2euler(parsed_node['orientation'])
            node_object.location       = parsed_node['position']
            
            # Add shading groups
            add_shading_groups(node_object, parsed_node)
            
            # Aurora properties
            node_object.auroraprops.meshtype         = 'TRIMESH'
            node_object.auroraprops.wirecolor        = parsed_node['wirecolor']
            node_object.auroraprops.tilefade         = parsed_node['tilefade']
            #node_object.auroraprops.scale            = parsed_node['scale']
            node_object.auroraprops.render           = (parsed_node['render'] == 1)
            node_object.auroraprops.shadow           = (parsed_node['shadow'] == 1)
            node_object.auroraprops.beaming          = (parsed_node['beaming'] == 1)
            node_object.auroraprops.inheritcolor     = (parsed_node['inheritcolor'] == 1)            
            node_object.auroraprops.rotatetexture    = (parsed_node['rotatetexture'] == 1)
            node_object.auroraprops.transparencyhint = parsed_node['transparencyhint']
            node_object.auroraprops.selfillumcolor   = parsed_node['selfillumcolor']
            node_object.auroraprops.shininess        = parsed_node['shininess']
            
            # Link object to scene
            glob_import_scene.objects.link(node_object)       
            object_dict[parsed_node['name']] = [node_object, parsed_node['parent']]  
        
        elif (parsed_node['type'] == 'aabb'): # Walkmesh
            # Create the walkmesh
            node_mesh = woknode2mesh(parsed_node)
            # Create the object
            node_object = bpy.data.objects.new(parsed_node['name'], node_mesh)
            
            # Set properties
            node_object.rotation_euler = nvb_utils.nwangle2euler(parsed_node['orientation'])
            node_object.location       = parsed_node['position']
            
            # Aurora properties
            node_object.auroraprops.meshtype         = 'AABB'
            node_object.auroraprops.wirecolor        = parsed_node['wirecolor']
            node_object.auroraprops.tilefade         = parsed_node['tilefade']
            node_object.auroraprops.render           = (parsed_node['render'] == 1)
            node_object.auroraprops.shadow           = (parsed_node['shadow'] == 1)
            node_object.auroraprops.transparencyhint = parsed_node['transparencyhint']
            
            # Link object to scene
            glob_import_scene.objects.link(node_object)       
            object_dict[parsed_node['name']] = [node_object, parsed_node['parent']]           
    
    # Set parents
    for node_name, node_info in object_dict.items():
        node_object = node_info[0]
        parent_name = node_info[1]
        if (parent_name.lower() != 'null'):
            if (parent_name.lower() == base_dummy.name.lower()):
                node_object.parent = base_dummy
            else:
                print('WARNING: Node ' + node_object.name + ' is parented to unknown node ' + parent_name)
        else:
            print('WARNING: Node ' + node_object.name + ' has parent NULL')
    
    #print('INFO: done loading walkmesh')
    

def load_mdl():
    
    # Read the ascii model from file
    ascii_mdl = read_ascii_mdl(glob_mdl_filepath)
    
    # Create the objects in the mdl file 
    parse_ascii_mdl(ascii_mdl)
    
    # We now should know the calssification of the objects
    # We can now add the dwk and pwk (wok/aabb is already in the mdl)
    mdl_classification  = get_mdl_classification()
    if (glob_import_walkmesh) and (mdl_classification != 'TILE'):
        walkmesh_filepath   = ''
        walkmesh_dummy_type = 'NONE'
        
        if (mdl_classification == 'DOOR'):
            walkmesh_dummy_type = 'DWKBASE'
            walkmesh_filepath = os.fsencode(os.path.join(glob_mdl_filedir, glob_mdl_filename + '.dwk'))
        #elif (mdl_classification == 'TILE'): # We load it directly from the mdl
            #walkmesh_dummy_type = 'WOKBASE'
            #walkmesh_filepath = os.fsencode(os.path.join(glob_mdl_filedir, glob_mdl_filename + '.wok'))
        elif (mdl_classification == 'CHARACTER'):
            # Could be placeable, but doesn't have to be
            walkmesh_dummy_type = 'PWKBASE'
            walkmesh_filepath   = os.fsencode(os.path.join(glob_mdl_filedir, glob_mdl_filename + '.pwk'))
        
        if (walkmesh_filepath != ''):
            ascii_walkmesh = read_ascii_mdl(walkmesh_filepath)
            if (len(ascii_walkmesh) > 0):
                parse_ascii_walkmesh(ascii_walkmesh, walkmesh_dummy_type)
        else:
            print('WARNING: No walkmesh file found')


###########################################################
## Called by blender
###########################################################      


def load(operator,
         context,
         filepath = '',
         import_items = {'GEOMETRY', 'ANIMATIONS'},
         import_walkmesh = True,
         import_shading_groups = False,
         use_image_search = False,
         one_texture_per_image = True,
         import_lights = True,
         import_fading_obj = True,
         ):    
    '''
    Called by the user interface or another script.
    '''
    
    global glob_mdl_filepath
    global glob_mdl_filename
    global glob_mdl_filedir
    global glob_import_items
    global glob_glob_mdl_filename
    global glob_import_walkmesh
    global glob_import_shading_groups
    global glob_use_image_search
    global glob_import_scene
    global glob_one_tex_per_image
    global glob_import_lights
    global glob_import_fading_obj
    
    glob_mdl_filepath          = os.fsencode(filepath)
    glob_mdl_filename          = os.path.splitext(os.path.basename(filepath))[0]
    glob_mdl_filedir           = os.path.dirname(filepath)
    glob_import_items          = import_items
    glob_import_walkmesh       = import_walkmesh
    glob_import_shading_groups = import_shading_groups
    glob_use_image_search      = use_image_search
    glob_one_tex_per_image     = one_texture_per_image
    glob_import_lights         = import_lights
    glob_import_fading_obj     = import_fading_obj
    
    glob_import_scene         = bpy.context.scene
    
    load_mdl()
    
    return {'FINISHED'}
