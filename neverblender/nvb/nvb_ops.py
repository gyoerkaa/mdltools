"""TODO: DOC."""

import math
import copy
import os
import re

import bpy
import mathutils

from . import nvb_def
from . import nvb_utils
from . import nvb_mtr


class NVB_OT_helper_restpose(bpy.types.Operator):
    """Apply current pose as restpose and adjust animation."""

    bl_idname = 'nvb.helper_restpose'
    bl_label = 'Apply current Pose'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        """Prevent execution if no armature is selected."""
        obj = context.object
        return obj and (obj.type == 'ARMATURE')

    def adjust_animations(self, armature, posebone, cmat):
        """TODO: DOC."""
        def adjust_loc(amt, posebone, kfvalues, cmat):
            mats = [cmat * mathutils.Matrix.Translation(v) for v in kfvalues]
            return [list(m.to_translation()) for m in mats]

        def adjust_axan(amt, posebone, kfvalues, cmat):
            mats = [cmat *
                    mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4()
                    for v in kfvalues]
            quats = [m.to_quaternion() for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def adjust_quat(amt, posebone, kfvalues, cmat):
            mats = [cmat * mathutils.Quaternion(v).to_matrix().to_4x4()
                    for v in kfvalues]
            return [list(m.to_quaternion()) for m in mats]

        def adjust_eul(amt, posebone, kfvalues, cmat):
            mats = [cmat * mathutils.Euler(v, 'XYZ').to_matrix().to_4x4()
                    for v in kfvalues]
            # Euler Filter
            euls = []
            e = posebone.rotation_euler
            for m in mats:
                e = m.to_euler('XYZ', e)
                euls.append(e)
            return euls

        action = armature.animation_data.action
        source_fcu = action.fcurves
        dp_list = [('rotation_axis_angle', 4, adjust_axan),
                   ('rotation_quaternion', 4, adjust_quat),
                   ('rotation_euler', 3, adjust_eul),
                   ('location', 3, adjust_loc)]
        for dp_suffix, dp_dim, adjust_func in dp_list:
            dp = 'pose.bones["' + posebone.name + '"].' + dp_suffix
            fcu = [source_fcu.find(dp, i)for i in range(dp_dim)]
            if fcu.count(None) < 1:
                frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points]
                      for i in range(dp_dim)]))
                frames.sort()
                values = [[fcu[i].evaluate(f)
                          for i in range(dp_dim)] for f in frames]
                # Adjust kfp to new coordinates
                values = adjust_func(armature, posebone, values, cmat)
                # Write back adjusted kfp values
                for i in range(dp_dim):
                    single_vals = [v[i] for v in values]
                    data = [d for z in zip(frames, single_vals) for d in z]
                    fcu[i].keyframe_points.foreach_set('co', data)
                    fcu[i].update()

    def execute(self, context):
        """Create pseudo bones"""
        armature = context.object
        # Save old pose matrices
        bpy.ops.object.mode_set(mode='POSE')
        original_pose_mat = dict()
        for posebone in armature.pose.bones:
            original_pose_mat[posebone.name] = posebone.matrix_basis.copy()
        # Apply current Pose
        bpy.ops.pose.armature_apply()
        # Adjust animations
        if armature.animation_data and armature.animation_data.action:
            for posebone in armature.pose.bones:
                op_mat = original_pose_mat[posebone.name]
                cmat = op_mat.inverted()
                self.adjust_animations(armature, posebone, cmat)
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}


