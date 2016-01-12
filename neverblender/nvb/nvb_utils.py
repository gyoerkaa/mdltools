import mathutils
import bpy
import os

from . import nvb_def


def isNull(s):
    return s.lower() == nvb_def.null


def isNumber(s):
    try:
        float(s)
    except ValueError:
        return False
    else:
        return True


def getValidExports(rootDummy, validExports):
    validExports.append(rootDummy.name)
    for child in rootDummy.children:
        getValidExports(child, validExports)


def getAnimationRootdummy(animScene):
    if animScene:
        for obj in animScene.objects:
            if obj.type == 'EMPTY':
                if (obj.nvb.dummytype == nvb_def.Dummytype.MDLROOT) and (obj.nvb.isanimation):
                    return obj
    return None


def isRootDummy(obj, dummytype = nvb_def.Dummytype.MDLROOT):
    if not obj:
        return False
    return (obj.type == 'EMPTY') and (obj.nvb.dummytype == dummytype) and (not obj.nvb.isanimation)


def getNodeType(obj):
    '''
    Get the node type (dummy, trimesh, skin, ...) of the blender object
    '''
    objType  = obj.type
    if objType == 'EMPTY':
        if   obj.nvb.dummytype == nvb_def.Dummytype.PATCH:
            return 'patch'
        elif obj.nvb.dummytype == nvb_def.Dummytype.REFERENCE:
            return 'reference'
    elif objType == 'MESH':
        if   obj.nvb.meshtype == nvb_def.Meshtype.TRIMESH:
            return 'trimesh'
        elif obj.nvb.meshtype == nvb_def.Meshtype.DANGLYMESH:
            return 'danglymesh'
        elif obj.nvb.meshtype == nvb_def.Meshtype.SKIN:
            return 'skin'
        elif obj.nvb.meshtype == nvb_def.Meshtype.EMITTER:
            return 'emitter'
        elif obj.nvb.meshtype == nvb_def.Meshtype.AABB:
            return 'aabb'
    elif objType == 'LAMP':
        return 'light'

    return 'dummy'


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def getImageFilename(image):
    '''
    '''
    filename = os.path.splitext(os.path.basename(image.filepath))[0]
    if (filename == ''):
        return image.name

    return filename


def getIsShadingGroup(vgroup):
    '''
    Determines wether vertex_group ist a shading group or not
    '''
    return (nvb_def.shadingGroupName in vgroup.name)


def setRotationAurora(obj, nwangle):
    rotMode = obj.rotation_mode
    if   rotMode == "QUATERNION":
        q = mathutils.Quaternion((nwangle[0], nwangle[1], nwangle[2]), nwangle[3])
        obj.rotation_quaternion = q
    elif rotMode == "AXIS_ANGLE":
        obj.rotation_axis_angle = [ auroraRot[3], \
                                    auroraRot[0], \
                                    auroraRot[1], \
                                    auroraRot[2] ]
    else: # Has to be euler
        q = mathutils.Quaternion((nwangle[0], nwangle[1], nwangle[2]), nwangle[3])
        eul = q.to_euler(rotMode)
        obj.rotation_euler = eul


def getAuroraRotFromObject(obj):
    '''
    Get the rotation from an object as Axis Angle in the format used by NWN
    NWN uses     [X, Y, Z, Angle]
    Blender uses [Angle, X, Y, Z]
    Depending on rotation_mode we have to get the rotation from different
    attributes
    '''
    rotMode = obj.rotation_mode

    if   rotMode == "QUATERNION":
        q = obj.rotation_quaternion
        return [q.axis[0], q.axis[1], q.axis[0], q.angle]
    elif rotMode == "AXIS_ANGLE":
        aa = obj.rotation_axis_angle
        return [aa[1], aa[2], aa[3], aa[0]]
    else: # Has to be Euler
        eul = obj.rotation_euler
        q   = eul.to_quaternion()
        return [q.axis[0], q.axis[1], q.axis[2], q.angle]

    return [0.0, 0.0, 0.0, 0.0]


def getAuroraRotFromMatrix(matrix):
    '''
    Get the rotation from a 4x4 matrix as Axis Angle in the format used by NWN
    NWN uses     [X, Y, Z, Angle]
    Blender uses [Angle, X, Y, Z]
    '''
    q = matrix.to_quaternion()
    return [q.axis[0], q.axis[1], q.axis[2], q.angle]


def getAuroraScale(obj):
    '''
    If the scale is uniform, i.e, x=y=z, we will return
    the value. Else we'll return 1.
    '''
    scale = obj.scale
    if (scale[0] == scale[1] == scale[2]):
        return scale[0]

    return 1.0


def nwtime2frame(time, fps = nvb_def.fps):
    '''
    For animations: Convert key time to frame number
    '''
    return round(fps*time)


def frame2nwtime(frame, fps = nvb_def.fps):
    return round(frame / fps, 7)


def euler2nwangle(eul):
    q = eul.to_quaternion()
    return [q.axis[0], q.axis[1], q.axis[2], q.angle]


