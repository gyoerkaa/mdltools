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
        rootDummy = nvb_utils.get_obj_mdl_base(obj)
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
            mdl_base_list = []
            obj_list = bpy.context.scene.objects
            for obj in obj_list:
                mbase = nvb_utils.get_obj_mdl_base(obj)
                if mbase and (mbase not in mdl_base_list):
                    mdl_base_list.append(mbase)
            # Render each mdl
            scene = bpy.context.scene
            self.setup_scene(scene)
            for mbase in mdl_base_list:
                img_name = 'mi_' + mbase.name
                img_path = os.fsencode(os.path.join(self.render_dir, img_name))
                scene.render.filepath = img_path
                mm_cam, _ = self.setup_objects(mbase, scene)
                scene.camera = mm_cam
                bpy.ops.render.render(animation=False, write_still=True)
        else:
            # Get root from active mdl
            if not context.object:
                return {'CANCELLED'}
            mdl_base = nvb_utils.get_mdl_base(context.object)
            if not mdl_base:
                return {'CANCELLED'}
            # Setup Render
            scene = bpy.context.scene
            self.img_size = scene.render.resolution_y
            self.setup_scene(scene)
            mm_cam, _ = self.setup_objects(mdl_base, scene)
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
            mats = [pinv * mathutils.Matrix.Translation(v) for v in kfvalues]
            return [m.to_translation() for m in mats]

        def adjust_axan(obj, kfvalues):
            pinv = obj.matrix_parent_inverse
            mats = [pinv *
                    mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4()
                    for v in kfvalues]
            quats = [m.to_quaternion() for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def adjust_quat(obj, kfvalues):
            pinv = obj.matrix_parent_inverse
            mats = [pinv * mathutils.Quaternion(v).to_matrix().to_4x4()
                    for v in kfvalues]
            return [list(m.to_quaternion()) for m in mats]

        def adjust_eul(obj, kfvalues):
            pinv = obj.matrix_parent_inverse
            mats = [pinv * mathutils.Euler(v, 'XYZ').to_matrix().to_4x4()
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
                values = adjust_func(obj, values)
                # Write back adjusted kfp values
                for i in range(dp_dim):
                    single_vals = [v[i] for v in values]
                    data = [d for z in zip(frames, single_vals) for d in z]
                    fcu[i].keyframe_points.foreach_set('co', data)
                    fcu[i].update()

    def apply_parent_inverse(self, obj):
        self.apply_parent_inverse_animations(obj)
        obj.matrix_basis = obj.matrix_parent_inverse * obj.matrix_basis
        obj.matrix_parent_inverse.identity()
        for c in obj.children:
            self.apply_parent_inverse(c)

    def adjust_animations(self, obj, scl_mat, trn_mat):
        """TODO: DOC."""
        def adjust_loc(obj, kfvalues, scl_mat, trn_mat):
            vecs = [mathutils.Vector(v) for v in kfvalues]
            mats = [mathutils.Matrix.Translation(v * scl_mat) * trn_mat
                    for v in vecs]
            return [m.to_translation() for m in mats]

        def adjust_axan(obj, kfvalues, scl_mat, trn_mat):
            mats = [mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4() *
                    scl_mat
                    for v in kfvalues]
            quats = [m.to_quaternion() for m in mats]
            return [[q.angle, *q.axis] for q in quats]

        def adjust_quat(obj, kfvalues, scl_mat, trn_mat):
            mats = [mathutils.Quaternion(v).to_matrix().to_4x4() * scl_mat
                    for v in kfvalues]
            return [list(m.to_quaternion()) for m in mats]

        def adjust_eul(obj, kfvalues, scl_mat, trn_mat):
            mats = [mathutils.Euler(v, 'XYZ').to_matrix().to_4x4() * scl_mat
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
                values = adjust_func(obj, values, scl_mat, trn_mat)
                # Write back adjusted kfp values
                for i in range(dp_dim):
                    single_vals = [v[i] for v in values]
                    data = [d for z in zip(frames, single_vals) for d in z]
                    fcu[i].keyframe_points.foreach_set('co', data)
                    fcu[i].update()

    def adjust_objects(self, obj, scl_mat, trn_mat):
        for c in obj.children:
            dcmp = c.matrix_basis.decompose()
            # Adjust translation, keep rotation, ditch scale
            new_trn = mathutils.Matrix.Translation(dcmp[0] * scl_mat) * trn_mat
            c.matrix_basis = new_trn * dcmp[1].to_matrix().to_4x4()
            # Get scale matrix
            new_scl = (mathutils.Matrix.Scale(dcmp[2][0], 4, [1, 0, 0]) *
                       mathutils.Matrix.Scale(dcmp[2][1], 4, [0, 1, 0]) *
                       mathutils.Matrix.Scale(dcmp[2][2], 4, [0, 0, 1]))
            # Apply to data
            if c.type == 'MESH':
                me = c.data
                for v in me.vertices:
                    v.co = v.co * scl_mat * new_scl
                me.update()
            # Apply to animations
            self.adjust_animations(c, scl_mat, trn_mat)
            # Only immediate children have their translation adjusted
            self.adjust_objects(c, scl_mat * new_scl, mathutils.Matrix())

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
            dcmp = mdl_base.matrix_basis.decompose()
            # Undo root transformations
            mdl_base.matrix_basis = dcmp[1].to_matrix().to_4x4()  # keep rot
            # Apply translation to immediate children and scale to all
            trn = mathutils.Matrix.Translation(dcmp[0]).to_4x4()
            scl = (mathutils.Matrix.Scale(dcmp[2][0], 4, [1, 0, 0]) *
                   mathutils.Matrix.Scale(dcmp[2][1], 4, [0, 1, 0]) *
                   mathutils.Matrix.Scale(dcmp[2][2], 4, [0, 0, 1]))
            self.adjust_objects(mdl_base, scl, trn)
            context.scene.update()
            return {'FINISHED'}
