"""TODO: DOC."""

import mathutils
import bpy
import os
import math
import re
import collections

import bpy_extras.image_utils

from . import nvb_def


class NodeResolver():
    """Solves naming conflicts.

    There may be several nodes with the same name in the mdl.
    However, Blender object names are unique.
    """

    def __init__(self):
        """TODO: DOC."""
        self.nodes = collections.OrderedDict()

    def insert_obj(self, node_name, node_idx, obj_name):
        """TODO: DOC."""
        if node_name not in self.nodes:
            self.nodes[node_name] = []
        self.nodes[node_name].append((obj_name, node_idx))

    def get_obj(self, node_name, node_idx):
        """TODO: DOC."""
        if node_name not in self.nodes:
            return None
        matches = self.nodes[node_name]
        if len(matches) == 1:  # Only one object was created using this name
            return bpy.data.objects[matches[0][0]]
        elif len(matches) > 1:
            # Return the node with the same index (position in the mdl)
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


def is_aurora_root(obj):
    """Return true if object obj is a rootdummy."""
    if not obj:
        return False
    return (obj.parent is None) and \
           (obj.type == 'EMPTY') and \
           (obj.nvb.emptytype == nvb_def.Emptytype.DUMMY)


def get_obj_aurora_root(obj):
    """Return the objects aurora root."""
    while obj:
        if is_aurora_root(obj):
            return obj
        obj = obj.parent
    return None


def get_aurora_root(obj=None, scene=None):
    """Return any aurora root."""
    # 1. Check the object and its parents
    match = get_obj_aurora_root(obj)
    if match:
        return match
    # 2. Nothing was found, try checking the objects in the scene
    if scene:
        matches = [m for m in scene.objects if is_aurora_root(m)]
        if matches:
            return matches[0]
    # 3. Still nothing, try checking all objects
    matches = [m for m in bpy.data.objects if is_aurora_root(m)]
    if matches:
        return matches[0]
    return None


def get_fcurve(action, data_path, index=0):
    """Get the fcurve with specified properties or create one."""
    fcu = action.fcurves.find(data_path, index)
    if not fcu:
        fcu = action.fcurves.new(data_path=data_path, index=index)
    return fcu


def get_aabb(aurora_root):
    """Find an AABB mesh for this mdl base."""
    def is_aabb(obj):
        """Return true if object obj is an aabb mesh."""
        return obj.type == 'MESH' and obj.nvb.meshtype == nvb_def.Meshtype.AABB
    ol = [c for c in aurora_root.children if is_aabb(c)]
    if len(ol) > 0:
        return ol[0]
    return None


def is_wkm_root(obj):
    """Return true if object obj is a root object for walkmeshes."""
    if not obj:
        return False
    return (obj.parent and
            obj.type == 'EMPTY' and
            (obj.nvb.emptytype == nvb_def.Emptytype.PWK or
             obj.nvb.emptytype == nvb_def.Emptytype.DWK))


def find_wkm_root(mdlRoot, wkmtype):
    """Find a walkmesh root."""
    emptytype = nvb_def.Emptytype.PWK
    if wkmtype == nvb_def.Walkmeshtype.DWK:
        emptytype = nvb_def.Emptytype.DWK
    ol = [c for c in mdlRoot.children
          if c.type == 'EMPTY' and c.nvb.emptytype == emptytype]
    if len(ol) > 0:
        return ol[0]
    return None


def create_wok_materials(mesh):
    """Adds walkmesh materials to the object."""
    # Add walkmesh materials
    for matname, matcolor in nvb_def.wok_materials:
        # Walkmesh materials are always shared between walkmeshes
        if matname in bpy.data.materials.keys():
            mat = bpy.data.materials[matname]
        else:
            mat = bpy.data.materials.new(matname)
            mat.diffuse_color = matcolor
            mat.diffuse_intensity = 1.0
            mat.specular_color = (0.0, 0.0, 0.0)
            mat.specular_intensity = 0.0
        mesh.materials.append(mat)


def get_children_recursive(obj, obj_list):
    """Generate a list of ths objects children."""
    for c in obj.children:
        obj_list.append(c)
        get_children_recursive(c, obj_list)


def get_last_frame(obj):
    """Get the last keyed frame of this object and its children."""
    obj_list = [obj]
    get_children_recursive(obj, obj_list)
    frame = nvb_def.anim_globstart
    for o in obj_list:
        if o.animation_data and o.animation_data.action:
            action = o.animation_data.action
            for fcu in action.fcurves:
                frame = max(max([p.co[0] for p in fcu.keyframe_points],
                                default=0), frame)
    return frame


def strip_trailing_numbers(s):
    """Removes trailing numbers resulting from duplicate object names."""
    return re.fullmatch(r'(.+?)(\.\d+)?$', s).group(1)


def generate_node_name(obj, strip_trailing=False):
    """Return a name for node/objects for use in the mdl."""
    new_name = obj.name
    if strip_trailing:
        new_name = strip_trailing_numbers(obj.name)
    new_name.replace(' ', '_')
    return new_name


