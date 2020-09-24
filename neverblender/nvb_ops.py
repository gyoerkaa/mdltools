"""Contains misc. Blender operators."""

import os

import bpy
import mathutils

from . import nvb_def
from . import nvb_utils


class NVB_OT_lensflare_new(bpy.types.Operator):
    """Add a new item to the flare list"""

    bl_idname = 'nvb.lightflare_new'
    bl_label = 'Add a new flare to a light'

    def execute(self, context):
        """TODO: DOC."""
        obj = context.object
        if (obj.type == 'LIGHT'):
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

    direction: bpy.props.EnumProperty(items=(('UP', 'Up', ''),
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


class NVB_OT_util_minimap(bpy.types.Operator):
    """Set up rendering for minimaps."""

    bl_idname = "nvb.util_minimap"
    bl_label = "Render Minimap"

    batch_mode: bpy.props.BoolProperty(
        name='Batch Mode',
        description='Renders pictures directly to render_dir',
        default=False)
    render_dir: bpy.props.StringProperty(
        name='Render Directory',
        description='Directory to render images to',
        default='')
    force_lowercase: bpy.props.BoolProperty(
        name='Force Lowercase',
        description='All output images filenames will be converted to lowercase',
        default=False)     
    img_size: bpy.props.IntProperty(
        name='Image Size',
        description='Image Size',
        default=32, min=8)
    z_offset: bpy.props.FloatProperty(
        name='Camera Distance',
        description='Camera distance to ground',
        default=20.0, min=10.0)
    light_color: bpy.props.FloatVectorProperty(
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

    def setup_objects(self, mdl_base, collection):
        """Create camera and lamp objects."""
        # Setup Lamp
        light_name = 'mm_light'
        if light_name in bpy.data.objects:
            mm_light = bpy.data.objects[light_name]
        else:   # Check if present in db
            light_data = bpy.data.lights.new(light_name, 'POINT')
            light_data.type = 'SUN'
            light_data.specular_factor = 0.0
            light_data.energy = 5.0
            light_data.use_shadow = False
            light_data.color = self.light_color

            mm_light = bpy.data.objects.new(light_name, light_data)

        if mm_light.name not in collection.objects:
            collection.objects.link(mm_light)

        mm_light.location = mdl_base.location
        mm_light.location.z += self.z_offset

        # Setup Camera
        cam_name = 'mm_cam'
        if cam_name in bpy.data.objects:
            mm_cam = bpy.data.objects[cam_name]
        else:
            cam_data = bpy.data.cameras.new(cam_name)
            cam_data.type = 'ORTHO'
            cam_data.ortho_scale = 10.0

            mm_cam = bpy.data.objects.new(cam_name, cam_data)

        if mm_cam.name not in collection.objects:
            collection.objects.link(mm_cam)

        mm_cam.location = mdl_base.location
        mm_cam.location.z += self.z_offset

        return mm_cam, mm_light

    def setup_scene(self, scene):
        """Setup scene settings."""
        scene.render.resolution_x = self.img_size
        scene.render.resolution_y = self.img_size
        scene.render.resolution_percentage = 100
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.image_settings.file_format = 'TARGA_RAW'

    def execute(self, context):
        """Create camera + lamp and Renders Minimap."""
        scene = bpy.context.scene
        collection = scene.collection
        if self.batch_mode:
            # Get mdl roots
            mdl_base_list = []
            obj_list = collection.objects
            for obj in obj_list:
                mbase = nvb_utils.get_obj_mdl_base(obj)
                if mbase and (mbase not in mdl_base_list):
                    mdl_base_list.append(mbase)
            # Set render settings
            self.setup_scene(scene)
            # Render a minimap for each tile
            for mbase in mdl_base_list:
                img_name = 'mi_' + mbase.name
                if self.force_lowercase:
                    img_name = img_name.lower()
                img_path = os.fsencode(os.path.join(self.render_dir, img_name))
                scene.render.filepath = img_path
                mm_cam, _ = self.setup_objects(mbase, collection)
                scene.camera = mm_cam
                bpy.ops.render.render(animation=False, write_still=True)
        else:
            # Get root from active mdl
            if not context.object:
                return {'CANCELLED'}
            mdl_base = nvb_utils.get_obj_mdl_base(context.object)
            if not mdl_base:
                return {'CANCELLED'}
            # Setup Render
            self.img_size = scene.render.resolution_y  # make image square
            self.setup_scene(scene)
            mm_cam, _ = self.setup_objects(mdl_base, collection)
            scene.camera = mm_cam

            self.report({'INFO'}, 'Ready to render')
        return {'FINISHED'}


class NVB_OT_util_transform(bpy.types.Operator):
    """Apply translation and scale to the whole model and its animations"""
    bl_idname = "nvb.util_transform"
    bl_label = "Apply Transform"

    def apply_parent_inverse_animations(self, obj):
        """TODO: DOC."""
        def adjust_loc(obj, kfvalues):
            pinv = obj.matrix_parent_inverse
            mats = [pinv @ mathutils.Matrix.Translation(v) for v in kfvalues]
            return [m.to_translation() for m in mats]

        def adjust_axan(obj, kfvalues):
            pinv = obj.matrix_parent_inverse
            mats = [pinv @
                    mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4()
                    for v in kfvalues]
            quats = [m.to_quaternion() for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def adjust_quat(obj, kfvalues):
            pinv = obj.matrix_parent_inverse
            mats = [pinv @ mathutils.Quaternion(v).to_matrix().to_4x4()
                    for v in kfvalues]
            return [list(m.to_quaternion()) for m in mats]

        def adjust_eul(obj, kfvalues):
            pinv = obj.matrix_parent_inverse
            mats = [pinv @ mathutils.Euler(v, 'XYZ').to_matrix().to_4x4()
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
            fcu = [source_fcu.find(data_path=dp, index=i)
                   for i in range(dp_dim)]
            if fcu.count(None) < 1:
                frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points]
                      for i in range(dp_dim)]))
                frames.sort()
                values = [[fcu[i].evaluate(f) for i in range(dp_dim)]
                          for f in frames]
                # Adjust kfp to new coordinates
                values = adjust_func(obj, values)
                # Write back adjusted kfp values
                for i in range(dp_dim):
                    single_vals = [v[i] for v in values]
                    data = [d for z in zip(frames, single_vals) for d in z]
                    fcu[i].keyframe_points.foreach_set('co', data)
                    fcu[i].update()

    def apply_parent_inverse(self, obj):
        self.apply_parent_inverse_animations(obj)
        obj.matrix_basis = obj.matrix_parent_inverse @ obj.matrix_basis
        obj.matrix_parent_inverse.identity()
        for c in obj.children:
            self.apply_parent_inverse(c)

    def adjust_animations(self, obj, scl_mat, trn_mat):
        """TODO: DOC."""
        def adjust_loc(obj, kfvalues, scl_mat, trn_mat):
            vecs = [mathutils.Vector(v) for v in kfvalues]
            vecs = [v @ trn_mat @ scl_mat for v in vecs]
            return vecs

        def adjust_axan(obj, kfvalues, scl_mat, trn_mat):
            mats = [mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4() @
                    scl_mat
                    for v in kfvalues]
            quats = [m.to_quaternion() for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def adjust_quat(obj, kfvalues, scl_mat, trn_mat):
            mats = [mathutils.Quaternion(v).to_matrix().to_4x4() @ scl_mat
                    for v in kfvalues]
            return [list(m.to_quaternion()) for m in mats]

        def adjust_eul(obj, kfvalues, scl_mat, trn_mat):
            mats = [mathutils.Euler(v, 'XYZ').to_matrix().to_4x4() @ scl_mat
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
        all_fcu = action.fcurves
        dp_list = [('rotation_axis_angle', 4, adjust_axan),
                   ('rotation_quaternion', 4, adjust_quat),
                   ('rotation_euler', 3, adjust_eul),
                   ('location', 3, adjust_loc)]
        for dp, dp_dim, adjust_func in dp_list:
            fcu = [all_fcu.find(data_path=dp, index=i)
                   for i in range(dp_dim)]
            if fcu.count(None) < 1:
                frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points]
                      for i in range(dp_dim)]))
                frames.sort()
                values = [[fcu[i].evaluate(f) for i in range(dp_dim)]
                          for f in frames]
                # Adjust kfp to new coordinates
                values = adjust_func(obj, values, scl_mat, trn_mat)
                # Write back adjusted kfp values
                for i in range(dp_dim):
                    single_vals = [v[i] for v in values]
                    data = [d for z in zip(frames, single_vals) for d in z]
                    fcu[i].keyframe_points.foreach_set('co', data)
                    fcu[i].update()

    def adjust_animations2(self, obj, vecS, vecT):
        """TODO: DOC."""
        def adjust_loc(obj, kfvalues, matS, vecT):
            vec_list = [mathutils.Vector(vec) @ matS for vec in kfvalues]
            if vecT:
                vec_list = [vec + vecT for vec in vec_list]
            return vec_list

        def adjust_axan(obj, kfvalues, matS, vecT):
            mat_list = [mathutils.Quaternion(v[1:], v[0]).to_matrix() @ matS
                        for v in kfvalues]
            quat_list = [m.to_quaternion() for m in mat_list]
            return [[q.angle, *q.axis] for q in quat_list]

        def adjust_quat(obj, kfvalues, matS, vecT):
            mat_list = [mathutils.Quaternion(v).to_matrix() @ matS
                        for v in kfvalues]
            return [list(m.to_quaternion()) for m in mat_list]

        def adjust_eul(obj, kfvalues, matS, vecT):
            mat_list = [mathutils.Euler(v, 'XYZ').to_matrix() @ matS
                        for v in kfvalues]
            # Euler Filter
            euls = []
            e = obj.rotation_euler
            for m in mat_list:
                e = m.to_euler('XYZ', e)
                euls.append(e)
            return euls

        if not (obj.animation_data and obj.animation_data.action):
            return
        action = obj.animation_data.action

        matS = mathutils.Matrix([[vecS[0], 0, 0],
                                 [0, vecS[1], 0],
                                 [0, 0, vecS[2]]])

        dp_list = [('rotation_axis_angle', 4, adjust_axan),
                   ('rotation_quaternion', 4, adjust_quat),
                   ('rotation_euler', 3, adjust_eul),
                   ('location', 3, adjust_loc)]
        all_fcu = action.fcurves
        for dp, dp_dim, adjust_func in dp_list:
            fcu = [all_fcu.find(data_path=dp, index=i)
                   for i in range(dp_dim)]
            if fcu.count(None) < 1:
                frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points]
                      for i in range(dp_dim)]))
                frames.sort()
                values = [[fcu[i].evaluate(f) for i in range(dp_dim)]
                          for f in frames]
                # Adjust kfp to new coordinates
                values = adjust_func(obj, values, matS, vecT)
                # Write back adjusted kfp values
                for i in range(dp_dim):
                    single_vals = [v[i] for v in values]
                    data = [d for z in zip(frames, single_vals) for d in z]
                    fcu[i].keyframe_points.foreach_set('co', data)
                list(map(lambda c: c.update(), fcu))
        action.fcurves.update()

    def adjust_objects(self, obj, scl_mat, trn_mat):
        for c in obj.children:
            old_vT, old_mR, old_vS = c.matrix_basis.decompose()
            # Adjust translation, keep rotation, ditch scale
            new_trn = mathutils.Matrix.Translation(old_vT @ scl_mat) @ trn_mat
            c.matrix_basis = new_trn @ old_mR.to_matrix().to_4x4()
            # Get scale matrix
            new_scl = (mathutils.Matrix.Scale(old_vS[0], 4, [1, 0, 0]) @
                       mathutils.Matrix.Scale(old_vS[1], 4, [0, 1, 0]) @
                       mathutils.Matrix.Scale(old_vS[2], 4, [0, 0, 1]))
            # Apply to data
            if c.type == 'MESH':
                me = c.data
                for v in me.vertices:
                    v.co = v.co @ scl_mat @ new_scl
                me.update()
            # Apply to animations
            self.adjust_animations(c, scl_mat, trn_mat)
            # Only immediate children have their translation adjusted
            self.adjust_objects(c, scl_mat @ new_scl, mathutils.Matrix())

    def adjust_objects2(self, obj, par_vS, par_vT=None):
        for chi in obj.children:
            chi_vT, chi_mR, chi_vS = chi.matrix_basis.decompose()
            # Adjust translation with parent scale and translation (if any)
            new_vT = mathutils.Vector(a * b for a, b in zip(chi_vT, par_vS))
            if par_vT:
                new_vT = new_vT + par_vT
            # Keep rotation
            chi.matrix_basis = mathutils.Matrix.Translation(new_vT) @ \
                chi_mR.to_matrix().to_4x4()
            # Apply to data
            if chi.type == 'MESH':
                me = chi.data
                for v in me.vertices:
                    v.co = mathutils.Vector(a * b * c for a, b, c in
                                            zip(v.co, par_vS, chi_vS))
                me.update()
            # Apply to animations
            self.adjust_animations2(chi, par_vS, par_vT)
            # Only immediate children have their translation adjusted
            self.adjust_objects2(chi, mathutils.Vector(a * b for a, b in
                                                       zip(par_vS, chi_vS)))

    def execute(self, context):
        """TODO: DOC."""
        mdl_base = nvb_utils.get_mdl_base(context.object)
        # Get translation and scale factors
        if not mdl_base:
            self.report({'ERROR'}, 'Error: No Aurora Root.')
            return {'CANCELLED'}
        else:
            # Apply parent inverses
            self.apply_parent_inverse(mdl_base)
            # Decompose to get root transforms
            vecT, matR, vecS = mdl_base.matrix_basis.decompose()
            # Undo root transformations
            mdl_base.matrix_basis = matR.to_matrix().to_4x4()  # keep rot
            # Apply translation to immediate children and scale to all
            self.adjust_objects2(mdl_base, vecS, vecT)
            context.scene.collection.objects.update()
            context.evaluated_depsgraph_get().update()
            return {'FINISHED'}
