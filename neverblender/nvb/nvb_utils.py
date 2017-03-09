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


def findEnd(asciiBlock):
    """Find the end of a key list.

    We don't know when a list of keys of keys will end. We'll have to
    search for the first non-numeric value
    """
    return next((i for i, v in enumerate(asciiBlock)
                 if not isNumber(v[0])), -1)


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
            eq = eq and (mat.alpha == alpha)
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
            return ((obj.nvb.meshtype == nvb_def.Meshtype.WALKMESH) and
                    (obj.nvb.walkmeshtype == nvb_def.Walkmeshtype.AABB))
        elif classification == nvb_def.Classification.DOOR:
            return ((obj.nvb.meshtype == nvb_def.Meshtype.WALKMESH) and
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
    if obj.type == 'EMPTY':
        return not nvb_def.Dummytype.isWalkmesh(obj.nvb.dummytype)
    elif obj.type == 'MESH':
        return ((obj.nvb.meshtype != nvb_def.Meshtype.WALKMESH) or
                ((obj.nvb.meshtype == nvb_def.Meshtype.WALKMESH) and
                 (obj.nvb.walkmeshtype == nvb_def.Walkmeshtype.AABB)))
    elif obj.type == 'LAMP':
        return True
    return False


def isRootDummy(obj):
    """TODO: DOC."""
    if not obj:
        return False
    return (obj.parent is None) and \
           (obj.type == 'EMPTY') and \
           (obj.nvb.emptytype == nvb_def.Emptytype.DUMMY)


def readRawAnimData(txtBlock):
    """TODO: DOC."""
    animData = []
    dlm = 'node '
    nodeList = [dlm+block for block in txtBlock.split(dlm) if block]
    l_isNumber = isNumber
    for node in nodeList:
        txtLines = [l.strip().split() for l in node.splitlines()]
        keylist = []
        nodename = ''
        nodetype = ''
        for i, line in enumerate(txtLines):
            try:
                label = line[0].lower()
            except IndexError:
                continue
            if not l_isNumber(label):
                if label == 'node':
                    nodetype = line[1].lower()
                    nodename = getAuroraString(line[2])
                elif (label[0] != '#'):
                    numKeys = findEnd(txtLines[i+1:])
                    if numKeys > 0:
                        # Set of unknown keys
                        keylist.append([label, txtLines[i+1:i+numKeys]])
                    else:
                        # Single unknown value
                        keylist.append([' '.join(line), []])
        if nodename:
            animData.append([nodename, nodetype, keylist])
    return animData


def writeRawAnimData(txt, animData, frameStart=0):
    """TODO: Doc."""
    for nodename, nodetype, keylist in animData:
        txt.write('node ' + nodetype + ' ' + nodename + '\n')
        for label, keys in keylist:
            if keylist:
                txt.write('  ' + label + ' ' + len(keys) + '\n')
                for k in keys:
                    nwtime = float(k[0])
                    values = [float(v) for v in k[1:]]
                    frame = frameStart + nwtime2frame(nwtime)
                    formatStr = '    {: >4d}' + \
                                ' '.join(['{: > 8.5f}']*len(values) + '\n')
                    s = formatStr.format(frame, *values)
                    txt.write(s)
            else:
                # Single unknown value
                txt.write('  ' + ' '.join(label) + '\n')
        txt.write('endnode\n')


def adjustRawAnimBounds(txtBlock, newStart, newEnd):
    """TODO: DOC."""
    originalData = readRawAnimData(txtBlock)
    # adjustedData = []
    for nodeName, nodeType, keyList in originalData:
        for label, keys in keyList:
            for k in keys:
                pass


def generateWalkmeshParent(rootDummy):
    """TODO: DOC."""
    suffix = ''
    if rootDummy.nvb.classification is nvb_def.Classification.DOOR:
        suffix = 'dwk'
    elif rootDummy.nvb.classification is nvb_def.Classification.TILE:
        suffix = 'wok'
    else:
        suffix = 'pwk'
    return rootDummy.name + '_' + suffix


def generateWalkmeshName(obj, rootDummy):
    """TODO: DOC."""
    classifcation = rootDummy.nvb.classification
    suffix = ''
    currentName = obj.name
    if obj.type == 'EMTPY':
        suffix = nvb_def.Dummytype.generateSuffix(obj, classifcation)
    elif obj.type == 'MESH':
        suffix = nvb_def.Walkmeshtype.generateSuffix(obj, classifcation)
    else:
        return currentName
    # No suffix or this node already has a valid suffix/name
    if (not suffix) or (suffix and currentName.endswith(suffix)):
        return currentName
    # Generate a valid name ourselves
    return rootDummy.name + '_' + suffix


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


def toggleAnimFocus(scene, rootDummy):
    """Set the Start and end frames of the timeline."""
    animList = rootDummy.nvb.animList
    animIdx = rootDummy.nvb.animListIdx

    anim = animList[animIdx]
    if (scene.frame_start == anim.frameStart) and \
       (scene.frame_end == anim.frameEnd):
        # Set timeline to all current animation
        scene.frame_start = 1
        lastFrame = 1
        for anim in animList:
            if lastFrame < anim.frameEnd:
                lastFrame = anim.frameEnd
        scene.frame_end = lastFrame
    else:
        # Set timeline to the current animation
        scene.frame_start = anim.frameStart
        scene.frame_end = anim.frameEnd
    scene.frame_current = scene.frame_start


def getAllChildren(obj, objList):
    """TODO: DOC."""
    if obj:
        objList.append(obj)
        for c in obj.children:
            getAllChildren(c, objList)


def checkAnimBounds(rootDummy):
    """
    Check for animations of this rootDummy.

    Returns true, if are non-overlapping and only use by one object.
    """
    if len(rootDummy.nvb.animList) < 2:
        return True
    # TODO: Interval tree
    animBounds = [(a.frameStart, a.frameEnd, idx) for idx, a in
                  enumerate(rootDummy.nvb.animList)]
    for a1 in animBounds:
        for a2 in animBounds:
            if (a1[0] <= a2[1]) and (a2[0] <= a1[1]) and (a1[2] != a2[2]):
                return False
    return True


def createAnimListItem(obj):
    """Append a new animation at the and of the animation list."""
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
        if obj.nvb.meshtype == nvb_def.Meshtype.WALKMESH:
            if obj.nvb.walkmeshtype == nvb_def.Walkmeshtype.AABB:
                return nvb_def.Walkmeshtype.AABB
            else:
                return nvb_def.Meshtype.TRIMESH
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


def setupMinimapRender(rootDummy,
                       scene,
                       lamp_color=(1.0, 1.0, 1.0),
                       alpha_mode='TRANSPARENT'):
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
    minimapLamp.data.distance = (rootDummy.nvb.minimapzoffset+20.0)*2.0
    minimapLamp.location.z = rootDummy.nvb.minimapzoffset+20.0

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
    minimapCam.location.z = rootDummy.nvb.minimapzoffset+20.0

    scene.camera = minimapCam
    # Adjust render settings
    scene.render.alpha_mode = alpha_mode
    scene.render.use_antialiasing = True
    scene.render.pixel_filter_type = 'BOX'
    scene.render.antialiasing_samples = '16'
    scene.render.use_shadows = False
    scene.render.use_envmaps = False
    scene.render.resolution_x = rootDummy.nvb.minimapsize
    scene.render.resolution_y = rootDummy.nvb.minimapsize
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.file_format = 'TARGA_RAW'


def addUVToList(uv, uvList, compress=True):
    """Helper function to avoid exporting mutiples of uv coordinates."""
    if compress and (uv in uvList):
        return uvList.index(uv)
    else:
        uvList.append(uv)
        return (len(uvList)-1)


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
