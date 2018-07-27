"""Contains Blender Operators for dealing with armatures"""

import re

import bpy
import mathutils

from . import nvb_def
from . import nvb_utils


class NVB_OT_amt_anims2psb(bpy.types.Operator):
    """Copy animations to pseudobones"""

    bl_idname = 'nvb.amt_anims2psb'
    bl_label = 'Copy Animations'
    bl_options = {'UNDO'}

    mats_edit_bone = dict()  # armature bone name => edit_bone.matrix
    amb_psb_pairs = []  # (armature bone name, pseudo bone name) tuples

    def get_psb_list(self, amb, psb_root):
        """Creates a list of pseudobones for this armature."""
        psb_list = [psb_root]
        nvb_utils.get_children_recursive(psb_root, psb_list)
        if amb.name in [n.name for n in psb_list]:
            # Create matrix for animation conversion
            self.amb_psb_pairs.append([amb.name, amb.name])
            self.mats_edit_bone[amb.name] = amb.matrix_local.copy()
        for c in amb.children:
            self.get_psb_list(c, psb_root)

    def transfer_animations(self, amt, amb_name, psb_name):
        """TODO: DOC."""
        def insert_kfp(fcu, frames, values, dp, dp_dim):
            # Add keyframes to fcurves
            kfp = [fcu[i].keyframe_points for i in range(dp_dim)]
            list(map(lambda x: x.add(len(values)), kfp))
            # Set values for all keyframe points
            for i, (frm, val) in enumerate(zip(frames, values)):
                for d in range(dp_dim):
                    p = kfp[d][i]
                    p.co = frm, val[d]
                    p.interpolation = 'LINEAR'
            list(map(lambda c: c.update(), fcu))

        def convert_loc(amt, posebone, psb, kfvalues, mat_eb):
            vecs = [mathutils.Vector(v) for v in kfvalues]
            quat = mat_eb.inverted().to_quaternion()
            list(map(lambda v: v.rotate(quat), vecs))
            return [psb.location + v for v in vecs]

        def convert_axan(amt, posebone, psb, kfvalues, mat_eb):
            mats = [mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4()
                    for v in kfvalues]
            mat_eb_inverted = mat_eb.to_3x3().to_4x4().inverted()
            mats = [mat_eb * m * mat_eb_inverted for m in mats]
            quats = [m.to_quaternion() for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def convert_quat(amt, posebone, psb, kfvalues, mat_eb):
            mats = [mathutils.Quaternion(v).to_matrix().to_4x4()
                    for v in kfvalues]
            mat_eb_inverted = mat_eb.to_3x3().to_4x4().inverted()
            mats = [mat_eb * m * mat_eb_inverted for m in mats]
            quats = [m.to_quaternion() for m in mats]
            return quats

        def convert_eul(amt, posebone, psb, kfvalues, mat_eb):
            mats = [mathutils.Euler(v, 'XYZ').to_matrix().to_4x4()
                    for v in kfvalues]
            mat_eb_inverted = mat_eb.to_3x3().to_4x4().inverted()
            mats = [mat_eb * m * mat_eb_inverted for m in mats]
            # Convert to Euler (with filter)
            euls = []
            e = posebone.rotation_euler
            for m in mats:
                e = m.to_euler('XYZ', e)
                euls.append(e)
            return euls

        def get_data_paths(rot_mode):
            """Get a list of all data paths depending on rotation mode."""
            dp_list = []
            # (data_path, dimension, conversion function, default value)
            dp_list.append(('location', 3, convert_loc, (0.0, 0.0, 0.0)))
            if rot_mode == 'AXIS_ANGLE':
                dp_list.append(('rotation_axis_angle', 4,
                                convert_axan, (1.0, 0.0, 0.0, 0.0)))
            elif rot_mode == 'QUATERNION':
                dp_list.append(('rotation_quaternion', 4,
                                convert_quat, (1.0, 0.0, 0.0, 0.0)))
            else:
                dp_list.append(('rotation_euler', 3,
                               convert_eul, (0.0, 0.0, 0.0)))
            return dp_list

        amt_action = amt.animation_data.action
        # Get posebone and pseudobone
        amt_posebone = amt.pose.bones[amb_name]
        psb = bpy.data.objects[psb_name]
        # Clear animation data and create new one
        psb.animation_data_clear()
        psb.animation_data_create()
        # Get action, create if needed.
        psb_action = psb.animation_data.action
        if not psb_action:
            psb_action = bpy.data.actions.new(name=psb.name)
            # psb_action.use_fake_user = True
            psb.animation_data.action = psb_action
        # All fcurves of the armature
        source_fcu = amt_action.fcurves
        # Build data paths depending on rotation mode
        psb.rotation_mode = amt_posebone.rotation_mode
        dp_list = get_data_paths(psb.rotation_mode)
        # Transfer keyframes
        mat_eb = self.mats_edit_bone[amb_name]
        for psb_dp, dp_dim, kfp_convert, kfp_dfl in dp_list:
            amt_dp = 'pose.bones["' + amb_name + '"].' + psb_dp
            amt_fcu = [source_fcu.find(amt_dp, i) for i in range(dp_dim)]
            if amt_fcu.count(None) < dp_dim:  # disregard empty animations
                # Get keyed frames
                frames = list(set().union(
                    *[[k.co[0] for k in amt_fcu[i].keyframe_points]
                      for i in range(dp_dim) if amt_fcu[i]]))
                frames.sort()
                values = [[amt_fcu[i].evaluate(f) if amt_fcu[i] else kfp_dfl[i]
                           for i in range(dp_dim)] for f in frames]
                # Convert from armature bone space to pseudobone space
                values = kfp_convert(amt, amt_posebone, psb, values, mat_eb)
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
        amt = context.object
        self.scene = context.scene
        self.amb_psb_pairs = []
        self.mats_edit_bone = dict()
        mdl_base = amt.nvb.util_psb_anim_target
        if not mdl_base:
            self.report({'INFO'}, 'Invalid Target')
            return {'CANCELLED'}
        # Get Pseudo bones
        bpy.ops.object.mode_set(mode='EDIT')
        for amb in amt.data.bones:
            if not amb.parent:
                self.get_psb_list(amb, mdl_base)
        bpy.ops.object.mode_set(mode='OBJECT')
        # Transfer animations
        if amt.animation_data and amt.animation_data.action:
            for amb_name, psb_name in self.amb_psb_pairs:
                self.transfer_animations(amt, amb_name, psb_name)
            context.scene.update()
        return {'FINISHED'}


class NVB_OT_amt_apply_pose(bpy.types.Operator):
    """Apply current pose as restpose and adjust animation."""

    bl_idname = 'nvb.amt_apply_pose'
    bl_label = 'Apply Current Pose'
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
            # Convert to Euler (with filter)
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
                      for i in range(dp_dim) if fcu[i]]))
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