def isNumber(s):
    """Check if the string s is a number."""
    try:
        float(s)
    except ValueError:
        return False
    else:
        return True


def str2float(s):
    """Custom float() conversion. Treat every error as 0.0."""
    try:
        f = float(s)
    except ValueError:
        f = 0.0
    return f


def getAuroraIdentifier(s):
    """Convert to lower case. Convert 'null' to empty string."""
    if (not s or s.lower() == nvb_def.null):
        return ''
    return s.lower()


def getAuroraTexture(s):
    """Convert to lower case. Convert 'null' to nvb_def.null."""
    if (not s or s.lower() == nvb_def.null):
        return nvb_def.null
    return s.lower()


def readRawAnimData(txtBlock):
    """TODO: DOC."""
    def findEnd(self, asciiBlock):
        """Find the end of a key list.

        We don't know when a list of keys of keys will end. We'll have to
        search for the first non-numeric value
        """
        l_isNumber = isNumber
        return next((i for i, v in enumerate(asciiBlock)
                     if not l_isNumber(v[0])), -1)

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
                    nodename = getAuroraIdentifier(line[2])
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


def toggle_anim_focus(scene, rootDummy):
    """Set the Start and end frames of the timeline."""
    animList = rootDummy.nvb.animList
    animIdx = rootDummy.nvb.animListIdx

    anim = animList[animIdx]
    if (scene.frame_start == anim.frameStart) and \
       (scene.frame_end == anim.frameEnd):
        # Set timeline to include all current
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


def createAnimListItem(mdl_root):
    """Append a new animation at the and of the animation list."""
    lastAnimEnd = nvb_def.anim_globstart
    for anim in mdl_root.nvb.animList:
        if anim.frameEnd > lastAnimEnd:
            lastAnimEnd = anim.frameEnd
    newAnim = mdl_root.nvb.animList.add()
    newAnim.root = mdl_root.name
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
        return obj.nvb.meshtype
    elif objType == 'LAMP':
        return nvb_def.Nodetype.LIGHT
    return nvb_def.Nodetype.DUMMY


def setObjAuroraRot(obj, nwangle):
    """TODO: DOC."""
    rotmode = obj.rotation_mode
    if rotmode == 'QUATERNION':
        obj.rotation_quaternion = mathutils.Quaternion(nwangle[:3], nwangle[3])
    elif rotmode == 'AXIS_ANGLE':
        obj.rotation_axis_angle = [nwangle[3]] + nwangle[:3]
    else:  # Has to be euler
        q = mathutils.Quaternion(nwangle[:3], nwangle[3])
        obj.rotation_euler = q.to_euler(rotmode)


def getAuroraScale(obj):
    """If scale is uniform (x=y=z) return the value; Else return 1."""
    scale = obj.scale
    if (scale[0] == scale[1] == scale[2]):
        return scale[0]
    return 1.0


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

    if not prevEul:  # Nothing to compare to, return original value
        return currEul
    # Original euler
    eul = currEul.copy()
    eul[0] = flipDiff(prevEul[0], eul[0])
    eul[1] = flipDiff(prevEul[1], eul[1])
    eul[2] = flipDiff(prevEul[2], eul[2])
    # Flipped euler
    flipEul = flip(eul)
    flipEul[0] = flipDiff(prevEul[0], flipEul[0])
    flipEul[1] = flipDiff(prevEul[1], flipEul[1])
    flipEul[2] = flipDiff(prevEul[2], flipEul[2])
    # Return the "better" = smoother euler
    currDist = distance(prevEul, eul)
    flipDist = distance(prevEul, flipEul)
    if flipDist < currDist:
        return flipEul
    else:
        return eul


def get_textures(material):
    """Get a list of (texture_idx, texture_name, texture_alpha) tuples."""
    def get_img_name(tslot):
        """Get the texture name for this texture slot."""
        imgname = ''
        tex = tslot.texture
        if tex.type == 'IMAGE':
            img = tex.image
            if img:
                if img.filepath:
                    imgname = \
                        os.path.splitext(os.path.basename(img.filepath))[0]
                elif img.name:
                    imgname = \
                        os.path.splitext(os.path.basename(img.name))[0]
        # Last resort: Texture name
        if not imgname:
            imgname = tex.name
        return imgname

    texList = [(idx, get_img_name(tslot), tslot.alpha_factor)
               for idx, tslot in enumerate(material.texture_slots)
               if tslot and material.use_textures[idx]]
    return texList


def create_texture(texname, imgname, filepath, tex_search):
    """TODO: Doc."""
    if texname in bpy.data.textures:
        # Load the image for the texture
        tex = bpy.data.textures[texname]
    else:
        tex = bpy.data.textures.new(texname, type='IMAGE')
        if (imgname in bpy.data.images):
            img = bpy.data.images[imgname]
            tex.image = img
        else:
            texpath = os.path.dirname(filepath)
            img = bpy_extras.image_utils.load_image(
                imgname + '.tga', texpath, recursive=tex_search,
                place_holder=False, ncase_cmp=True)
            if img is None:
                img = bpy.data.images.new(imgname, 512, 512)
            img.name = imgname
            tex.image = img
    return tex