def nwangle2euler(nwangle):
    q = mathutils.Quaternion((nwangle[0], nwangle[1], nwangle[2]), nwangle[3])
    return q.to_euler()


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


def checkObjectNames(theOriginal, newSuffix, oldSuffix = ''):
    '''
    Checks if it possible to copy the object and it's children with the suffix
    It would be impossible if:
        - An object with the same name already exists
        - Object data with the same name already exists
    '''
    oldName = theOriginal.name
    newName = 'ERROR'
    if oldSuffix:
        if oldName.endswith(oldSuffix):
            newName = oldName[:len(oldName)-len(oldSuffix)]
            if newName.endswith('.'):
                newName = newName[:len(newName)-1]
        else:
            newName = oldName.partition('.')[0]
            if not newName:
                print('Neverblender: Unable to generate new name')
                return False
        newName = newName + '.' + newSuffix
    else:
        newName = oldName + '.' + newSuffix

    if newName in bpy.data.objects:
        print('Neverblender: Duplicate object')
        return False

    objType = theOriginal.type
    if (objType == 'LAMP'):
        if newName in bpy.data.lamps:
            print('Neverblender: Duplicate lamp')
            return False
    elif (objType == 'MESH'):
        if theOriginal.animation_data:
            action = theOriginal.animation_data.action
            for fcurve in action.fcurves:
                dataPath = fcurve.data_path
                if dataPath.endswith('alpha_factor'):
                    if newName in bpy.data.materials:
                        print('Neverblender: Duplicate Material')
                        return False

        if newName in bpy.data.actions:
            print('Neverblender: Duplicate Action')
            return False

    valid = True
    for child in theOriginal.children:
        valid = valid and checkObjectNames(child, newSuffix, oldSuffix)

    return valid


def copyAnimScene(scene, theOriginal, newSuffix, oldSuffix = '', parent = None):
    '''
    Copy object and all it's children to scene.
    For object with simple (position, rotation) or no animations we
    create a linked copy.
    For alpha animation we'll need to copy the data too.
    '''
    oldName = theOriginal.name
    newName = 'ERROR'
    if oldSuffix:
        if oldName.endswith(oldSuffix):
            newName = oldName[:len(oldName)-len(oldSuffix)]
            if newName.endswith('.'):
                newName = newName[:len(newName)-1]
        else:
            newName = oldName.partition('.')[0]
            if not newName:
                return
        newName = newName + '.' + newSuffix
    else:
        newName = oldName + '.' + newSuffix

    theCopy        = theOriginal.copy()
    theCopy.name   = newName
    theCopy.parent = parent

    # We need to copy the data for:
    # - Lamps
    # - Meshes & materials when there are alphakeys
    objType = theOriginal.type
    if (objType == 'LAMP'):
        data         = theOriginal.data.copy()
        data.name    = newName
        theCopy.data = data
    elif (objType == 'MESH'):
        if theOriginal.animation_data:
            action = theOriginal.animation_data.action
            for fcurve in action.fcurves:
                dataPath = fcurve.data_path
                if dataPath.endswith('alpha_factor'):
                    data         = theOriginal.data.copy()
                    data.name    = newName
                    theCopy.data = data
                    # Create a copy of the material
                    if (theOriginal.active_material):
                        material      = theOriginal.active_material.copy()
                        material.name = newName
                        theCopy.active_material = material
                        break
            actionCopy = action.copy()
            actionCopy.name = newName
            theCopy.animation_data.action = actionCopy

    # Link copy to the anim scene
    scene.objects.link(theCopy)

    # Convert all child objects too
    for child in theOriginal.children:
        copyAnimScene(scene, child, newSuffix, oldSuffix, theCopy)

    # Return the copied rootDummy
    return theCopy


def renameAnimScene(obj, newSuffix, oldSuffix = ''):
    '''
    Copy object and all it's children to scene.
    For object with simple (position, rotation) or no animations we
    create a linked copy.
    For alpha animation we'll need to copy the data too.
    '''
    oldName = obj.name
    newName = 'ERROR'
    if oldSuffix:
        if oldName.endswith(oldSuffix):
            newName = oldName[:len(oldName)-len(oldSuffix)]
            if newName.endswith('.'):
                newName = newName[:len(newName)-1]
        else:
            newName = oldName.partition('.')[0]
            if not newName:
                return
        newName = newName + '.' + newSuffix
    else:
        newName = oldName + '.' + newSuffix

    obj.name = newName
    if obj.data:
        obj.data.name = newName
    # We need to copy the data for:
    # - Lamps
    # - Meshes & materials when there are alphakeys
    objType = obj.type
    if (objType == 'MESH'):
        if obj.animation_data:
            action = obj.animation_data.action
            action.name = newName
            for fcurve in action.fcurves:
                dataPath = fcurve.data_path
                if dataPath.endswith('alpha_factor'):
                    # Create a copy of the material
                    if (obj.active_material):
                        material      = obj.active_material
                        material.name = newName
                        break

    # Convert all child objects too
    for child in obj.children:
        renameAnimScene(child, newSuffix, oldSuffix)

    # Return the renamed rootDummy
    return obj
