"""TODO: DOC."""

import math
import mathutils
import bpy
import os
import collections

from . import nvb_def


class NodeNameResolver(collections.OrderedDict):
    """TODO: DOC."""

    def insertObj(self, nodeName, nodeParentName, nodeIdx, objName):
        """TODO: DOC."""
        if nodeName in self:
            self[nodeName].append((nodeParentName, nodeIdx, objName))
        else:
            self[nodeName] = [(nodeParentName, nodeIdx, objName)]

    def findObj(self, nodeName, nodeParentName='', nodeIdx=-1):
        """Find the name of the created object.

        If was only one node with that name the name of the imported object
        will be returned. However, if there were multiple nodes with the same
        names, we will return the best match:
            - Same parents (use '?' as parameter if the parent is unknown)
            - If the parent is unknown the closest node with the lowest ID will
              be returned.
        """
        objName = ''
        if nodeName in self:
            if len(self[nodeName]) > 1:
                # Multiple objects with the same name.
                # This is bad, but that's why we're doing all this.
                # 1. check for same parents
                if (nodeParentName != '?') and (nodeParentName in self):
                    matches = [m for m in self[nodeParentName] if
                               nodeParentName == m[0]]
                    if matches:
                        objName = matches[0][2]  # Arbitrary decision
                # 2. Use the nearest node with lowest position
                if (nodeIdx >= 0) and not objName:
                    mp = -1
                    m = None
                    for potentialMatch in self[nodeName]:
                        if (potentialMatch[1] < nodeIdx) and \
                           (potentialMatch[1] > mp):
                            mp = potentialMatch[1]
                            m = potentialMatch[2]
                    objName = m
            else:
                # Only a single object with the name (ideal case)
                objName = self[nodeName][0][2]

        return objName


def isNumber(s):
    """Check if the string s is a number."""
    try:
        float(s)
    except ValueError:
        return False
    else:
        return True


def getAuroraString(s):
    """Convert 'null' to empty string."""
    if (not s or s.lower() == nvb_def.null):
        return ''
    return s


def findMaterial(diffuse=(1.0, 1.0, 1.0),
                 specular=(1.0, 1.0, 1.0),
                 imageName='',
                 alpha=1.0):
    """Find a material with similar values.

    Compares the diffuse, specular and image values of the material
    to the parameters.
    """
    def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
        return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

    def isclose_3f(a, b, rel_tol=0.1):
        return (isclose(a[0], b[0], rel_tol) and
                isclose(a[1], b[1], rel_tol) and
                isclose(a[2], b[2], rel_tol))

    for mat in bpy.data.materials:
        eq = False
        if not imageName:
            # No texture
            eq = not mat.active_texture
            eq = eq and (mat.alpha_factor == alpha)
        else:
            # Has to have a texture
            if mat.active_texture:
                if mat.active_texture.type == 'IMAGE':
                    if mat.active_texture.image.name:
                        eq = (mat.active_texture.image.name == imageName)
                active_texslot = mat.texture_slots[mat.active_texture_index]
                eq = eq and (active_texslot.alpha_factor == alpha)

        eq = eq and isclose_3f(mat.diffuse_color, diffuse)
        eq = eq and isclose_3f(mat.specular_color, specular)
        if eq:
            return mat

    return None


def belongsToWalkmesh(obj, classification):
    """Check if this object belongs to a walkmesh."""
    if not obj:
        return False
    if obj.type == 'EMPTY':
        return nvb_def.Dummytype.isWalkmesh(obj.nvb.dummytype)
    elif obj.type == 'MESH':
        if classification == nvb_def.Classification.TILE:
            return ((obj.nvb.meshtype == nvb_def.Walkmeshtype.WALKMESH) and
                    (obj.nvb.walkmeshtype == nvb_def.Walkmeshtype.TILE))
        elif classification == nvb_def.Classification.DOOR:
            return ((obj.nvb.meshtype == nvb_def.Walkmeshtype.WALKMESH) and
                    ((obj.nvb.walkmeshtype == nvb_def.Walkmeshtype.DWKOPEN1) or
                     (obj.nvb.walkmeshtype == nvb_def.Walkmeshtype.DWKOPEN2) or
                     (obj.nvb.walkmeshtype == nvb_def.Walkmeshtype.DWKCLOSED)))
        else:
            return ((obj.nvb.meshtype == nvb_def.Meshtype.WALKMESH) and
                    (obj.nvb.walkmeshtype == nvb_def.Walkmeshtype.PWK))
    return False


