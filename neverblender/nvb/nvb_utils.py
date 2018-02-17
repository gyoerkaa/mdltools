"""TODO: DOC."""

import mathutils
import bpy
import os
import math

from . import nvb_def


class NodeResolver():
    """Solves naming conflicts.

    There may be several nodes with the same name in the mdl.
    However, Blender object names are unique, we need to fix this.
    """

    def __init__(self):
        """TODO: DOC."""
        self.nodes = dict()

    def create_obj(self, node_name, node_idx, obj_name):
        """TODO: DOC."""
        if node_name not in self.nodes:
            self.nodes[node_name] = []
        self.nodes[node_name].append((obj_name, node_idx))

    def get_obj(self, node_name, node_idx):
        """TODO: DOC."""
        if node_name not in self.nodes:
            return None
        matches = self.nodes[node_name]
        if len(matches) == 1:
            # Only one object was created using this node name
            return bpy.data.objects[matches[0][0]]
        elif len(matches) > 1:
            # Return the node with the same index
            filtered = list(filter(lambda x: x[1] == node_idx, matches))
            filtered.sort(key=lambda x: x[1])
            if filtered:
                return bpy.data.objects[filtered[0][0]]
        return None

    def get_obj_parent(self, node_name, node_idx):
        """TODO: DOC."""
        if node_name not in self.nodes:
            return None
        matches = self.nodes[node_name]
        if len(matches) == 1:
            # Only one object was created using this node name
            return bpy.data.objects[matches[0][0]]
        elif len(matches) > 1:
            # Get all nodes with lower indices
            # (= located before this node in the MDL)
            filtered = list(filter(lambda x: x[1] < node_idx, matches))
            # Of these nodes, return the one with highest index
            if filtered:
                filtered.sort(key=lambda x: x[1])
                return bpy.data.objects[filtered[-1][0]]
        return None


def get_texture_slots(mat):
    """Get the diffuse, normal, and specular textures of this material."""
    def is_diff(ts):
        return (ts.use_map_color_diffuse and
                not ts.use_map_normal and
                not ts.use_map_color_spec)

    def is_norm(ts):
        return (not ts.use_map_color_diffuse and
                ts.use_map_normal)

    def is_spec(ts):
        return (not ts.use_map_color_diffuse and
                ts.use_map_color_spec)
    used_tslots = [ts for idx, ts in enumerate(mat.texture_slots)
                   if ts and mat.use_textures[idx]]
    ts_diff = [ts for ts in used_tslots if is_diff(ts)] + [None]
    ts_norm = [ts for ts in used_tslots if is_norm(ts)] + [None]
    ts_spec = [ts for ts in used_tslots if is_spec(ts)] + [None]
    return ts_diff[0], ts_norm[0], ts_spec[0]


def find_material(tdiff_name='', tnorm_name='', tspec_name='',
                  col_diff=(-1.0, -1.0, -1.0), col_spec=(-1.0, -1.0, -1.0),
                  alpha=-1.0):
    """Find a material with similar values.

    Compares the diffuse, specular and image values of the material
    to the parameters.
    """
    def cmp_col(a, b, rel_tol=0.1):
        """Compares two colors."""
        def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
            return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
        return (isclose(a[0], b[0], rel_tol) and
                isclose(a[1], b[1], rel_tol) and
                isclose(a[2], b[2], rel_tol))

    def get_tslot_img(tslot):
        """Compares two textures (i.e their image names)"""
        if tslot:
            tex = tslot.texture
            if tex and tex.type == 'IMAGE':
                return tex.image.name
        return ''

    for mat in bpy.data.materials:
        eq = False
        # Check diffuse and specular color
        eq = col_diff and cmp_col(mat.diffuse_color, col_diff)
        eq = eq and (col_spec and cmp_col(mat.specular_color, col_spec))
        # Texture slots to check
        tslot_diff, tslot_norm, tslot_spec = get_texture_slots(mat)
        # Check diffuse texture
        if tdiff_name:
            # The texture we're looking for has to have a diffuse texture
            if tslot_diff:
                eq = eq and (tdiff_name == get_tslot_img(tslot_diff))
                eq = eq and (alpha == tslot_diff.alpha_factor)
            else:
                # This material doesn't have one
                continue
        else:
            # The texture we're looking for cannot have a diffuse texture
            if tslot_diff:
                continue
            eq = eq and (alpha == mat.alpha)
        # Check normal texture
        if tnorm_name and tslot_norm:
                eq = eq and (tnorm_name == get_tslot_img(tslot_norm))
        # Check specular texture
        if tspec_name and tslot_spec:
                eq = eq and (tspec_name == get_tslot_img(tslot_spec))
        if eq:
            return mat
    return None


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
    return s.lower()


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
    # TODO: Speed this one up, maybe with childrenRecursive(), check whether
    #       read only is ok first
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


