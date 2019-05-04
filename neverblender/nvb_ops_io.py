"""Contains Blender Operators for MDL Import/Export."""

import os
import math
import bpy
import bpy_extras

from . import nvb_mdl
from . import nvb_mtr
from . import nvb_def
from . import nvb_utils


class NVB_OT_mdlexport(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    """Export Aurora Engine model (.mdl)"""

    bl_idname = 'scene.nvb_mdlexport'
    bl_label = 'Export Aurora MDL'
    bl_options = {'PRESET'}

    filename_ext = '.mdl'
    filter_glob: bpy.props.StringProperty(
            default='*.mdl',
            options={'HIDDEN'})
    # Misc Export Settings
    export_animations: bpy.props.BoolProperty(
            name='Export Animations',
            description='Export animations',
            default=True)
    export_walkmesh: bpy.props.BoolProperty(
            name='Export Walkmesh',
            description='Export a walkmesh',
            default=True)
    export_smoothgroups: bpy.props.BoolProperty(
            name='Export Smooth Groups',
            description='Generate smooth groups from sharp edges'
                        '(When disabled every face belongs to the same group)',
            default=True)
    export_normals: bpy.props.BoolProperty(
            name='Export Normals and Tangents',
            description='Add normals and tangents to MDL',
            default=False)
    export_mtr: bpy.props.BoolProperty(
            name='Export MTR',
            description='Export material data to MTR files',
            default=True)
    # UV Map Export settings
    uv_merge: bpy.props.BoolProperty(
            name='Merge UVs',
            description='Join uv-vertices with identical coordinates',
            default=True)
    uv_mode: bpy.props.EnumProperty(
            name='Mode',
            description='Determines which meshes get uv maps',
            items=(('TEX', 'Textured Meshes',
                    'Add UV Maps only to textured and rendered meshes'),
                   ('REN', 'Rendered Meshes',
                    'Add UV Maps only to rendered meshes'),
                   ('ALL', 'All',
                    'Add UV Maps to all meshes')),
            default='REN')
    uv_order: bpy.props.EnumProperty(
            name='Order',
            description='Determines ordering of uv maps in MDL',
            items=(('AL0', 'Alphabetical',
                    'Alphabetical ordering'),
                   ('AL1', 'Alphabetical (Active First)',
                    'Alphabetical ordering, active UVMap will be first'),
                   ('ACT', 'Active Only',
                    'Export active UVMap only')),
            default='ACT')
    # Blender Setting to use
    apply_modifiers: bpy.props.BoolProperty(
            name='Apply Modifiers',
            description='Apply Modifiers before exporting',
            default=True)
    strip_trailing: bpy.props.BoolProperty(
            name='Strip Trailing Numbers',
            description='Strips trailing numbers from object names',
            default=False)
    frame_set_zero: bpy.props.BoolProperty(
            name='Export at Frame 0',
            description='Set frame to 0 for export',
            default=False)
    batch_mode: bpy.props.EnumProperty(
            name='Batch Mode',
            description='Export multiple MDLs',
            items=(('OFF', 'Off', 'Export active MDL only'),
                   ('SEL', 'Selected', 'Export selected MDLs'),
                   ('SCN', 'Scene', 'Export all MDLs in active scene')),
            default='OFF')

    def mdl_export(self, context, options):
        """TODO: DOC."""
        def get_filepath(old_path, new_name, new_ext):
            """Creates filenames for walkmeshes and batch export."""
            old_dir = os.path.dirname(old_path)
            new_name = new_name + new_ext
            return os.path.join(old_dir, new_name)

        def get_walkmeshtype(mdl_base):
            """Creates filenames for walkmeshes and batch export."""
            if mdl_base.nvb.classification == nvb_def.Classification.DOOR:
                return nvb_def.Walkmeshtype.DWK
            elif mdl_base.nvb.classification == nvb_def.Classification.TILE:
                return nvb_def.Walkmeshtype.WOK
            else:
                return nvb_def.Walkmeshtype.PWK

        # (Re)set to object-mode, if an object is selected
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
        # Set frame to zero, if specified in options
        if self.frame_set_zero:
            options.scene.frame_current = 0
            bpy.context.scene.update()
        # Gather MDLs to export
        mdl_list = []
        if options.batch_mode == 'OFF':  # Get active object only
            base = nvb_utils.get_mdl_base(context.object,
                                          options.scene.collection,
                                          options.scene)
            wkm_name = os.path.splitext(os.path.basename(options.filepath))[0]
            if base:
                mdl_list.append((base, options.filepath, wkm_name))
        else:  # Get multiple objects
            obj_list = []
            if options.batch_mode == 'SCN':
                # Get all object in scene (master collection)
                obj_list = bpy.context.scene.collection.all_objects
            elif options.batch_mode == 'SEL':
                # Get all selected objects
                obj_list = bpy.context.selected_objects
            for obj in obj_list:
                base = nvb_utils.get_obj_mdl_base(obj)
                if base and (base not in mdl_list):
                    # Build a custom filename
                    mdl_path = get_filepath(options.filepath,
                                            base.name, '.mdl')
                    mdl_list.append((base, mdl_path, base.name))
        # Export MDLs
        for mdl_base, mdl_path, wkm_name in mdl_list:
            options.mdlname = mdl_base.name
            options.filepath = mdl_path
            options.classification = mdl_base.nvb.classification
            # Export MDL
            ascii_lines = []
            nvb_mdl.Mdl.generate_ascii(mdl_base, ascii_lines, options)
            with open(os.fsencode(options.filepath), 'w') as f:
                f.write('\n'.join(ascii_lines))
            # Export walkmesh for MDL
            if options.export_walkmesh:
                wkm_type = get_walkmeshtype(mdl_base)
                wkm_ext = '.' + wkm_type
                ascii_lines = []
                nvb_mdl.Mdl.generate_ascii_wkm(mdl_base, ascii_lines,
                                               wkm_type, options)
                if ascii_lines:
                    wkm_path = get_filepath(mdl_path, wkm_name, wkm_ext)
                    with open(os.fsencode(wkm_path), 'w') as f:
                        f.write('\n'.join(ascii_lines))
        # Export MTRs
        for mtr_name, blen_mat_name in options.mtr_list:
            blen_mat = bpy.data.materials[blen_mat_name]
            ascii_lines = nvb_mtr.Mtr.generate_ascii(blen_mat, options)
            mtr_path = get_filepath(options.filepath, mtr_name, '.mtr')
            with open(os.fsencode(mtr_path), 'w') as f:
                f.write('\n'.join(ascii_lines))
        return {'FINISHED'}

    def draw(self, context):
        """Draw the export UI."""
        layout = self.layout
        # Misc Export Settings
        box = layout.box()
        box.prop(self, 'export_animations')
        box.prop(self, 'export_walkmesh')
        box.prop(self, 'export_smoothgroups')
        box.prop(self, 'export_normals')
        box.prop(self, 'export_mtr')
        # UV Map settings
        box = layout.box()
        box.label(text='UV Map Settings')
        sub = box.column()
        sub.prop(self, 'uv_merge')
        sub.prop(self, 'uv_mode')
        sub.prop(self, 'uv_order')
        # Blender Settings
        box = layout.box()
        box.label(text='Blender Settings')
        sub = box.column()
        sub.prop(self, 'apply_modifiers')
        sub.prop(self, 'strip_trailing')
        sub.prop(self, 'frame_set_zero')
        sub.prop(self, 'batch_mode')

    def execute(self, context):
        """TODO: DOC."""
        addon = context.preferences.addons[__package__]
        addon_prefs = addon.preferences

        options = nvb_def.ExportOptions()
        options.filepath = self.filepath
        options.scene = context.scene
        options.depsgraph = context.depsgraph
        # Misc Export Settings
        options.export_animations = self.export_animations
        options.export_walkmesh = self.export_walkmesh
        options.export_smoothgroups = self.export_smoothgroups
        options.export_normals = self.export_normals
        options.export_wirecolor = addon_prefs.export_wirecolor
        # UV Map settings
        options.uv_merge = self.uv_merge
        options.uv_level = self.uv_mode
        options.uv_order = self.uv_order
        # Material Export Settings
        options.export_mtr = self.export_mtr
        options.mtr_ref = addon_prefs.export_mat_mtr_ref
        options.mat_diffuse_ref = addon_prefs.export_mat_diffuse_ref
        # Blender Settings
        options.apply_modifiers = self.apply_modifiers
        options.strip_trailing = self.strip_trailing
        options.batch_mode = self.batch_mode
        return self.mdl_export(context, options)

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        # Generate a file name from active object
        scene = context.scene
        mdl_base = nvb_utils.get_mdl_base(context.object,
                                          scene.collection,
                                          scene)
        if mdl_base:
            generated_name = nvb_utils.generate_node_name(mdl_base, True)
            self.filepath = generated_name + '.mdl'
        else:
            self.filepath = 'untitled.mdl'
        return {'RUNNING_MODAL'}


class NVB_OT_mdlimport(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Import Aurora Engine model (.mdl)"""

    bl_idname = 'scene.nvb_mdlimport'
    bl_label = 'Import Aurora MDL'
    bl_options = {'UNDO', 'PRESET'}

    files: bpy.props.CollectionProperty(
        name='File Path',
        description='Path used for importing the file',
        type=bpy.types.OperatorFileListElement)
    directory: bpy.props.StringProperty()
    filter_glob: bpy.props.StringProperty(default='*.mdl', options={'HIDDEN'})
    filename_ext = '.mdl'

    import_walkmesh: bpy.props.BoolProperty(
        name='Import Walkmesh',
        description='Load placeable and door walkmeshes',
        default=True)
    import_smoothgroups: bpy.props.BoolProperty(
        name='Import Smooth Groups',
        description='Import smooth groups as sharp edges',
        default=True)
    import_normals: bpy.props.BoolProperty(
        name='Import Normals',
        description='Import normals from MDL',
        default=True)
    # Materials Options
    mat_import: bpy.props.BoolProperty(
        name='Import Materials',
        description='Import materials and textures',
        default=True)
    mat_automerge: bpy.props.BoolProperty(
        name='Merge Materials',
        description='Merge materials with the same values',
        default=True)
    mat_shader: bpy.props.EnumProperty(
        name='Shader',
        description='',
        items=(('ShaderNodeEeveeSpecular', 'Eevee Specular', ''),
               ('ShaderNodeBsdfPrincipled', 'Principled BSDF', '')),
        default='ShaderNodeEeveeSpecular')
    mtr_import: bpy.props.BoolProperty(
        name='Import MTR files',
        description='Load external material files ' +
                    '(will overwride material in MDL)',
        default=True)
    tex_search: bpy.props.BoolProperty(
        name='Image Search',
        description='Search for images in subdirectories \
                     (Warning: May be slow)',
        default=False)
    # Animation Options
    anim_import: bpy.props.BoolProperty(name='Import Animations',
                                        description='Import animation data',
                                        default=True)
    anim_fps_use: bpy.props.BoolProperty(name='Use Custom fps',
                                         description='Use custom fps value',
                                         default=True)
    anim_fps: bpy.props.IntProperty(name='Scene Framerate',
                                    description='Custom fps value',
                                    default=30,
                                    min=1, max=60)
    anim_restpose: bpy.props.BoolProperty(
        name='Insert Rest Pose',
        description='Insert rest keyframe before every animation',
        default=True)
    # Blender Settings
    rotmode: bpy.props.EnumProperty(
        name='Rotation Mode',
        description='',
        items=(('AXIS_ANGLE', 'Axis Angle', ''),
               ('QUATERNION', 'Quaternion', ''),
               ('XYZ', 'Euler XYZ', '')),
        default='XYZ')
    collections_create: bpy.props.BoolProperty(
        name='Create Collections',
        description='Create new collection for each imported mdl.',
        default=False)
    fix_uvs: bpy.props.BoolProperty(
        name='Fix degenerated UVs',
        description='Fix degenerated UV coordinates (tverts)',
        default=False)
    mdl_location: bpy.props.FloatVectorProperty(
        name='Location',
        description='Location of newly imported model',
        default=(0.0, 0.0, 0.0), size=3, options={'HIDDEN'})
    import_geometry: bpy.props.BoolProperty(name='Import Geometry',
                                            description='Render Lights',
                                            default=True, options={'HIDDEN'})
    hide_lights: bpy.props.BoolProperty(name='Hide Lights',
                                        description='Do not render Lights',
                                        default=True, options={'HIDDEN'})
    hide_fading: bpy.props.BoolProperty(name='Hide Fading Objects',
                                        description='Do not render Fading Objects',
                                        default=False, options={'HIDDEN'})

    def mdl_import(self, context, options):
        def load_file(context, mdl_filepath, options, collections_create):
            mdl_filedir, mdl_filename = os.path.split(mdl_filepath)
            mdl_name = os.path.splitext(mdl_filename)[0]

            options.mdlname = mdl_name
            options.filepath = mdl_filepath

            # Create a new collection
            parent_collection = context.scene.collection
            collection = bpy.data.collections.new(name=mdl_name)
            parent_collection.children.link(collection)
            options.collection = collection

            mdl = nvb_mdl.Mdl()
            mdl.parse_mdl(mdl_filepath, options)

            if options.import_walkmesh:
                # Try loading the placeable walkmesh (pwk)
                pwk_filename = mdl_name + '.' + nvb_def.Walkmeshtype.PWK
                pwk_filepath = os.path.join(mdl_filedir, pwk_filename)
                if os.path.isfile(os.fsencode(pwk_filepath)):
                    mdl.parse_wkm(pwk_filepath ,nvb_def.Walkmeshtype.PWK, options)
                # Try loading the door walkmesh (dwk)
                dwk_filename = mdl_name + '.' + nvb_def.Walkmeshtype.DWK
                dwk_filepath = os.path.join(mdl_filedir, dwk_filename)
                if os.path.isfile(os.fsencode(dwk_filepath)):
                    mdl.parse_wkm(dwk_filepath ,nvb_def.Walkmeshtype.DWK, options)

            mdl.create(options)

        def generate_location(idx):
            k = math.floor(math.floor(math.sqrt(idx)-1)/2)+1
            return (10.0 * min(k, max(-k, -2*k + abs(i-(4*k*k)-k))),
                    10.0 * min(k, max(-k, -2*k + abs(i-(4*k*k)+k))), 0.0)

        # Build list of files
        pathlist = [os.path.join(self.directory, f.name) for f in self.files]
        if not pathlist:
            pathlist.append(self.filepath)
        # Import models
        if len(pathlist) == 1:  # single model => use location in options
            load_file(context, pathlist[0], options, self.collections_create)
        else:  # multiple models => place in a spiral, generate new locations
            for i, filepath in enumerate(pathlist):
                options.mdl_location = generate_location(i)
                load_file(context, filepath, options, self.collections_create)
        return {'FINISHED'}

    def draw(self, context):
        """Draw the export UI."""
        layout = self.layout
        # Misc Import Settings
        box = layout.box()
        box.prop(self, 'import_walkmesh')
        box.prop(self, 'import_smoothgroups')
        box.prop(self, 'import_normals')

        # Material Import Settings
        box = layout.box()
        box.prop(self, 'mat_import')
        sub = box.column()
        sub.enabled = self.mat_import
        sub.prop(self, 'mat_shader', text='')
        sub.prop(self, 'mat_automerge')
        sub.prop(self, 'mtr_import')
        sub.prop(self, 'tex_search')

        # Animation Import Settings
        box = layout.box()
        box.prop(self, 'anim_import')
        sub1 = box.column()
        sub1.enabled = self.anim_import
        sub1.prop(self, 'anim_restpose')
        row = sub1.row(align=True)
        row.prop(self, 'anim_fps_use', text='')
        sub2 = row.row(align=True)
        sub2.enabled = self.anim_fps_use
        sub2.prop(self, 'anim_fps')

        # Blender Settings
        box = layout.box()
        box.label(text='Blender Settings')
        box.prop(self, 'rotmode')
        box.prop(self, 'collections_create')
        box.prop(self, 'fix_uvs')

    def execute(self, context):
        """TODO: DOC."""
        options = nvb_def.ImportOptions()
        options.filepath = self.filepath
        options.scene = context.scene
        options.collection = context.collection
        # Misc Import Settings
        options.import_geometry = self.import_geometry
        options.import_walkmesh = self.import_walkmesh
        options.importSmoothGroups = self.import_smoothgroups
        options.import_normals = self.import_normals
        # Material Options
        options.importMaterials = self.mat_import
        options.mat_automerge = self.mat_automerge
        options.mat_shader = self.mat_shader
        options.importMTR = self.mtr_import
        options.tex_search = self.tex_search
        # Animation Options
        options.anim_import = self.anim_import
        options.anim_restpose = self.anim_restpose
        options.anim_fps_use = self.anim_fps_use
        options.anim_fps = self.anim_fps
        # Blender Settings
        options.rotmode = self.rotmode
        options.fix_uvs = self.fix_uvs
        options.mdl_location = self.mdl_location
        options.hide_lights = self.hide_lights
        options.hide_fading = self.hide_fading
        return self.mdl_import(context, options)


class NVB_OT_mdl_superimport(bpy.types.Operator,
                             bpy_extras.io_utils.ImportHelper):
    """Import animations from supermodel onto existing mdl"""
    bl_idname = 'scene.nvb_superimport'
    bl_label = 'Import Supermodel'

    files: bpy.props.CollectionProperty(
        name='File Path',
        description='Path used for importing the file',
        type=bpy.types.OperatorFileListElement)
    directory: bpy.props.StringProperty()
    filter_glob: bpy.props.StringProperty(default='*.mdl', options={'HIDDEN'})
    filename_ext = '.mdl'

    anim_fps_use: bpy.props.BoolProperty(name='Use Custom fps',
                                         description='Use custom fps value',
                                         default=False)
    anim_fps: bpy.props.IntProperty(name='Scene Framerate',
                                    description='Custom fps value',
                                    default=30,
                                    min=1, max=60)
    anim_restpose: bpy.props.BoolProperty(
        name='Insert Rest Pose',
        description='Insert rest keyframe before every animation',
        default=True)
    anim_ignore_existing: bpy.props.BoolProperty(
        name='Ignore Existing',
        description='Do not import already existing animations',
        default=True)

    def mdl_import(self, context, options):
        def load_file(mdl_filepath, mdl_base, options):
            _, mdl_filename = os.path.split(mdl_filepath)
            mdl_name = os.path.splitext(mdl_filename)[0]

            options.mdlname = mdl_name
            options.filepath = mdl_filepath
            mdl = nvb_mdl.Mdl()
            mdl.parse_mdl(mdl_filepath, options)
            mdl.create_super(mdl_base, options)

        # Build list of files
        pathlist = [os.path.join(self.directory, f.name) for f in self.files]
        # Import models
        mdl_base = nvb_utils.get_obj_mdl_base(context.object)
        if round(mdl_base.nvb.animscale, 3) != 1.0:
            options.anim_scale = mdl_base.nvb.animscale
        for filepath in pathlist:
            load_file(filepath, mdl_base, options)
        return {'FINISHED'}

    @classmethod
    def poll(self, context):
        """Check presence of aurora base."""
        return nvb_utils.get_obj_mdl_base(context.object) is not None

    def draw(self, context):
        """Draw the export UI."""
        layout = self.layout

        # Animation Import Settings
        box = layout.box()
        box.prop(self, 'anim_ignore_existing')
        box.prop(self, 'anim_restpose')
        row = box.row(align=True)
        row.prop(self, 'anim_fps_use', text='')
        sub = row.row(align=True)
        sub.enabled = self.anim_fps_use
        sub.prop(self, 'anim_fps')

    def execute(self, context):
        options = nvb_def.ImportOptions()
        options.scene = context.scene

        options.anim_fps_use = self.anim_fps_use
        options.anim_fps = self.anim_fps
        options.anim_restpose = self.anim_restpose
        options.anim_ignore_existing = self.anim_ignore_existing
        return self.mdl_import(context, options)

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)

        return {'RUNNING_MODAL'}