class NVB_OT_amt_amt2psb(bpy.types.Operator):
    """Generate pseudobones from blender armature."""

    bl_idname = 'nvb.amt_amt2psb'
    bl_label = 'Generate Pseudo Bones'
    bl_options = {'UNDO'}

    mats_edit_bone = dict()  # armature bone name => edit_bone.matrix
    amb_psb_pairs = []  # (armature bone name, pseudo bone name) tuples
    scene = None

    def create_mesh(self, mvector, meshname):
        """Create a mesh with the shape of a blender bone."""
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
        # name for newly created mesh = pseudo-bone
        if amb.parent:
            psb_head = amb.head_local - amb.parent.head_local
            psb_tail = amb.tail_local - amb.parent.head_local
        else:
            psb_head = amb.head_local
            psb_tail = amb.tail_local
        # Create the mesh for the pseudo bone
        mesh = None
        if amb.nvb.util_psb_btype != 'EMT':
            mesh = self.create_mesh(psb_tail-psb_head, amb.name)
        # Create object holding the mesh
        psb = bpy.data.objects.new(amb.name, mesh)
        psb.location = psb_head
        psb.parent = psb_parent
        psb.nvb.render = False
        bpy.context.scene.objects.link(psb)
        # Create matrix for animation conversion
        self.amb_psb_pairs.append([amb.name, psb.name])
        self.mats_edit_bone[amb.name] = amb.matrix_local.copy()
        for c in amb.children:
            self.generate_bones(c, psb)

    def transfer_animations(self, amt, amt_action, amb_name, psb_name,
                            frame_offset=0):
        """TODO: DOC."""
        def insert_kfp(fcu, frames, values, dp, dp_dim):
            # Add keyframes to fcurves
            kfp_list = [fcu[d].keyframe_points for d in range(dp_dim)]
            kfp_cnt = [len(fcu[d].keyframe_points) for d in range(dp_dim)]
            list(map(lambda x: x.add(len(values)), kfp_list))
            # Set values for all keyframe points
            for i, (frm, val) in enumerate(zip(frames, values)):
                for d in range(dp_dim):
                    kfp = kfp_list[d][i+kfp_cnt[d]]
                    kfp.co = frm, val[d]
                    kfp.interpolation = 'LINEAR'
            list(map(lambda c: c.update(), fcu))

        def convert_loc2(amt, posebone, psb, kfvalues, mat_eb):
            vecs = [mathutils.Vector(v) for v in kfvalues]
            quat = mat_eb.inverted().to_quaternion()
            list(map(lambda v: v.rotate(quat), vecs))
            return [psb.location + v for v in vecs]

        def convert_loc(amt, posebone, psb, kfvalues, mat_eb):
            mats = [mathutils.Matrix.Translation(v) for v in kfvalues]
            if posebone.parent:
                cmat = mathutils.Matrix.Translation((0, 0, -1))
            else:
                cmat = mathutils.Matrix()
            mat_eb_inverted = mat_eb.to_3x3().to_4x4().inverted()
            mats = [mat_eb * m * mat_eb_inverted * cmat for m in mats]
            return [list(m.to_translation()) for m in mats]

        def convert_axan(amt, posebone, psb, kfvalues, mat_eb):
            mats = [mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4()
                    for v in kfvalues]
            mat_eb_inverted = mat_eb.to_3x3().to_4x4().inverted()
            mats = [mat_eb * m * mat_eb_inverted for m in mats]
            quats = [m.to_quaternion() for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def convert_quat(amt, posebone, psb, kfvalues, mat_eb):
            mats = [mathutils.Quaternion(v).to_matrix().to_4x4()
                    for v in kfvalues]
            mat_eb_inverted = mat_eb.to_3x3().to_4x4().inverted()
            mats = [mat_eb * m * mat_eb_inverted for m in mats]
            quats = [m.to_quaternion() for m in mats]
            return quats

        def convert_eul(amt, posebone, psb, kfvalues, mat_eb):
            mats = [mathutils.Euler(v, 'XYZ').to_matrix().to_4x4()
                    for v in kfvalues]
            mat_eb_inverted = mat_eb.to_3x3().to_4x4().inverted()
            mats = [mat_eb * m * mat_eb_inverted for m in mats]
            # Convert to Euler (with filter)
            euls = []
            e = posebone.rotation_euler
            for m in mats:
                e = m.to_euler('XYZ', e)
                euls.append(e)
            return euls

        def get_data_paths(rot_mode):
            """Get a list of all data paths depending on rotation mode."""
            dp_list = []
            # (data_path, dimension, group_name,
            #  conversion function, default value)
            dp_list.append(('location', 'Location', 3,
                            convert_loc, (0.0, 0.0, 0.0)))
            if rot_mode == 'AXIS_ANGLE':
                dp_list.append(('rotation_axis_angle', 'Rotation', 4,
                                convert_axan, (1.0, 0.0, 0.0, 0.0)))
            elif rot_mode == 'QUATERNION':
                dp_list.append(('rotation_quaternion', 'Rotation', 4,
                                convert_quat, (1.0, 0.0, 0.0, 0.0)))
            else:
                dp_list.append(('rotation_euler', 'Rotation', 3,
                               convert_eul, (0.0, 0.0, 0.0)))
            return dp_list

        # Get posebone and pseudobone
        amt_posebone = amt.pose.bones[amb_name]
        psb = bpy.data.objects[psb_name]  # Pseudo-bone
        mat_eb = self.mats_edit_bone[amb_name]  # Edit-bone matrix
        # Get animation data, create if needed.
        if not psb.animation_data:
            psb.animation_data_create()
        # Get action, create if needed.
        psb_action = psb.animation_data.action
        if not psb_action:
            psb_action = bpy.data.actions.new(name=psb.name)
            psb.animation_data.action = psb_action
        # All fcurves of the armature
        source_fcu = amt_action.fcurves
        # Build data paths depending on rotation mode
        psb.rotation_mode = amt_posebone.rotation_mode
        dp_list = get_data_paths(psb.rotation_mode)
        # Transfer keyframes
        for psb_dp, group_name, dp_dim, kfp_convert, kfp_dfl in dp_list:
            amt_dp = 'pose.bones["' + amb_name + '"].' + psb_dp
            amt_fcu = [source_fcu.find(amt_dp, i) for i in range(dp_dim)]
            if amt_fcu.count(None) < dp_dim:  # disregard empty animations
                # Get keyed frames
                frames = list(set().union(
                    *[[k.co[0] for k in amt_fcu[i].keyframe_points]
                      for i in range(dp_dim) if amt_fcu[i]]))
                frames.sort()
                values = [[amt_fcu[i].evaluate(f) if amt_fcu[i] else kfp_dfl[i]
                           for i in range(dp_dim)] for f in frames]
                # values = [[amt_fcu[i].evaluate(f) for i in range(dp_dim)]
                #           for f in frames]
                # Convert from armature bone space to pseudobone space
                values = kfp_convert(amt, amt_posebone, psb, values, mat_eb)
                # Create fcurves for pseudo bone
                psb_fcu = [nvb_utils.get_fcurve(psb_action, psb_dp, i,
                                                group_name)
                           for i in range(dp_dim)]
                # Add offset to frames (do it here AFTER getting values)
                if frame_offset != 0:
                    frames = [f + frame_offset for f in frames]
                # Add keyframes to fcurves
                insert_kfp(psb_fcu, frames, values, psb_dp, dp_dim)

    def add_constraints(self, amt, amb_name, psb_name):
        """Apply transform constraint to pseudo bone from armature bone."""
        psb = bpy.data.objects[psb_name]

        con = psb.constraints.new('COPY_ROTATION')
        con.target = amt
        con.subtarget = amb_name
        con.target_space = 'LOCAL_WITH_PARENT'
        con.owner_space = 'WORLD'

        con = psb.constraints.new('COPY_LOCATION')
        con.target = amt
        con.subtarget = amb_name
        con.target_space = 'WORLD'
        con.owner_space = 'WORLD'

    @classmethod
    def poll(self, context):
        """Prevent execution if no armature is selected."""
        obj = context.object
        return obj and (obj.type == 'ARMATURE')

    def execute(self, context):
        """Create pseudo bones and copy animations"""
        armature = context.object
        addon = context.user_preferences.addons[__package__]
        self.scene = context.scene
        self.amb_psb_pairs = []
        self.mats_edit_bone = dict()
        # Parent-less bones will be parented to this object (or not if None)
        psb_parent = None
        # Create an mdl_base holding animation data
        mdl_base = None
        if addon.preferences.util_psb_insert_base or \
           addon.preferences.util_psb_anim_mode == 'NLA_STRIPS' or \
           addon.preferences.util_psb_anim_mode == 'NLA_TRACKS':
            mdl_base = bpy.data.objects.new('aurora_base', None)
            context.scene.objects.link(mdl_base)
            psb_parent = mdl_base
        # Create an extra root object for the armature
        if addon.preferences.util_psb_insert_root:
            psb_root = bpy.data.objects.new('rootdummy', None)
            psb_root.parent = mdl_base
            psb_root.location = armature.location
            context.scene.objects.link(psb_root)
            psb_parent = psb_root
        # Create Pseudo bones
        bpy.ops.object.mode_set(mode='EDIT')
        for amt_bone in armature.data.bones:
            if not amt_bone.parent:
                self.generate_bones(amt_bone, psb_parent)
        bpy.ops.object.mode_set(mode='OBJECT')
        context.scene.update()
        # Transfer animations
        anim_mode = addon.preferences.util_psb_anim_mode
        if anim_mode != 'NONE':
            # Only copy frames from current action (if any)
            if anim_mode == 'ACTION':
                if armature.animation_data and armature.animation_data.action:
                    action = armature.animation_data.action
                    for amb_name, psb_name in self.amb_psb_pairs:
                        self.transfer_animations(armature, action,
                                                 amb_name, psb_name, 0)
            # Use blender data to create mdl animations
            else:
                animation_list = []
                # Grab strips from active track, each strip is an animation
                if anim_mode == 'NLA_STRIPS':
                    nla_track = armature.animation_data.nla_tracks.active
                    for nla_strip in nla_track.strips:
                        if not nla_strip.mute:
                            anim_name = nla_strip.name
                            anim_length = nla_strip.action_frame_end - \
                                nla_strip.action_frame_start
                            action_list = [nla_strip.action]
                            animation_list.append(
                                [anim_name, anim_length, action_list])
                # Grab strips from all tracks, each track is an animation
                elif anim_mode == 'NLA_TRACKS':
                    for nla_track in armature.animation_data.nla_tracks:
                        if not nla_track.mute:
                            anim_name = nla_track.name
                            anim_length = max([s.action_frame_end
                                               for s in nla_track.strips
                                               if not s.mute])
                            action_list = [s.action for s in nla_track.strips
                                           if not s.mute]
                            animation_list.append(
                                [anim_name, anim_length, action_list])
                # Transfer keyframes and create animations
                for anim_name, anim_length, action_list in animation_list:
                    new_anim = nvb_utils.create_anim_list_item(mdl_base)
                    new_anim.name = anim_name
                    new_anim.root = mdl_base.name
                    new_anim.frameEnd = new_anim.frameStart + anim_length
                    print(new_anim.name)
                    print(new_anim.frameStart)
                    for action in action_list:
                        for amb_name, psb_name in self.amb_psb_pairs:
                            self.transfer_animations(armature, action,
                                                     amb_name, psb_name,
                                                     new_anim.frameStart)
            context.scene.update()
        return {'FINISHED'}


class NVB_OT_amt_psb2amt(bpy.types.Operator):
    """Generate armature from pseudo bones."""

    bl_idname = 'nvb.amt_psb2amt'
    bl_label = 'Generate Armature'
    bl_options = {'UNDO'}

    # Dummys (Empties) with these names are ignored
    excluded_psb_names = ['hand', 'head', 'head_hit', 'hhit', 'impact', 'impc',
                          'ground', 'grnd', 'handconjure', 'headconjure',
                          'lhand', 'rhand', 'lforearm', 'rforearm']
    # Saved settings from aurora base
    auto_connect = False  # Connect bones when possible
    strip_name = False  # Strip trailing numbers from names
    split_action = False  # Split animation into multiple actions
    multi_track = False  # Create multiple NLA Tracks holding the actions
    # Generated bones
    generated = []

    def can_connect(self, obj, parent_dist):
        """Determine whether the bone belonging to this object can be
           connected to it's parent."""
        if parent_dist <= 0.01 and self.auto_connect:
            # If location is animated the bone cannot be connected
            if obj.animation_data:
                action = obj.animation_data.action
                if action:
                    dp_list = [fcu.data_path for fcu in action.fcurves]
                    return 'location' not in dp_list
            return True
        return False

    def is_psb(self, obj):
        """Return true if the object is a pseudo bone."""
        # Some objects like impact nodes can never be pseudo bones
        if obj.type == 'EMPTY':
            # Match objects ending with '.XYZ' numbers as well
            obj_name = obj.name
            matches = [re.fullmatch(s+'(\\.\\d+)?', obj_name)
                       for s in self.excluded_psb_names]
            if (matches.count(None) < len(matches)) or \
               (obj.nvb.emptytype != nvb_def.Emptytype.DUMMY):
                return False
        elif obj.type == 'MESH':
            # Ignore skinmeshes, emitters and walkmeshes
            if (obj.nvb.meshtype == nvb_def.Meshtype.SKIN) or \
               (obj.nvb.meshtype == nvb_def.Meshtype.AABB) or \
               (obj.nvb.meshtype == nvb_def.Meshtype.EMITTER):
                return False
        return True

    def generate_bones(self, amt, psb, amb_parent=None,
                       parent_mat=mathutils.Matrix()):
        """TODO: doc."""
        def convert_loc(obj, pmat):
            dc_pm = pmat.decompose()
            return mathutils.Matrix.Translation(dc_pm[0]) * \
                obj.matrix_parent_inverse * obj.matrix_basis
        # Calculate head (relative to parent head)
        psb_mat = convert_loc(psb, parent_mat)
        bhead = psb_mat.translation
        # Calculate tail (relative to head)
        btail = bhead + mathutils.Vector([0.0, 0.2, 0.0])  # For Empties
        valid_children = [c for c in psb.children if self.is_psb(c)]
        if valid_children:
            # Multiple children: Calculate centroid
            clocs = [convert_loc(c, psb_mat).translation
                     for c in valid_children]
            btail = sum(clocs, mathutils.Vector())/len(valid_children)
        else:
            # No children: Generate location from mesh bounding box
            if psb.type == 'MESH':
                btail = 2 * (sum((mathutils.Vector(p) for p in psb.bound_box),
                             mathutils.Vector()) / 8) + bhead
        # Create armature bone
        amb_name = psb.name
        if self.strip_name:
            amb_name = nvb_utils.strip_trailing_numbers(psb.name)
        amb = amt.data.edit_bones.new(amb_name)
        amb.roll = 0
        amb.head = bhead
        if amb_parent:
            amb.parent = amb_parent
            # Try to connect head with parent tail
            if self.can_connect(psb, (amb_parent.tail - amb.head).length):
                amb.head = amb_parent.tail
                amb.use_connect = True
        amb.tail = btail
        # Save values for animation transfer
        dc_ml = psb.matrix_local.decompose()
        cmat = psb.matrix_parent_inverse
        cmat = mathutils.Matrix.Translation(dc_ml[0]).inverted() * cmat
        self.generated.append([psb, amb.name, cmat.copy()])
        # Create children
        for c in valid_children:
            self.generate_bones(amt, c, amb, psb_mat)

    def transfer_animations(self, amt, amt_action, amt_bone_name, psb,
                            cmat, frame_range=None):
        """TODO: DOC."""
        def insert_kfp(fcu, frames, values, dp, dp_dim):
            # Add keyframes to fcurves
            kfp = [fcu[i].keyframe_points for i in range(dp_dim)]
            list(map(lambda x: x.add(len(values)), kfp))
            # Set values for all keyframe points
            for i, (frm, val) in enumerate(zip(frames, values)):
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
            # Convert to Euler (with filter)
            euls = []
            e = posebone.rotation_euler
            for m in mats:
                e = m.to_euler('XYZ', e)
                euls.append(e)
            return euls

        if amt_bone_name not in amt.pose.bones:
            return
        amt_posebone = amt.pose.bones[amt_bone_name]
        amt_posebone.rotation_mode = psb.rotation_mode
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
                    if frame_range:
                        min_frame, max_frame = frame_range
                        frames = list(set().union(
                            *[[k.co[0] for k in psb_fcu[i].keyframe_points
                              if min_frame <= k.co[0] <= max_frame]
                              for i in range(dp_dim) if psb_fcu[i]]))
                    else:
                        frames = list(set().union(
                            *[[k.co[0] for k in psb_fcu[i].keyframe_points]
                              for i in range(dp_dim) if psb_fcu[i]]))
                    frames.sort()
                    # Evaluate fcurve at keyed frames
                    values = [[psb_fcu[i].evaluate(f)
                              for i in range(dp_dim)] for f in frames]
                    # Convert from pseudo-bone to armature-bone space
                    values = convert_func(amt, amt_posebone, values, cmat)
                    # Create fcurves for armature
                    amt_fcu = [nvb_utils.get_fcurve(amt_action, amt_dp, i,
                                                    amt_bone_name)
                               for i in range(dp_dim)]
                    # Adjust for frame range
                    if frame_range:
                        min_frame = frame_range[0]
                        frames = [f - min_frame for f in frames]
                    # Add keyframes to fcurves
                    insert_kfp(amt_fcu, frames, values, dp, dp_dim)

    def add_constraints(self, amt, amt_bone_name, psb):
        """Apply transform constraint to pseudo bone from armature bone."""
        posebone = amt.pose.bones[amt_bone_name]

        con = posebone.constraints.new('COPY_ROTATION')
        con.target = psb
        con.target_space = 'WORLD'
        con.owner_space = 'LOCAL_WITH_PARENT'

        con = posebone.constraints.new('COPY_LOCATION')
        con.target = psb
        con.target_space = 'WORLD'
        con.owner_space = 'WORLD'

    @classmethod
    def poll(self, context):
        """Prevent execution if no root was found."""
        mdl_base = nvb_utils.get_obj_mdl_base(context.object)
        return (mdl_base is not None)

    def execute(self, context):
        """Create the armature"""
        mdl_base = nvb_utils.get_obj_mdl_base(context.object)
        addon = context.user_preferences.addons[__package__]

        self.auto_connect = addon.preferences.util_amt_connect
        self.strip_name = addon.preferences.util_amt_strip_name
        self.split_action = addon.preferences.util_amt_split_action
        self.multi_track = addon.preferences.util_amt_multi_track
        self.generated = []

        # Get source for armature
        if addon.preferences.util_amt_src == 'ALL':
            psb_root = mdl_base
        else:
            psb_root = context.object

        # Create armature
        bpy.ops.object.add(type='ARMATURE', location=psb_root.location)
        amt = context.scene.objects.active
        amt.name = mdl_base.name + '.armature'
        amt.rotation_mode = psb_root.rotation_mode

        # Create the bones
        bpy.ops.object.mode_set(mode='EDIT')
        for child in psb_root.children:
            if self.is_psb(child):
                self.generate_bones(amt, child)
        context.scene.update()
        bpy.ops.object.mode_set(mode='OBJECT')

        # Set bone properties for re-conversion to pseudo-bones
        for psb, amb_name, _ in self.generated:
            if psb.type == 'EMPTY':
                amt.data.bones[amb_name].nvb.util_psb_btype = 'EMT'
            else:
                amt.data.bones[amb_name].nvb.util_psb_btype = 'ME1'

        # Copy animations
        anim_mode = addon.preferences.util_amt_anim_mode
        if anim_mode != 'OFF':
            bpy.ops.object.mode_set(mode='POSE')
            if anim_mode == 'CON':  # Add constraints to bones
                for psb, amt_bone_name, _ in self.generated:
                    self.add_constraints(amt, amt_bone_name, psb)
            elif anim_mode == 'KFP':  # Copy keyframes to bones
                # Get or create animation data and action
                if not amt.animation_data:
                    amt.animation_data_create()
                action_list = []
                if self.split_action and mdl_base.nvb.animList:
                    for anim in mdl_base.nvb.animList:
                        action_name = amt.name + '.' + anim.name
                        action = bpy.data.actions.new(name=action_name)
                        interval = (anim.frameStart, anim.frameEnd)
                        action_list.append((anim.name, action, interval))
                else:
                    action = bpy.data.actions.new(name=amt.name)
                    action_list.append((amt.name, action, None))
                    amt.animation_data.action = action
                # Copy keyframes to action(s)
                for _, amt_action, frame_range in action_list:
                    for psb, amt_bname, cmat in self.generated:
                        self.transfer_animations(amt, amt_action, amt_bname,
                                                 psb, cmat, frame_range)
                if self.split_action:  # Create NLA tracks to hold actions
                    if self.multi_track:  # One NLA track per action
                        for anim_name, action, _ in action_list:
                            nla_track = amt.animation_data.nla_tracks.new()
                            nla_track.name = anim_name
                            nla_track.strips.new(action.name, 0, action)
                    else:  # Single NLA track for all actions
                        nla_track = amt.animation_data.nla_tracks.new()
                        nla_track.name = mdl_base.name
                        for anim_name, action, frame_range in action_list:
                            strip = nla_track.strips.new(
                                anim_name, frame_range[0], action)
                            strip.name = anim_name
                        amt.animation_data.nla_tracks.active = nla_track
            bpy.ops.object.mode_set(mode='OBJECT')
        del self.generated
        return {'FINISHED'}