def createRestPose(obj, frame=1):
    """TODO: DOC."""

    def getCurve(fcurves, data_path, index=0):
        """TODO: DOC."""
        fc = fcurves.find(data_path, index)
        if not fc:
            fc = fcurves.new(data_path=data_path, index=index)
        return fc

    # Get animation data, create if needed.
    animData = obj.animation_data
    if not animData:
        animData = obj.animation_data_create()
    # Get action, create if needed.
    action = animData.action
    if not action:
        action = bpy.data.actions.new(name=obj.name)
        action.use_fake_user = True
        animData.action = action
    kfOptions = {'FAST'}
    dp_names = [fcu.data_path for fcu in action.fcurves]
    if 'rotation_euler' in dp_names:
        curveX = getCurve(action.fcurves, 'rotation_euler', 0)
        curveY = getCurve(action.fcurves, 'rotation_euler', 1)
        curveZ = getCurve(action.fcurves, 'rotation_euler', 2)
        rot = obj.nvb.restrot
        curveX.keyframe_points.insert(frame, rot[0], kfOptions)
        curveY.keyframe_points.insert(frame, rot[1], kfOptions)
        curveZ.keyframe_points.insert(frame, rot[2], kfOptions)
    if 'location' in dp_names:
        curveX = getCurve(action.fcurves, 'location', 0)
        curveY = getCurve(action.fcurves, 'location', 1)
        curveZ = getCurve(action.fcurves, 'location', 2)
        loc = obj.nvb.restloc
        curveX.keyframe_points.insert(frame, loc[0], kfOptions)
        curveY.keyframe_points.insert(frame, loc[1], kfOptions)
        curveZ.keyframe_points.insert(frame, loc[2], kfOptions)


