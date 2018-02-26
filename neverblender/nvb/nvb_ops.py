"""TODO: DOC."""

import math
import copy
import os

import bpy
import bpy_extras
import mathutils

from . import nvb_def
from . import nvb_utils
from . import nvb_io


class NVB_OT_helper_amt2psd(bpy.types.Operator):
    """Generate pseudobone from blender armature."""
    bl_idname = 'nvb.helper_amt_topseudo'
    bl_label = 'Generate MDL pseudo bones from Armature'

    def create_bone_geometry(amt_bone, prefix=''):
        """TODO: DOC."""
        # head_loc = amt_bone.head
        # tail_loc = amt_bone.tail
        pass

    def generateBones(self, armature):
        """TODO: doc."""
        pass

    @classmethod
    def poll(self, context):
        """Prevent execution if no armature is selected."""
        obj = context.object
        return obj and (obj.type == 'ARMATURE')

    def execute(self, context):
        """Create pseudo bones"""
        pass


class NVB_OT_helper_psd2amt(bpy.types.Operator):
    """Generate armature from skinmesh weights and mdl bones."""

    bl_idname = 'nvb.helper_amt_frompseudo'
    bl_label = 'Generate Armature from MDL pseudo bones'

    # For detecting pseudo bones
    pb_skingroups = []
    pb_ignore = ['hand', 'head', 'head_hit', 'hhit', 'impact', 'impc',
                 'ground', 'grnd', 'handconjure', 'headconjure']
    pb_prefix = '?'
    pb_suffix = '?'

    def can_connect(self, obj):
        """Determnine whether the bone belonging to this object can be
           connected to it's parent."""
        # If location is animated the bone cannot be connected
        if obj.animation_data:
            action = obj.animation_data.action
            if action:
                for fcu in action.fcurves:
                    if 'location' in fcu.data_path:
                        return False
        return True

    def setupPseudoBoneDetection(self, aur_root, strict=False):
        """TODO: doc."""
        # Get all names of skinmesh vertex groups which exist as object
        children = []
        nvb_utils.getAllChildren(aur_root, children)
        cnames = [c.name for c in children]
        for c in children:
            if c.nvb.meshtype == nvb_def.Meshtype.SKIN:
                self.pb_skingroups.extend([vg.name for vg in c.vertex_groups
                                           if vg.name in cnames])
        self.pb_prefix = os.path.commonprefix(self.pb_skingroups)
        self.pb_prefix = self.pb_prefix if self.pb_prefix else '?'
        self.pb_suffix = \
            os.path.commonprefix([n[::-1] for n in self.pb_skingroups])
        self.pb_suffix = self.pb_suffix[::-1] if self.pb_suffix else '?'

    def detectPseudoBonesRoot(self, auroraRoot, strict=False):
        """TODO: doc."""
        for c in auroraRoot.children:
            for cc in c.children:
                if self.isPseudoBone(cc, strict):
                    return c
        return None

    def isPseudoBone(self, obj, strict=False):
        """TODO: doc."""
        oname = obj.name
        if strict:
            # Object is referred to in any vertex group of a skinmesh
            if oname in self.pb_skingroups:
                return True
            # Some objects like impact nodes never are pseudo bones
            if oname in self.pb_ignore:
                return False
            # Maybe: Object carries a common suffix or prefix
            if oname.startswith(self.pb_prefix) or \
               oname.endswith(self.pb_suffix):
                return True
            # If any child is a pseudo bone this object is too
            children = []
            nvb_utils.getAllChildren(obj, children)
            cn = [c.name for c in children]
            return bool(set(cn) & set(self.pb_skingroups))
        else:
            return (oname.lower() not in self.pb_ignore) and \
                   (obj.nvb.meshtype != nvb_def.Meshtype.SKIN)
        return False

    def generateBones(self, amt, obj, strict=False,
                      pbone=None, ploc=mathutils.Vector()):
        """TODO: doc."""
        # TODO set every rotation to 0 before creating a bone
        bone = None
        bhead = obj.matrix_local.translation + ploc
        # rot = pmat.decompose()[1].inverted().to_matrix().to_4x4()
        if self.isPseudoBone(obj, strict):
            bone = amt.edit_bones.new(obj.name)
            bone.roll = 0
            # Set head
            if pbone:
                bone.parent = pbone
                # Merge head with parent tail if distance is short enough
                dist = math.sqrt(math.pow(pbone.tail.x - bhead.x, 2) +
                                 math.pow(pbone.tail.y - bhead.y, 2) +
                                 math.pow(pbone.tail.z - bhead.z, 2))
                if dist <= 0.01:
                    bhead = pbone.tail
                    if obj.nvb.helper_amt_connect and self.can_connect(obj):
                        bone.use_connect = True
            bone.head = bhead
            # Set tail
            btail = mathutils.Vector([0.0, 0.0, 0.0])
            valid_children = [c for c in obj.children
                              if self.isPseudoBone(c, strict)]
            if len(valid_children) >= 2:
                # Multiple children: Calculate average location
                locsum = mathutils.Vector([0.0, 0.0, 0.0])
                for c in valid_children:
                    locsum = locsum + bhead + c.matrix_local.translation
                btail = locsum/len(valid_children)
            elif len(valid_children) == 1:
                btail = bhead + valid_children[0].matrix_local.translation
            else:
                # No children: Generate location from object bounding box
                if obj.type == 'MESH':
                    center = bhead + \
                             (sum((mathutils.Vector(p) for p in obj.bound_box),
                              mathutils.Vector()) / 8)
                    btail = center + center - bone.head
                elif obj.type == 'EMPTY':
                    if pbone:
                        btail = pbone.tail - pbone.head + bhead
                    else:
                        btail = bhead + mathutils.Vector([0.0, 0.2, 0.0])

            bone.tail = btail
            # Align coordinate system to parent bone
            # if pbone:
            #     bone.align_roll(pbone.z_axis)
        for c in obj.children:
            self.generateBones(amt, c, strict, bone, bhead)

    @classmethod
    def poll(self, context):
        """Prevent execution if no root was found."""
        auroraRoot = nvb_utils.findObjRootDummy(context.object)
        return (auroraRoot is not None)

    def execute(self, context):
        """Create the armature"""
        aur_root = nvb_utils.findObjRootDummy(context.object)
        # Get source for armature
        if aur_root.nvb.helper_amt_source == 'SKIN':
            # Get all vertex groups with a name that exists as object
            self.setupPseudoBoneDetection(aur_root)
            pb_root = self.detectPseudoBonesRoot(aur_root)
            print(pb_root.name)
            print(self.pb_skingroups)
            if not pb_root:
                self.report({'INFO'}, 'Error: No Pseudo Bone root.')
                return {'CANCELLED'}
            strict = True
        else:
            pb_root = context.object
            strict = False
        # Create armature
        bpy.ops.object.add(type='ARMATURE',
                           enter_editmode=True,
                           location=pb_root.location)
        amt = context.scene.objects.active
        amt.name = aur_root.name + '.armature'
        bpy.ops.object.mode_set(mode='EDIT')
        # Create the bones
        for c in pb_root.children:
            self.generateBones(amt.data, c, strict)
        # Copy animations
        bpy.ops.object.mode_set(mode='POSE')
        if aur_root.nvb.helper_amt_copyani:
            nvb_utils.copyAnims2Armature(amt, pb_root)
        # Update scene and objects
        bpy.ops.object.mode_set(mode='OBJECT')
        context.scene.update()
        return {'FINISHED'}