def belongsToMdl(obj, classification):
    """TODO: Doc."""
    if not obj:
        return False
    return ((obj.nvb.meshtype != nvb_def.Meshtype.WALKMESH) or
            (obj.nvb.walkmeshtype == nvb_def.Walkmeshtype.AABB) or
            (not nvb_def.Dummytype.isWalkmesh(obj.nvb.dummytype)))


def isRootDummy(obj):
    """TODO: DOC."""
    if not obj:
        return False
    return (obj.parent is None) and \
           (obj.nvb.emptytype == nvb_def.Emptytype.DUMMY)


def findObjRootDummy(obj):
    """TODO: DOC."""
    while obj:
        if isRootDummy(obj):
            return obj
        obj = obj.parent
    return None


def findRootDummy(obj=None):
    """TODO: DOC."""
    # 1. Check the object and its parents
    match = findObjRootDummy(obj)
    if match:
        return match
    # 2. Nothing was found, try checking the objects in the current scene
    if bpy.context.scene:
        matches = [m for m in bpy.context.scene.objects if isRootDummy(m)]
        if matches:
            return matches[0]
    # 3. Still nothing, try checking all objects
    matches = [m for m in bpy.data.objects if isRootDummy(m)]
    if matches:
        return matches[0]

    return None


def createAnimListItem(obj):
    """TODO: Doc."""
    newAnim = obj.nvb.animList.add()
    newAnim.root = obj.name
    lastAnimEnd = nvb_def.anim_globstart
    for anim in obj.nvb.animList:
        if anim.frameEnd > lastAnimEnd:
            lastAnimEnd = anim.frameEnd
    newAnim.frameStart = lastAnimEnd + nvb_def.anim_offset
    newAnim.frameEnd = newAnim.frameStart
    return newAnim


def getNodeType(obj):
    """Get the node type (dummy, trimesh, skin, ...) of the blender object."""
    objType = obj.type
    if objType == 'EMPTY':
        return obj.nvb.emptytype
    elif objType == 'MESH':
        if (obj.nvb.meshtype == nvb_def.Meshtype.WALKMESH and
                obj.nvb.walkmeshtype == nvb_def.Walkmeshtype.TILE):
            return nvb_def.Nodetype.AABB
        else:
            return obj.nvb.meshtype
    elif objType == 'LAMP':
        return nvb_def.Nodetype.LIGHT

    return nvb_def.Nodetype.DUMMY


def chunker(seq, size):
    """TODO: DOC."""
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def getImageFilename(image):
    """Return the image name without the file extension."""
    # Try getting the image name from the image source path
    filename = os.path.splitext(os.path.basename(image.filepath))[0]
    if (filename == ''):
        # If that doesn't work, get it from the image name
        filename = os.path.splitext(os.path.basename(image.name))[0]

    return filename


def setObjectRotationAurora(obj, nwangle):
    """TODO: DOC."""
    rotMode = obj.rotation_mode
    if rotMode == "QUATERNION":
        q = mathutils.Quaternion((nwangle[0], nwangle[1], nwangle[2]),
                                 nwangle[3])
        obj.rotation_quaternion = q
    elif rotMode == "AXIS_ANGLE":
        obj.rotation_axis_angle = [nwangle[3],
                                   nwangle[0],
                                   nwangle[1],
                                   nwangle[2]]
    else:  # Has to be euler
        q = mathutils.Quaternion((nwangle[0], nwangle[1], nwangle[2]),
                                 nwangle[3])
        eul = q.to_euler(rotMode)
        obj.rotation_euler = eul


def getAuroraRotFromObject(obj):
    """Get Rotation as axis angle in aurora format/order.

    Get the rotation from an object as Axis Angle in the format used by NWN
    NWN uses     [X, Y, Z, Angle]
    Blender uses [Angle, X, Y, Z]
    Depending on rotation_mode we have to get the rotation from different
    attributes
    """
    rotMode = obj.rotation_mode

    if rotMode == "QUATERNION":
        q = obj.rotation_quaternion
        return [q.axis[0], q.axis[1], q.axis[0], q.angle]
    elif rotMode == "AXIS_ANGLE":
        aa = obj.rotation_axis_angle
        return [aa[1], aa[2], aa[3], aa[0]]
    else:  # Has to be Euler
        eul = obj.rotation_euler
        q = eul.to_quaternion()
        return [q.axis[0], q.axis[1], q.axis[2], q.angle]

    return [0.0, 0.0, 0.0, 0.0]


def getAuroraRotFromMatrix(matrix):
    """Get Rotation as axis angle in aurora format/order.

    Get the rotation from a 4x4 matrix as Axis Angle in the format used by NWN
    NWN uses     [X, Y, Z, Angle]
    Blender uses [Angle, X, Y, Z]
    """
    q = matrix.to_quaternion()
    return [q.axis[0], q.axis[1], q.axis[2], q.angle]


