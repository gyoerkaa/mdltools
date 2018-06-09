"""Contains Blender Operators for dealing with armatures"""

import re

import bpy
import mathutils

from . import nvb_def
from . import nvb_utils


class NVB_OT_amt_anims2psb(bpy.types.Operator):
    """Apply current pose as restpose and adjust animation."""

    bl_idname = 'nvb.amt_anims2psb'
    bl_label = 'Copy Animations'
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
        amt_data = dict()
        for posebone in armature.pose.bones:
            amt_data[posebone.basename] = posebone.matrix_basis.copy()
        # Adjust animations
        if armature.animation_data and armature.animation_data.action:
            for posebone in armature.pose.bones:
                op_mat = amt_data[posebone.name]
                cmat = op_mat.inverted()
                self.adjust_animations(armature, posebone, cmat)
        bpy.ops.object.mode_set(mode='OBJECT')
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


class NVB_OT_amt_amt2psb(bpy.types.Operator):
    """Generate pseudobones from blender armature."""

    bl_idname = 'nvb.amt_amt2psb'
    bl_label = 'Generate Pseudo Bones'
    bl_options = {'UNDO'}

    mats_edit_bone = dict()  # armature bone name => edit_bone.matrix
    amb_psb_pairs = []  # (armature bone name, pseudo bone name) tuples
    scene = None

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
        if amb.parent:
            psb_head = amb.head_local - amb.parent.head_local
            psb_tail = amb.tail_local - amb.parent.head_local
        else:
            psb_head = amb.head_local
            psb_tail = amb.tail_local
        # Create the mesh for the pseudo bone
        mesh = self.create_mesh(psb_tail-psb_head, amb.name)
        # Create object holding the mesh
        psb = bpy.data.objects.new(amb.name, mesh)
        psb.location = psb_head
        psb.parent = psb_parent
        bpy.context.scene.objects.link(psb)
        # Create matrix for animation conversion
        # amt_eb = amt.data.edit_bones[amt_bone.name]
        # amt_eb_m = amt_eb.matrix.to_3x3().to_4x4().copy()
        self.amb_psb_pairs.append([amb.name, psb.name])
        self.mats_edit_bone[amb.name] = amb.matrix_local.copy()
        for c in amb.children:
            self.generate_bones(c, psb)

    def transfer_animations(self, amt, amb_name, psb_name):
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

        def convert_loc(amt, posebone, kfvalues, mat_eb):
            mats = [mathutils.Matrix.Translation(v) for v in kfvalues]
            if posebone.parent:
                cmat = mathutils.Matrix.Translation((0, 0, -1))
            else:
                cmat = mathutils.Matrix()
            mats = [mat_eb * m * mat_eb.to_3x3().to_4x4().inverted() * cmat
                    for m in mats]
            # mats = [amt.convert_space(posebone, m, 'LOCAL', 'WORLD') *
            #         mat_eb.to_3x3().to_4x4().inverted() for m in mats]
            # mats = [pw.inverted() * m for pw, m in zip(mats_pw, mats)]
            return [list(m.to_translation()) for m in mats]

        def convert_axan(amt, posebone, kfvalues, mat_eb):
            mats = [mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4()
                    for v in kfvalues]
            mat_eb_inverted = mat_eb.to_3x3().to_4x4().inverted()
            mats = [mat_eb * m * mat_eb_inverted for m in mats]
            quats = [m.to_quaternion() for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def convert_quat(amt, posebone, kfvalues, mat_eb):
            mats = [mathutils.Quaternion(v).to_matrix().to_4x4()
                    for v in kfvalues]
            mat_eb_inverted = mat_eb.to_3x3().to_4x4().inverted()
            mats = [mat_eb * m * mat_eb_inverted for m in mats]
            quats = [m.to_quaternion() for m in mats]
            return quats

        def convert_eul(amt, posebone, kfvalues, mat_eb):
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

        amt_action = amt.animation_data.action
        # Get posebone and pseudobone
        amt_posebone = amt.pose.bones[amb_name]
        psb = bpy.data.objects[psb_name]
        # Get animation data, create if needed.
        if not psb.animation_data:
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
        dp_list = [('location', 3, convert_loc)]
        rot_dp = {'AXIS_ANGLE': ('rotation_axis_angle', 4, convert_axan),
                  'QUATERNION': ('rotation_quaternion', 4, convert_quat)}
        dp_list.append(rot_dp.get(
            psb.rotation_mode, ('rotation_euler', 3, convert_eul)))
        # Transfer keyframes
        mat_eb = self.mats_edit_bone[amb_name]
        for psb_dp, dp_dim, convert_func in dp_list:
            amt_dp = 'pose.bones["' + amb_name + '"].' + psb_dp
            amt_fcu = [source_fcu.find(amt_dp, i) for i in range(dp_dim)]
            if amt_fcu.count(None) < 1:
                # Get keyed frames
                frames = list(set().union(
                    *[[k.co[0] for k in amt_fcu[i].keyframe_points]
                      for i in range(dp_dim)]))
                frames.sort()
                values = []
                values = [[amt_fcu[i].evaluate(f)
                          for i in range(dp_dim)] for f in frames]
                # Convert from armature bone space to pseudobone space
                values = convert_func(amt, amt_posebone, values, mat_eb)
                # Create fcurves for pseudo bone
                psb_fcu = [psb_action.fcurves.new(psb_dp, i)
                           for i in range(dp_dim)]
                # Add keyframes to fcurves
                insert_kfp(psb_fcu, frames, values, psb_dp, dp_dim)

    def add_constraints(self, amt, amt_bone_name, psb):
        """Apply transform constraint to pseudo bone from armature bone."""
        con = psb.constraints.new('COPY_TRANSFORMS')
        con.target = amt
        con.subtarget = amt_bone_name
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
        self.scene = context.scene
        self.amb_psb_pairs = []
        self.mats_edit_bone = dict()
        # Create an extra root object for the armature
        psb_root = None
        if False:
            psb_root = bpy.data.objects.new(armature.name, None)
            psb_root.location = armature.location
            context.scene.objects.link(psb_root)
        # Create Pseudo bones
        bpy.ops.object.mode_set(mode='EDIT')
        for amb in armature.data.bones:
            if not amb.parent:
                self.generate_bones(amb, psb_root)
        bpy.ops.object.mode_set(mode='OBJECT')
        context.scene.update()
        # Transfer animations
        if armature.nvb.helper_amt_animcopy:
            if armature.animation_data and armature.animation_data.action:
                for amb_name, psb_name in self.amb_psb_pairs:
                    self.transfer_animations(armature, amb_name, psb_name)
                context.scene.update()
        return {'FINISHED'}


class NVB_OT_amt_psb2amt(bpy.types.Operator):
    """Generate armature from pseudo bones."""

    bl_idname = 'nvb.amt_psb2amt'
    bl_label = 'Generate Armature'
    bl_options = {'UNDO'}

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
            dc_pm = pmat.decompose()
            return mathutils.Matrix.Translation(dc_pm[0]) * \
                obj.matrix_parent_inverse * obj.matrix_basis
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
            # Convert to Euler (with filter)
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
        anim_mode = aurora_root.nvb.helper_amt_animode
        if anim_mode != 'OFF':
            bpy.ops.object.mode_set(mode='POSE')
            # Get or create animation data and action
            if not armature.animation_data:
                armature.animation_data_create()
            if not armature.animation_data.action:
                amt_action = bpy.data.actions.new(name=armature.name)
                armature.animation_data.action = amt_action
            if anim_mode == 'KFP':  # Copy keyframes to bones
                for psb, amb_name, cmat in self.generated:
                    self.transfer_animations(armature, psb, amb_name, cmat)
            elif anim_mode == 'CON':  # Add constraints to bones
                for psb, amb_name, _ in self.generated:
                    self.add_constraints(armature, amb_name, psb)
            bpy.ops.object.mode_set(mode='OBJECT')
        del self.generated
        return {'FINISHED'}