class NVB_OT_anim_clone(bpy.types.Operator):
    """Clone animation and add it to the animation list"""

    bl_idname = 'nvb.anim_clone'
    bl_label = 'Clone animation'

    @classmethod
    def poll(cls, context):
        """Prevent execution if no rootdummy was found."""
        rootdummy = nvb_utils.findObjRootDummy(context.object)
        if rootdummy is not None:
            return (len(rootdummy.nvb.animList) > 0)
        return False

    def cloneEmitter(self, rawasciiID):
        """Clone the animations's emitter data."""
        txt = bpy.data.texts[rawasciiID].copy()
        txt.name = bpy.data.texts[rawasciiID].name + '_copy'
        txt.use_fake_user = True
        return txt.name

    def cloneFrames(self, target, an_start, an_end, clone_start):
        """Clone the animations keyframes."""
        if target.animation_data and target.animation_data.action:
            # in_options = {'FAST'}
            action = target.animation_data.action
            offset = clone_start - an_start
            for fc in action.fcurves:
                # Get the keyframe points of the selected animation
                vals = [(p.co[0] + offset, p.co[1]) for p in fc.keyframe_points
                        if an_start <= p.co[0] <= an_end]
                kfp = fc.keyframe_points
                nkfp = len(kfp)
                kfp.add(len(vals))
                for i in range(len(vals)):
                    kfp[nkfp+i].co = vals[i]
                """
                # Get the keyframe points of the selected animation
                kfp = [(p.co[0] + offset, p.co[1]) for p in fc.keyframe_points
                       if an_start <= p.co[0] <= an_end]
                for p in kfp:
                    fc.keyframe_points.insert(p[0], p[1], in_options)
                """
                # For compatibility with older blender versions
                try:
                    fc.update()
                except AttributeError:
                    pass

    def execute(self, context):
        """Clone the animation."""
        rootd = nvb_utils.findObjRootDummy(context.object)
        anim = rootd.nvb.animList[rootd.nvb.animListIdx]
        animStart = anim.frameStart
        animEnd = anim.frameEnd
        # Adds a new animation to the end of the list
        clone = nvb_utils.createAnimListItem(rootd)
        # Copy data
        clone.frameEnd = clone.frameStart + (animEnd - animStart)
        clone.ttime = anim.ttime
        clone.root = anim.root
        clone.name = anim.name + '_copy'
        # Copy events
        for e in anim.eventList:
            clonedEvent = clone.eventList.add()
            clonedEvent.frame = clone.frameStart + (e.frame - animStart)
            clonedEvent.name = e.name
        # Copy emitter data
        rawascii = anim.rawascii
        if rawascii and (rawascii in bpy.data.texts):
            clone.rawascii = self.cloneEmitter(rawascii)
        # Copy keyframes
        objList = []
        nvb_utils.getAllChildren(rootd, objList)
        for obj in objList:
            # Copy the objects animation
            self.cloneFrames(obj, animStart, animEnd, clone.frameStart)
            # Copy the object's material animation
            if obj.active_material:
                self.cloneFrames(obj.active_material,
                                 animStart, animEnd, clone.frameStart)
            # Copy the object's shape key animation
            if obj.data and obj.data.shape_keys:
                self.cloneFrames(obj.data.shape_keys,
                                 animStart, animEnd, clone.frameStart)
        return {'FINISHED'}


