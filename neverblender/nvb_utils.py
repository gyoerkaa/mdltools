import math
import mathutils
import bpy
from . import nvb_presets
 

def get_is_shadinggr(vertex_group):
    '''
    Determines wether vertex_group ist a shading group or not
    '''
    return (nvb_presets.shading_group_name in vertex_group.name)
 

def getRotationAurora(object):    
    auroraRot    = [0.0, 0.0, 0.0, 0.0]
    oldRotMode = object.rotation_mode
    
    object.rotation_mode = 'AXIS_ANGLE'
    auroraRot[0] = object.rotation_axis_angle[1]
    auroraRot[1] = object.rotation_axis_angle[2]
    auroraRot[2] = object.rotation_axis_angle[3]
    auroraRot[3] = object.rotation_axis_angle[0]
    object.rotation_mode = oldRotMode
    
    return auroraRot

    
def setRotationAurora(object, auroraRot):    
    
    # Save old rotation mode so we are able restore it afterwars
    oldRotMode = object.rotation_mode 
    # Change to axis-angle mode, else the change will not show
    # in 3D view    
    object.rotation_mode = 'AXIS_ANGLE'
    object.rotation_axis_angle = [auroraRot[3], \
                                  auroraRot[0], \
                                  auroraRot[1], \
                                  auroraRot[2]]
    # This will convert axis-angle to euler xyz
    #object.rotation_mode = 'XYZ'
    # Restore the old mode now
    #object.rotation_mode = oldRotMode

    
def nwtime2frame(time, fps):
    '''
    For animations: Convert key time to frame number
    '''
    return round(fps*time)


def frame2nwtime(frame, fps):
    return round(frame / fps, 7)
    
    
    
def euler2nwangle(eulerangle):

    nwangle = (0.0, 0.0, 0.0, 0.0)
    
    # Euler to quaternion
    tmp = eulerangle[0]/2.0
    cx = math.cos(tmp)
    sx = math.sin(tmp)
    
    tmp = eulerangle[1]/2.0
    cy = math.cos(tmp)
    sy = math.sin(tmp)
    
    tmp = eulerangle[2]/2.0
    cz  = math.cos(tmp)
    sz  = math.sin(tmp)
    
    qw = cx*cy*cz - sx*sy*sz
    qx = sx*cy*cz - cx*sy*sz
    qy = cx*sy*cz + sx*cy*sz
    qz = cx*cy*sz + sx*sy*cz
    
    # Quaternion to axis/angle
    phi2 = math.acos(qw)
    if (phi2 != 0.0):
        tmp = 1/math.sin(phi2)
        nwangle = (tmp * qx, tmp * qy, tmp * qz, 2.0 * phi2)
    
    return nwangle
    
   
def nwangle2euler(nwangle):  
    eulerRot = [0.0,0.0,0.0]

    try:
        # Axis-angle to quaternion        
        phi2 = 0.5 * nwangle[3]
    
        tmp = math.sin(phi2)
        qx = nwangle[0]*tmp
        qy = nwangle[1]*tmp
        qz = nwangle[2]*tmp
        qw = math.cos(phi2)
    
        # Quaternion to euler
        tmp = qx * qx - qz * qz
        r =(qw*qw + tmp - qy*qy)
    
        phi_z = math.atan2(2.0 * (qx*qy + qw*qz), r)
        phi_y = math.asin( 2.0 * (qw*qy - qx*qz))
        phi_x = math.atan2(2.0 * (qw*qx + qy*qz), r-  2.0 * tmp)
        
        eulerRot = [phi_x, phi_y, phi_z]
    except:
        pass

    return eulerRot


def get_mdlbase(scene):
    if scene is None:
        return None
        
    for object in scene.objects:
        if (object.type == 'EMPTY'):
            if (object.auroraprops.dummytype == 'MDLBASE'):
                return object
    
    return None

    
def nvb_minimap_render_setup(mdlbase, render_scene, lamp_color = (1.0,1.0,1.0)):
    # Create the lamp if not already present in scene
    if 'MinimapLamp' in render_scene.objects:
        MinimapLampObject = render_scene.objects['MinimapLamp']
    else:
        # Check if present in db
        if 'MinimapLamp' in bpy.data.objects:
            MinimapLampObject = bpy.data.objects['MinimapLamp']
        else:
            MinimapLamp       = bpy.data.lamps.new('MinimapLamp.lamp', 'POINT')
            MinimapLampObject = bpy.data.objects.new('MinimapLamp', MinimapLamp)
        bpy.context.scene.objects.link(MinimapLampObject)
        
    # Adjust lamp properties
    MinimapLampObject.data.use_specular = False
    MinimapLampObject.data.color        = lamp_color
    MinimapLampObject.data.falloff_type = 'CONSTANT'
    MinimapLampObject.data.distance     = (mdlbase.auroraprops.minimapzoffset+20.0)*2.0
    MinimapLampObject.location.z        = mdlbase.auroraprops.minimapzoffset+20.0
     
    # Create the cam if not already present in scene
    if 'MinimapCam' in render_scene.objects:
        MinimapCamObject = render_scene.objects['MinimapCam']
    else:
        # Check if present in db
        if 'MinimapCam' in bpy.data.objects:
            MinimapCamObject = bpy.data.objects['MinimapCam']
        else:
            MinimapCam       = bpy.data.cameras.new('MinimapCam.cam')
            MinimapCamObject = bpy.data.objects.new('MinimapCam', MinimapCam)
        bpy.context.scene.objects.link(MinimapCamObject)
    # Adjust cam properties
    MinimapCamObject.data.type        = 'ORTHO'
    MinimapCamObject.data.ortho_scale = 10.0
    MinimapCamObject.location.z       = mdlbase.auroraprops.minimapzoffset+20.0
                
    bpy.context.scene.camera = MinimapCamObject
                
    # Adjust render settings
    render_scene.render.use_antialiasing           = True
    render_scene.render.pixel_filter_type          = 'BOX'
    render_scene.render.antialiasing_samples       = '16'
    render_scene.render.use_shadows                = False
    render_scene.render.use_envmaps                = False 
    render_scene.render.resolution_x               = mdlbase.auroraprops.minimapsize
    render_scene.render.resolution_y               = mdlbase.auroraprops.minimapsize
    render_scene.render.resolution_percentage      = 100
    render_scene.render.image_settings.color_mode  = 'RGB'
    render_scene.render.image_settings.file_format = 'TARGA_RAW'
    
    