﻿import math
import mathutils
import bpy
import os

from . import nvb_def


def isNull(s):
    return s.lower() == nvb_def.null


def getName(s):
    '''
    To be able to switch to case sensitive and back
    Still not certain mdl node names are case sensitive
    '''
    #return s.lower()
    return s


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


def getShagrId(shagrName):
    return  int(shagrName[-4:])


def getShagrName(shagrId):
    return  nvb_def.shagrPrefix + "{0:0>4}".format(shagrId)


def isShagr(vgroup):
    '''
    Determines wether vertex_group ist a shading group or not
    '''
    return (nvb_def.shagrPrefix in vgroup.name)


def setObjectRotationAurora(obj, nwangle):
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


def setMaterialAuroraAlpha(mat, alpha):
    #if alpha <= 1.0:
    mat.use_transparency = True
    tex = mat.active_texture
    if tex:
        mat.alpha = 0.0
        tslotIdx = mat.active_texture_index
        tslot    = mat.texture_slots[tslotIdx]
        tslot.use_map_alpha = True
        tslot.alpha_factor  = alpha
    else:
        mat.alpha = alpha


def setObjectAuroraAlpha(obj, alpha):
    '''
    This will set
        1. texture_slot.alpha_factor when there is a texture
        2. material.alpha there is no texture, but a material
        3. Do nothing, when there is no material
    '''
    mat = obj.active_material
    if mat:
        setMaterialAuroraAlpha(mat, alpha)


def getAuroraAlpha(obj):
    '''
    This will return
        1. texture_slot.alpha_factor when there is a texture
        2. material.alpha when there is no texture
        3. 1.0 when there is no material
    '''
    mat = obj.active_material
    if mat and mat.use_transparency:
        tex = mat.active_texture
        if tex:
            tslotIdx = mat.active_texture_index
            tslot    = mat.texture_slots[tslotIdx]
            return tslot.alpha_factor
        else:
            return mat.alpha
    else:
        return 1.0


def setupMinimapRender(mdlbase, scene, lamp_color = (1.0, 1.0, 1.0)):
    # Create the lamp if not already present in scene
    lampName = 'MinimapLamp'
    camName  = 'MinimapCamera'

    if lampName in scene.objects:
        minimapLamp = scene.objects[lampName]
    else:
        # Check if present in db
        if lampName in bpy.data.objects:
            minimapLamp = bpy.data.objects[lampName]
        else:
            if lampName in bpy.data.lamps:
                lampData = bpy.data.lamps[lampName]
            else:
                lampData = bpy.data.lamps.new(lampName, 'POINT')
            minimapLamp = bpy.data.objects.new(lampName , lampData)
        scene.objects.link(minimapLamp)
    # Adjust lamp properties
    minimapLamp.data.use_specular = False
    minimapLamp.data.color        = lamp_color
    minimapLamp.data.falloff_type = 'CONSTANT'
    minimapLamp.data.distance     = (mdlbase.nvb.minimapzoffset+20.0)*2.0
    minimapLamp.location.z        = mdlbase.nvb.minimapzoffset+20.0

    # Create the cam if not already present in scene
    if camName in scene.objects:
        minimapCam = scene.objects[camName]
    else:
        # Check if present in db
        if camName in bpy.data.objects:
            minimapCam = bpy.data.objects[camName]
        else:
            if camName in bpy.data.cameras:
                camData = bpy.data.cameras[camName]
            else:
                camData = bpy.data.cameras.new(camName)
            minimapCam = bpy.data.objects.new(camName, camData)
        scene.objects.link(minimapCam)
    # Adjust cam properties
    minimapCam.data.type        = 'ORTHO'
    minimapCam.data.ortho_scale = 10.0
    minimapCam.location.z       = mdlbase.nvb.minimapzoffset+20.0

    scene.camera = minimapCam
    # Adjust render settings
    scene.render.use_antialiasing           = True
    scene.render.pixel_filter_type          = 'BOX'
    scene.render.antialiasing_samples       = '16'
    scene.render.use_shadows                = False
    scene.render.use_envmaps                = False
    scene.render.resolution_x               = mdlbase.nvb.minimapsize
    scene.render.resolution_y               = mdlbase.nvb.minimapsize
    scene.render.resolution_percentage      = 100
    scene.render.image_settings.color_mode  = 'RGB'
    scene.render.image_settings.file_format = 'TARGA_RAW'


def copyAnimSceneCheck(theOriginal, newSuffix, oldSuffix = ''):
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
        valid = valid and copyAnimSceneCheck(child, newSuffix, oldSuffix)

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


def createHookModifiers(obj):
    skingrName = ''
    for vg in obj.vertex_groups:
        if vg.name in bpy.data.objects:
            mod = obj.modifiers.new(vg.name + '.skin', 'HOOK')
            mod.object = bpy.data.objects[vg.name]
            mod.vertex_group = vg


def eulerFilter(currEul, prevEul):

    def distance(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])

    def flip(e):
        f = e.copy()
        f[0] += math.pi
        f[1] *= -1
        f[1] += math.pi
        f[2] += math.pi
        return f

    def flipDiff(a, b):
        while abs(a - b) > math.pi:
            if a < b:
                b -= 2 * math.pi
            else:
                b += 2 * math.pi
        return b

    if not prevEul:
        # Nothing to compare to, return original value
        return currEul

    eul = currEul.copy()
    eul[0] = flipDiff(prevEul[0], eul[0])
    eul[1] = flipDiff(prevEul[1], eul[1])
    eul[2] = flipDiff(prevEul[2], eul[2])

    # Flip current euler
    flipEul = flip(eul)
    flipEul[0] = flipDiff(prevEul[0], flipEul[0])
    flipEul[1] = flipDiff(prevEul[1], flipEul[1])
    flipEul[2] = flipDiff(prevEul[2], flipEul[2])

    currDist = distance(prevEul, eul)
    flipDist = distance(prevEul, flipEul)

    if flipDist < currDist:
        return flipEul
    else:
        return eul