class NVB_OT_anim_scale(bpy.types.Operator):
    """Open a dialog to scale a single animation"""

    bl_idname = 'nvb.anim_scale'
    bl_label = 'Scale animation'

    scaleFactor = bpy.props.FloatProperty(name='scale',
                                          description='Scale the animation',
                                          min=0.1,
                                          default=1.0)

    @classmethod
    def poll(cls, context):
        """Prevent execution if no rootdummy was found."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def scaleFramesUp(self, target, animStart, animEnd, scaleFactor):
        """TODO:DOC."""
        if target.animation_data and target.animation_data.action:
            oldSize = animEnd - animStart
            newSize = scaleFactor * oldSize
            padding = newSize - oldSize
            action = target.animation_data.action
            for fcurve in action.fcurves:
                # Move keyframes back to create enough space
                for p in reversed(fcurve.keyframe_points):
                    if (p.co[0] > animEnd):
                        p.co[0] += padding
                        p.handle_left.x += padding
                        p.handle_right.x += padding
                # Now scale the animation
                for p in fcurve.keyframe_points:
                    if (animStart < p.co[0] <= animEnd):
                        oldFrame = p.co[0]
                        newFrame = (oldFrame - animStart + 1) * \
                            scaleFactor + animStart - 1
                        p.co[0] = newFrame
                        p.handle_left.x = newFrame - \
                            (oldFrame - p.handle_left.x)
                        p.handle_right.x = newFrame + \
                            (p.handle_right.x - oldFrame)
                # For compatibility with older blender versions
                try:
                    fcurve.update()
                except AttributeError:
                    pass

    def scaleFramesDown(self, target, animStart, animEnd, scaleFactor):
        """TODO:DOC."""
        if target.animation_data and target.animation_data.action:
            oldSize = animEnd - animStart
            newSize = scaleFactor * oldSize
            padding = newSize - oldSize
            action = target.animation_data.action
            for fcurve in action.fcurves:
                    # Scale the animation down first
                    for p in fcurve.keyframe_points:
                        if (animStart < p.co[0] <= animEnd):
                            oldFrame = p.co[0]
                            newFrame = (oldFrame - animStart + 1) * \
                                scaleFactor + animStart - 1
                            p.co[0] = newFrame
                            p.handle_left.x = newFrame - \
                                (oldFrame - p.handle_left.x)
                            p.handle_right.x = newFrame + \
                                (p.handle_right.x - oldFrame)
                    # Move keyframes forward to close gaps
                    for p in fcurve.keyframe_points:
                        if (p.co[0] > animEnd):
                            p.co[0] += padding
                            p.handle_left.x += padding
                            p.handle_right.x += padding
                    # For compatibility with older blender versions
                    try:
                        fcurve.update()
                    except AttributeError:
                        pass

    def scaleEmitter(self, anim, scaleFactor):
        """TODO:DOC."""
        if anim.rawascii and (anim.rawascii in bpy.data.texts):
            txt = bpy.data.texts[anim.rawascii]
            rawdata = copy.deepcopy(txt.as_string())
            animData = []
            animData = nvb_utils.readRawAnimData(rawdata)
            for nodeName, nodeType, keyList in animData:
                for label, keys in keyList:
                    for k in keys:
                        k[0] = str(int(k[0]) * scaleFactor)
            txt.clear()
            nvb_utils.writeRawAnimData(txt, animData)

    def scaleFrames(self, target, animStart, animEnd, scaleFactor):
        """TODO:DOC."""
        if target.animation_data and target.animation_data.action:
            if scaleFactor > 1.0:
                self.scaleFramesUp(target, animStart, animEnd, scaleFactor)
            elif scaleFactor < 1.0:
                self.scaleFramesDown(target, animStart, animEnd, scaleFactor)

    def execute(self, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if not nvb_utils.checkAnimBounds(rootDummy):
            self.report({'INFO'}, 'Error: Nested animations.')
            return {'CANCELLED'}
        ta = rootDummy.nvb.animList[rootDummy.nvb.animListIdx]
        # Check resulting length (has to be >= 1)
        oldSize = ta.frameEnd - ta.frameStart + 1
        newSize = self.scaleFactor * oldSize
        if (newSize < 1):
            self.report({'INFO'}, 'Error: Resulting size < 1.')
            return {'CANCELLED'}
        if (math.fabs(oldSize - newSize) < 1):
            self.report({'INFO'}, 'Error: Same size.')
            return {'CANCELLED'}
        # Get a list of affected objects
        objList = []
        nvb_utils.getAllChildren(rootDummy, objList)
        # Adjust Emitter data
        self.scaleEmitter(ta, self.scaleFactor)
        # Adjust keyframes
        for obj in objList:
            # Adjust the objects animation
            self.scaleFrames(obj, ta.frameStart, ta.frameEnd, self.scaleFactor)
            # Adjust the object's material animation
            if obj.active_material:
                self.scaleFrames(obj.active_material,
                                 ta.frameStart, ta.frameEnd, self.scaleFactor)
            # Adjust the object's shape key animation
            if obj.data and obj.data.shape_keys:
                self.scaleFrames(obj.data.shape_keys,
                                 ta.frameStart, ta.frameEnd, self.scaleFactor)
        # Adjust the bounds of animations coming after the
        # target (scaled) animation
        padding = newSize - oldSize
        for a in reversed(rootDummy.nvb.animList):
            if a.frameStart > ta.frameEnd:
                a.frameStart += padding
                a.frameEnd += padding
                for e in a.eventList:
                    e.frame += padding
        # Adjust the target (scaled) animation itself
        ta.frameEnd += padding
        for e in ta.eventList:
            e.frame = (e.frame - ta.frameStart + 1) * \
                self.scaleFactor + ta.frameStart - 1
        # Re-adjust the timeline to the new bounds
        nvb_utils.toggleAnimFocus(context.scene, rootDummy)
        return {'FINISHED'}

    def draw(self, context):
        """TODO:DOC."""
        layout = self.layout

        row = layout.row()
        row.label('Scaling: ')
        row = layout.row()
        row.prop(self, 'scaleFactor', text='Factor')

        layout.separator()

    def invoke(self, context, event):
        """TODO:DOC."""
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class NVB_OT_anim_crop(bpy.types.Operator):
    """Open a dialog to crop a single animation"""

    bl_idname = 'nvb.anim_crop'
    bl_label = 'Crop animation'

    cropFront = bpy.props.IntProperty(
                    name='cropFront',
                    min=0,
                    description='Insert Frames before the first keyframe')
    cropBack = bpy.props.IntProperty(
                    name='cropBack',
                    min=0,
                    description='Insert Frames after the last keyframe')

    @classmethod
    def poll(cls, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def cropEmitter(self, anim):
        """TODO:DOC."""
        if anim.rawascii and (anim.rawascii in bpy.data.texts):
            rawascii = bpy.data.texts[anim.rawascii]
            txt = copy.deepcopy(rawascii.as_string())
            oldData = []
            oldData = nvb_utils.readRawAnimData(txt)
            newData = []
            # Grab some values for speed
            cf = self.cropFront
            cb = (anim.frameEnd - anim.frameStart) - self.cropBack
            for nodeName, nodeType, oldKeyList in oldData:
                newKeyList = []
                for label, oldKeys in oldKeyList:
                    newKeys = []
                    for k in oldKeys:
                        frame = int(k[0])
                        if (cf < frame < cb):
                            newKeys.append(k)
                    newKeyList.append([label, newKeys])
                newData.append([nodeName, nodeType, newKeyList])
            txt.clear()
            nvb_utils.writeRawAnimData(txt, newData)

    def cropFrames(self, target, animStart, animEnd):
        """TODO:DOC."""
        if target.animation_data and target.animation_data.action:
            # Grab some values for speed
            cf = self.cropFront
            cb = self.cropBack
            # Find out which frames to delete
            action = target.animation_data.action
            framesToDelete = []
            # Find out which ones to delete
            for fcurve in target.animation_data.action.fcurves:
                for p in fcurve.keyframe_points:
                    if (animStart <= p.co[0] < animStart + cf) or \
                       (animEnd - cb < p.co[0] <= animEnd):
                        framesToDelete.append((fcurve.data_path, p.co[0]))
            # Delete the frames by accessing them from the object.
            # (Can't do it directly)
            for dp, f in framesToDelete:
                target.keyframe_delete(dp, frame=f)
            # Move the keyframes to the front to remove gaps
            for fcurve in action.fcurves:
                for p in fcurve.keyframe_points:
                    if (p.co[0] >= animStart):
                        p.co[0] -= cf
                        p.handle_left.x -= cf
                        p.handle_right.x -= cf
                        if (p.co[0] >= animEnd):
                            p.co[0] -= cb
                            p.handle_left.x -= cb
                            p.handle_right.x -= cb
                # For compatibility with older blender versions
                try:
                    fcurve.update()
                except AttributeError:
                    pass

    def execute(self, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if not nvb_utils.checkAnimBounds(rootDummy):
            self.report({'INFO'}, 'Failure: Convoluted animations.')
            return {'CANCELLED'}
        animList = rootDummy.nvb.animList
        currentAnimIdx = rootDummy.nvb.animListIdx
        anim = animList[currentAnimIdx]
        # Grab some values for speed
        cf = self.cropFront
        cb = self.cropBack
        animStart = anim.frameStart
        animEnd = anim.frameEnd
        totalCrop = cf + cb
        # Resulting length has to be at lest 1 frame
        if totalCrop > (animEnd - animStart + 1):
            self.report({'INFO'}, 'Failure: Resulting length < 1.')
            return {'CANCELLED'}
        # Get a list of affected objects
        objList = []
        nvb_utils.getAllChildren(rootDummy, objList)
        # Crop Emitter
        self.cropEmitter(anim)
        # Pad keyframes
        for obj in objList:
            # Copy the objects animation
            self.cropFrames(obj, animStart, animEnd)
            # Copy the object's material animation
            if obj.active_material:
                self.cropFrames(obj.active_material, animStart, animEnd)
            # Copy the object's shape key animation
            if obj.data and obj.data.shape_keys:
                self.cropFrames(obj.data.shape_keys, animStart, animEnd)
        # Update the animations in the list
        for a in rootDummy.nvb.animList:
            if a.frameStart > animStart:
                a.frameStart -= totalCrop
                a.frameEnd -= totalCrop
                for e in a.eventList:
                    e.frame -= totalCrop
        # Adjust the target animation itself
        for idx, e in enumerate(anim.eventList):
            if (animStart <= e.frame < animStart + cf) or \
               (animEnd - cb < e.frame <= animEnd):
                anim.eventList.remove(idx)
                anim.eventListIdx = 0
            else:
                e.frame -= totalCrop
        anim.frameEnd -= totalCrop
        # Re-adjust the timeline to the new bounds
        nvb_utils.toggleAnimFocus(context.scene, rootDummy)
        return {'FINISHED'}

    def draw(self, context):
        """TODO:DOC."""
        layout = self.layout

        row = layout.row()
        row.label('Crop: ')
        row = layout.row()
        split = row.split()
        col = split.column(align=True)
        col.prop(self, 'cropFront', text='Front')
        col.prop(self, 'cropBack', text='Back')

        layout.separator()

    def invoke(self, context, event):
        """TODO:DOC."""
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class NVB_OT_anim_pad(bpy.types.Operator):
    """Open a dialog to pad a single animation"""

    bl_idname = 'nvb.anim_pad'
    bl_label = 'Pad animation'

    padFront = bpy.props.IntProperty(
                    name='padFront',
                    min=0,
                    description='Insert Frames before the first keyframe')
    padBack = bpy.props.IntProperty(
                    name='padBack',
                    min=0,
                    description='Insert Frames after the last keyframe')

    @classmethod
    def poll(cls, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def padEmitter(self, anim):
        """TODO:DOC."""
        if anim.rawascii and (anim.rawascii in bpy.data.texts):
            rawdata = bpy.data.texts[anim.rawascii]
            txt = copy.deepcopy(rawdata.as_string())
            animData = []
            animData = nvb_utils.readRawAnimData(txt)
            for nodeName, nodeType, keyList in animData:
                for label, keys in keyList:
                    for k in keys:
                        k[0] = str(int(k[0]) + self.padFront)
            txt.clear()
            nvb_utils.writeRawAnimData(txt, animData)

    def padFrames(self, target, animStart, animEnd):
        """TODO:DOC."""
        if target.animation_data and target.animation_data.action:
            action = target.animation_data.action
            for fcurve in action.fcurves:
                for p in reversed(fcurve.keyframe_points):
                    if p.co[0] > animEnd:
                        p.co[0] += self.padBack
                        p.handle_left.x += self.padBack
                        p.handle_right.x += self.padBack
                    if p.co[0] >= animStart:
                        p.co[0] += self.padFront
                        p.handle_left.x += self.padFront
                        p.handle_right.x += self.padFront
                # For compatibility with older blender versions
                try:
                    fcurve.update()
                except AttributeError:
                    pass

    def execute(self, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if not nvb_utils.checkAnimBounds(rootDummy):
            self.report({'INFO'}, 'Failure: Convoluted animations.')
            return {'CANCELLED'}
        ta = rootDummy.nvb.animList[rootDummy.nvb.animListIdx]
        # Cancel if padding is 0
        if (self.padFront + self.padBack) <= 0:
            self.report({'INFO'}, 'Failure: No changes.')
            return {'CANCELLED'}
        # Get a list of affected objects
        objList = []
        nvb_utils.getAllChildren(rootDummy, objList)
        # Pad Emitter
        self.padEmitter(ta)
        # Pad keyframes
        for obj in objList:
            # Pad the objects animation
            self.padFrames(obj, ta.frameStart, ta.frameEnd)
            # Pad the object's material animation
            if obj.active_material:
                self.padFrames(obj.active_material, ta.frameStart, ta.frameEnd)
            # Pad the object's shape key animation
            if obj.data and obj.data.shape_keys:
                self.padFrames(obj.data.shape_keys, ta.frameStart, ta.frameEnd)
        # Update the animations in the list
        totalPadding = self.padBack + self.padFront
        for a in rootDummy.nvb.animList:
            if a.frameStart > ta.frameEnd:
                a.frameStart += totalPadding
                a.frameEnd += totalPadding
                for e in a.eventList:
                    e.frame += totalPadding
        # Update the target animation itself
        ta.frameEnd += totalPadding
        for e in ta.eventList:
            e.frame += self.padFront
        # Re-adjust the timeline to the new bounds
        nvb_utils.toggleAnimFocus(context.scene, rootDummy)
        return {'FINISHED'}

    def draw(self, context):
        """TODO:DOC."""
        layout = self.layout

        row = layout.row()
        row.label('Padding: ')
        row = layout.row()
        split = row.split()
        col = split.column(align=True)
        col.prop(self, 'padFront', text='Front')
        col.prop(self, 'padBack', text='Back')

        layout.separator()

    def invoke(self, context, event):
        """TODO:DOC."""
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class NVB_OT_anim_focus(bpy.types.Operator):
    """Set the Start and end frames of the timeline"""

    bl_idname = 'nvb.anim_focus'
    bl_label = 'Set start and end frame of the timeline to the animation'

    @classmethod
    def poll(self, context):
        """Prevent execution if animation list is empty."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def execute(self, context):
        """Set the timeline to this animation."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        scene = context.scene

        nvb_utils.toggleAnimFocus(scene, rootDummy)
        return {'FINISHED'}


class NVB_OT_anim_new(bpy.types.Operator):
    """Add a new animation to the animation list"""

    bl_idname = 'nvb.anim_new'
    bl_label = 'Create new animation'

    @classmethod
    def poll(self, context):
        """Prevent execution if no object is selected."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        return (rootDummy is not None)

    def execute(self, context):
        """Create the animation"""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        newanim = nvb_utils.createAnimListItem(rootDummy)
        newanim.root = rootDummy.name
        return {'FINISHED'}