def copyAnims2Armature(armature, source,
                       destructive=False, convertangles=False):
    """TODO: DOC."""
    # Process animations of the armature itself

    # Process animations/poses of the bones
    bones = armature.data.bones
    if not bones:
        return
    # Get or create animation data for this armature
    if not armature.animation_data:
        armature.animation_data_create()
    # Get or create action for the animation data
    amt_action = armature.animation_data.action
    if not amt_action:
        amt_action = bpy.data.actions.new(name=armature.name)
        amt_action.use_fake_user = True
        armature.animation_data.action = amt_action
    for amt_bone in bones:
        amt_posebone = armature.pose.bones[amt_bone.name]
        amt_posebone.rotation_mode = 'XYZ'
        # Check wether there is an pseudo bone object with the same
        # name as the bone
        if amt_bone.name in bpy.data.objects:
            psb_bone = bpy.data.objects[amt_bone.name]
            # Gather rotation and location keyframe points
            # Their coordinates need to be adjusted for use with bones
            mat1 = psb_bone.matrix_world.inverted()
            mat2 = amt_bone.matrix_local
            if psb_bone.animation_data and psb_bone.animation_data.action:
                psb_all_fcu = psb_bone.animation_data.action.fcurves
                """
                psb_dp = 'rotation_quaternion'
                psb_dp = rotation_axis_angle'
                """
                # Rotation Euler
                psb_dp = 'rotation_euler'
                psb_fcu = [psb_all_fcu.find(psb_dp, i) for i in range(3)]
                if psb_fcu.count(None) < 3:
                    amt_dp = 'pose.bones["' + amt_bone.name + '"].' + psb_dp
                    # Get keyframes
                    keyed_frames = list(set().union(
                        *[[k.co[0] for k in psb_fcu[i].keyframe_points]
                          for i in range(3)]))
                    keyed_frames.sort()
                    psb_kfp = [[f,
                                (psb_fcu[0].evaluate(f),
                                 psb_fcu[1].evaluate(f),
                                 psb_fcu[2].evaluate(f))]
                               for f in keyed_frames]
                    # Adjust to bone coordinates
                    d = amt_posebone.rotation_euler
                    for kfp in psb_kfp:
                        a = mathutils.Euler(kfp[1], 'XYZ').to_matrix().to_4x4()
                        b = armature.convert_space(amt_posebone,
                                                   a,
                                                   'LOCAL_WITH_PARENT',
                                                   'LOCAL')
                        c = b.to_euler('XYZ', d)
                        d = c
                        kfp[1] = (c[0], c[1], c[2])
                        # ori = mathutils.Vector(kfp[1])
                        # kfp[1] = ori * mat1 * mat2
                    # Add keyframes
                    amt_fcu = [amt_action.fcurves.new(amt_dp, i)
                               for i in range(3)]
                    amt_kfp = [amt_fcu[i].keyframe_points for i in range(3)]
                    list(map(lambda x: x.add(len(psb_kfp)), amt_kfp))
                    for i in range(len(psb_kfp)):
                        eul = psb_kfp[i][1]
                        for j in range(3):
                            p = amt_kfp[j][i]
                            p.co = psb_kfp[i][0], eul[j]
                            p.interpolation = 'LINEAR'
                            p.handle_left_type = 'AUTO_CLAMPED'
                            p.handle_right_type = 'AUTO_CLAMPED'
                    list(map(lambda x: x.update(), amt_fcu))
                # Location
                psb_dp = 'location'
                psb_fcu = [psb_all_fcu.find(psb_dp, i) for i in range(3)]
                if psb_fcu.count(None) < 3:
                    amt_dp = 'pose.bones["' + amt_bone.name + '"].' + psb_dp
                    # Get keyframes
                    keyed_frames = list(set().union(
                        *[[k.co[0] for k in psb_fcu[i].keyframe_points]
                          for i in range(3)]))
                    keyed_frames.sort()
                    psb_loc = psb_bone.location
                    psb_kfp = [[f,
                                (psb_fcu[0].evaluate(f) - psb_loc[0],
                                 psb_fcu[1].evaluate(f) - psb_loc[1],
                                 psb_fcu[2].evaluate(f) - psb_loc[2])]
                               for f in keyed_frames]
                    # Adjust to bone coordinates
                    for kfp in psb_kfp:
                        ori = mathutils.Vector(kfp[1])
                        kfp[1] = ori * mat1 * mat2
                    # Add keyframes
                    amt_fcu = [amt_action.fcurves.new(amt_dp, i)
                               for i in range(3)]
                    amt_kfp = [amt_fcu[i].keyframe_points for i in range(3)]
                    list(map(lambda x: x.add(len(psb_kfp)), amt_kfp))
                    for i in range(len(psb_kfp)):
                        for j in range(3):
                            p = amt_kfp[j][i]
                            p.co = psb_kfp[i][0], psb_kfp[i][1][j]
                            p.interpolation = 'LINEAR'
                            p.handle_left_type = 'AUTO_CLAMPED'
                            p.handle_right_type = 'AUTO_CLAMPED'
                    list(map(lambda x: x.update(), amt_fcu))


def copyAnims2Mdl(armature, source,
                  destructive=False, convertangles=False, prefix=''):
    """TODO: DOC."""
    # Process animations/poses of the bones
    bones = armature.data.bones
    if not bones:
        return
    # Get animation data for this armature
    if not armature.animation_data:
        return
    # Get for the animation data
    amt_action = armature.animation_data.action
    if not amt_action:
        return
    # Check if the bones can be created at all:
    for amt_bone in bones:
        # This bone already exists as object
        if amt_bone.name in bpy.data.objects:
            # TODO: Tell the user to rename bone/Object or
            #       only transfer animations instead
            return
    for amt_bone in bones:
        # Check wether there is an pseudo bone object with the same
        # name as the bone
        # amt_posebone = armature.pose.bones[amt_bone.name]
        if amt_bone.name in bpy.data.objects:
            pass
            # psb_bone = bpy.data.objects[amt_bone.name]
            # Gather rotation and location keyframe points
            # Their coordinates need to be adjusted for use with bones
            # mat1 = psb_bone.matrix_world.decompose()[1]\
            #     .to_matrix().inverted().to_4x4()
            # mat2 = amt_bone.matrix_local.decompose()[1]\
            #     .to_matrix().to_4x4()
