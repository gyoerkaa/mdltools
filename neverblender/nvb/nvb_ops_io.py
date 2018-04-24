import os
import bpy
import bpy_extras

from . import nvb_mdl
from . import nvb_mtr
from . import nvb_def
from . import nvb_utils


class NVB_OT_mdlexport(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    """Export Aurora Engine model (.mdl)"""

    bl_idname = 'nvb.mdlexport'
    bl_label = 'Export Aurora MDL'
    bl_options = {'PRESET'}

    filename_ext = '.mdl'
    filter_glob = bpy.props.StringProperty(
            default='*.mdl',
            options={'HIDDEN'})
    # Misc Export Settings
    export_animations = bpy.props.BoolProperty(
            name='Export Animations',
            description='Export animations',
            default=True)
    export_walkmesh = bpy.props.BoolProperty(
            name='Export Walkmesh',
            description='Export a walkmesh',
            default=True)
    export_smoothgroups = bpy.props.BoolProperty(
            name='Export Smooth Groups',
            description='Generate smooth groups from sharp edges'
                        '(When disabled every face belongs to the same group)',
            default=True)
    export_normals = bpy.props.BoolProperty(
            name='Export Normals and Tangents',
            description='Add normals and tangents to MDL',
            default=False)
    # UV Map Export settings
    uv_autojoin = bpy.props.BoolProperty(
            name='Auto Join UVs',
            description='Join uv-vertices with identical coordinates',
            default=True)
    uv_mode = bpy.props.EnumProperty(
            name='Mode',
            description='Determines which meshes get uv maps',
            items=(('TEX', 'Textured Meshes',
                    'Add UV Maps only to textured and rendered meshes'),
                   ('REN', 'Rendered Meshes',
                    'Add UV Maps only to rendered meshes'),
                   ('ALL', 'All',
                    'Add UV Maps to all meshes')),
            default='REN')
    uv_order = bpy.props.EnumProperty(
            name='Order',
            description='Determines ordering of uv maps in MDL',
            items=(('AL0', 'Alphabetical',
                    'Alphabetical ordering'),
                   ('AL1', 'Alphabetical (Active First)',
                    'Alphabetical ordering, active UVMap will be first'),
                   ('ACT', 'Active Only',
                    'Export active UVMap only')),
            default='AL0')
    # Material Export Settings
    mtr_export = bpy.props.BoolProperty(
            name='Export MTR',
            description='Create MTR file holding material data (if specified)',
            default=True)
    mtr_ref = bpy.props.EnumProperty(
            name='Reference Mode',
            description='Specifies the way MTRs are referenced',
            items=(('bitmap', 'bitmap',
                    'Use "bitmap" to refernce MTRs'),
                   ('materialname', 'materialname',
                    'Use "materialname" to refernce MTRs')),
            default='bitmap')
    # Blender Setting to use
    apply_modifiers = bpy.props.BoolProperty(
            name='Apply Modifiers',
            description='Apply Modifiers before exporting',
            default=True)
    batch_mode = bpy.props.EnumProperty(
            name='Batch Mode',
            description='Export multiple MDLs',
            items=(('OFF', 'Off', 'Export active MDL only'),
                   ('SEL', 'Selected', 'Export selected MDLs'),
                   ('SCN', 'Scene', 'Export all MDLs in active scene')),
            default='OFF')

    def draw(self, context):
        """Draw the export UI."""
        layout = self.layout
        # Misc Export Settings
        box = layout.box()
        box.prop(self, 'export_animations')
        box.prop(self, 'export_walkmesh')
        box.prop(self, 'export_smoothgroups')
        box.prop(self, 'export_normals')
        # UV Map settings
        box = layout.box()
        box.label(text='UV Map Settings')
        sub = box.column()
        sub.prop(self, 'uv_autojoin')
        sub.prop(self, 'uv_mode')
        sub.prop(self, 'uv_order')
        # Material Export Settings
        box = layout.box()
        box.label(text='Material Settings')
        box.prop(self, 'mtr_export')
        sub = box.row(align=True)
        sub.active = self.mtr_export
        sub.prop(self, 'mtr_ref')
        # Blender Settings
        box = layout.box()
        box.label(text='Blender Settings')
        sub = box.column()
        sub.prop(self, 'apply_modifiers')
        sub.prop(self, 'batch_mode')

    def save_file(self, context, options):
        """TODO: DOC."""
        def get_filepath(old_path, new_name, new_ext):
            """Creates filenames for walkmeshes and batch export."""
            old_dir = os.path.dirname(old_path)
            new_name = new_name + new_ext
            return os.path.join(old_dir, new_name)

        def get_walkmeshtype(mdl_root):
            """Creates filenames for walkmeshes and batch export."""
            if mdl_root.nvb.classification == nvb_def.Classification.DOOR:
                return nvb_def.Walkmeshtype.DWK
            elif mdl_root.nvb.classification == nvb_def.Classification.TILE:
                return nvb_def.Walkmeshtype.WOK
            else:
                return nvb_def.Walkmeshtype.PWK

        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
        # Gather MDLs to export
        root_list = []
        if options.batch_mode == 'OFF':  # Get active object only
            root = nvb_utils.get_aurora_root(bpy.context.object)
            wkm_name = os.path.splitext(os.path.basename(options.filepath))[0]
            root_list.append((root, options.filepath, wkm_name))
        else:  # Get multiple objects
            obj_list = []
            if options.batch_mode == 'SCN':
                obj_list = bpy.context.scene.objects
            elif options.batch_mode == 'SEL':
                obj_list = bpy.context.selected.objects
            for obj in obj_list:
                root = nvb_utils.get_obj_aurora_root(obj)
                if root and (root not in root_list):
                    # Build a custom filename
                    mdl_path = get_filepath(options.filepath,
                                            root.name, '.mdl')
                    root_list.append((root, mdl_path, root.name))
        # Export MDLs
        for mdl_root, mdl_path, wkm_name in root_list:
            # print([mdl_root, mdl_path])
            options.mdlname = mdl_root.name
            options.filepath = mdl_path
            options.classification = mdl_root.nvb.classification
            # Export MDL
            ascii_lines = []
            nvb_mdl.Mdl.generateAscii(mdl_root, ascii_lines, options)
            with open(os.fsencode(options.filepath), 'w') as f:
                f.write('\n'.join(ascii_lines))
            # Export walkmesh for MDL
            if options.exportWalkmesh:
                wkm_type = get_walkmeshtype(mdl_root)
                wkm_ext = '.' + wkm_type
                ascii_lines = []
                nvb_mdl.Mdl.generateAsciiWalkmesh(mdl_root, ascii_lines,
                                                  wkm_type, options)
                if ascii_lines:
                    wkm_path = get_filepath(mdl_path, wkm_name, wkm_ext)
                    with open(os.fsencode(wkm_path), 'w') as f:
                        f.write('\n'.join(ascii_lines))
        # Export MTRs
        if options.mtr_export:
            for mat_name in options.mtrdb:
                mat = bpy.data.materials[mat_name]
                ascii_lines = nvb_mtr.Mtr.generateAscii(mat, options)
                mtr_path = get_filepath(options.filepath,
                                        mat.nvb.mtrname, '.mtr')
                with open(os.fsencode(mtr_path), 'w') as f:
                    f.write('\n'.join(ascii_lines))
        return {'FINISHED'}

    def execute(self, context):
        """TODO: DOC."""
        options = nvb_def.ExportOptions()
        options.filepath = self.filepath
        options.scene = context.scene
        # Misc Export Settings
        options.exportAnimations = self.export_animations
        options.exportWalkmesh = self.export_walkmesh
        options.exportSmoothGroups = self.export_smoothgroups
        options.exportNormals = self.export_normals
        # UV Map settings
        options.uvmapAutoJoin = self.uv_autojoin
        options.uvmapMode = self.uv_mode
        options.uvmapOrder = self.uv_order
        # Material Export Settings
        options.mtr_export = self.mtr_export
        options.mtr_ref = self.mtr_ref
        # Blender Settings
        options.apply_modifiers = self.apply_modifiers
        options.batch_mode = self.batch_mode
        return self.save_file(context, options)


class NVB_OT_mdlimport(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Import Aurora Engine model (.mdl)"""

    bl_idname = 'nvb.mdlimport'
    bl_label = 'Import Aurora MDL'
    bl_options = {'UNDO', 'PRESET'}

    filename_ext = '.mdl'
    filter_glob = bpy.props.StringProperty(default='*.mdl',
                                           options={'HIDDEN'})
    import_walkmesh = bpy.props.BoolProperty(
        name='Import Walkmesh',
        description='Load placeable and door walkmeshes',
        default=True)
    import_smoothgroups = bpy.props.BoolProperty(
        name='Import Smooth Groups',
        description='Import smooth groups as sharp edges',
        default=True)
    import_normals = bpy.props.BoolProperty(
        name='Import Normals',
        description='Import normals from MDL',
        default=True)
    # Materials Options
    mat_import = bpy.props.BoolProperty(
        name='Import Materials',
        description='Import materials and textures',
        default=True)
    mtr_import = bpy.props.BoolProperty(
        name='Load MTR files',
        description='Load external material files ' +
                    '(will overwride material in MDL)',
        default=True)
    mat_automerge = bpy.props.BoolProperty(
        name='Auto Merge Materials',
        description='Merge materials with same settings',
        default=True)
    tex_search = bpy.props.BoolProperty(
        name='Image Search',
        description='Search for images in subdirectories \
                     (Warning: May be slow)',
        default=False)
    # Animation Options
    anim_import = bpy.props.BoolProperty(
        name='Import Animations',
        description='Import animation data',
        default=True)
    fps_use = bpy.props.BoolProperty(name='Use Custom fps',
                                     description='Use custom fps value',
                                     default=True)
    fps = bpy.props.IntProperty(name='Scene Framerate',
                                description='Custom fps value',
                                default=30,
                                min=1, max=60)
    restpose = bpy.props.BoolProperty(
        name='Insert Rest Pose',
        description='Insert rest keyframe before every animation',
        default=True)
    # Blender Settings
    rotmode = bpy.props.EnumProperty(
            name='Rotation Mode',
            description='',
            items=(('AXIS_ANGLE', 'Axis Angle', ''),
                   ('QUATERNION', 'Quaternion', ''),
                   ('XYZ', 'Euler XYZ', '')),
            default='XYZ')
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
        box.prop(self, 'import_walkmesh')
        box.prop(self, 'import_smoothgroups')
        box.prop(self, 'import_normals')

        # Material Import Settings
        box = layout.box()
        box.prop(self, 'mat_import')
        sub = box.column()
        sub.enabled = self.mat_import
        sub.prop(self, 'mat_automerge')
        sub.prop(self, 'mtr_import')
        sub.prop(self, 'tex_search')

        # Animation Import Settings
        box = layout.box()
        box.prop(self, 'anim_import')
        sub1 = box.column()
        sub1.enabled = self.anim_import
        sub1.prop(self, 'restpose')
        row = sub1.row(align=True)
        row.prop(self, 'fps_use', text='')
        sub2 = row.row(align=True)
        sub2.enabled = self.fps_use
        sub2.prop(self, 'fps')

        # Blender Settings
        box = layout.box()
        box.label(text='Blender Settings')
        box.prop(self, 'rotmode')

    def load_mdl(self, context, options):
        """Called from blender ui."""
        mdl_path, mdl_filename = os.path.split(options.filepath)
        options.mdlname = os.path.splitext(mdl_filename)[0]

        with open(os.fsencode(options.filepath), 'r') as mdlfile:
            mdl = nvb_mdl.Mdl()
            asciiData = mdlfile.read()
            mdl.readAscii(asciiData, options)
            # Try to load walkmeshes ... pwk (placeable) and dwk (door)
            if options.importWalkmesh:
                for wkmtype in nvb_def.Walkmeshtype.IMPORT:
                    wkmFilename = options.mdlname + '.' + wkmtype
                    wkmPath = os.fsencode(os.path.join(mdl_path, wkmFilename))
                    try:
                        wkmFile = open(wkmPath, 'r')
                    except IOError:
                        pass  # There is no such file
                    else:
                        asciiData = wkmFile.read()
                        mdl.readAsciiWalkmesh(asciiData, wkmtype, options)
                        wkmFile.close()
            mdl.create(options)
        return {'FINISHED'}

    def execute(self, context):
        """TODO: DOC."""
        options = nvb_def.ImportOptions()
        options.filepath = self.filepath
        options.scene = context.scene
        # Misc Import Settings
        options.importWalkmesh = self.import_walkmesh
        options.importSmoothGroups = self.import_smoothgroups
        options.importNormals = self.import_normals
        # Material Options
        options.importMaterials = self.mat_import
        options.importMTR = self.mtr_import
        options.mat_automerge = self.mat_automerge
        options.tex_search = self.tex_search
        # Animation Options
        options.importAnimations = self.anim_import
        options.restpose = self.restpose
        options.customfps = self.fps_use
        options.fps = self.fps
        # Hidden settings for batch processing
        options.minimapMode = self.minimapMode
        options.minimapSkipFade = self.minimapSkipFade
        # Blender Settings
        options.rotmode = self.rotmode
        return self.load_mdl(context, options)