class NVB_OT_anim_delete(bpy.types.Operator):
    """Delete the selected animation and its keyframes"""

    bl_idname = 'nvb.anim_delete'
    bl_label = 'Delete an animation'

    @classmethod
    def poll(self, context):
        """Prevent execution if animation list is empty."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def deleteFrames(self, target, frameStart, frameEnd):
        """Delete the animation's keyframes."""
        if target.animation_data and target.animation_data.action:
            # Find out which frames to delete
            action = target.animation_data.action
            framesToDelete = []
            for fcurve in action.fcurves:
                for p in fcurve.keyframe_points:
                    if (frameStart <= p.co[0] <= frameEnd):
                        framesToDelete.append((fcurve.data_path, p.co[0]))
            # Delete them by accessing them from the object.
            # (Can't do it directly)
            for dp, f in framesToDelete:
                target.keyframe_delete(dp, frame=f)

    def execute(self, context):
        """Delete the animation."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        animList = rootDummy.nvb.animList
        animListIdx = rootDummy.nvb.animListIdx
        anim = animList[animListIdx]
        # Grab some data for speed
        frameStart = anim.frameStart
        frameEnd = anim.frameEnd
        # Get a list of affected objects
        objList = []
        nvb_utils.getAllChildren(rootDummy, objList)
        # Remove keyframes
        for obj in objList:
            # Delete the objects animation
            self.deleteFrames(obj, frameStart, frameEnd)
            # Delete the object's material animation
            if obj.active_material:
                self.deleteFrames(obj.active_material, frameStart, frameEnd)
            # Delete the object's shape key animation
            if obj.data and obj.data.shape_keys:
                self.deleteFrames(obj.data.shape_keys, frameStart, frameEnd)
        # Remove animation from List
        animList.remove(animListIdx)
        if animListIdx > 0:
            rootDummy.nvb.animListIdx = animListIdx - 1
        return {'FINISHED'}


class NVB_OT_anim_moveback(bpy.types.Operator):
    """Move an animation and its keyframes to the end of the animation list"""

    bl_idname = 'nvb.anim_moveback'
    bl_label = 'Move to end.'

    @classmethod
    def poll(self, context):
        """Prevent execution if animation list is empty."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 1)
        return False

    def moveFrames(self, target, oldStart, oldEnd, newStart):
        """Move the animation's keyframes."""
        if target.animation_data and target.animation_data.action:
            insertionOptions = {'FAST'}
            action = target.animation_data.action
            framesToDelete = []
            for fcurve in action.fcurves:
                for p in fcurve.keyframe_points:
                    if (oldStart <= p.co[0] <= oldEnd):
                        framesToDelete.append((fcurve.data_path, p.co[0]))
                        newFrame = p.co[0] + newStart - oldStart
                        fcurve.keyframe_points.insert(newFrame, p.co[1],
                                                      insertionOptions)
                fcurve.update()
            # Delete the frames by accessing them from the object.
            # (Can't do it directly)
            for dp, f in framesToDelete:
                target.keyframe_delete(dp, frame=f)

    def execute(self, context):
        """Move the animation to the end of the animation list."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if not nvb_utils.checkAnimBounds(rootDummy):
            self.report({'INFO'}, 'Failure: Convoluted animations.')
            return {'CANCELLED'}
        animList = rootDummy.nvb.animList
        currentAnimIdx = rootDummy.nvb.animListIdx
        anim = animList[currentAnimIdx]
        # Grab some data for speed
        oldStart = anim.frameStart
        oldEnd = anim.frameEnd
        # Get the end of the timeline
        newStart = 0
        for a in rootDummy.nvb.animList:
            if a.frameEnd > newStart:
                newStart = a.frameEnd
        newStart = newStart + nvb_def.anim_offset
        # Get a list of affected objects
        objList = [rootDummy]
        for o in objList:
            for c in o.children:
                objList.append(c)
        # Move keyframes
        for obj in objList:
            # Delete the objects animation
            self.moveFrames(obj, oldStart, oldEnd, newStart)
            # Delete the object's material animation
            if obj.active_material:
                self.moveFrames(obj.active_material,
                                oldStart, oldEnd, newStart)
            # Delete the object's shape key animation
            if obj.data and obj.data.shape_keys:
                self.moveFrames(obj.data.shape_keys,
                                oldStart, oldEnd, newStart)

        # Adjust animations in the list
        for e in anim.eventList:
            e.frame = newStart + (e.frame - oldStart)
        anim.frameStart = newStart
        anim.frameEnd = newStart + (oldEnd - oldStart)
        # Set index
        newAnimIdx = len(animList) - 1
        animList.move(currentAnimIdx, newAnimIdx)
        rootDummy.nvb.animListIdx = newAnimIdx
        # Re-adjust the timeline to the new bounds
        nvb_utils.toggleAnimFocus(context.scene, rootDummy)
        return {'FINISHED'}


class NVB_OT_anim_move(bpy.types.Operator):
    """Move an item in the animation list, without affecting keyframes"""

    bl_idname = 'nvb.anim_move'
    bl_label = 'Move an animation in the list, without affecting keyframes'

    direction = bpy.props.EnumProperty(items=(('UP', 'Up', ''),
                                              ('DOWN', 'Down', '')))

    @classmethod
    def poll(self, context):
        """Prevent execution if animation list has less than 2 elements."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 1)
        return False

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        animList = rootDummy.nvb.animList

        currentIdx = rootDummy.nvb.animListIdx
        newIdx = 0
        maxIdx = len(animList) - 1
        if self.direction == 'DOWN':
            newIdx = currentIdx + 1
        elif self.direction == 'UP':
            newIdx = currentIdx - 1
        else:
            return {'CANCELLED'}

        newIdx = max(0, min(newIdx, maxIdx))
        if newIdx == currentIdx:
            return {'CANCELLED'}
        animList.move(currentIdx, newIdx)
        rootDummy.nvb.animListIdx = newIdx
        return {'FINISHED'}


