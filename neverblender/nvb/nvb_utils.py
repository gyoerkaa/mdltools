"""TODO: DOC."""

import mathutils
import bpy
import os
import collections
import math

from . import nvb_def


class NodeNameResolver(collections.OrderedDict):
    """Solves naming conflicts."""

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
    """Return true, if an object belongs in the mdl file."""
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
    """Return true, if an object is the rootdummy."""
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
        nodetype = ''
        nodename = ''
        for i, line in enumerate(txtLines):
            try:
                label = line[0].lower()
            except IndexError:
                continue
            if not l_isNumber(label):
                if label == 'node':
                    nodetype = line[1].lower()
                    nodename = getAuroraString(line[2])
                elif label == 'endnode':
                    break
                elif (label[0] != '#'):
                    numKeys = findEnd(txtLines[i+1:])
                    if numKeys > 1:
                        # Set of unknown keys
                        keylist.append([label, txtLines[i+1:i+numKeys+1]])
                    elif numKeys == 1:
                        # Single unknown key
                        keylist.append([label, [txtLines[i+1]]])
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
                # Unknown keys
                txt.write('  ' + label + ' ' + str(len(keys)) + '\n')
                for k in keys:
                    # reformat frame
                    frame = int(float(k[0]))
                    s = '    {: >4d} '.format(frame) + ' '.join(k[1:]) + '\n'
                    txt.write(s)
            else:
                # Single unknown value
                txt.write('  ' + ' '.join(label) + '\n')
        txt.write('endnode\n')


def adjustRawAnimBounds(txtBlock, scaleFactor):
    """TODO: DOC."""
    animData = readRawAnimData(txtBlock)
    for nodeName, nodeType, keyList in animData:
        for label, keys in keyList:
            for k in keys:
                frame = int(k[0]) * scaleFactor
                k[0] = str(frame)
    txtBlock.clear()
    writeRawAnimData(txtBlock, animData)


def generateWalkmeshParent(rootDummy):
    """Create the name for the walkmesh rootdummy (append '_pwk')."""
    suffix = ''
    if rootDummy.nvb.classification is nvb_def.Classification.DOOR:
        suffix = 'dwk'
    elif rootDummy.nvb.classification is nvb_def.Classification.TILE:
        suffix = 'wok'
    else:
        suffix = 'pwk'
    return rootDummy.name + '_' + suffix


def generateWalkmeshName(obj, rootDummy):
    """Create the name for the object in the walkmesh."""
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
    """Return the rootdummy of this object."""
    while obj:
        if isRootDummy(obj):
            return obj
        obj = obj.parent
    return None


def findRootDummy(obj=None):
    """Return any rootdummy in any scene."""
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
    """Generate a list of ths objects children."""
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
    lastAnimEnd = nvb_def.anim_globstart
    for anim in obj.nvb.animList:
        if anim.frameEnd > lastAnimEnd:
            lastAnimEnd = anim.frameEnd
    newAnim = obj.nvb.animList.add()
    newAnim.root = obj.name
    start = int(math.ceil((lastAnimEnd + nvb_def.anim_offset) / 10.0)) * 10
    newAnim.frameStart = start
    newAnim.frameEnd = start
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
    return round(frame/fps, 7)


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
