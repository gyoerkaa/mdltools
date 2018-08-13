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


def is_mdl_base(obj):
    """Return true if object obj is a rootdummy."""
    if not obj:
        return False
    return (obj.parent is None) and \
           (obj.type == 'EMPTY') and \
           (obj.nvb.emptytype == nvb_def.Emptytype.DUMMY)


def get_obj_mdl_base(obj):
    """Return the objects aurora root."""
    while obj:
        if is_mdl_base(obj):
            return obj
        obj = obj.parent
    return None


def get_mdl_base(obj=None, scene=None):
    """Return any aurora root."""
    # 1. Check the object and its parents
    match = get_obj_mdl_base(obj)
    if match:
        return match
    # 2. Nothing was found, try checking the objects in the scene
    if scene:
        matches = [m for m in scene.objects if is_mdl_base(m)]
        if matches:
            return matches[0]
    # 3. Still nothing, try checking all objects
    matches = [m for m in bpy.data.objects if is_mdl_base(m)]
    if matches:
        return matches[0]
    return None


def get_fcurve(action, data_path, index=0, group_name=None):
    """Get the fcurve with specified properties or create one."""
    fcu = action.fcurves.find(data_path, index)
    if not fcu:  # Create new Curve
        fcu = action.fcurves.new(data_path=data_path, index=index)
        if group_name:  # Add curve to group
            if group_name in action.groups:
                group = action.groups[group_name]
            else:
                group = action.groups.new(group_name)
            fcu.group = group
    return fcu


def get_action(target, action_name):
    """Get the active action or create one."""
    # Get animation data, create if needed
    anim_data = target.animation_data
    if not anim_data:
        anim_data = target.animation_data_create()
    # Get action, create if needed
    action = anim_data.action
    if not action:
        action = bpy.data.actions.new(name=action_name)
        # action.use_fake_user = True
        anim_data.action = action
    return action


def get_aabb(mdl_base):
    """Find an AABB mesh for this mdl base."""
    def is_aabb(obj):
        """Return true if object obj is an aabb mesh."""
        return obj.type == 'MESH' and obj.nvb.meshtype == nvb_def.Meshtype.AABB
    ol = [c for c in mdl_base.children if is_aabb(c)]
    if len(ol) > 0:
        return ol[0]
    return None


def is_wkm_base(obj):
    """Return true if object obj is a root object for walkmeshes."""
    if not obj:
        return False
    return (obj.parent and
            obj.type == 'EMPTY' and
            (obj.nvb.emptytype == nvb_def.Emptytype.PWK or
             obj.nvb.emptytype == nvb_def.Emptytype.DWK))