class NVB_OT_lensflare_new(bpy.types.Operator):
    """Add a new item to the flare list"""

    bl_idname = 'nvb.lightflare_new'
    bl_label = 'Add a new flare to a light'

    def execute(self, context):
        """TODO: DOC."""
        obj = context.object
        if (obj.type == 'LAMP'):
            obj.data.nvb.flareList.add()

        return {'FINISHED'}


class NVB_OT_lensflare_delete(bpy.types.Operator):
    """Delete the selected item from the flare list"""

    bl_idname = 'nvb.lightflare_delete'
    bl_label = 'Deletes a flare from the light'

    @classmethod
    def poll(self, context):
        """Enable only if the list isn't empty."""
        obj = context.object
        return len(obj.data.nvb.flareList) > 0

    def execute(self, context):
        """TODO: DOC."""
        obj = context.object
        flareList = obj.data.nvb.flareList
        flareIdx = obj.data.nvb.flareListIdx

        flareList.remove(flareIdx)
        if flareIdx > 0:
            flareIdx = flareIdx - 1

        return {'FINISHED'}


class NVB_OT_lensflare_move(bpy.types.Operator):
    """Move an item in the flare list"""

    bl_idname = 'nvb.lightflare_move'
    bl_label = 'Move an item in the flare list'

    direction = bpy.props.EnumProperty(items=(('UP', 'Up', ''),
                                              ('DOWN', 'Down', '')))

    @classmethod
    def poll(self, context):
        """TODO: DOC."""
        obj = context.object
        return len(obj.data.nvb.flareList) > 0

    def execute(self, context):
        """TODO: DOC."""
        obj = context.object
        flareList = obj.data.nvb.flareList

        currentIdx = obj.data.nvb.flareListIdx
        newIdx = 0
        maxIdx = len(flareList) - 1
        if self.direction == 'DOWN':
            newIdx = currentIdx + 1
        elif self.direction == 'UP':
            newIdx = currentIdx - 1
        else:
            return {'CANCELLED'}

        newIdx = max(0, min(newIdx, maxIdx))
        flareList.move(currentIdx, newIdx)
        obj.data.nvb.flareListIdx = newIdx
        return {'FINISHED'}


