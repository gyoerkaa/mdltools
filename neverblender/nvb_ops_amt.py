"""Contains Blender Operators for dealing with armatures"""

import re

import bpy
import mathutils

from . import nvb_def
from . import nvb_utils


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
            mats = [cmat @ mathutils.Matrix.Translation(v) for v in kfvalues]
            return [list(m.to_translation()) for m in mats]

        def adjust_axan(amt, posebone, kfvalues, cmat):
            mats = [cmat @
                    mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4()
                    for v in kfvalues]
            quats = [m.to_quaternion() for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def adjust_quat(amt, posebone, kfvalues, cmat):
            mats = [cmat @ mathutils.Quaternion(v).to_matrix().to_4x4()
                    for v in kfvalues]
            return [list(m.to_quaternion()) for m in mats]

        def adjust_eul(amt, posebone, kfvalues, cmat):
            mats = [cmat @ mathutils.Euler(v, 'XYZ').to_matrix().to_4x4()
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
            fcu = [source_fcu.find(data_path=dp, index=i)
                   for i in range(dp_dim)]
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
        """Set current pose as restpose and adjust animations."""
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
    """Generate exportable bones from blender armature and copy animations."""

    bl_idname = 'nvb.amt_amt2psb'
    bl_label = 'Generate Pseudo Bones'
    bl_options = {'UNDO'}

    mats_edit_bone = dict()  # armature bone name => edit_bone.matrix
    amb_psb_pairs = []  # (armature bone name, pseudo bone name) tuples
    amt_bone_shapes = dict()  # armature bone name => pseudo-bone shape

    scene = None
    collection = None
    dummy_type = 'PLAIN_AXES'
    dummy_size = 0.5

    use_existing: bpy.props.BoolProperty(
        name='Use Existing Bones', default=False,
        description='Use existing pseudo-bones instead of creating new ones')

    def create_parent_objects(self, context, armature,
                              anim_mode, create_base, create_root):
        mdl_base = None
        psd_bone_root = None
        if anim_mode in ['NLA_STRIPS', 'NLA_TRACKS'] or create_base:
            mdl_base = bpy.data.objects.new(armature.name+'.mdl', None)
            self.collection.objects.link(mdl_base)
            psd_bone_root = mdl_base
        if create_root:
            psd_bone_root = bpy.data.objects.new('rootdummy', None)
            psd_bone_root.parent = mdl_base
            psd_bone_root.location = armature.location
            self.collection.objects.link(psd_bone_root)
        context.scene.update()
        return mdl_base, psd_bone_root

    def create_mesh(self, mvector, meshname):
        """Create a mesh with the shape of a blender bone."""
        vertices = [(+0.0, +0.0, 0.0),
                    (-0.1, -0.1, 0.1),
                    (-0.1, +0.1, 0.1),
                    (+0.1, -0.1, 0.1),
                    (+0.1, +0.1, 0.1),
                    (+0.0, +0.0, 1.0)]
        faces = [(0, 1, 2),
                 (0, 2, 4),
                 (0, 4, 3),
                 (0, 3, 1),
                 (4, 2, 5),
                 (3, 4, 5),
                 (2, 1, 5),
                 (1, 3, 5)]
        mesh = nvb_utils.build_mesh(vertices, faces, meshname)

        rot = mathutils.Vector((0, 0, 1)).rotation_difference(mvector)
        mesh.transform(mathutils.Matrix.Rotation(rot.angle, 4, rot.axis))
        mesh.transform(mathutils.Matrix.Scale(mvector.length, 4))
        mesh.update()
        return mesh

    def create_psd_bones(self, amt_bone, psb_parent=None):
        """Creates pseusobone (mesh) objects from armature bones."""
        # Location for newly created mesh = pseudo-bone
        psb_head = amt_bone.head_local
        psb_tail = amt_bone.tail_local
        if amt_bone.parent:
            psb_head = psb_head - amt_bone.parent.head_local
            psb_tail = psb_tail - amt_bone.parent.head_local
        # Create pseudo bone object
        if amt_bone.nvb.psd_bone_shape == 'EMT':
            # Pseudo Bone will be an Empty
            psb = bpy.data.objects.new(amt_bone.name, None)
            psb.empty_display_type = self.dummy_type
            psb.empty_display_size = self.dummy_size
        else:
            # Pseudo Bone will be a Mesh
            mesh = self.create_mesh(psb_tail-psb_head, amt_bone.name)
            psb = bpy.data.objects.new(amt_bone.name, mesh)

        psb.location = psb_head
        psb.parent = psb_parent
        psb.nvb.render = False
        self.collection.objects.link(psb)
        # Create matrix for animation conversion
        self.amb_psb_pairs.append([amt_bone.name, psb.name])
        self.mats_edit_bone[amt_bone.name] = amt_bone.matrix_local.copy()
        for c in amt_bone.children:
            self.create_psd_bones(c, psb)

    def get_psd_bones(self, amt_bone, psd_bone_root):
        """Creates a list of pseudobones for this armature."""
        psd_bone_list = [psd_bone_root]
        nvb_utils.get_children_recursive(psd_bone_root, psd_bone_list)
        if amt_bone.name in [n.name for n in psd_bone_list]:
            psd_bone_name = amt_bone.name
            # Adjust pseudo bones location (remove "leftover" location)
            psd_bone_loc = amt_bone.head_local
            if amt_bone.parent:
                psd_bone_loc = psd_bone_loc - amt_bone.parent.head_local
            psd_bone = bpy.data.objects[psd_bone_name]
            psd_bone.location = psd_bone_loc
            # Add to list and copy matrix for animation conversion
            self.amb_psb_pairs.append([amt_bone.name, psd_bone_name])
            self.mats_edit_bone[amt_bone.name] = amt_bone.matrix_local.copy()
        for c in amt_bone.children:
            self.get_psd_bones(c, psd_bone_root)

    def copy_keyframes(self, amt, amt_action, amb_name, psb_name,
                       frame_offset=0):
        """Copies keyframes from armature bone to pseudo bone."""
        def insert_kfp(fcu, frames, values, dp, dp_dim):
            # Add keyframes to fcurves
            kfp_list = [fcu[d].keyframe_points for d in range(dp_dim)]
            kfp_cnt = [len(fcu[d].keyframe_points) for d in range(dp_dim)]
            list(map(lambda x: x.add(len(values)), kfp_list))
            # Set values for all keyframe points
            for i, (frm, val) in enumerate(zip(frames, values)):
                for d in range(dp_dim):
                    kfp = kfp_list[d][kfp_cnt[d]+i]
                    kfp.co = frm, val[d]
                    kfp.interpolation = 'LINEAR'
            list(map(lambda c: c.update(), fcu))

        def convert_loc(amt, posebone, psb, kfvalues, mat_eb):
            vecs = [mathutils.Vector(v) for v in kfvalues]
            eb_quat_adjusted = mat_eb.to_quaternion()
            list(map(lambda v: v.rotate(eb_quat_adjusted), vecs))
            return [psb.location + v for v in vecs]

        def convert_axan(amt, posebone, psb, kfvalues, mat_eb):
            mats = [mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4()
                    for v in kfvalues]
            mat_eb_inverted = mat_eb.to_3x3().to_4x4().inverted()
            mats = [mat_eb @ m @ mat_eb_inverted for m in mats]
            quats = [m.to_quaternion() for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def convert_quat(amt, posebone, psb, kfvalues, mat_eb):
            mats = [mathutils.Quaternion(v).to_matrix().to_4x4()
                    for v in kfvalues]
            mat_eb_adjusted = mat_eb.to_3x3().to_4x4().inverted()
            mats = [mat_eb @ m @ mat_eb_adjusted for m in mats]
            quats = [m.to_quaternion() for m in mats]
            return quats

        def convert_eul(amt, posebone, psb, kfvalues, mat_eb):
            mats = [mathutils.Euler(v, 'XYZ').to_matrix().to_4x4()
                    for v in kfvalues]
            mat_eb_adjusted = mat_eb.to_3x3().to_4x4().inverted()
            mats = [mat_eb @ m @ mat_eb_adjusted for m in mats]
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
        amt_bone = amt.pose.bones[amb_name]
        psd_bone = bpy.data.objects[psb_name]  # pseudo-bone
        mat_eb = self.mats_edit_bone[amb_name]  # edit-bone matrix
        # Get animation data, create if needed.
        if not psd_bone.animation_data:
            psd_bone.animation_data_create()
        # Get action, create if needed.
        psd_action = psd_bone.animation_data.action
        if not psd_action:
            psd_action = bpy.data.actions.new(name=psd_bone.name)
            psd_bone.animation_data.action = psd_action
        # All fcurves of the armature
        source_fcu = amt_action.fcurves
        # Build data paths depending on rotation mode
        psd_bone.rotation_mode = amt_bone.rotation_mode
        dp_list = get_data_paths(psd_bone.rotation_mode)
        # Transfer keyframes
        for psd_dp, group_name, dp_dim, kfp_convert, kfp_dfl in dp_list:
            amt_dp = 'pose.bones["' + amb_name + '"].' + psd_dp
            amt_fcu = [source_fcu.find(data_path=amt_dp, index=i)
                       for i in range(dp_dim)]
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
                values = kfp_convert(amt, amt_bone, psd_bone, values, mat_eb)
                # Create fcurves for pseudo bone
                psb_fcu = [nvb_utils.get_fcurve(psd_action, psd_dp, i,
                                                group_name)
                           for i in range(dp_dim)]
                # Add offset to frames (do it here AFTER getting values)
                if frame_offset != 0:
                    frames = [f + frame_offset for f in frames]
                # Add keyframes to fcurves
                insert_kfp(psb_fcu, frames, values, psd_dp, dp_dim)

    def copy_events(self, amt, amt_action_list, mdl_anim):
        """Creates animation events from keyframes armature events."""
        event_names = [ev.name for ev in amt.nvb.amt_event_list]
        event_data = []
        for ev_idx, ev_name in enumerate(event_names):
            dp = 'nvb.amt_event_list[' + str(ev_idx) + '].fire'
            for action in amt_action_list:
                fcu = action.fcurves.find(data_path=dp, index=0)
                if fcu:
                    event_data.extend([(p.co[0], ev_name)
                                       for p in fcu.keyframe_points])
        event_data.sort(key=lambda x: x[0])
        # Add events to the animations event list
        start_frame = mdl_anim.frameStart
        for ev_frame, ev_name in event_data:
            new_event = mdl_anim.eventList.add()
            new_event.name = ev_name
            new_event.frame = start_frame + ev_frame

    def copy_animations(self, mdl_base, armature, animation_list,
                        create_meta_data=True):
        # Clear all objects animation data (if any)
        for _, psd_bone_name in self.amb_psb_pairs:
            psd_bone = bpy.data.objects[psd_bone_name]
            if psd_bone.animation_data:
                psd_bone.animation_data_clear()
        # Clear existing meta data, if we are to create new ones
        if create_meta_data:
            # Clear the animation list in the mdl base
            for _ in range(len(mdl_base.nvb.animList)):
                mdl_base.nvb.animList.remove(0)
            mdl_base.nvb.animListIdx = 0
        # Create new animation data
        for anim_name, anim_length, action_list, transtime in animation_list:
            frame_offset = 0
            if create_meta_data:
                new_anim = nvb_utils.create_anim_list_item(mdl_base)
                new_anim.name = anim_name
                new_anim.root_obj = mdl_base
                new_anim.transtime = transtime
                new_anim.frameEnd = new_anim.frameStart + anim_length
                frame_offset = new_anim.frameStart
                self.copy_events(armature, action_list, new_anim)
            # Add new animation data
            for action in action_list:
                for amt_bone_name, psd_bone_name in self.amb_psb_pairs:
                    self.copy_keyframes(armature, action,
                                        amt_bone_name, psd_bone_name,
                                        frame_offset)

    def create_constraints(self, amt):
        """Apply transform constraint to pseudo bone from armature bone."""
        for amt_bone_name, psd_bone_name in self.amb_psb_pairs:
            psd_bone = bpy.data.objects[psd_bone_name]

            con = psd_bone.constraints.new('COPY_ROTATION')
            con.target = amt
            con.subtarget = amt_bone_name
            con.target_space = 'LOCAL_WITH_PARENT'
            con.owner_space = 'WORLD'

            con = psd_bone.constraints.new('COPY_LOCATION')
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

        addon = context.preferences.addons[__package__]
        addon_prefs = addon.preferences

        anim_mode = addon_prefs.util_psb_anim_mode
        create_base = addon_prefs.util_psb_insert_base
        create_root = addon_prefs.util_psb_insert_root

        self.scene = context.scene
        self.collection = context.collection
        self.dummy_type = addon_prefs.import_dummy_type
        self.dummy_size = addon_prefs.import_dummy_size

        self.amb_psb_pairs = []
        self.mats_edit_bone = dict()

        bpy.ops.object.mode_set(mode='EDIT')
        if self.use_existing:
            mdl_base = armature.nvb.util_psb_anim_target
            if not mdl_base:
                self.report({'INFO'}, 'Invalid Target')
                return {'CANCELLED'}
            # Get pseudo bones
            for amt_bone in armature.data.bones:
                if not amt_bone.parent:
                    self.get_psd_bones(amt_bone, mdl_base)
        else:
            # Create helper objects for grouping and holding animation data
            mdl_base, psd_bone_root = self.create_parent_objects(
                context, armature, anim_mode, create_base, create_root)
            # Save some date (somehow we can't access them properly otherwise)
            # Create pseudo bones
            for amt_bone in armature.data.bones:
                if not amt_bone.parent:
                    self.create_psd_bones(amt_bone, psd_bone_root)
            context.scene.update()
        bpy.ops.object.mode_set(mode='OBJECT')

        # Transfer animations
        if anim_mode == 'ACTION':
            anim_list = []
            if armature.animation_data and armature.animation_data.action:
                action = armature.animation_data.action
                anim_list.append(['unnamed', 1, [action], 7.5])
            self.copy_animations(mdl_base, armature, anim_list, False)
        elif anim_mode == 'NLA_TRACKS':
            anim_list = []
            for nla_track in armature.animation_data.nla_tracks:
                if not nla_track.mute:
                    anim_name = nla_track.name
                    anim_length = max([s.action_frame_end
                                       for s in nla_track.strips
                                       if not s.mute])
                    action_list = [s.action for s in nla_track.strips
                                   if not s.mute]
                    transtime = nla_track.strips[0].blend_in
                    anim_list.append([anim_name, anim_length, action_list,
                                      transtime])
            self.copy_animations(mdl_base, armature, anim_list, True)
        elif anim_mode == 'NLA_STRIPS':
            anim_list = []
            nla_track = armature.animation_data.nla_tracks.active
            for nla_strip in nla_track.strips:
                if not nla_strip.mute:
                    anim_name = nla_strip.name
                    anim_length = nla_strip.action_frame_end - \
                        nla_strip.action_frame_start
                    action_list = [nla_strip.action]
                    transtime = nla_strip.blend_in
                    anim_list.append([anim_name, anim_length, action_list,
                                     transtime])
            self.copy_animations(mdl_base, armature, anim_list, True)

        context.scene.update()
        return {'FINISHED'}


class NVB_OT_amt_psb2amt(bpy.types.Operator):
    """Generate armature from pseudo bones."""

    bl_idname = 'nvb.amt_psb2amt'
    bl_label = 'Generate Armature'
    bl_options = {'UNDO'}

    # Dummys (Empties) with these names are ignored
    excluded_bone_names = ['hand', 'head', 'head_hit', 'hhit', 'impact',
                           'impc', 'ground', 'grnd', 'handconjure',
                           'headconjure', 'lhand', 'rhand', 'lforearm',
                           'rforearm']
    # Generated bones
    generated_bones = []

    def is_connected(self, obj, parent_dist):
        """Determine whether the bone belonging to this object can be
           connected to it's parent."""
        if parent_dist <= 0.01:
            # If location is animated the bone cannot be connected
            if obj.animation_data and obj.animation_data.action:
                action = obj.animation_data.action
                dp_list = [fcu.data_path for fcu in action.fcurves]
                return 'location' not in dp_list
            return True
        return False

    def is_psd_bone(self, obj):
        """Return true if the object is a pseudo bone."""
        # Some objects like impact nodes can never be pseudo bones
        if obj.type == 'EMPTY':
            # Match objects ending with '.XYZ' numbers as well
            obj_name = obj.name
            matches = [re.fullmatch(s+'(\\.\\d+)?', obj_name)
                       for s in self.excluded_bone_names]
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

    def create_bones_rec(self, amt, psb, auto_connect=False, strip_name=False,
                         amb_parent=None, parent_mat=mathutils.Matrix()):
        """TODO: doc."""
        def convert_loc(obj, pmat):
            dc_pm = pmat.decompose()
            return mathutils.Matrix.Translation(dc_pm[0]) @ \
                obj.matrix_parent_inverse @ obj.matrix_basis
        # Calculate head (relative to parent head)
        psb_mat = convert_loc(psb, parent_mat)
        bhead = psb_mat.translation
        # Calculate tail (relative to head)
        btail = bhead + mathutils.Vector([0.0, 0.2, 0.0])  # For Empties
        valid_children = [c for c in psb.children if self.is_psd_bone(c)]
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
        if strip_name:
            amb_name = nvb_utils.strip_trailing_numbers(psb.name)
        amb = amt.data.edit_bones.new(amb_name)
        amb.roll = 0
        amb.head = bhead
        if amb_parent:
            amb.parent = amb_parent
            # Try to connect head with parent tail
            if auto_connect and \
               self.is_connected(psb, (amb_parent.tail - amb.head).length):
                amb.head = amb_parent.tail
                amb.use_connect = True
        amb.tail = btail
        # Save values for animation transfer
        dc_ml = psb.matrix_local.decompose()
        cmat = psb.matrix_parent_inverse
        cmat = mathutils.Matrix.Translation(dc_ml[0]).inverted() @ cmat
        self.generated_bones.append([amb.name, psb, cmat.copy()])
        # Create children
        for c in valid_children:
            self.create_bones_rec(amt, c, auto_connect, strip_name,
                                  amb, psb_mat)

    def create_bones(self, context, amt, psd_bone_root,
                     auto_connect, strip_name):
        bpy.ops.object.mode_set(mode='EDIT')
        for child in psd_bone_root.children:
            if self.is_psd_bone(child):
                self.create_bones_rec(amt, child, auto_connect, strip_name)
        context.scene.update()
        bpy.ops.object.mode_set(mode='OBJECT')

    def create_bone_properties(self, context, amt):
        """Sets bone properties for re-conversion to pseudo-bones"""
        for amt_bone_name, psd_bone, _ in self.generated_bones:
            if psd_bone.type == 'EMPTY':
                amt.data.bones[amt_bone_name].nvb.psd_bone_shape = 'EMT'
            else:
                amt.data.bones[amt_bone_name].nvb.psd_bone_shape = 'ME1'

    def copy_keyframes(self, amt, amt_action, amt_bone_name, psb,
                       cmat, frame_range=None):
        """TODO: DOC."""
        def insert_kfp(fcu, frames, values, dp, dp_dim):
            # Add keyframes to fcurves
            kfp = [fcu[d].keyframe_points for d in range(dp_dim)]
            list(map(lambda x: x.add(len(values)), kfp))
            # Set values for all keyframe points
            for d in range(dp_dim):
                kfp_data = [None] * 2 * len(values)
                kfp_data[::2] = frames
                kfp_data[1::2] = [v[d] for v in values]
                kfp[d].foreach_set('co', kfp_data)
                for p in kfp[d]:
                    p.interpolation = 'LINEAR'
            list(map(lambda c: c.update(), fcu))

        def convert_loc(amt, posebone, kfvalues, cmat):
            mats = [cmat @ mathutils.Matrix.Translation(v) for v in kfvalues]
            mats = [amt.convert_space(pose_bone=posebone,
                                      matrix=m,
                                      from_space='LOCAL_WITH_PARENT',
                                      to_space='LOCAL')
                    for m in mats]
            return [list(m.to_translation()) for m in mats]

        def convert_axan(amt, posebone, kfvalues, cmat):
            mats = [cmat @
                    mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4()
                    for v in kfvalues]
            quats = [amt.convert_space(pose_bone=posebone,
                                       matrix=m,
                                       from_space='LOCAL_WITH_PARENT',
                                       to_space='LOCAL').to_quaternion()
                     for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def convert_quat(amt, posebone, kfvalues, cmat):
            mats = [cmat @ mathutils.Quaternion(v).to_matrix().to_4x4()
                    for v in kfvalues]
            mats = [amt.convert_space(pose_bone=posebone,
                                      matrix=m,
                                      from_space='LOCAL_WITH_PARENT',
                                      to_space='LOCAL').to_quaternion()
                    for m in mats]
            return [list(m.to_quaternion()) for m in mats]

        def convert_eul(amt, posebone, kfvalues, cmat):
            mats = [cmat @ mathutils.Euler(v, 'XYZ').to_matrix().to_4x4()
                    for v in kfvalues]
            mats = [amt.convert_space(pose_bone=posebone,
                                      matrix=m,
                                      from_space='LOCAL_WITH_PARENT',
                                      to_space='LOCAL')
                    for m in mats]
            # Convert to Euler (with filter)
            euls = []
            e = posebone.rotation_euler
            for m in mats:
                e = m.to_euler('XYZ', e)
                euls.append(e)
            return euls

        if amt_bone_name not in amt.pose.bones:
            return
        amt_bone = amt.pose.bones[amt_bone_name]
        amt_bone.rotation_mode = psb.rotation_mode
        if psb.animation_data and psb.animation_data.action:
            source_fcu = psb.animation_data.action.fcurves
            # Copy rotation keyframes
            dp_list = [('rotation_axis_angle', 4, convert_axan),
                       ('rotation_quaternion', 4, convert_quat),
                       ('rotation_euler', 3, convert_eul),
                       ('location', 3, convert_loc)]
            for dp, dp_dim, convert_func in dp_list:
                psb_fcu = [source_fcu.find(data_path=dp, index=i)
                           for i in range(dp_dim)]
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
                    values = convert_func(amt, amt_bone, values, cmat)
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

    def copy_events(self, amt, amt_action, event_dict):
        """Creates keyframed events from the vevent list that mdls use."""
        def insert_kfp(fcu, frames):
            # Add keyframes to fcurves
            fcu.keyframe_points.add(len(frames))
            kfp_data = [0.0]*2*len(frames)
            kfp_data[::2] = frames
            fcu.keyframe_points.foreach_set('co', kfp_data)
            fcu.update()
        # Create missing event lists
        for event_name in event_dict.keys():
            if event_name not in amt.nvb.amt_event_list:
                nvb_utils.amt_event_list_item_create(amt, event_name)
        # Create keyframes
        for idx, amt_event in enumerate(amt.nvb.amt_event_list):
            if amt_event.name in event_dict:
                data_path = 'nvb.amt_event_list[' + str(idx) + '].fire'
                fcu = nvb_utils.get_fcurve(amt_action, data_path, 0, 'Events')
                insert_kfp(fcu, event_dict.pop(amt_event.name))

    def copy_animations(self, amt, action_list):
        """Copies animations to the newly created armatures"""
        if not amt.animation_data:
            amt.animation_data_create()
        nvb_utils.amt_event_list_init(amt)
        # Copy keyframes to action(s)
        for _, amt_action, event_dict, frame_range, transtime in action_list:
            for amb_name, psb, cmat in self.generated_bones:
                self.copy_keyframes(amt, amt_action, amb_name,
                                    psb, cmat, frame_range)
            self.copy_events(amt, amt_action, event_dict)

    def get_psd_bone_actions(self, mdl_base, amt, single_action=True):
        """Get a list of action to hold the animations from the mdl."""
        def get_event_list(mdl_base, anim_list, offset=0):
            event_dict = dict()
            for anim in anim_list:
                for event in anim.eventList:
                    ev_name = event.name.lower()
                    if ev_name in event_dict:
                        event_dict[ev_name].append(float(event.frame-offset))
                    else:
                        event_dict[ev_name] = [float(event.frame-offset)]
            return event_dict
        action_list = []
        if single_action:  # single action for all keyframes
            action = bpy.data.actions.new(name=amt.name)
            events = get_event_list(mdl_base, mdl_base.nvb.animList, 0)
            action_list.append((amt.name, action, events, None, 7.5))
        else:
            for anim in mdl_base.nvb.animList:
                action_name = amt.name + '.' + anim.name
                action = bpy.data.actions.new(name=action_name)
                frame_range = (anim.frameStart, anim.frameEnd)
                events = get_event_list(mdl_base, [anim], anim.frameStart)
                transtime = anim.transtime
                # root_name = anim.root_obj.name if anim.root_obj else ''
                action_list.append((anim.name, action, events,
                                    frame_range, transtime))
        return action_list

    def create_constraints(self, amt):
        """Apply transform constraint to pseudo bone from armature bone."""
        for amt_bone_name, psd_bone, _ in self.generated_bones:
            amt_bone = amt.pose.bones[amt_bone_name]
            constraint = amt_bone.constraints.new('COPY_ROTATION')
            constraint.target = psd_bone
            constraint.target_space = 'WORLD'
            constraint.owner_space = 'LOCAL_WITH_PARENT'
            constraint = amt_bone.constraints.new('COPY_LOCATION')
            constraint.target = psd_bone
            constraint.target_space = 'WORLD'
            constraint.owner_space = 'WORLD'

    @classmethod
    def poll(self, context):
        """Prevent execution if no root was found."""
        mdl_base = nvb_utils.get_obj_mdl_base(context.object)
        return (mdl_base is not None)

    def execute(self, context):
        """Create the armature"""
        mdl_base = nvb_utils.get_obj_mdl_base(context.object)
        addon = context.preferences.addons[__package__]
        addon_prefs = addon.preferences
        self.generated_bones = []

        # Get source for armature
        if addon_prefs.util_amt_src == 'ALL':
            psd_bone_root = mdl_base
        else:
            psd_bone_root = context.object

        # Create armature
        bpy.ops.object.add(type='ARMATURE', location=psd_bone_root.location)
        amt = context.active_object
        amt.name = mdl_base.name + '.armature'
        amt.rotation_mode = psd_bone_root.rotation_mode
        # amt_data = bpy.data.armatures.new(mdl_base.name + '.armature')
        # amt = bpy.data.objects.new(mdl_base.name + '.armature', amt_data)
        # context.view_layer.objects.active = amt
        # amt.rotation_mode = psd_bone_root.rotation_mode

        # Create the bones
        self.create_bones(context, amt, psd_bone_root,
                          addon_prefs.util_amt_connect,
                          addon_prefs.util_amt_strip_name)
        self.create_bone_properties(context, amt)  # Second pass necessary

        # Copy animations
        bpy.ops.object.mode_set(mode='POSE')
        anim_mode = addon_prefs.util_amt_anim_mode
        if anim_mode == 'CONSTRAINT':
            # Add constraints to bones so they follow the pseudo-bones
            # movements
            self.create_constraints(amt)
        elif anim_mode == 'NLA_TRACKS':
            action_list = self.get_psd_bone_actions(mdl_base, amt, False)
            self.copy_animations(amt, action_list)
            amt.nvb.use_amt_events = True
            # Create mutliple nla-tracks with a single nla-strip. Each track
            # corresponds to an animation from the mdl
            for anim_name, action, _, _, transtime in action_list:
                nla_track = amt.animation_data.nla_tracks.new()
                nla_track.name = anim_name
                strip = nla_track.strips.new(action.name, 0, action)
                strip.blend_in = transtime
        elif anim_mode == 'NLA_STRIPS':
            action_list = self.get_psd_bone_actions(mdl_base, amt, False)
            self.copy_animations(amt, action_list)
            amt.nvb.use_amt_events = True
            # Create single nla-track and multiple strips. Each strip
            # corresponds to an animation from the mdl
            nla_track = amt.animation_data.nla_tracks.new()
            nla_track.name = mdl_base.name
            for anim_name, action, _, frame_range, transtime in action_list:
                strip = nla_track.strips.new(anim_name, frame_range[0], action)
                strip.name = anim_name
                strip.blend_in = transtime
            amt.animation_data.nla_tracks.active = nla_track
        elif anim_mode == 'ACTION':
            action_list = self.get_psd_bone_actions(mdl_base, amt, True)
            self.copy_animations(amt, action_list)
            # Create a single action holding all keyframes from the mdl
            # Animation data (start & end frames, etc) is not saved
            if len(action_list) > 0:
                _, action, _, _, _ = action_list[0]
                amt.animation_data.action = action
        bpy.ops.object.mode_set(mode='OBJECT')
        del self.generated_bones
        return {'FINISHED'}