def get_wkm_base(mdl_base, wkmtype):
    """Find a walkmesh root."""
    emptytype = nvb_def.Emptytype.PWK
    if wkmtype == nvb_def.Walkmeshtype.DWK:
        emptytype = nvb_def.Emptytype.DWK
    ol = [c for c in mdl_base.children
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


def get_last_keyframe(root_obj):
    """Get the last keyed frame of this object and its children."""
    def get_max_frame(target):
        frame = nvb_def.anim_globstart
        if target:
            if target.animation_data and target.animation_data.action:
                for fcu in target.animation_data.action.fcurves:
                    frame = max(max([p.co[0] for p in fcu.keyframe_points],
                                    default=0), frame)
            return frame
    obj_list = [root_obj]
    get_children_recursive(root_obj, obj_list)
    frame_list = [nvb_def.anim_globstart]
    for obj in obj_list:
        frame_list.append(get_max_frame(obj))
        mat = obj.active_material
        if mat:
            frame_list.append(get_max_frame(mat))
        part_sys = obj.particle_systems.active
        if part_sys:
            frame_list.append(get_max_frame(part_sys.settings))
    return max(frame_list)


def get_frame_interval(obj):
    """Get the first and last keyed frame of this object and its children."""
    obj_list = [obj]
    get_children_recursive(obj, obj_list)
    max_frame = nvb_def.anim_globstart
    min_frame = nvb_def.anim_globstart + 1000
    for o in obj_list:
        if o.animation_data and o.animation_data.action:
            action = o.animation_data.action
            for fcu in action.fcurves:
                max_frame = max(max([p.co[0] for p in fcu.keyframe_points],
                                    default=0), max_frame)
                min_frame = min(min([p.co[0] for p in fcu.keyframe_points],
                                    default=0), min_frame)
    return (min_frame, max_frame)


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


def str2bool(s):
    """Custom bool conversion. Only numbers >= 1 are True."""
    try:
        b = (int(s) >= 1)
    except ValueError:
        b = False
    return b


def str2int(s):
    """Custom int conversion. Convert to float first, then int."""
    return int(float(s))


def str2float(s):
    """Custom float conversion. Treat every error as 0.0."""
    try:
        f = float(s)
    except ValueError:
        f = 0.0
    return f


def str2identifier(s):
    """Convert to lower case. Convert 'null' to empty string."""
    if (not s or s.lower() == nvb_def.null):
        return ''
    return s.lower()


def str2texture(s):
    """Convert to lower case. Convert 'null' to nvb_def.null."""
    if (not s or s.lower() == nvb_def.null):
        return nvb_def.null
    return s.lower()


def toggle_anim_focus(scene, mdl_base):
    """Set the Start and end frames of the timeline."""
    animList = mdl_base.nvb.animList
    animIdx = mdl_base.nvb.animListIdx

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


def checkAnimBounds(mdl_base):
    """
    Check for animations of this mdl base.

    Returns true, if are non-overlapping and only use by one object.
    """
    if len(mdl_base.nvb.animList) < 2:
        return True
    # TODO: use an interval tree
    animBounds = [(a.frameStart, a.frameEnd, idx) for idx, a in
                  enumerate(mdl_base.nvb.animList)]
    for a1 in animBounds:
        for a2 in animBounds:
            if (a1[0] <= a2[1]) and (a2[0] <= a1[1]) and (a1[2] != a2[2]):
                return False
    return True


def amt_event_list_item_create(amt, event_name):
    event_list = amt.nvb.amt_event_list
    # Add new event
    event = event_list.add()
    amt.nvb.amt_event_list_idx = len(amt.nvb.amt_event_list)-1
    event.name = event_name
    # Add empty fcurves (to make sure they are conveniently grouped)
    anim_data = amt.animation_data
    if not anim_data:
        anim_data = amt.animation_data.create()
    action = anim_data.action
    if not action:
        action = bpy.data.actions.new(amt.name)
    data_path = 'nvb.amt_event_list[' + str(amt.nvb.amt_event_list_idx) + \
                '].fire'
    fcu = get_fcurve(action, data_path, 0, 'Events')
    fcu.group = action.groups['Events']  # force group


def amt_event_list_init(amt):
    event_list = amt.nvb.amt_event_list
    if len(event_list) > 0:
        return
    amt.nvb.amt_event_list_idx = 0
    # Create new events:
    for ev_name in nvb_def.animation_event_names:
        ev = event_list.add()
        ev.name = ev_name


def create_anim_list_item(mdl_base, check_keyframes=False):
    """Append a new animation at the and of the animation list."""
    last_frame = max([nvb_def.anim_globstart] +
                     [a.frameEnd for a in mdl_base.nvb.animList])
    if check_keyframes:
        last_frame = max(last_frame, get_last_keyframe(mdl_base))
    anim = mdl_base.nvb.animList.add()
    anim.name = mdl_base.name
    start = int(math.ceil((last_frame + nvb_def.anim_offset) / 10.0)) * 10
    anim.frameStart = start
    anim.frameEnd = start
    return anim


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


def get_connected_vertices(vertex_list):
    """TODO: Doc."""
    def check_dist(vec_a, vec_b):
        return math.sqrt(sum([math.pow(a-b, 2)
                              for a, b in zip(vec_a, vec_b)])) < 1.0
    pass


def get_convex_hull_2d(vertex_list):
    """Project the points to 2D plane (omit Z) and calculate convex hull."""
    def uv_split(u, v, points):
        # return points on left side of UV
        return [p for p in points if (p - u).cross(v - u) < 0]

    def uv_search(u, v, points):
        if not points:
            return []
        # find furthest point W, and split search to WV, UW
        w = min(points, key=lambda p: (p - u).cross(v - u))
        p1, p2 = uv_split(w, v, points), uv_split(u, w, points)
        return uv_search(w, v, p1) + [w] + uv_search(u, w, p2)

    def convex_hull(points):
        # find two hull points, U, V, and split to left and right search
        u = min(points, key=lambda p: p[0])
        v = max(points, key=lambda p: p[0])
        left, right = uv_split(u, v, points), uv_split(v, u, points)
        # find convex hull on each side
        return [v] + uv_search(u, v, left) + [u] + uv_search(v, u, right)

    vertex_list_2d = [mathutils.Vector(v.co[:2]) for v in vertex_list]
    return convex_hull(vertex_list_2d)


def minimum_area_rectangle(convex_hull):
    """TODO: Doc."""
    def mostfar(j, n, s, c, mx, my, hull):  # advance j to extreme point
        xn, yn = hull[j][0], hull[j][1]
        rx, ry = xn*c - yn*s, xn*s + yn*c
        best = mx*rx + my*ry
        while True:
            x, y = rx, ry
            xn, yn = hull[(j+1) % n][0], hull[(j+1) % n][1]
            rx, ry = xn*c - yn*s, xn*s + yn*c
            if mx*rx + my*ry >= best:
                j = (j+1) % n
                best = mx*rx + my*ry
            else:
                return (x, y, j)

    n = len(convex_hull)
    iL = iR = iP = 1  # indexes left, right, opposite
    pi = 4*math.atan(1)
    min_rect = (1e33, 0, 0, 0, 0, 0, 0)
    for i in range(n-1):
        dx = convex_hull[i+1][0] - convex_hull[i][0]
        dy = convex_hull[i+1][1] - convex_hull[i][1]
        theta = pi-math.atan2(dy, dx)
        s, c = math.sin(theta), math.cos(theta)
        yC = convex_hull[i][0]*s + convex_hull[i][1]*c

        xP, yP, iP = mostfar(iP, n, s, c, 0, 1)
        if i == 0:
            iR = iP
        xR, yR, iR = mostfar(iR, n, s, c,  1, 0)
        xL, yL, iL = mostfar(iL, n, s, c, -1, 0)
        area = (yP-yC)*(xR-xL)
        if area < min_rect[0]:
            min_rect = (area, xR-xL, yP-yC, i, iL, iP, iR)
    return min_rect
