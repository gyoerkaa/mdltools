"""Contains misc. Blender Operators."""

import os
import re

import bpy
import mathutils

from . import nvb_def
from . import nvb_utils


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


class NVB_OT_helper_amt2psb(bpy.types.Operator):
    """Generate pseudobones from blender armature."""

    bl_idname = 'nvb.helper_amt2psb'
    bl_label = 'Generate Pseudo Bones'
    bl_options = {'UNDO'}

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

    def generate_bones(self, amt_bone, psb_parent=None):
        """Creates a pseusobone (mesh) object from an armature bone."""
        # name for newly created mesh = pseudo bone
        psb_name = amt_bone.name
        if amt_bone.parent:
            psb_head = amt_bone.head_local - amt_bone.parent.head_local
            psb_tail = amt_bone.tail_local - amt_bone.parent.head_local
        else:
            psb_head = amt_bone.head_local
            psb_tail = amt_bone.tail_local
        # Create the mesh for the pseudo bone
        mesh = self.create_mesh(psb_tail-psb_head, psb_name)
        # Create object holding the mesh
        psb = bpy.data.objects.new(psb_name, mesh)
        psb.location = psb_head
        psb.parent = psb_parent
        bpy.context.scene.objects.link(psb)
        # Create matrix for animation conversion
        cmat = mathutils.Matrix()
        if psb_parent:
            cmat = psb_parent.matrix_world
        cmat = cmat * psb.matrix_local
        cmat = cmat * amt_bone.matrix_local.inverted()
        self.generated.append([amt_bone.name, psb, cmat])
        for c in amt_bone.children:
            self.generate_bones(c, psb)

    def transfer_animations(self, armature, amt_bone_name, psb, cmat):
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

        def convert_loc(amt, posebone, kfvalues, psb, cmat):
            mats = [mathutils.Matrix.Translation(v) for v in kfvalues]
            mats = [amt.convert_space(posebone, m, 'LOCAL_WITH_PARENT',
                    'WORLD') for m in mats]
            mats = [psb.convert_space(None, m, 'WORLD',
                    'LOCAL') for m in mats]
            return [list(m.to_translation()) for m in mats]

        def convert_axan(amt, posebone, kfvalues, psb, cmat):
            mats = [cmat *
                    mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4()
                    for v in kfvalues]
            quats = [amt.convert_space(posebone, m, 'LOCAL_WITH_PARENT',
                     'LOCAL').to_quaternion() for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def convert_quat(amt, posebone, kfvalues, psb, cmat):
            mats = [cmat * mathutils.Quaternion(v).to_matrix().to_4x4()
                    for v in kfvalues]
            mats = [amt.convert_space(posebone, m, 'LOCAL_WITH_PARENT',
                    'LOCAL') for m in mats]
            return [list(m.to_quaternion()) for m in mats]

        def convert_eul(amt, posebone, kfvalues, psb, cmat):
            mats = [mathutils.Euler(v, 'XYZ').to_matrix().to_4x4()
                    for v in kfvalues]
            mats = [amt.convert_space(posebone, m, 'LOCAL_WITH_PARENT',
                    'WORLD') for m in mats]
            mats = [psb.convert_space(None, m, 'WORLD',
                    'LOCAL') for m in mats]
            # Convert to Euler (with filter)
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
                convert_func(armature, amt_posebone, values, psb, cmat)
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
        """Create pseudo bones and copy animations"""
        armature = context.object
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
        # Transfer animations
        if armature.nvb.helper_amt_copyani:
            if armature.animation_data and armature.animation_data.action:
                for amb_name, psb, cmat in self.generated:
                    self.transfer_animations(armature, amb_name, psb, cmat)
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

    bl_idname = 'nvb.helper_genwok'
    bl_label = 'Load walkmesh materials'

    @classmethod
    def poll(self, context):
        """Enable only if a Lamp is selected."""
        return (context.object and context.object.type == 'MESH')

    def execute(self, context):
        """Delete all current materials and add walkmesh materials."""
        obj = context.object
        # Remove all material slots
        for i in range(len(obj.material_slots)):
            bpy.ops.object.material_slot_remove()
        # Add wok materials
        nvb_utils.create_wok_materials(obj.data)
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

    def create_pwk(self, mdl_root, scene):
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

        prefix = get_prefix(mdl_root)
        # Find or create walkmesh root
        wkmroot = nvb_utils.find_wkm_root(mdl_root, nvb_def.Walkmeshtype.PWK)
        newname = mdl_root.name + '_pwk'
        if wkmroot:
            # Adjust existing object
            if wkmroot.name != newname:
                wkmroot.name = newname
            wkmroot.parent = mdl_root
        else:
            # make a new one
            wkmroot = bpy.data.objects.new(newname, None)
            wkmroot.nvb.emptytype = nvb_def.Emptytype.PWK
            wkmroot.parent = mdl_root
            scene.objects.link(wkmroot)
        # Get all children of the mdlroot (to check existing objects)
        obj_list = [mdl_root]
        nvb_utils.get_children_recursive(mdl_root, obj_list)
        # FROM HERE ON: Walkmesh objects - all parented to wkmroot
        # Adjust name and parent of exising mesh(es)
        meshlist = [o for o in obj_list if o.name.endswith('_wg')]
        for obj in meshlist:
            newname = mdl_root.name + '_wg'
            if obj.name != newname:
                obj.name = newname
            obj.parent = wkmroot
        # Create missing mesh
        meshname = mdl_root.name + '_wg'
        if meshname not in bpy.data.objects:
            verts, faces = get_mdl_bbox(mdl_root)
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
        self.create_dummys(dummy_data, prefix, mdl_root, scene, obj_list)

    def create_dwk(self, mdl_root, scene):
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

        prefix = mdl_root.name[-2:]
        # Find or create walkmesh root (wkmroot)
        wkmroot = nvb_utils.find_wkm_root(mdl_root, nvb_def.Walkmeshtype.DWK)
        newname = mdl_root.name + '_dwk'
        if wkmroot:
            # Adjust existing
            if wkmroot.name != newname:
                # Avoid renaming to same name (results in '.001' suffix)
                wkmroot.name = newname
            wkmroot.parent = mdl_root
        else:
            # Make a new one
            wkmroot = bpy.data.objects.new(newname, None)
            wkmroot.nvb.emptytype = nvb_def.Emptytype.DWK
            wkmroot.parent = mdl_root
            scene.objects.link(wkmroot)
        # Get all children of the mdlroot (to check existing objects)
        obj_list = [mdl_root]
        nvb_utils.get_children_recursive(mdl_root, obj_list)
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
        obj.parent = mdl_root
        obj.nvb.shadow = False
        # Create special dummys
        dummy_data = [['_hand', (0.0, 0.0, 1.0)],
                      ['_head', (0.0, 0.0, 2.5)],
                      ['_hhit', (0.0, 0.0, 3.0)],
                      ['_impc', (0.0, 0.0, 1.5)],
                      ['_grnd', (0.0, 0.0, 0.0)]]
        self.create_dummys(dummy_data, prefix, mdl_root, scene, obj_list)

    @classmethod
    def poll(self, context):
        """Prevent execution if no object is selected."""
        return context.object is not None

    def execute(self, context):
        """Create Walkmesh root and objects."""
        mdl_root = nvb_utils.get_obj_aurora_root(context.object)
        if not mdl_root:
            self.report({'ERROR'}, 'No MDL root')
            return {'CANCELLED'}
        scene = bpy.context.scene
        wkm_type = mdl_root.nvb.helper_node_mdltype
        if wkm_type == nvb_def.Walkmeshtype.PWK:
            self.create_pwk(mdl_root, scene)
        elif wkm_type == nvb_def.Walkmeshtype.DWK:
            self.create_dwk(mdl_root, scene)
        elif wkm_type == nvb_def.Walkmeshtype.WOK:
            self.create_wok(mdl_root, scene)
        self.report({'INFO'}, 'Created objects')
        return {'FINISHED'}


class NVB_OT_render_minimap(bpy.types.Operator):
    """Set up rendering for minimaps."""

    bl_idname = "nvb.render_minimap"
    bl_label = "Render Minimap"

    batch_mode = bpy.props.BoolProperty(
        name='Batch Mode',
        description='Renders pictures directly to render_dir',
        default=False)
    render_dir = bpy.props.StringProperty(
        name='Render Directory',
        description='Directors to render images to',
        default='')
    img_size = bpy.props.IntProperty(
        name='Image Size',
        description='Image Size',
        default=32, min=8)
    z_offset = bpy.props.FloatProperty(
        name='Camera Distance',
        description='Camera distance to ground',
        default=20.0, min=10.0)
    light_color = bpy.props.FloatVectorProperty(
        name='Light Color',
        description='Light Color',
        subtype='COLOR_GAMMA',
        default=(1.0, 1.0, 1.0),
        min=0.0, max=1.0,
        soft_min=0.0, soft_max=1.0)

    @classmethod
    def poll(self, context):
        """Prevent execution if no object is selected."""
        return True

    def setup_objects(self, root, scene):
        """Create camera and lamp objects."""
        # Setup Lamp
        lamp_name = 'mm_lamp'
        if lamp_name in scene.objects:
            mm_lamp = scene.objects[lamp_name]
        else:   # Check if present in db
            if lamp_name in bpy.data.objects:
                mm_lamp = bpy.data.objects[lamp_name]
            else:
                lamp_data = bpy.data.lamps.new(lamp_name, 'POINT')
                mm_lamp = bpy.data.objects.new(lamp_name, lamp_data)
            scene.objects.link(mm_lamp)
        mm_lamp.data.use_specular = False
        mm_lamp.data.color = self.light_color
        mm_lamp.data.falloff_type = 'CONSTANT'
        mm_lamp.data.distance = self.z_offset * 2.0
        mm_lamp.location = root.location
        mm_lamp.location.z += self.z_offset
        # Setup Camera
        cam_name = 'mm_cam'
        if cam_name in scene.objects:
            mm_cam = scene.objects[cam_name]
        else:   # Check if present in db
            if cam_name in bpy.data.objects:
                mm_cam = bpy.data.objects[cam_name]
            else:
                cam_data = bpy.data.cameras.new(cam_name)
                mm_cam = bpy.data.objects.new(cam_name, cam_data)
            scene.objects.link(mm_cam)
        mm_cam.data.type = 'ORTHO'
        mm_cam.data.ortho_scale = 10.0
        mm_cam.location = root.location
        mm_cam.location.z += self.z_offset

        return mm_cam, mm_lamp

    def setup_scene(self, scene):
        """Setup scene settings."""
        scene.render.alpha_mode = 'TRANSPARENT'
        scene.render.use_antialiasing = True
        scene.render.pixel_filter_type = 'BOX'
        scene.render.antialiasing_samples = '16'
        scene.render.use_shadows = False
        scene.render.use_envmaps = False
        scene.render.resolution_x = self.img_size
        scene.render.resolution_y = self.img_size
        scene.render.resolution_percentage = 100
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.image_settings.file_format = 'TARGA_RAW'

    def execute(self, context):
        """Create camera + lamp and Renders Minimap."""
        if self.batch_mode:
            # Get mdl roots
            root_list = []
            obj_list = bpy.context.scene.objects
            for obj in obj_list:
                root = nvb_utils.get_obj_aurora_root(obj)
                if root and (root not in root_list):
                    root_list.append(root)
            # Render each mdl
            scene = bpy.context.scene
            self.setup_scene(scene)
            for root in root_list:
                img_name = 'mi_' + root.name
                img_path = os.fsencode(os.path.join(self.render_dir, img_name))
                scene.render.filepath = img_path
                mm_cam, _ = self.setup_objects(root, scene)
                scene.camera = mm_cam
                bpy.ops.render.render(animation=False, write_still=True)
        else:
            # Get root from active mdl
            if not context.object:
                return {'CANCELLED'}
            root = nvb_utils.get_aurora_root(context.object)
            if not root:
                return {'CANCELLED'}
            # Setup Render
            scene = bpy.context.scene
            self.img_size = scene.render.resolution_x
            self.setup_scene(scene)
            mm_cam, _ = self.setup_objects(root, scene)
            scene.camera = mm_cam

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


class NVB_OT_helper_transform(bpy.types.Operator):
    """Apply translation and scale to the whole model and its animations"""
    bl_idname = "nvb.helper_transform"
    bl_label = "Apply Transform"

    def adjust_animations(self, obj, adj_mat):
        """TODO: DOC."""
        def adjust_loc(obj, kfvalues, adj_mat):
            trn, _, scl = adj_mat.decompose()
            vecs = [mathutils.Vector(val) for val in kfvalues]
            return [[x * y for x, y in zip(v + trn, scl)] for v in vecs]

        def adjust_axan(obj, kfvalues, adj_mat):
            mats = [mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4() *
                    adj_mat
                    for v in kfvalues]
            quats = [m.to_quaternion() for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def adjust_quat(obj, kfvalues, adj_mat):
            mats = [mathutils.Quaternion(v).to_matrix().to_4x4() * adj_mat
                    for v in kfvalues]
            return [list(m.to_quaternion()) for m in mats]

        def adjust_eul(obj, kfvalues, adj_mat):
            mats = [mathutils.Euler(v, 'XYZ').to_matrix().to_4x4() * adj_mat
                    for v in kfvalues]
            # Euler Filter
            euls = []
            e = obj.rotation_euler
            for m in mats:
                e = m.to_euler('XYZ', e)
                euls.append(e)
            return euls

        if not (obj.animation_data and obj.animation_data.action):
            return
        action = obj.animation_data.action
        source_fcu = action.fcurves
        dp_list = [('rotation_axis_angle', 4, adjust_axan),
                   ('rotation_quaternion', 4, adjust_quat),
                   ('rotation_euler', 3, adjust_eul),
                   ('location', 3, adjust_loc)]
        for dp, dp_dim, adjust_func in dp_list:
            fcu = [source_fcu.find(dp, i) for i in range(dp_dim)]
            if fcu.count(None) < 1:
                frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points]
                      for i in range(dp_dim)]))
                frames.sort()
                values = [[fcu[i].evaluate(f)
                          for i in range(dp_dim)] for f in frames]
                # Adjust kfp to new coordinates
                values = adjust_func(obj, values, adj_mat)
                # Write back adjusted kfp values
                for i in range(dp_dim):
                    single_vals = [v[i] for v in values]
                    data = [d for z in zip(frames, single_vals) for d in z]
                    fcu[i].keyframe_points.foreach_set('co', data)
                    fcu[i].update()

    def adjust_trans(self, obj, adj_mat):
        """Apply translation to immediate children only."""
        for c in obj.children:
            c.matrix_basis = c.matrix_basis * adj_mat
            self.adjust_animations(c, adj_mat)

    def adjust_scale(self, obj, adj_mat):
        """Apply scale to all children."""
        for c in obj.children:
            dcmp = c.matrix_basis.decompose()
            trans = mathutils.Matrix.Translation(dcmp[0] * adj_mat)
            rot = dcmp[1].to_matrix().to_4x4()
            scl = (mathutils.Matrix.Scale(dcmp[2][0], 4, [1, 0, 0]) *
                   mathutils.Matrix.Scale(dcmp[2][1], 4, [0, 1, 0]) *
                   mathutils.Matrix.Scale(dcmp[2][2], 4, [0, 0, 1]))
            c.matrix_basis = trans * rot
            # Apply to data
            if c.type == 'MESH':
                me = c.data
                for v in me.vertices:
                    v.co = v.co * adj_mat * scl
                me.update()
            self.adjust_animations(c, adj_mat * scl)
            self.adjust_scale(c, adj_mat * scl)

    def execute(self, context):
        """TODO: DOC."""
        root = nvb_utils.get_aurora_root(context.object)
        # Get translation and scale factors
        if True:  # Use transformations from root
            dcmp = root.matrix_basis.decompose()
            trans = mathutils.Matrix.Translation(dcmp[0])
            rot = dcmp[1].to_matrix().to_4x4()
            scl = (mathutils.Matrix.Scale(dcmp[2][0], 4, [1, 0, 0]) *
                   mathutils.Matrix.Scale(dcmp[2][1], 4, [0, 1, 0]) *
                   mathutils.Matrix.Scale(dcmp[2][2], 4, [0, 0, 1]))
            # Undo root Transformations
            root.matrix_basis = rot
        else:  # TODO: Use custom transformations
            trans = mathutils.Matrix()
            scl = mathutils.Matrix()
        self.adjust_trans(root, trans)
        self.adjust_scale(root, scl)
        context.scene.update()
        return {'FINISHED'}