class NVB_OT_animevent_new(bpy.types.Operator):
    """Add a new item to the event list"""

    bl_idname = 'nvb.animevent_new'
    bl_label = 'Add a new event to an animation'

    @classmethod
    def poll(self, context):
        """Enable only if there is an animation."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        animList = rootDummy.nvb.animList

        return len(animList) > 0

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        anim = rootDummy.nvb.animList[rootDummy.nvb.animListIdx]

        eventList = anim.eventList
        newEvent = eventList.add()
        if anim.frameStart <= bpy.context.scene.frame_current <= anim.frameEnd:
            newEvent.frame = bpy.context.scene.frame_current
        else:
            newEvent.frame = anim.frameStart

        return {'FINISHED'}


class NVB_OT_animevent_delete(bpy.types.Operator):
    """Delete the selected item from the event list"""

    bl_idname = 'nvb.animevent_delete'
    bl_label = 'Deletes an event from an animation'

    @classmethod
    def poll(self, context):
        """Enable only if the list isn't empty."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            animList = rootDummy.nvb.animList
            if len(animList) > 0:
                anim = animList[rootDummy.nvb.animListIdx]
                eventList = anim.eventList
                return len(eventList) > 0
        return False

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        anim = rootDummy.nvb.animList[rootDummy.nvb.animListIdx]
        eventList = anim.eventList
        eventIdx = anim.eventListIdx

        eventList.remove(eventIdx)
        if eventIdx > 0:
            eventIdx = eventIdx - 1

        return{'FINISHED'}


class NVB_OT_animevent_move(bpy.types.Operator):
    """Move an item in the event list"""

    bl_idname = 'nvb.animevent_move'
    bl_label = 'Move an item in the event  list'

    direction = bpy.props.EnumProperty(items=(('UP', 'Up', ''),
                                              ('DOWN', 'Down', '')))

    @classmethod
    def poll(self, context):
        """Enable only if the list isn't empty."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            animList = rootDummy.nvb.animList
            if len(animList) > 0:
                anim = animList[rootDummy.nvb.animListIdx]
                eventList = anim.eventList
                return len(eventList) > 0
        return False

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        anim = rootDummy.nvb.animList[rootDummy.nvb.animListIdx]
        eventList = anim.eventList

        currentIdx = anim.eventListIdx
        newIdx = 0
        maxIdx = len(eventList) - 1
        if self.direction == 'DOWN':
            newIdx = currentIdx + 1
        elif self.direction == 'UP':
            newIdx = currentIdx - 1
        else:
            return {'CANCELLED'}

        newIdx = max(0, min(newIdx, maxIdx))
        eventList.move(currentIdx, newIdx)
        anim.eventListIdx = newIdx
        return {'FINISHED'}


class NVB_OT_light_genname(bpy.types.Operator):
    """Generate a name for the light based on type"""

    bl_idname = 'nvb.light_generatename'
    bl_label = 'Generate a name for the light'

    @classmethod
    def poll(self, context):
        """Enable only if a Lamp is selected."""
        return (context.object and context.object.type == 'LAMP')

    def execute(self, context):
        """TODO: DOC."""
        obj = context.object
        rootDummy = nvb_utils.findObjRootDummy(obj)
        if not rootDummy:
            self.report({'INFO'}, 'Failure: No rootdummy.')
            return {'CANCELLED'}
        currentSuffix = nvb_def.Lighttype.getSuffix(obj)
        newSuffix = nvb_def.Lighttype.generateSuffix(obj)
        baseName = rootDummy.name
        if newSuffix:
            # Remove old suffix first
            if currentSuffix:
                baseName = obj.name[:-1*len(currentSuffix)]
            newName = baseName + '' + newSuffix
            if newName in bpy.data.objects:
                self.report({'INFO'}, 'Failure: Name already exists.')
                return {'CANCELLED'}
            elif obj.name.endswith(newSuffix):
                self.report({'INFO'}, 'Failure: Suffix already exists.')
                return {'CANCELLED'}
            else:
                obj.name = newName
                return {'FINISHED'}
        self.report({'INFO'}, 'Failure: No suffix found.')
        return {'CANCELLED'}


class NVB_OT_dummy_genname(bpy.types.Operator):
    """Generate an appropriate name for the dummy"""

    bl_idname = 'nvb.dummy_generatename'
    bl_label = 'Generate a name for the dummy'

    @classmethod
    def poll(self, context):
        """Enable only if a Empty is selected."""
        return (context.object and context.object.type == 'EMPTY')

    def execute(self, context):
        """TODO: DOC."""
        obj = context.object
        rootDummy = nvb_utils.findObjRootDummy(obj)
        if not rootDummy:
            self.report({'INFO'}, 'Failure: No rootdummy.')
            return {'CANCELLED'}
        currentSuffix = nvb_def.Dummytype.getSuffix(obj)
        newSuffix = nvb_def.Dummytype.generateSuffix(
                        obj,
                        rootDummy.nvb.classification)
        baseName = rootDummy.name
        if newSuffix:
            # Remove old suffix first
            if currentSuffix:
                baseName = obj.name[:-1*len(currentSuffix)]
            newName = baseName + '_' + newSuffix
            if newName in bpy.data.objects:
                self.report({'INFO'}, 'Failure: Name already exists.')
                return {'CANCELLED'}
            elif obj.name.endswith(newSuffix):
                self.report({'INFO'}, 'Failure: Suffix already exists.')
                return {'CANCELLED'}
            else:
                obj.name = newName
                return {'FINISHED'}
        self.report({'INFO'}, 'Failure: No suffix found.')
        return {'CANCELLED'}


class NVB_OT_import(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Import Aurora Engine model (.mdl)"""

    bl_idname = 'nvb.mdlimport'
    bl_label = 'Import Aurora MDL'
    bl_options = {'UNDO', 'PRESET'}

    filename_ext = '.mdl'
    filter_glob = bpy.props.StringProperty(default='*.mdl',
                                           options={'HIDDEN'})
    importAnimations = bpy.props.BoolProperty(
            name='Import Animations',
            description='Import animation data if available',
            default=True)
    importWalkmesh = bpy.props.BoolProperty(
            name='Import Walkmesh',
            description='Load placeable and door walkmeshes if available',
            default=True)
    importSmoothGroups = bpy.props.BoolProperty(
            name='Import Smooth Groups',
            description='Import smooth groups as sharp edges',
            default=True)
    importNormals = bpy.props.BoolProperty(
            name='Import Normals',
            description='Import normals from MDL if available',
            default=True)
    importMaterials = bpy.props.BoolProperty(
            name='Import Materials',
            description='Import materials and textures',
            default=True)
    # Sub-Options for Materials
    materialLoadMTR = bpy.props.BoolProperty(
            name='Load MTR files',
            description='Use external material file if available ' +
                        '(will override material in MDL)',
            default=True)
    materialAutoMerge = bpy.props.BoolProperty(
            name='Auto Merge Materials',
            description='Merge Materials with same settings',
            default=True)
    textureDefaultRoles = bpy.props.BoolProperty(
            name='Texture Default Roles',
            description='Auto apply settings to create diffuse, normal ' +
                        'and specular textures',
            default=True)
    textureSearch = bpy.props.BoolProperty(
            name='Image Search',
            description='Search for images in subdirectories \
                         (Warning: May be slow)',
            default=False)
    # Blender Settings
    customfps = bpy.props.BoolProperty(name='Use Custom fps',
                                       description='Use custom fps value',
                                       default=True)
    fps = bpy.props.IntProperty(name='Custom fps',
                                description='Custom fps value',
                                default=30,
                                min=1, max=60)
    # Hidden settings for batch processing
    minimapMode = bpy.props.BoolProperty(
            name='Minimap Mode',
            description='Ignore lights and fading objects',
            default=False,
            options={'HIDDEN'})
    minimapSkipFade = bpy.props.BoolProperty(
            name='Minimap Mode: Import Fading Objects',
            description='Ignore fading objects',
            default=False,
            options={'HIDDEN'})

    def draw(self, context):
        """Draw the export UI."""
        layout = self.layout
        # Misc Import Settings
        box = layout.box()
        box.prop(self, 'importAnimations')
        box.prop(self, 'importWalkmesh')
        box.prop(self, 'importSmoothGroups')
        box.prop(self, 'importNormals')
        # Material Import Settings
        box = layout.box()
        box.prop(self, 'importMaterials')
        sub = box.column()
        sub.enabled = self.importMaterials
        sub.prop(self, 'materialLoadMTR')
        sub.prop(self, 'materialAutoMerge')
        sub.prop(self, 'textureDefaultRoles')
        sub.prop(self, 'textureSearch')
        # Blender Settings
        box = layout.box()
        box.label(text='Blender Settings')
        row = box.row(align=True)
        row.prop(self, 'customfps', text='')
        sub = row.row(align=True)
        sub.enabled = self.customfps
        sub.prop(self, 'fps', text='Scene Framerate')

    def execute(self, context):
        """TODO: DOC."""
        options = nvb_def.ImportOptions()
        options.filepath = self.filepath
        options.scene = context.scene
        # Misc Import Settings
        options.importSmoothGroups = self.importSmoothGroups
        options.importNormals = self.importNormals
        options.importAnimations = self.importAnimations
        options.importMaterials = self.importMaterials
        # Material Import Settings
        options.materialLoadMTR = self.materialLoadMTR
        options.materialAutoMerge = self.materialAutoMerge
        options.textureDefaultRoles = self.textureDefaultRoles
        options.textureSearch = self.textureSearch
        # Hidden settings for batch processing
        options.minimapMode = self.minimapMode
        options.minimapSkipFade = self.minimapSkipFade
        # Blender Settings
        options.customfps = self.customfps
        options.fps = self.fps
        return nvb_io.loadMdl(self, context, options)