def getAuroraScale(obj):
    """If scale is uniform (x=y=z) return the value; Else return 1."""
    scale = obj.scale
    if (scale[0] == scale[1] == scale[2]):
        return scale[0]

    return 1.0


def nwtime2frame(time, fps=nvb_def.anim_fps):
    """Convert key time to frame number."""
    return round(fps*time)


def frame2nwtime(frame, fps=nvb_def.anim_fps):
    """TODO: DOC."""
    return round(frame / fps, 7)


def euler2nwangle(eul):
    """TODO: DOC."""
    q = eul.to_quaternion()
    return [q.axis[0], q.axis[1], q.axis[2], q.angle]


def nwangle2euler(nwangle):
    """TODO: DOC."""
    q = mathutils.Quaternion((nwangle[0], nwangle[1], nwangle[2]), nwangle[3])
    return q.to_euler()


def setMaterialAuroraAlpha(mat, alpha):
    """Set the alpha value of material or texture.

    This will set
        1. texture_slot.alpha_factor when there is a texture
        2. material.alpha there is no texture, but a material
        3. Do nothing, when there is no material
    """
    mat.use_transparency = True
    tex = mat.active_texture
    if tex:
        mat.alpha = 0.0
        tslotIdx = mat.active_texture_index
        tslot = mat.texture_slots[tslotIdx]
        tslot.use_map_alpha = True
        tslot.alpha_factor = alpha
    else:
        mat.alpha = alpha


def setObjectAuroraAlpha(obj, alpha):
    """Set the alpha value of material or texture.

    This will set
        1. texture_slot.alpha_factor when there is a texture
        2. material.alpha there is no texture, but a material
        3. Do nothing, when there is no material
    """
    mat = obj.active_material
    if mat:
        setMaterialAuroraAlpha(mat, alpha)


def getAuroraAlpha(obj):
    """Get the alpha value of material or texture.

    This will return
        1. texture_slot.alpha_factor when there is a texture
        2. material.alpha when there is no texture
        3. 1.0 when there is no material
    """
    mat = obj.active_material
    if mat and mat.use_transparency:
        tex = mat.active_texture
        if tex:
            tslotIdx = mat.active_texture_index
            tslot = mat.texture_slots[tslotIdx]
            return tslot.alpha_factor
        else:
            return mat.alpha
    else:
        return 1.0


def setupMinimapRender(mdlroot,
                       scene,
                       lamp_color=(1.0, 1.0, 1.0),
                       alpha_mode='SKY'):
    """TODO: DOC."""
    # Create the lamp if not already present in scene
    lampName = 'MinimapLamp'
    camName = 'MinimapCamera'

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
            minimapLamp = bpy.data.objects.new(lampName, lampData)
        scene.objects.link(minimapLamp)
    # Adjust lamp properties
    minimapLamp.data.use_specular = False
    minimapLamp.data.color = lamp_color
    minimapLamp.data.falloff_type = 'CONSTANT'
    minimapLamp.data.distance = (mdlroot.nvb.minimapzoffset+20.0)*2.0
    minimapLamp.location.z = mdlroot.nvb.minimapzoffset+20.0

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
    minimapCam.data.type = 'ORTHO'
    minimapCam.data.ortho_scale = 10.0
    minimapCam.location.z = mdlroot.nvb.minimapzoffset+20.0

    scene.camera = minimapCam
    # Adjust render settings
    scene.render.alpha_mode = alpha_mode
    scene.render.use_antialiasing = True
    scene.render.pixel_filter_type = 'BOX'
    scene.render.antialiasing_samples = '16'
    scene.render.use_shadows = False
    scene.render.use_envmaps = False
    scene.render.resolution_x = mdlroot.nvb.minimapsize
    scene.render.resolution_y = mdlroot.nvb.minimapsize
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.file_format = 'TARGA_RAW'


def addUVToList(uv, uvList):
    """Helper function to keep UVs unique."""
    if uv in uvList:
        return uvList.index(uv)
    else:
        uvList.append(uv)
        return (len(uvList)-1)


def createHookModifiers(obj):
    """TODO: DOC."""
    for vg in obj.vertex_groups:
        if vg.name in bpy.data.objects:
            mod = obj.modifiers.new(vg.name + '.skin', 'HOOK')
            mod.object = bpy.data.objects[vg.name]
            mod.vertex_group = vg


def eulerFilter(currEul, prevEul):
    """TODO: DOC."""
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