class NVB_OT_helper_amt2psb(bpy.types.Operator):
    """Generate pseudobones from blender armature."""

    bl_idname = 'nvb.helper_amt2psb'
    bl_label = 'Generate Pseudo Bones'
    bl_options = {'UNDO'}

    prefix = ''
    generated = []

    def create_mesh(self, mvector, meshname):
        """TODO: DOC."""
        verts = [+0.0, +0.0, 0.0,
                 -0.1, -0.1, 0.1,
                 -0.1, +0.1, 0.1,
                 +0.1, -0.1, 0.1,
                 +0.1, +0.1, 0.1,
                 +0.0, +0.0, 1.0]
        faces = [0, 1, 2, 0,
                 0, 2, 4, 0,
                 0, 4, 3, 0,
                 0, 3, 1, 0,
                 4, 2, 5, 0,
                 3, 4, 5, 0,
                 2, 1, 5, 0,
                 1, 3, 5, 0]
        mesh = bpy.data.meshes.new(meshname)
        # Create Verts
        mesh.vertices.add(len(verts)/3)
        mesh.vertices.foreach_set('co', verts)
        # Create Faces
        mesh.tessfaces.add(len(faces)/4)
        mesh.tessfaces.foreach_set('vertices_raw', faces)
        mesh.validate()
        rot = mathutils.Vector((0, 0, 1)).rotation_difference(mvector)
        mesh.transform(mathutils.Matrix.Rotation(rot.angle, 4, rot.axis))
        mesh.transform(mathutils.Matrix.Scale(mvector.length, 4))
        mesh.update()
        return mesh

    def generate_bones(self, amb, psb_parent=None):
        """Creates a pseusobone (mesh) object from an armature bone."""
        # name for newly created mesh = pseudo bone
        psb_name = self.prefix + amb.name
        if amb.parent:
            psb_head = amb.head_local - amb.parent.head_local
            psb_tail = amb.tail_local - amb.parent.head_local
        else:
            psb_head = amb.head_local
            psb_tail = amb.tail_local
        # Create the mesh for the pseudo bone
        mesh = self.create_mesh(psb_tail-psb_head, psb_name)
        # Create object holding the mesh
        psb = bpy.data.objects.new(psb_name, mesh)
        psb.location = psb_head
        psb.parent = psb_parent
        bpy.context.scene.objects.link(psb)
        self.generated.append([amb.name, psb])
        for c in amb.children:
            self.generate_bones(c, psb)

    def transfer_animations(self, armature, amt_bone_name, psb):
        """TODO: DOC."""
        def insert_kfp(fcu, kfp_frames, kfp_data, dp, dp_dim):
            # Add keyframes to fcurves
            kfp = [fcu[i].keyframe_points for i in range(dp_dim)]
            list(map(lambda x: x.add(len(kfp_data)), kfp))
            # Set values for all keyframe points
            for i in range(len(kfp_data)):
                frm = kfp_frames[i]
                val = kfp_data[i]
                for j in range(dp_dim):
                    p = kfp[j][i]
                    p.co = frm, val[j]
                    p.interpolation = 'LINEAR'
            list(map(lambda c: c.update(), fcu))

        def convert_loc(amt, posebone, kfvalues, cmat=mathutils.Matrix()):
            mats = [cmat * mathutils.Matrix.Translation(v) for v in kfvalues]
            mats = [amt.convert_space(posebone, m, 'LOCAL_WITH_PARENT',
                    'LOCAL') for m in mats]
            return [list(m.to_translation()) for m in mats]

        def convert_axan(amt, posebone, kfvalues, cmat=mathutils.Matrix()):
            mats = [cmat *
                    mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4()
                    for v in kfvalues]
            quats = [amt.convert_space(posebone, m, 'LOCAL_WITH_PARENT',
                     'LOCAL').to_quaternion() for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def convert_quat(amt, posebone, kfvalues, cmat=mathutils.Matrix()):
            mats = [cmat * mathutils.Quaternion(v).to_matrix().to_4x4()
                    for v in kfvalues]
            mats = [amt.convert_space(posebone, m, 'LOCAL_WITH_PARENT',
                    'LOCAL') for m in mats]
            return [list(m.to_quaternion()) for m in mats]

        def convert_eul(amt, posebone, kfvalues, cmat=mathutils.Matrix()):
            mats = [cmat * mathutils.Euler(v, 'XYZ').to_matrix().to_4x4()
                    for v in kfvalues]
            mats = [amt.convert_space(posebone, m, 'LOCAL_WITH_PARENT',
                    'LOCAL') for m in mats]
            # Euler Filter
            euls = []
            e = posebone.rotation_euler
            for m in mats:
                e = m.to_euler('XYZ', e)
                euls.append(e)
            return euls

        amt_action = armature.animation_data.action
        # Get posebone for coordinate transformation
        amt_posebone = armature.pose.bones[amt_bone_name]
        psb.rotation_mode = amt_posebone.rotation_mode
        # Get animation data, create if needed.
        if not psb.animation_data:
            psb.animation_data_create()
        # Get action, create if needed.
        psb_action = psb.animation_data.action
        if not psb_action:
            psb_action = bpy.data.actions.new(name=psb.name)
            psb_action.use_fake_user = True
            psb.animation_data.action = psb_action
        # All fcurves of the armature
        source_fcu = amt_action.fcurves
        # Copy rotation keyframes
        dp_list = [('rotation_axis_angle', 4, convert_axan),
                   ('rotation_quaternion', 4, convert_quat),
                   ('rotation_euler', 3, convert_eul),
                   ('location', 3, convert_loc)]
        for psb_dp, dp_dim, convert_func in dp_list:
            amt_dp = 'pose.bones["' + amt_bone_name + '"].' + psb_dp
            amt_fcu = [source_fcu.find(amt_dp, i) for i in range(dp_dim)]
            if amt_fcu.count(None) < 1:
                # Get keyed frames
                frames = list(set().union(
                    *[[k.co[0] for k in amt_fcu[i].keyframe_points]
                      for i in range(dp_dim)]))
                frames.sort()
                values = [[amt_fcu[i].evaluate(f)
                          for i in range(dp_dim)] for f in frames]
                # Convert from armature bone space to pseudobone space
                convert_func(armature, amt_posebone, values)
                # Create fcurves for pseudo bone
                psb_fcu = [psb_action.fcurves.new(psb_dp, i)
                           for i in range(dp_dim)]
                # Add keyframes to fcurves
                insert_kfp(psb_fcu, frames, values, psb_dp, dp_dim)

    @classmethod
    def poll(self, context):
        """Prevent execution if no armature is selected."""
        obj = context.object
        return obj and (obj.type == 'ARMATURE')

    def execute(self, context):
        """Create pseudo bones"""
        armature = context.object
        # Create an extra root object for the armature
        psb_root = None
        if False:
            psb_root = bpy.data.objects.new(armature.name, None)
            psb_root.location = armature.location
            context.scene.objects.link(psb_root)
        # Create Pseudo bones
        for amb in armature.data.bones:
            if not amb.parent:
                self.generate_bones(amb, psb_root)
        # Transfer animations
        if armature.nvb.helper_amt_copyani:
            if armature.animation_data and armature.animation_data.action:
                    for amb_name, psb in self.generated:
                        self.transfer_animations(armature, amb_name, psb)
        return {'FINISHED'}


class NVB_OT_helper_psb2amt(bpy.types.Operator):
    """Generate armature from pseudo bones."""

    bl_idname = 'nvb.helper_psb2amt'
    bl_label = 'Generate Armature'

    # Dummys with these names are ignored
    psb_ignore = ['hand', 'head', 'head_hit', 'hhit', 'impact', 'impc',
                  'ground', 'grnd', 'handconjure', 'headconjure',
                  'lhand', 'rhand', 'lforearm', 'rforearm']
    # Saved settings from aurora root
    auto_connect = False
    # Generated bones
    generated = []

    def can_connect(self, obj):
        """Determine whether the bone belonging to this object can be
           connected to it's parent."""
        # If location is animated the bone cannot be connected
        if obj.animation_data:
            action = obj.animation_data.action
            if action:
                if 'location' in [fcu.data_path for fcu in action.fcurves]:
                    return False
        return self.auto_connect

    def is_pbone(self, obj):
        """TODO: doc."""
        oname = obj.name
        # Ignore skinmeshes and walkmeshes
        if (obj.nvb.meshtype == nvb_def.Meshtype.SKIN) or \
           (obj.nvb.meshtype == nvb_def.Meshtype.AABB) or \
           (obj.nvb.meshtype == nvb_def.Meshtype.EMITTER):
            return False
        # Some objects like impact nodes can never be pseudo bones
        if obj.type == 'EMPTY':
            # Match objects ending with '.XYZ' numbers as well
            matches = [re.fullmatch(s+'(\.\d+)?', oname)
                       for s in self.psb_ignore]
            if matches.count(None) < len(matches):
                return False
            if obj.nvb.emptytype != nvb_def.Emptytype.DUMMY:
                return False
        return True

    def generate_bones(self, amt, obj, amt_bone_parent=None,
                       parent_mat=mathutils.Matrix()):
        """TODO: doc."""
        def convert_loc(obj, pmat):
            mat = obj.matrix_parent_inverse * obj.matrix_basis
            dc_pm = pmat.decompose()
            mat = mathutils.Matrix.Translation(dc_pm[0]) * mat
            return mat
        # Calculate head (relative to parent head)
        obj_mat = convert_loc(obj, parent_mat)
        bhead = obj_mat.translation
        # Calculate tail (relative to head)
        btail = bhead + mathutils.Vector([0.0, 0.2, 0.0])  # For Empties
        valid_children = [c for c in obj.children if self.is_pbone(c)]
        if valid_children:
            # Multiple children: Calculate centroid
            clocs = [convert_loc(c, obj_mat).translation
                     for c in valid_children]
            btail = sum(clocs, mathutils.Vector())/len(valid_children)
        else:
            # No children: Generate location from mesh bounding box
            if obj.type == 'MESH':
                btail = 2 * (sum((mathutils.Vector(p) for p in obj.bound_box),
                             mathutils.Vector()) / 8) + bhead
        # Create armature bone
        amt_bone = amt.data.edit_bones.new(obj.name)
        amt_bone.roll = 0
        amt_bone.head = bhead
        if amt_bone_parent:
            amt_bone.parent = amt_bone_parent
            # Merge head with parent tail if distance is short enough
            if (amt_bone_parent.tail - amt_bone.head).length <= 0.01:
                amt_bone.head = amt_bone_parent.tail
                amt_bone.use_connect = self.can_connect(obj)
        amt_bone.tail = btail
        # Save values for animation transfer
        dc_ml = obj.matrix_local.decompose()
        cmat = obj.matrix_parent_inverse
        cmat = mathutils.Matrix.Translation(dc_ml[0]).inverted() * cmat
        self.generated.append([obj, amt_bone.name, cmat.copy()])
        # Create children
        for c in valid_children:
            self.generate_bones(amt, c, amt_bone, obj_mat)

    def transfer_animations(self, armature, psb, amt_bone_name, cmat):
        """TODO: DOC."""
        def insert_kfp(fcu, kfp_frames, kfp_data, dp, dp_dim):
            # Add keyframes to fcurves
            kfp = [fcu[i].keyframe_points for i in range(dp_dim)]
            list(map(lambda x: x.add(len(kfp_data)), kfp))
            # Set values for all keyframe points
            for i in range(len(kfp_data)):
                frm = kfp_frames[i]
                val = kfp_data[i]
                for j in range(dp_dim):
                    p = kfp[j][i]
                    p.co = frm, val[j]
                    p.interpolation = 'LINEAR'
            list(map(lambda c: c.update(), fcu))

        def convert_loc(amt, posebone, kfvalues, cmat):
            mats = [cmat * mathutils.Matrix.Translation(v) for v in kfvalues]
            mats = [amt.convert_space(posebone, m, 'LOCAL_WITH_PARENT',
                    'LOCAL') for m in mats]
            return [list(m.to_translation()) for m in mats]

        def convert_axan(amt, posebone, kfvalues, cmat):
            mats = [cmat *
                    mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4()
                    for v in kfvalues]
            quats = [amt.convert_space(posebone, m, 'LOCAL_WITH_PARENT',
                     'LOCAL').to_quaternion() for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def convert_quat(amt, posebone, kfvalues, cmat):
            mats = [cmat * mathutils.Quaternion(v).to_matrix().to_4x4()
                    for v in kfvalues]
            mats = [amt.convert_space(posebone, m, 'LOCAL_WITH_PARENT',
                    'LOCAL') for m in mats]
            return [list(m.to_quaternion()) for m in mats]

        def convert_eul(amt, posebone, kfvalues, cmat):
            mats = [cmat * mathutils.Euler(v, 'XYZ').to_matrix().to_4x4()
                    for v in kfvalues]
            mats = [amt.convert_space(posebone, m, 'LOCAL_WITH_PARENT',
                    'LOCAL') for m in mats]
            # Euler Filter
            euls = []
            e = posebone.rotation_euler
            for m in mats:
                e = m.to_euler('XYZ', e)
                euls.append(e)
            return euls

        if amt_bone_name not in armature.pose.bones:
            return
        amt_posebone = armature.pose.bones[amt_bone_name]
        amt_posebone.rotation_mode = psb.rotation_mode
        # Gather rotation and location keyframe points
        # Their coordinates need to be adjusted to use them with bones
        amt_action = armature.animation_data.action
        if psb.animation_data and psb.animation_data.action:
            source_fcu = psb.animation_data.action.fcurves
            # Copy rotation keyframes
            dp_list = [('rotation_axis_angle', 4, convert_axan),
                       ('rotation_quaternion', 4, convert_quat),
                       ('rotation_euler', 3, convert_eul),
                       ('location', 3, convert_loc)]
            for dp, dp_dim, convert_func in dp_list:
                psb_fcu = [source_fcu.find(dp, i) for i in range(dp_dim)]
                if psb_fcu.count(None) < 1:
                    amt_dp = 'pose.bones["' + amt_bone_name + '"].' + dp
                    # Get keyed frames
                    frames = list(set().union(
                        *[[k.co[0] for k in psb_fcu[i].keyframe_points]
                          for i in range(dp_dim)]))
                    frames.sort()
                    values = [[psb_fcu[i].evaluate(f)
                              for i in range(dp_dim)] for f in frames]
                    # Convert from pseudo-bone to armature-bone space
                    values = convert_func(armature, amt_posebone, values, cmat)
                    # Create fcurves for armature
                    amt_fcu = [nvb_utils.get_fcurve(amt_action, amt_dp, i)
                               for i in range(dp_dim)]
                    # Add keyframes to fcurves
                    insert_kfp(amt_fcu, frames, values, dp, dp_dim)

    @classmethod
    def poll(self, context):
        """Prevent execution if no root was found."""
        aurora_root = nvb_utils.get_obj_aurora_root(context.object)
        return (aurora_root is not None)

    def execute(self, context):
        """Create the armature"""
        aurora_root = nvb_utils.get_obj_aurora_root(context.object)
        self.auto_connect = aurora_root.nvb.helper_amt_connect
        self.generated = []
        # Get source for armature
        if aurora_root.nvb.helper_amt_source == 'ALL':
            psb_root = aurora_root
        else:
            psb_root = context.object
        # Create armature
        bpy.ops.object.add(type='ARMATURE', location=psb_root.location)
        armature = context.scene.objects.active
        armature.name = aurora_root.name + '.armature'
        armature.rotation_mode = psb_root.rotation_mode
        # Create the bones
        bpy.ops.object.mode_set(mode='EDIT')
        for child in psb_root.children:
            if self.is_pbone(child):
                self.generate_bones(armature, child)
        context.scene.update()
        bpy.ops.object.mode_set(mode='OBJECT')
        # Copy animations
        if aurora_root.nvb.helper_amt_copyani:
            bpy.ops.object.mode_set(mode='POSE')
            # Get or create animation data and action
            if not armature.animation_data:
                armature.animation_data_create()
            if not armature.animation_data.action:
                amt_action = bpy.data.actions.new(name=armature.name)
                armature.animation_data.action = amt_action
            # Copy animation to every bone
            for psb, amb_name, cmat in self.generated:
                self.transfer_animations(armature, psb, amb_name, cmat)
            bpy.ops.object.mode_set(mode='OBJECT')
        del self.generated
        return {'FINISHED'}


class NVB_OT_anim_clone(bpy.types.Operator):
    """Clone animation and add it to the animation list"""

    bl_idname = 'nvb.anim_clone'
    bl_label = 'Clone animation'

    @classmethod
    def poll(cls, context):
        """Prevent execution if no rootdummy was found."""
        rootdummy = nvb_utils.get_obj_aurora_root(context.object)
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
                # For compatibility with older blender versions
                try:
                    fc.update()
                except AttributeError:
                    pass

    def execute(self, context):
        """Clone the animation."""
        rootd = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def execute(self, context):
        """Set the timeline to this animation."""
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
        return (rootDummy is not None)

    def execute(self, context):
        """Create the animation"""
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 1)
        return False

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
        animList = rootDummy.nvb.animList

        return len(animList) > 0

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
        if rootDummy is not None:
            animList = rootDummy.nvb.animList
            if len(animList) > 0:
                anim = animList[rootDummy.nvb.animListIdx]
                eventList = anim.eventList
                return len(eventList) > 0
        return False

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
        anim = rootDummy.nvb.animList[rootDummy.nvb.animListIdx]
        eventList = anim.eventList
        eventIdx = anim.eventListIdx

        eventList.remove(eventIdx)
        if eventIdx > 0:
            eventIdx = eventIdx - 1

        return {'FINISHED'}


class NVB_OT_animevent_move(bpy.types.Operator):
    """Move an item in the event list"""

    bl_idname = 'nvb.animevent_move'
    bl_label = 'Move an item in the event  list'

    direction = bpy.props.EnumProperty(items=(('UP', 'Up', ''),
                                              ('DOWN', 'Down', '')))

    @classmethod
    def poll(self, context):
        """Enable only if the list isn't empty."""
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
        if rootDummy is not None:
            animList = rootDummy.nvb.animList
            if len(animList) > 0:
                anim = animList[rootDummy.nvb.animListIdx]
                eventList = anim.eventList
                return len(eventList) > 0
        return False

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.get_obj_aurora_root(context.object)
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
        rootDummy = nvb_utils.get_obj_aurora_root(obj)
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


class NVB_OT_helper_genwok(bpy.types.Operator):
    """Load all materials for aabb walkmeshes for the selected object"""

    bl_idname = "nvb.helper_genwok"
    bl_label = "Load walkmesh materials"

    def execute(self, context):
        """Delete all current materials and add walkmesh materials."""
        obj = context.object
        if obj and (obj.type == 'MESH'):
            # Remove all material slots
            for i in range(len(obj.material_slots)):
                bpy.ops.object.material_slot_remove()
            # Add wok materials
            nvb_utils.create_wok_materials(obj.data)
        else:
            self.report({'ERROR'}, 'A mesh must be selected.')
            return {'CANCELLED'}

        return {'FINISHED'}


class NVB_OT_helper_node_setup(bpy.types.Operator):
    """Helper to add missing walkmesh objects and dummys."""

    bl_idname = "nvb.helper_node_setup"
    bl_label = "Setup Nodes"

    def create_dummys(self, ddata, prefix, parent, scene, obj_list=[]):
        if not obj_list:
            return
        for suffix, loc in ddata:
            existing = [o for o in obj_list if o.name.endswith(suffix)]
            existing_names = [o.name for o in existing]
            newname = prefix + suffix
            if newname in existing_names:
                # Adjust name and parent for existing objects
                for obj in existing:
                    if obj.name != newname:
                        # Avoid renaming to same name (results in .001 suffix)
                        obj.name = newname
                    obj.parent = parent
            else:
                # Create missing dummies
                obj = bpy.data.objects.new(newname, None)
                obj.location = loc
                obj.parent = parent
                scene.objects.link(obj)

    def create_wok(self, mdlroot, scene):
        """Adds necessary (walkmesh) objects to mdlRoot."""
        def create_wok_mesh(meshname):
            """Ge the bounding box for all object in the mesh."""
            verts = [(+5.0,  5.0, 0.0),
                     (+5.0, -5.0, 0.0),
                     (-5.0, +5.0, 0.0),
                     (-5.0, +5.0, 0.0)]
            faces = [1, 0, 2, 3]
            mesh = bpy.data.meshes.new(meshname)
            # Create Verts
            mesh.vertices.add(4)
            mesh.vertices.foreach_set('co', verts)
            # Create Faces
            mesh.tessfaces.add(1)
            mesh.tessfaces.foreach_set('vertices_raw', faces)
            mesh.validate()
            mesh.update()
            return mesh

        # Add a plane for the wok
        objname = mdlroot.name + '_wok'
        mesh = create_wok_mesh(objname)
        nvb_utils.create_wok_materials(mesh)
        obj = bpy.data.objects.new(objname, mesh)
        obj.nvb.meshtype = nvb_def.Meshtype.AABB
        obj.location = (0.0, 0.0, 0.0)
        obj.parent = mdlroot
        scene.objects.link(obj)

    def create_pwk(self, mdlroot, scene):
        """Adds necessary (walkmesh) objects to mdlRoot."""
        def get_prefix(mdlroot):
            basename = mdlroot.name
            dpos = basename[::-1].find('_')
            if dpos >= 0:
                return basename[-1*dpos:]
            return basename[-3:]

        def get_mdl_bbox(mdlroot):
            """Ge the bounding box for all object in the mesh."""
            verts = [(-0.5, -0.5, 0.0),
                     (-0.5, -0.5, 2.0),
                     (-0.5, 0.5, 0.0),
                     (-0.5, 0.5, 2.0),
                     (0.5, -0.5, 0.0),
                     (0.5, -0.5, 2.0),
                     (0.5, 0.5, 0.0),
                     (0.5, 0.5, 2.0)]
            faces = [[0, 1, 3, 2],
                     [2, 3, 7, 6],
                     [6, 7, 5, 4],
                     [1, 0, 4, 5],
                     [4, 0, 2, 6],
                     [7, 3, 1, 5]]
            return (verts, faces)

        def create_pwk_mesh(meshname, verts, faces):
            """Get the default mesh for a generic door."""
            mesh = bpy.data.meshes.new(meshname)
            # Create Verts
            mesh.vertices.add(len(verts))
            mesh.vertices.foreach_set('co', [co for v in verts for co in v])
            # Create Faces
            mesh.tessfaces.add(len(faces))
            mesh.tessfaces.foreach_set('vertices_raw',
                                       [i for f in faces for i in f])
            mesh.validate()
            mesh.update()
            return mesh

        prefix = get_prefix(mdlroot)
        # Find or create walkmesh root
        wkmroot = nvb_utils.findWkmRoot(mdlroot, nvb_def.Walkmeshtype.PWK)
        newname = mdlroot.name + '_pwk'
        if wkmroot:
            # Adjust existing object
            if wkmroot.name != newname:
                wkmroot.name = newname
            wkmroot.parent = mdlroot
        else:
            # make a new one
            wkmroot = bpy.data.objects.new(newname, None)
            wkmroot.nvb.emptytype = nvb_def.Emptytype.PWK
            wkmroot.parent = mdlroot
            scene.objects.link(wkmroot)
        # Get all children of the mdlroot (to check existing objects)
        obj_list = []
        nvb_utils.getAllChildren(mdlroot, obj_list)
        # FROM HERE ON: Walkmesh objects - all parented to wkmroot
        # Adjust name and parent of exising mesh(es)
        meshlist = [o for o in obj_list if o.name.endswith('_wg')]
        for obj in meshlist:
            newname = mdlroot.name + '_wg'
            if obj.name != newname:
                obj.name = newname
            obj.parent = wkmroot
        # Create missing mesh
        meshname = mdlroot.name + '_wg'
        if meshname not in bpy.data.objects:
            verts, faces = get_mdl_bbox(mdlroot)
            mesh = create_pwk_mesh(meshname, verts, faces)
            obj = bpy.data.objects.new(meshname, mesh)
            obj.parent = wkmroot
            scene.objects.link(obj)
        # Create dummys
        dummy_data = [['_pwk_use01', (0.0, -1.0, 0.0)],
                      ['_pwk_use02', (0.0, +1.0, 0.0)]]
        self.create_dummys(dummy_data, prefix, wkmroot, scene, obj_list)
        # FROM HERE ON: Special objects - all parented to mdlroot
        # Create special dummys
        dummy_data = [['_hand', (0.5, 0.0, 1.0)],
                      ['_head', (0.0, 0.0, 2.0)],
                      ['_head_hit', (0.0, 0.0, 2.2)],
                      ['_impact', (0.0, 0.0, 1.0)],
                      ['_ground', (0.0, 0.0, 0.0)]]
        self.create_dummys(dummy_data, prefix, mdlroot, scene, obj_list)

    def create_dwk(self, mdlroot, scene):
        """Add necessary (walkmesh) objects to mdlRoot."""
        def create_dwk_mesh(meshname):
            """Generate the default (walk)mesh for a generic door."""
            verts = [2.0, -0.1, 0.0,
                     0.0, -0.1, 0.0,
                     2.0, -0.1, 3.0,
                     0.0, -0.1, 3.0,
                     2.0,  0.1, 0.0,
                     0.0,  0.1, 0.0,
                     2.0,  0.1, 3.0,
                     0.0,  0.1, 3.0]
            faces = [3, 7, 5, 1,
                     7, 3, 2, 6,
                     7, 6, 4, 5,
                     2, 0, 4, 6,
                     1, 0, 2, 3]
            mesh = bpy.data.meshes.new(meshname)
            # Create Verts
            mesh.vertices.add(8)
            mesh.vertices.foreach_set('co', verts)
            # Create Faces
            mesh.tessfaces.add(5)
            mesh.tessfaces.foreach_set('vertices_raw', faces)
            mesh.validate()
            mesh.update()
            return mesh

        def create_sam_mesh(meshname):
            """Generate the default SAM mesh for a generic door."""
            verts = [-1.0, 0.0, 0.0,
                     +1.0, 0.0, 0.0,
                     -1.0, 0.0, 3.0,
                     +1.0, 0.0, 3.0]
            faces = [1, 0, 2, 3]
            mesh = bpy.data.meshes.new(meshname)
            # Create Verts
            mesh.vertices.add(4)
            mesh.vertices.foreach_set('co', verts)
            # Create Faces
            mesh.tessfaces.add(1)
            mesh.tessfaces.foreach_set('vertices_raw', faces)
            mesh.validate()
            mesh.update()
            return mesh

        prefix = mdlroot.name[-2:]
        # Find or create walkmesh root (wkmroot)
        wkmroot = nvb_utils.findWkmRoot(mdlroot, nvb_def.Walkmeshtype.DWK)
        print(wkmroot)
        newname = mdlroot.name + '_dwk'
        if wkmroot:
            # Adjust existing
            if wkmroot.name != newname:
                # Avoid renaming to same name (results in '.001' suffix)
                wkmroot.name = newname
            wkmroot.parent = mdlroot
        else:
            # Make a new one
            wkmroot = bpy.data.objects.new(newname, None)
            wkmroot.nvb.emptytype = nvb_def.Emptytype.DWK
            wkmroot.parent = mdlroot
            scene.objects.link(wkmroot)
        # Get all children of the mdlroot (to check existing objects)
        obj_list = []
        nvb_utils.getAllChildren(mdlroot, obj_list)
        # FROM HERE ON: Walkmesh objects - all parented to wkmroot
        # Create walkmesh dummys
        # Parented to wkmroot!
        dummy_data = [['_DWK_dp_open1_01', (0.2, -2.0, 0.0)],
                      ['_DWK_dp_open2_01', (0.2, +2.0, 0.0)],
                      ['_DWK_dp_closed_01', (0.3, -0.7, 0.0)],
                      ['_DWK_dp_closed_02', (0.3, +0.7, 0.0)],
                      ['_DWK_dp_open1_02', (0.2, -2.0, 0.0)],  # optional
                      ['_DWK_dp_open2_02', (0.2, +2.0, 0.0)],  # optional
                      ['_DWK_use01', (0.0, -0.7, 0.0)],
                      ['_DWK_use02', (0.0, +0.7, 0.0)]]
        self.create_dummys(dummy_data, prefix, wkmroot, scene, obj_list)
        # Create (walk)meshes
        mesh_data = [['_DWK_wg_closed', (0.0, 0.0, 0.0)],
                     ['_DWK_wg_open1', (0.0, 0.0, -1.3962633609771729)],
                     ['_DWK_wg_open2', (0.0, 0.0, 1.3962633609771729)]]
        for suffix, rot in mesh_data:
            newname = prefix + suffix  # the correct name
            # Adjust existing objects
            existing = [o for o in obj_list if o.name.endswith(suffix)]
            for obj in existing:
                if obj.name != newname:
                    obj.name = newname
                obj.parent = wkmroot
            # Create missing objects
            if newname not in bpy.data.objects:
                mesh = create_dwk_mesh(newname)
                obj = bpy.data.objects.new(newname, mesh)
                obj.location = (-1.0, 0.0, 0.0)
                obj.rotation_euler = mathutils.Euler(rot)
                obj.parent = wkmroot
                scene.objects.link(obj)
        # FROM HERE ON: Special objects - parented to mdlroot
        # Create SAM object
        if 'sam' in bpy.data.objects:
            obj = bpy.data.objects['sam']
        else:
            mesh = create_sam_mesh('sam')
            obj = bpy.data.objects.new('sam', mesh)
            obj.location = (0.0, 0.0, 0.0)
            scene.objects.link(obj)
        obj.parent = mdlroot
        obj.nvb.shadow = False
        # Create special dummys
        dummy_data = [['_hand', (0.0, 0.0, 1.0)],
                      ['_head', (0.0, 0.0, 2.5)],
                      ['_hhit', (0.0, 0.0, 3.0)],
                      ['_impc', (0.0, 0.0, 1.5)],
                      ['_grnd', (0.0, 0.0, 0.0)]]
        self.create_dummys(dummy_data, prefix, mdlroot, scene, obj_list)

    @classmethod
    def poll(self, context):
        """Prevent execution if no object is selected."""
        return (context.object is not None)

    def execute(self, context):
        """Create Walkmesh root and objects."""
        mdlroot = nvb_utils.get_obj_aurora_root(context.object)
        if not mdlroot:
            self.report({'ERROR'}, 'No MDL root')
            return {'CANCELLED'}
        scene = bpy.context.scene
        wkmtype = mdlroot.nvb.helper_node_mdltype
        if wkmtype == nvb_def.Walkmeshtype.PWK:
            self.create_pwk(mdlroot, scene)
        elif wkmtype == nvb_def.Walkmeshtype.DWK:
            self.create_dwk(mdlroot, scene)
        elif wkmtype == nvb_def.Walkmeshtype.WOK:
            self.create_wok(mdlroot, scene)
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
        mdlRoot = nvb_utils.get_obj_aurora_root(context.object)
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
                return {'FINISHED'}
            else:
                self.report({'INFO'}, 'Duplicate Name')
                return {'CANCELLED'}
        else:
            self.report({'INFO'}, 'Empty Name')
            return {'CANCELLED'}


class NVB_OT_helper_scale(bpy.types.Operator):
    """TODO: DOC"""
    bl_idname = "nvb.helper_scale"
    bl_label = "Scale"

    def execute(self, context):
        """TODO: DOC."""
        # obj = context.object
        # aur_root = nvb_utils.get_aurora_root(obj)

        # return {'CANCELLED'}
        return {'FINISHED'}


class NVB_OT_mtr_generate(bpy.types.Operator):
    """Generate a new Text Block containing from the current material."""
    bl_idname = "nvb.mtr_generate"
    bl_label = "Generate MTR"

    @classmethod
    def poll(self, context):
        """Enable only if mtrs are used and in text mode."""
        mat = context.material
        return mat is not None and mat.nvb.usemtr and mat.nvb.mtrsrc == 'TEXT'

    def execute(self, context):
        """TODO: DOC."""
        material = context.material
        if not material:
            self.report({'ERROR'}, 'Error: No material.')
            return {'CANCELLED'}
        mtr = nvb_mtr.Mtr()
        # Either change existing or create new text block
        if material.nvb.mtrtext and material.nvb.mtrtext in bpy.data.texts:
            txtBlock = bpy.data.texts[material.nvb.mtrtext]
            mtr.loadTextBlock(txtBlock)
        else:
            if material.nvb.mtrname:
                txtname = material.nvb.mtrname + '.mtr'
            else:
                txtname = material.name + '.mtr'
            txtBlock = bpy.data.texts.new(txtname)
            material.nvb.mtrtext = txtBlock.name
        options = nvb_def.ExportOptions()
        asciiLines = nvb_mtr.Mtr.generateAscii(material, options)
        txtBlock.clear()
        txtBlock.write('\n'.join(asciiLines))
        # Report
        self.report({'INFO'}, 'Created ' + txtBlock.name)
        return {'FINISHED'}


class NVB_OT_mtr_embed(bpy.types.Operator):
    """Embed the MTR file into the blend file by creating a Text block"""
    bl_idname = "nvb.mtr_embed"
    bl_label = "Embed MTR"

    @classmethod
    def poll(self, context):
        """Enable only if mtrs are used and a path is set."""
        mat = context.material
        if mat is not None and mat.nvb.usemtr:
            return mat.nvb.mtrpath != ''
        return False

    def execute(self, context):
        """TODO: DOC."""
        material = context.material
        if not material:
            self.report({'ERROR'}, 'Error: No material.')
            return {'CANCELLED'}
        # Get the previously stored filepath
        if not material.nvb.mtrpath:
            self.report({'ERROR'}, 'Error: No path to file.')
            return {'CANCELLED'}
        bpy.ops.text.open(filepath=material.nvb.mtrpath, internal=True)
        return {'FINISHED'}


class NVB_OT_mtr_open(bpy.types.Operator):
    """Open material file"""
    bl_idname = "nvb.mtr_open"
    bl_label = "Open MTR"

    filename_ext = '.mtr'
    filter_glob = bpy.props.StringProperty(default='*.mtr', options={'HIDDEN'})
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")

    @classmethod
    def poll(self, context):
        """Enable only if mtrs are used and in file mode."""
        mat = context.material
        if mat is not None:
            return mat.nvb.usemtr and mat.nvb.mtrsrc == 'FILE'
        return False

    def execute(self, context):
        material = context.material
        if not material:
            self.report({'ERROR'}, 'Error: No material.')
            return {'CANCELLED'}
        if material.nvb.mtrsrc != 'FILE':
            self.report({'ERROR'}, 'Error: Wrong MTR mode.')
            return {'CANCELLED'}
        if not self.filepath:
            self.report({'ERROR'}, 'Error: No path to file.')
            return {'CANCELLED'}
        mtrpath, mtrfilename = os.path.split(self.filepath)
        # Load mtr
        mtr = nvb_mtr.Mtr(material.name)
        if not mtr.loadFile(self.filepath):
            self.report({'ERROR'}, 'Error: Invalid file.')
            return {'CANCELLED'}
        options = nvb_def.ImportOptions()
        options.filepath = self.filepath
        mtr.create(material, options)
        self.report({'INFO'}, 'Loaded ' + mtrfilename)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        # Open browser, take reference to 'self'
        # read the path to selected file,
        # put path in declared string type data structure self.filepath

        return {'RUNNING_MODAL'}


class NVB_OT_mtr_reload(bpy.types.Operator):
    """Reload MTR, update current material"""
    bl_idname = "nvb.mtr_reload"
    bl_label = "Reload MTR"

    def reload_file(self, material):
        """Reload mtr file from disk."""
        if not material.nvb.mtrpath:
            self.report({'ERROR'}, 'Error: No path to file.')
            return {'CANCELLED'}
        mtrpath = material.nvb.mtrpath
        # Reload
        mtr = nvb_mtr.Mtr(material.name)
        if not mtr.loadFile(mtrpath):
            self.report({'ERROR'}, 'Error: No data.')
            return {'CANCELLED'}
        options = nvb_def.ImportOptions()
        options.filepath = material.nvb.mtrpath  # for image search
        mtr.create(material, options)
        self.report({'INFO'}, 'Reloaded ' + os.path.split(mtrpath)[1])
        return {'FINISHED'}

    def reload_text(self, material):
        """Reload mtr data from Blender text block."""
        if not material.nvb.mtrtext:
            self.report({'ERROR'}, 'Error: No text block.')
            return {'CANCELLED'}
        if material.nvb.mtrtext not in bpy.data.texts:
            self.report({'ERROR'}, 'Error: ' + material.nvb.mtrtext +
                        ' does not exist.')
            return {'CANCELLED'}
        txt_block = bpy.data.texts[material.nvb.mtrtext]
        # Reload data
        mtr = nvb_mtr.Mtr(material.name)
        if not mtr.loadTextBlock(txt_block):
            self.report({'ERROR'}, 'Error: No data.')
            return {'CANCELLED'}
        mtr.filepath = material.nvb.mtrpath  # Restore filepath
        options = nvb_def.ImportOptions()
        options.filepath = material.nvb.mtrpath  # for image search
        mtr.create(material, options)
        self.report({'INFO'}, 'Reloaded ' + txt_block.name)
        return {'FINISHED'}

    @classmethod
    def poll(self, context):
        """Enable only if mtrs are used."""
        mat = context.material
        if mat is not None and mat.nvb.usemtr:
            return (mat.nvb.mtrsrc == 'FILE' and mat.nvb.mtrpath != '') or \
                   (mat.nvb.mtrsrc == 'TEXT' and mat.nvb.mtrtext != '')
        return False

    def execute(self, context):
        """TODO: DOC."""
        material = context.material
        if not material:
            self.report({'ERROR'}, 'Error: No material.')
            return {'CANCELLED'}
        if material.nvb.mtrsrc == 'FILE':
            return self.reload_file(material)
        elif material.nvb.mtrsrc == 'TEXT':
            return self.reload_text(material)


class NVB_OT_mtrparam_new(bpy.types.Operator):
    """Add a new item to the parameter list"""

    bl_idname = 'nvb.mtrparam_new'
    bl_label = 'Add a new parameter'

    @classmethod
    def poll(self, context):
        """Enable only if there is a material."""
        mat = context.material
        return mat is not None and mat.nvb.usemtr

    def execute(self, context):
        """TODO: DOC."""
        material = context.material
        plist = material.nvb.mtrparam_list

        param = plist.add()
        if param.ptype == 'int':
            param.pvalue = '1'
        elif param.ptype == 'float':
            param.pvalue = '1.0 1.0 1.0'
        return {'FINISHED'}


class NVB_OT_mtrparam_delete(bpy.types.Operator):
    """Delete the selected parameter from the parameter list"""

    bl_idname = 'nvb.mtrparam_delete'
    bl_label = 'Delete a parameter'

    @classmethod
    def poll(self, context):
        """Enable only if the list isn't empty."""
        mat = context.material
        if mat is not None and mat.nvb.usemtr:
            return len(mat.nvb.mtrparam_list) > 0
        return False

    def execute(self, context):
        """TODO: DOC."""
        mat = context.material
        plist = mat.nvb.mtrparam_list
        plist_idx = mat.nvb.mtrparam_list_idx

        plist.remove(plist_idx)
        if plist_idx > 0:
            plist_idx = plist_idx - 1
        return {'FINISHED'}