class NVB_OT_export(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    """Export Aurora Engine model (.mdl)"""

    bl_idname = 'nvb.mdlexport'
    bl_label = 'Export Aurora MDL'
    bl_options = {'PRESET'}

    filename_ext = '.mdl'
    filter_glob = bpy.props.StringProperty(
            default='*.mdl',
            options={'HIDDEN'})
    # Misc Export Settings
    exportAnimations = bpy.props.BoolProperty(
            name='Export Animations',
            description='Export animations',
            default=True)
    exportWalkmesh = bpy.props.BoolProperty(
            name='Export Walkmesh',
            description='Export a walkmesh',
            default=True)
    exportSmoothGroups = bpy.props.BoolProperty(
            name='Export Smooth groups',
            description='Generate smooth groups from sharp edges'
                        '(When disabled every face belongs to the same group)',
            default=True)
    exportNormals = bpy.props.BoolProperty(
            name='Export Normals and Tangents',
            description='Add normals and tangents to MDL',
            default=False)
    # UV Map Export settings
    uvmapAutoJoin = bpy.props.BoolProperty(
            name='Auto Join UVs',
            description='Join uv-vertices with identical coordinates',
            default=True)
    uvmapMode = bpy.props.EnumProperty(
            name='Mode',
            description='Determines which meshes get uv maps',
            items=(('TEX', 'Textured Meshes',
                    'Add UV Maps only to textured and rendered meshes'),
                   ('REN', 'Rendered Meshes',
                    'Add UV Maps only to rendered meshes'),
                   ('ALL', 'All',
                    'Add UV Maps to all meshes'),
                   ),
            default='REN',
            )
    uvmapOrder = bpy.props.EnumProperty(
            name='Order',
            description='Determines ordering of uv maps in MDL',
            items=(('AL0', 'Alphabetical',
                    'Alphabetical orering'),
                   ('AL1', 'Alphabetical (Active First)',
                    'Alphabetical orering, active UVMap will be first'),
                   ('ACT', 'Active Only',
                    'Export active UVMap only'),
                   ),
            default='AL0',
            )
    # Material Export Settings
    materialUseMTR = bpy.props.BoolProperty(
            name='Reference MTR file',
            description='Add a reference to MTR file ' +
                        '(Filename will be the objects material name)',
            default=False)
    textureOrder = bpy.props.EnumProperty(
            name='Texture Order',
            items=(('TSL', 'Texture Slot',
                    'Texture index is texture slot index'),
                   ('CON', 'Consecutive',
                    'Consecutive numbering'),
                   ),
            default='TSL',
            )
    # Blender Setting to use
    applyModifiers = bpy.props.BoolProperty(
            name='Apply Modifiers',
            description='Apply Modifiers before exporting',
            default=True)

    def draw(self, context):
        """Draw the export UI."""
        layout = self.layout
        # Misc Export Settings
        box = layout.box()
        box.prop(self, 'exportAnimations')
        box.prop(self, 'exportWalkmesh')
        box.prop(self, 'exportSmoothGroups')
        box.prop(self, 'exportNormals')
        # UV Map settings
        box = layout.box()
        box.label(text='UV Map Settings')
        sub = box.column()
        sub.prop(self, 'uvmapAutoJoin')
        sub.prop(self, 'uvmapMode')
        sub.prop(self, 'uvmapOrder')
        # Material Export Settings
        box = layout.box()
        box.label(text='Material Settings')
        sub = box.column()
        sub.prop(self, 'materialUseMTR')
        sub.prop(self, 'textureOrder')
        # Blender Settings
        box = layout.box()
        box.label(text='Blender Settings')
        sub = box.column()
        sub.prop(self, 'applyModifiers')

    def execute(self, context):
        """TODO: DOC."""
        options = nvb_def.ExportOptions()
        options.filepath = self.filepath
        options.scene = context.scene
        # Misc Export Settings
        options.exportAnimations = self.exportAnimations
        options.exportWalkmesh = self.exportWalkmesh
        options.exportSmoothGroups = self.exportSmoothGroups
        options.exportNormals = self.exportNormals
        # UV Map settings
        options.uvmapAutoJoin = self.uvmapAutoJoin
        options.uvmapMode = self.uvmapMode
        options.uvmapOrder = self.uvmapOrder
        # Material Export Settings
        options.materialUseMTR = self.materialUseMTR
        options.textureOrder = self.textureOrder
        # Blender Settings
        options.applyModifiers = self.applyModifiers
        return nvb_io.saveMdl(self, context, options)


class NVB_OT_helper_genwok(bpy.types.Operator):
    """Load all materials for aabb walkmeshes for the selected object"""

    bl_idname = "nvb.helper_loadwokmat"
    bl_label = "Load walkmesh materials"

    def execute(self, context):
        """Delete all current materials and add walkmesh materials."""
        selected_object = context.object
        if (selected_object) and (selected_object.type == 'MESH'):
            object_mesh = selected_object.data

            # Remove all current material slots
            for i in range(len(selected_object.material_slots)):
                bpy.ops.object.material_slot_remove()

            # Create materials
            for matDef in nvb_def.wok_materials:
                matName = matDef[0]

                # Walkmesh materials should be shared across multiple
                # walkmeshes, as they always identical
                if matName in bpy.data.materials.keys():
                    mat = bpy.data.materials[matName]
                else:
                    mat = bpy.data.materials.new(matName)

                    mat.diffuse_color = matDef[1]
                    mat.diffuse_intensity = 1.0
                    mat.specular_color = (0.0, 0.0, 0.0)
                    mat.specular_intensity = matDef[2]

                object_mesh.materials.append(mat)
        else:
            self.report({'INFO'}, 'A mesh must be selected')
            return {'CANCELLED'}

        return {'FINISHED'}


class NVB_OT_helper_genobjects(bpy.types.Operator):
    """Helper to add missing walkmesh objects."""

    bl_idname = "nvb.helper_wkm_setup"
    bl_label = "Setup Walkmesh"

    @classmethod
    def poll(self, context):
        """Prevent execution if no object is selected."""
        return (context.object is not None)

    def execute(self, context):
        """Create Walkmesh root and objects."""
        mdlroot = nvb_utils.findObjRootDummy(context.object)
        if not mdlroot:
            return {'CANCELLED'}
        scene = bpy.context.scene
        wkmtype = mdlroot.nvb.helper_wkm_type
        if wkmtype == nvb_def.Walkmeshtype.PWK:
            nvb_utils.createPWKObjects(mdlroot, scene)
        elif wkmtype == nvb_def.Walkmeshtype.DWK:
            nvb_utils.createDWKObjects(mdlroot, scene)
        self.report({'INFO'}, 'Created objects')
        return {'FINISHED'}


class NVB_OT_helper_mmsetup(bpy.types.Operator):
    """Set up rendering for minimaps."""

    bl_idname = "nvb.helper_minimap_setup"
    bl_label = "Render Minimap"

    @classmethod
    def poll(self, context):
        """Prevent execution if no object is selected."""
        return (context.object is not None)

    def execute(self, context):
        """Create camera + lamp and Renders Minimap."""
        mdlRoot = nvb_utils.findObjRootDummy(context.object)
        if not mdlRoot:
            return {'CANCELLED'}
        scene = bpy.context.scene

        nvb_utils.setupMinimapRender(mdlRoot, scene)
        bpy.ops.render.render(use_viewport=True)
        # bpy.ops.render.view_show()

        self.report({'INFO'}, 'Ready to render')
        return {'FINISHED'}


class NVB_OT_helper_genskgr(bpy.types.Operator):
    """TODO: DOC"""
    bl_idname = "nvb.skingroup_add"
    bl_label = "Add new Skingroup"

    def execute(self, context):
        """TODO: DOC."""
        obj = context.object
        skingrName = obj.nvb.skingroup_obj
        # Check if there is already a vertex group with this name
        if skingrName:
            if (skingrName not in obj.vertex_groups.keys()):
                # Create the vertex group
                obj.vertex_groups.new(skingrName)
                obj.nvb.skingroup_obj = ''

                self.report({'INFO'}, 'Created vertex group ' + skingrName)
                return{'FINISHED'}
            else:
                self.report({'INFO'}, 'Duplicate Name')
                return {'CANCELLED'}
        else:
            self.report({'INFO'}, 'Empty Name')
            return {'CANCELLED'}


class NVB_OT_mtr_embed(bpy.types.Operator):
    """Embed the MTR file into the blend file by creating a Text block."""
    bl_idname = "nvb.mtr_embed"
    bl_label = "Embed MTR"

    def execute(self, context):
        """TODO: DOC."""
        pass
        return{'FINISHED'}


class NVB_OT_mtr_generate(bpy.types.Operator):
    """Generate a new Text Block containing from the current material."""
    bl_idname = "nvb.mtr_generate"
    bl_label = "Generate MTR"

    def execute(self, context):
        """TODO: DOC."""
        pass
        return{'FINISHED'}


class NVB_OT_mtr_open(bpy.types.Operator):
    """Open material file."""
    bl_idname = "nvb.mtr_open"
    bl_label = "Open MTR"

    filename_ext = '.mtr'
    filter_glob = bpy.props.StringProperty(default='.mtr', options={'HIDDEN'})

    filepath = bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        print("filepath= " + self.filepath)
        return{'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        # Open browser, take reference to 'self'
        # read the path to selected file,
        # put path in declared string type data structure self.filepath

        return {'RUNNING_MODAL'}


class NVB_OT_mtr_reload(bpy.types.Operator):
    """Reload MTR, update current material."""
    bl_idname = "nvb.mtr_reload"
    bl_label = "Reload MTR"

    def execute(self, context):
        """TODO: DOC."""
        pass
        return{'FINISHED'}
