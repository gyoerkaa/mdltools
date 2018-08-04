"""Contains misc. Blender Operators."""

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


class NVB_OT_util_genwok(bpy.types.Operator):
    """Load all materials for aabb walkmeshes for the selected object"""

    bl_idname = 'nvb.util_genwok'
    bl_label = 'Load walkmesh materials'

    @classmethod
    def poll(self, context):
        """Enable only if a Lamp is selected."""
        return (context.object and context.object.type == 'MESH')

    def execute(self, context):
        """Delete all current materials and add walkmesh materials."""
        obj = context.object
        # Remove all material slots
        for _ in range(len(obj.material_slots)):
            bpy.ops.object.material_slot_remove()
        # Add wok materials
        nvb_utils.create_wok_materials(obj.data)
        return {'FINISHED'}


class NVB_OT_util_nodes(bpy.types.Operator):
    """Helper to add missing walkmesh objects and dummys."""

    bl_idname = "nvb.util_nodes"
    bl_label = "Setup Nodes"

    def create_dummys(self, ddata, prefix, parent, scene, obj_list=[]):
        if not obj_list:
            return
        for suffix, loc in ddata:
            dummy_name = prefix + suffix
            existing = [o for o in obj_list if o.name.endswith(suffix)]
            if existing:  # Adjust name and parent for existing objects
                for obj in existing:
                    if obj.name != dummy_name:
                        # Avoid renaming to same name (results in .001 suffix)
                        obj.name = dummy_name
                    obj.parent = parent
            else:  # Create missing dummies
                obj = bpy.data.objects.new(dummy_name, None)
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

    def create_pwk(self, mdl_base, scene):
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

        prefix = get_prefix(mdl_base)
        # Find or create walkmesh root
        wkmroot = nvb_utils.get_wkm_base(mdl_base, nvb_def.Walkmeshtype.PWK)
        newname = mdl_base.name + '_pwk'
        if wkmroot:
            # Adjust existing object
            if wkmroot.name != newname:
                wkmroot.name = newname
            wkmroot.parent = mdl_base
        else:
            # make a new one
            wkmroot = bpy.data.objects.new(newname, None)
            wkmroot.nvb.emptytype = nvb_def.Emptytype.PWK
            wkmroot.parent = mdl_base
            scene.objects.link(wkmroot)
        # Get all children of the mdlroot (to check existing objects)
        obj_list = [mdl_base]
        nvb_utils.get_children_recursive(mdl_base, obj_list)
        # FROM HERE ON: Walkmesh objects - all parented to wkmroot
        # Adjust name and parent of exising mesh(es)
        meshlist = [o for o in obj_list if o.name.endswith('_wg')]
        for obj in meshlist:
            newname = mdl_base.name + '_wg'
            if obj.name != newname:
                obj.name = newname
            obj.parent = wkmroot
        # Create missing mesh
        meshname = mdl_base.name + '_wg'
        if meshname not in bpy.data.objects:
            verts, faces = get_mdl_bbox(mdl_base)
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
        self.create_dummys(dummy_data, prefix, mdl_base, scene, obj_list)

    def create_dwk(self, mdl_base, scene):
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

        prefix = mdl_base.name[-2:]
        # Find or create walkmesh root (wkmroot)
        wkmroot = nvb_utils.get_wkm_base(mdl_base, nvb_def.Walkmeshtype.DWK)
        newname = mdl_base.name + '_dwk'
        if wkmroot:
            # Adjust existing
            if wkmroot.name != newname:
                # Avoid renaming to same name (results in '.001' suffix)
                wkmroot.name = newname
            wkmroot.parent = mdl_base
        else:
            # Make a new one
            wkmroot = bpy.data.objects.new(newname, None)
            wkmroot.nvb.emptytype = nvb_def.Emptytype.DWK
            wkmroot.parent = mdl_base
            scene.objects.link(wkmroot)
        # Get all children of the mdlroot (to check existing objects)
        obj_list = [mdl_base]
        nvb_utils.get_children_recursive(mdl_base, obj_list)
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
        obj.parent = mdl_base
        obj.nvb.shadow = False
        # Create special dummys
        dummy_data = [['_hand', (0.0, 0.0, 1.0)],
                      ['_head', (0.0, 0.0, 2.5)],
                      ['_hhit', (0.0, 0.0, 3.0)],
                      ['_impc', (0.0, 0.0, 1.5)],
                      ['_grnd', (0.0, 0.0, 0.0)]]
        self.create_dummys(dummy_data, prefix, mdl_base, scene, obj_list)

    @classmethod
    def poll(self, context):
        """Prevent execution if no object is selected."""
        return context.object is not None

    def execute(self, context):
        """Create Walkmesh root and objects."""
        mdl_base = nvb_utils.get_obj_mdl_base(context.object)
        addon = context.user_preferences.addons[__package__]
        scene = bpy.context.scene
        if not mdl_base:
            self.report({'ERROR'}, 'No MDL root')
            return {'CANCELLED'}
        wkm_type = addon.preferences.util_node_mdltype
        if wkm_type == nvb_def.Walkmeshtype.PWK:
            self.create_pwk(mdl_base, scene)
        elif wkm_type == nvb_def.Walkmeshtype.DWK:
            self.create_dwk(mdl_base, scene)
        elif wkm_type == nvb_def.Walkmeshtype.WOK:
            self.create_wok(mdl_base, scene)
        self.report({'INFO'}, 'Created objects')
        return {'FINISHED'}


class NVB_OT_util_minimap(bpy.types.Operator):
    """Set up rendering for minimaps."""

    bl_idname = "nvb.util_minimap"
    bl_label = "Render Minimap"

    batch_mode = bpy.props.BoolProperty(
        name='Batch Mode',
        description='Renders pictures directly to render_dir',
        default=False)
    render_dir = bpy.props.StringProperty(
        name='Render Directory',
        description='Directory to render images to',
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
