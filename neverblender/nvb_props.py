"""TODO: DOC."""

import os
import platform

from . import bpy
from . import nvb_def
from . import nvb_utils


def NVB_psb_anim_target_poll(self, object):
    return nvb_utils.is_mdl_base(object)


def NVB_anim_root_obj_poll(self, object):
    return nvb_utils.get_obj_mdl_base(object) is not None


def NVB_psb_anim_mode_update(self, context):
    addon = context.preferences.addons[__package__]
    anim_mode = addon.preferences.util_psb_anim_mode
    if anim_mode == 'NLA_STRIPS' or anim_mode == 'NLA_TRACKS':
        addon.preferences.util_psb_insert_base = True


class NVB_OT_decompile_detect_options(bpy.types.Operator):
    """Reload set, update current data"""
    bl_idname = 'nvb.decompile_detect_options'
    bl_label = "Autodetect Command"

    @classmethod
    def poll(self, context):
        """Always ok to run."""
        return True

    def execute(self, context):
        """Reload the set file."""
        addon = context.preferences.addons[__package__]
        addon_prefs = addon.preferences
        compiler_path = addon_prefs.import_compiler_path

        print(compiler_path)
        # Without a path we can't do anything
        if not compiler_path:
            self.report({'ERROR'}, "No compiler path")
            return{'CANCELLED'}

        compiler_dir, compiler_filename = os.path.split(compiler_path) 

        # Known compilers are: cleanmodels and nwnmdlcomp
        compile_cmd = []
        if "cleanmodels" in compiler_filename.lower():
            compile_cmd = ["-d", "-i", "%in_dir%", "-o", "%out_dir%", "-p", "%in_filename%"] 
        elif "nwnmdlcomp" in compiler_filename.lower():
            compile_cmd = ["-d", "%in_path%", "%out_path%"]
        else:
            self.report({'ERROR'}, "Unknown compiler")
            return{'CANCELLED'}

        # If platform isn't windows and its an exe file: Add wine as a prefix
        if (platform.system() != "Windows") and (os.path.splitext(compiler_path)[1] == ".exe"):
            compile_cmd = ["wine", "%compiler%"] + compile_cmd

        addon_prefs.import_compiler_command = " ".join(compile_cmd)
        return {'FINISHED'}



class NVB_addon_properties(bpy.types.AddonPreferences):
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __package__

    compiler_path: bpy.props.StringProperty(name="Path to compiler",
                                            subtype='FILE_PATH')
    # Export preferences
    export_mat_mtr: bpy.props.BoolProperty(
        name="Export MTR files", default=True,
        description="Generate MTR files to hold materials data")  
    export_mat_mtr_ref: bpy.props.EnumProperty(
            name="MTR Reference",
            description="Specify the way MTR files are referenced from MDL files",
            items=[('bitmap',
                    "bitmap", "Use 'bitmap'", 0),
                   ('materialname',
                    "materialname", "Use 'materialname'", 1)],
            default='bitmap')
    export_mat_diffuse_ref: bpy.props.EnumProperty(
        name="Diffuse Reference",
        description="Specify the way the diffuse textures are referenced in the MDL",
        items=[('bitmap',
                "bitmap", "Diffuse as 'bitmap'", 0),
               ('texture0',
                "texture0", "Diffuse as 'texture0'", 1)],
        default='bitmap')
    export_smoothgroups_binary: bpy.props.BoolProperty(
        name="Binary Smoothing groups", default=True,
        description="Smoothing group IDs will be powers of two")
    export_smoothgroups_distinct_verts: bpy.props.BoolProperty(
        name="Distinct Smoothing groups", default=False,
        description="Smoothing group will never share a vertex")          
    export_wirecolor: bpy.props.BoolProperty(
        name="Object Color as Wirecolor", default=True,
        description="Use Blender's Object Color property to hold Wirecolor")
    export_metadata: bpy.props.BoolProperty(
        name="Export Metadata", default=True,
        description="Include export time and filedependancy in the mdl")      
    export_tileset_info: bpy.props.BoolProperty(
        name="Export Tileset Info", default=False,
        description="Create a tileset NFO file which holds data for generating set files")        

    # Import preferences
    import_placement: bpy.props.EnumProperty(
        name="Placement",
        description="Placement when importing multiple models",
        items=[('SPIRAL', "Spiral", "Spiral on a 10x10 Grid", 0),
               ('LINE', "Line", "Line with 10 units distance", 1) ],
        default='SPIRAL')
    import_mesh_validation: bpy.props.BoolProperty(
        name="Mesh Validation", default=False,
        description="Turn on Blenders mesh validation for imported geometry (Removes two sided faces)")
    import_mat_mtr: bpy.props.BoolProperty(
        name="Import mtr files", default=True,
        description="Import MTR files.")        
    import_ignore_mdl_diffuse_color: bpy.props.BoolProperty(
        name="Ignore diffuse color", default=False,
        description="Ignore diffuse color MDL parameter when importing")
    import_ignore_mdl_specular_color: bpy.props.BoolProperty(
        name="Ignore specular color", default=True,
        description="Ignore specular color MDL parameter when importing")
    import_ignore_mdl_ambient_color: bpy.props.BoolProperty(
        name="Ignore ambient color", default=True,
        description="Ignore ambient color MDL parameter when importing")
    import_compiler_use: bpy.props.BoolProperty(
        name="External Decompiler", default=False,
        description="Use external program for decompiling binary models")
    import_compiler_path: bpy.props.StringProperty(
        name="Decompiler Path", default="",
        description="Path to external decompiler",  
        subtype='FILE_PATH',
        options=set())
    import_compiler_command: bpy.props.StringProperty(
        name="Decompile Command", default="",
        description="Additional options for external (de)compiler",  
        subtype='NONE',
        options=set())

    # General Preferences
    dummy_type: bpy.props.EnumProperty(
        name="Dummy Type",
        description="Type of the Empty to use for Dummies",
        items=[('PLAIN_AXES', "Plain Axes", "", 0),
               ('ARROWS', "Arrows", "", 1),
               ('SINGLE_ARROW', "Single Arrow", "", 2),
               ('CIRCLE', "Circle", "", 3),
               ('CUBE', "Cube", "", 4),
               ('SPHERE', "Sphere", "", 5), ],
        default='PLAIN_AXES')
    dummy_size: bpy.props.FloatProperty(
        name='Dummy Size',
        description='Size of the Empty to use for Dummies',
        default=0.5, min=0.1, max=1.0)    
    mat_displacement_mode: bpy.props.EnumProperty(
        name="Displacement Mode",
        description="Usage of height/displacement maps",
        items=[('BUMP', "Bump", "Bump node connected to the shaders normal Socket", 0),
                ('DISPLACEMENT', "Displacement", "Displacement node connected to material output", 1), ],
        default='BUMP')

    # Object & Dummy Helper
    util_nodes_type: bpy.props.EnumProperty(
        name='Type',
        items=[(nvb_def.Walkmeshtype.PWK,
                'Placeable', 'Setup objects for placeables', 0),
               (nvb_def.Walkmeshtype.DWK,
                'Door', 'Setup objects for doors', 1),
               (nvb_def.Walkmeshtype.WOK,
                'Tile', 'Setup objects for tiles', 2), ],
        default=nvb_def.Walkmeshtype.PWK)
    util_nodes_dwk_mode: bpy.props.EnumProperty(
        name='Mode',
        items=[('gen_swing1',
                'Generic: Swinging',
                'Generic door swinging open both ways, two open states',
                0),
               ('gen_slide1',
                'Generic: Sliding',
                'Generic door sliding open, single opened state',
                1),
               ],
        default='gen_swing1')
    util_nodes_pwk_mode: bpy.props.EnumProperty(
        name='Mode',
        items=[('aabr',
                'Axis Aligned Bounding Box',
                'Objects will be enclosed in an axis aligned bounding box',
                0),
               ('mabr',
                'Minimum Area Bounding Box',
                'Objects will be enclosed in a minimum area bounding box',
                1),
               ('chull',
                'Convex Hull',
                'Objects will be enclosed in their convex hull',
                2),
               ],
        default='aabr')
    util_nodes_pwk_detect_islands: bpy.props.BoolProperty(
        name='Detect Islands', default=True,
        description='Detect vertex islands, create mutliple meshes')

    # Armature Helper
    util_amt_src: bpy.props.EnumProperty(
        name='Source',
        description='Source to take objects from',
        items=[('ALL', 'All', 'All objects in the mdl', 0),
               ('ACT', 'Active', 'Active object and its children', 1),
               ],
        default='ALL')
    util_amt_anim_mode: bpy.props.EnumProperty(
        name='Animations',
        description='Transfer animations to newly created objects',
        items=[('NONE', 'None', 'No animations transfer', 0),
               ('CONSTRAINT', 'Constraints', 'Create constraints', 1),
               ('ACTION', 'Keyframes',
                'Copy all keyframes to a single action', 2),
               ('NLA_STRIPS', 'NLA Strips (Single Track)',
                'Separate animation into multiple actions and add each ' +
                'to an NLA-strip in a single NLA-track', 3),
               ('NLA_TRACKS', 'NLA Tracks',
                'Separate animation into multiple actions and add each ' +
                'to an NLA-track', 4),
               ],
        default='ACTION')
    util_amt_connect: bpy.props.BoolProperty(
        name='Auto Connect', default=True,
        description='Connect bones when possible')
    util_amt_strip_name: bpy.props.BoolProperty(
        name='Strip Trailing', default=False,
        description='Strip trailing numbers from names')

    # Pseudo Bones Helper
    util_psb_insert_base: bpy.props.BoolProperty(
        name='Add Aurora Base', default=True,
        description='Add an aurora base holding animation and model data')
    util_psb_insert_root: bpy.props.BoolProperty(
        name='Add Rootdummy', default=True,
        description='Add an animation root (Empty) as a parent for all bones')
    util_psb_anim_mode: bpy.props.EnumProperty(
        name='Animations', description='Source to take animations from',
        items=[('ACTION', 'Active Action',
                'Take keyframes from currently active action', 0),
               ('NLA_STRIPS', 'NLA Strips',
                'Take keyframes from active NLA track, ' +
                'create an animation for each strip', 1),
               ('NLA_TRACKS', 'NLA Tracks',
                'Take keyframes from all NLA tracks, ' +
                'create an animation for each track', 2),
               ('NONE', 'No Animations',
                'Animations will not be copied', 3)],
        default='ACTION', update=NVB_psb_anim_mode_update)

    # Tile Slicer
    util_tsl_destructive: bpy.props.BoolProperty(
        name="Destructive", default=False,
        description="Create new objects instead of modifying existing ones")    
    util_tsl_target: bpy.props.EnumProperty(
        name="Target",
        description="Select the objects to slice",
        items=[('SCENE', "Scene", 
                "All Objects in current scene", 0),
               ('COLLECTION', "Active Collection",
                "All Objects in active collection", 1),
               ('SELECTED', "Selected", 
                "All selected objects", 2),
               ],
        default='SCENE')
    util_tsl_origin: bpy.props.EnumProperty(
        name="Origin",
        description="Objects affected by the tile slicer",
        items=[('AUTO', "Automatic", "Slice All Objects", 0),
               ('CURSOR', "3D cursor", "Only Slice Walkmeshes", 1)],
        default='AUTO')

    def draw(self, context):
        """Draw the addon prefences."""
        # Three colums: General, Import, Export
        layout = self.layout
        split = layout.split(factor=0.33)

        # General settings
        col = split.column()
        box = col.box()
        box.label(text='General')
        box.prop(self, 'mat_displacement_mode')

        box = col.box()
        box.label(text='Dummy Settings')
        box.prop(self, 'dummy_type', text="Type")
        box.prop(self, 'dummy_size', text="Size")

        
        # Import settings
        col = split.column()
        box = col.box()
        box.label(text='Import')
        box.prop(self, 'import_placement')
        box.prop(self, 'import_mesh_validation')

        box = col.box()
        box.label(text="Colors from MDL")        
        box.prop(self, 'import_ignore_mdl_diffuse_color', text="Ignore Diffuse")
        box.prop(self, 'import_ignore_mdl_specular_color', text="Ignore Specular")
        box.prop(self, 'import_ignore_mdl_ambient_color', text="Ignore Ambient")

        box = col.box()
        box.prop(self, 'import_compiler_use')
        sub = box.column()
        sub.active = self.import_compiler_use
        sub.prop(self, "import_compiler_path", text="Path")
        row = sub.row(align=True)
        row.prop(self, "import_compiler_command", text="Command")
        row.operator(NVB_OT_decompile_detect_options.bl_idname, icon='FILE_REFRESH', text='')

        # Export Settings
        col = split.column()
        box = col.box()
        box.label(text='Export')
        box.prop(self, 'export_mat_diffuse_ref')
        box.prop(self, 'export_wirecolor')
        box.prop(self, 'export_smoothgroups_binary')
        sub = box.row()
        sub.active = self.export_smoothgroups_binary
        sub.prop(self, 'export_smoothgroups_distinct_verts')
        box.prop(self, 'export_metadata')
        box.prop(self, 'export_tileset_info')

        box = col.box()
        box.prop(self, 'export_mat_mtr')
        sub = box.column()
        sub.active = self.export_mat_mtr
        sub.prop(self, "export_mat_mtr_ref")


class NVB_PG_animevent(bpy.types.PropertyGroup):
    """Properties for a single event in the even list."""

    name: bpy.props.StringProperty(name='Name', default='unnamed',
                                   description='Name for this event',
                                   options=set())
    frame: bpy.props.IntProperty(
        name='Frame', default=1,
        description='Frame at which the event should fire',
        options=set())


class NVB_PG_amt_event(bpy.types.PropertyGroup):
    """Properties for a single (armature) event in the even list."""

    name: bpy.props.StringProperty(name='Name', default='unnamed',
                                   description='Name for this event',
                                   options=set())
    fire: bpy.props.BoolProperty(
        name='Fire', default=False,
        description='Animate to make the event fire at the current frame')


class NVB_PG_anim(bpy.types.PropertyGroup):
    """Properties for a single animation in the animation list."""

    name: bpy.props.StringProperty(name='Name',
                                   description='Name of this animation',
                                   default='unnamed', options=set())
    ttime: bpy.props.FloatProperty(
        name='Transitiontime', subtype='TIME', options=set(),
        description='Blending time between animations in seconds',
        default=0.25, min=0.0, soft_max=60.0)
    transtime: bpy.props.FloatProperty(
        name='Transitiontime', subtype='TIME', options=set(),
        description='Blending time between animations in frames',
        default=7.5, min=0.0, soft_max=60.0)
    root: bpy.props.StringProperty(name='Root', default='', options=set(),
                                   description='Entry point of the animation')
    root_obj: bpy.props.PointerProperty(
        name='Root', description='Entry point of the animation',
        type=bpy.types.Object, options=set(), poll=NVB_anim_root_obj_poll)
    mute: bpy.props.BoolProperty(name='Export', default=False, options=set(),
                                 description='Export animation to MDL')
    frameStart: bpy.props.IntProperty(name='Start', default=0, options=set(),
                                      description='Animation Start', min=0)
    frameEnd: bpy.props.IntProperty(name='End', default=0, options=set(),
                                    description='Animation End', min=0)

    eventList: bpy.props.CollectionProperty(type=NVB_PG_animevent)
    eventListIdx: bpy.props.IntProperty(name='Index for event List',
                                        default=0, options=set())


class NVB_PG_mtrparameter(bpy.types.PropertyGroup):
    """Properties for a single parameter in the flare list."""
    ptype: bpy.props.EnumProperty(name='Type', description='Parameter type',
                                  items=[('float', 'float', 'float', 0),
                                         ('int', 'int', 'int', 1)],
                                  default='int', options=set())
    pname: bpy.props.StringProperty(name='Name',
                                    description='Parameter name',
                                    default='name', options=set())
    pvalue: bpy.props.StringProperty(name='Value',
                                     description='Parameter value',
                                     default='', options=set())


class NVB_PG_set_element(bpy.types.PropertyGroup):
    """Properties for a single flare in the flare list."""
    el_name: bpy.props.StringProperty(
        name='Name', description='Name of this element (only for display)',
        default='', options=set())
    el_size: bpy.props.StringProperty(
        name='Size', description='Size of this element (only for display)',
        default='', options=set())


class NVB_PG_scene(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for meshes, lamps and empties.
    """
    # Set loading (mass tile loading)
    set_filepath: bpy.props.StringProperty(name='Filepath',
                                           description='Path to SET file',
                                           default='', options=set())
    set_mode: bpy.props.EnumProperty(
        name='Set View Mode',
        items=[('GP', 'Groups', 'Display Groups', 0),
               ('TR', 'Terrains', 'Display terrain types', 1),
               ('CR', 'Crossers', 'Display crosser types', 2)],
        default='GP', options=set())
    set_group_list: bpy.props.CollectionProperty(type=NVB_PG_set_element)
    set_group_list_idx: bpy.props.IntProperty(name='SET Group list index',
                                              default=0, options=set())
    set_crosser_list: bpy.props.CollectionProperty(type=NVB_PG_set_element)
    set_crosser_list_idx: bpy.props.IntProperty(name='SET Crosser list index',
                                                default=0, options=set())
    set_terrain_list: bpy.props.CollectionProperty(type=NVB_PG_set_element)
    set_terrain_list_idx: bpy.props.IntProperty(name='SET Terrain list index',
                                                default=0, options=set())


class NVB_PG_material_mtr(bpy.types.PropertyGroup):
    """Holds additional properties needed for mtr files format.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for meshes, lamps and empties.
    """
    # MTR Panel
    use: bpy.props.BoolProperty(name='Use MTR',
                                description='Write date to MTR file',
                                default=True, options=set())
    # For gui editing
    shader_vs: bpy.props.StringProperty(name='Vertex Shader',
                                        description='Specify Vertex shader',
                                        default='', options=set())
    shader_fs: bpy.props.StringProperty(name='Fragment Shader',
                                        description='Specify Fragment shader',
                                        default='', options=set())
    shader_gs: bpy.props.StringProperty(name='Geometry Shader',
                                        description='Specify Geometry shader',
                                        default='', options=set())                                        
    param_list: bpy.props.CollectionProperty(type=NVB_PG_mtrparameter)
    param_list_idx: bpy.props.IntProperty(name='MTR parameter list index',
                                          default=0, options=set())

                                      
class NVB_PG_material(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    Main class for material properties, actual properties should be in
    parent modules to reduce clutter
    """
    mtr: bpy.props.PointerProperty(type=NVB_PG_material_mtr)


class NVB_PG_flare(bpy.types.PropertyGroup):
    """Properties for a single flare in the flare list."""
    texture: bpy.props.StringProperty(name='Texture',
                                      description='Texture name',
                                      default=nvb_def.null, options=set())
    size: bpy.props.FloatProperty(name='Size', description='Flare size',
                                  default=1, min=0)
    position: bpy.props.FloatProperty(name='Position', subtype='DISTANCE',
                                      description='Flare position',
                                      default=1, min=-1.0, max=1.0)
    colorshift: bpy.props.FloatVectorProperty(name='Colorshift',
                                              description='Colorshift',
                                              subtype='COLOR_GAMMA',
                                              default=(0.0, 0.0, 0.0),
                                              min=-1.0, max=2.0,
                                              soft_min=0.0, soft_max=1.0)


class NVB_PG_bone(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for bones.
    """
    # Armature Helper
    psd_bone_shape: bpy.props.EnumProperty(
        name='Bone Shape', description='Shape for the Pseudo-Bone',
        items=[('EMT', 'Empty', 'Converts bone to an empty', 0),
               ('ME1', 'Mesh (Octahedron)', 'Convert bone to an octahedron', 1)
               ],
        default='ME1', options=set())


class NVB_PG_emitter(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    This class defines all additional properties needed by the mdl file
    format for emitters.
    """
    # Emitter Properties
    update: bpy.props.EnumProperty(
        name='Update',
        items=[('fountain', 'Fountain',
                'Emit in a fountain shape, based on the spread value', 1),
               ('single', 'Single',
                'Emit a single particle', 2),
               ('explosion', 'Explosion',
                'Triggered by a detonate event', 3),
               ('lightning', 'Lightning',
                'Two-Point lightning effect, requires a reference node', 4)],
        default='fountain', options=set())
    loop: bpy.props.BoolProperty(
        name='Loop',
        description='Emits multiple particles if update is set to Single',
        default=False, options=set())
    render: bpy.props.EnumProperty(
        name='Render',
        items=[('normal', 'Normal',
                'Particles face camera', 1),
               ('linked', 'Linked',
                'Particles face camera and are stretched to link', 2),
               ('billboard_to_local_z', 'Billboard to Local Z',
                'Particles preserve their facing from birth', 3),
               ('billboard_to_world_z', 'Billboard to World Z',
                'Partciles face up', 4),
               ('aligned_to_world_z', 'Aligned to World Z',
                'TODO: Unknown', 5),
               ('aligned_to_particle_dir', 'Aligned to Particle',
                'Particles align to their angle at birth', 6),
               ('motion_blur', 'Motion Blur',
                'Stretch and overlap particles', 7),
               ],
        default='normal', options=set())
    blend: bpy.props.EnumProperty(
        name='Blend',
        items=[('normal', "Normal",
                "No blending", 1),
               ('punch_through', "Punch-Through",
                "TODO: Unknown", 2),
               ('lighten', "Lighten",
                "Uses lighten blending mode", 3),
               ],
        default='normal', options=set())
    spawntype: bpy.props.EnumProperty(
        name='Spawn Type',
        items=[('0', 'Normal',
                'Emit particles based on birthrate', 0),
               ('1', 'Trail',
                'Emit particles based on amount per meter', 1),
               ('-1', 'Invalid',
                'Invalid Spawntype', -1),                
               ],
        default='0', options=set())
    renderorder: bpy.props.IntProperty(
        name='Render Order',
        description='Helps the engine priotize emitters, \
                     lower order = higher priority',
        default=0, min=0, options=set())

    # Particle Properties
    birthrate: bpy.props.IntProperty(name='Birthrate',
                                     default=1, min=0)
    lifeexp: bpy.props.FloatProperty(name='Life Exp.', subtype='TIME',
                                     default=0.0, min=-1.0)
    mass: bpy.props.FloatProperty(
        name='Mass',
        description='Weight of the particles, \
		             Negative numbers make the particles float up',
        default=0.0)
    # velocity => from blender ".normal_factor"
    # randvel => from blender ".factor_random"
    # particleRot => from blender ".angular_velocity_factor"
    spread: bpy.props.FloatProperty(
        name='Spread',
        description='Particle spread angle for Fountain type emitters',
        subtype='ANGLE', unit='ROTATION',
        default=0.0, min=0.0, soft_max=6.29)
    splat: bpy.props.BoolProperty(
        name='Splat',
        description='On collision the particle is placed flat (face up) \
                     on the contacting surface',
        default=False, options=set())
    affectedbywind: bpy.props.BoolProperty(
        name='Affected by Wind',
        description='Wind effects affect the particles',
        default=False, options=set())
    colorstart: bpy.props.FloatVectorProperty(
        name='Color Start', description='Particle color at birth',
        subtype='COLOR_GAMMA', size=3,
        default=(1.0, 1.0, 1.0), min=0.0, soft_max=1.0, max=2.0)
    colorend: bpy.props.FloatVectorProperty(
        name='Color End', description='Particle color at death',
        subtype='COLOR_GAMMA', size=3,
        default=(1.0, 1.0, 1.0), min=0.0, soft_max=1.0, max=2.0)
    alphastart: bpy.props.FloatProperty(
        name='Alpha Start', description='Particle alpha at birth',
        default=1, min=0.0, max=1.0)
    alphaend: bpy.props.FloatProperty(
        name='Alpha End', description='Particle alpha at death',
        default=1.0, min=0.0, max=1.0)
    sizestart: bpy.props.FloatProperty(
        name='Start x-Size', description='Particle size at birth',
        default=1.0, min=0.0)
    sizeend: bpy.props.FloatProperty(
        name='Start x-Size', description='Particle size at death',
        default=1.0, min=0.0)
    sizestart_y: bpy.props.FloatProperty(
        name='Start y-Size', description='Particle size at birth',
        default=1.0, min=0.0)
    sizeend_y: bpy.props.FloatProperty(
        name='Start y-Size', description='Particle size at death',
        default=1.0, min=0.0)
    bounce: bpy.props.BoolProperty(
        name='Bounce',
        description='The particles bounce against static walkmeshes',
        default=False, options=set())
    bounce_co: bpy.props.FloatProperty(
        name='Bounce coefficient',
        description='How much each particle bounces',
        default=0.0)
    blurlength: bpy.props.FloatProperty(
        name='Blur Length', subtype='DISTANCE', description='???',
        default=0.0, min=0.0)
    deadspace: bpy.props.FloatProperty(
        name='Dead Space', description='???',
        default=0.0)
    # Texture Properties
    particletype: bpy.props.EnumProperty(
        name='Type',
        items=[('texture', 'Texure',
                'Textured Particles', 0),
               ('chunk', 'Chunk',
                'Particle shape based on MDL file', 1),
               ],
        default='texture', options=set())
    texture: bpy.props.StringProperty(name='Texture',
                                      description='Texture name',
                                      subtype='FILE_NAME', maxlen=64,
                                      default=nvb_def.null, options=set())
    chunkname: bpy.props.StringProperty(name='Chunk Name',
                                    description='Model name for a chunk',
                                    subtype='FILE_NAME', maxlen=16,
                                    default=nvb_def.null, options=set())
    twosidedtex: bpy.props.BoolProperty(
        name='Two Sided',
        description='Texture is visible from both sides',
        default=False, options=set())
    m_istinted: bpy.props.BoolProperty(
        name='Tinted',
        description='Tint the particles with the ambient color of the scene',
        default=False, options=set())
    # Texture animation properties
    xgrid: bpy.props.IntProperty(name='X Grid', description='Texture grid',
                                 default=1, min=0)
    ygrid: bpy.props.IntProperty(name='Y Grid', description='Texture grid',
                                 default=1, min=0)
    fps: bpy.props.FloatProperty(
        name='Speed',
        description='FPS value used to cycle between frames',
        default=0.0, min=0.0)
    framestart: bpy.props.IntProperty(
        name='Frame Start',
        description='Starting frame in texture grid',
        default=0, min=0)
    frameend: bpy.props.IntProperty(
        name='Frame End',
        description='Ending frame in texture grid',
        default=0, min=0)
    random: bpy.props.BoolProperty(
        name='Random Frame',
        description='Display a random frame from the texture grid',
        default=False, options=set())
    # Point to Point Properties
    p2p: bpy.props.BoolProperty(
        name='P2P',
        description='Point to Point emitter',
        default=False, options=set())
    p2p_sel: bpy.props.EnumProperty(
        name='P2P Type',
        items=[('0', 'Undefined (?)',
                'Gravity? Undefined? Unused? nobody knows', 0),
               ('1', 'Bezier',
                '', 1),
               ('2', 'Gravity',
                '', 2),
               ],
        default='1', options=set())
    p2p_bezier2: bpy.props.FloatProperty(
        name='Source', subtype='DISTANCE',
        description='Source Bezier Handle',
        default=0.0, min=0.0)  # Bezier type p2p
    p2p_bezier3: bpy.props.FloatProperty(
        name='Target', subtype='DISTANCE',
        description='Target Bezier Handle',
        default=0.0, min=0.0)  # Bezier type p2p
    combinetime: bpy.props.FloatProperty(
        name='Combine Time', subtype='TIME',
        description='Time for the particles to reach the reference node',
        default=0.0, min=0.0)  # Bezier type p2p
    grav: bpy.props.FloatProperty(
        name='Gravity',
        description='Particles are pulled towards the reference node',
        default=0.0)  # Gravity type p2p
    drag: bpy.props.FloatProperty(
        name='Drag',
        description='Particles overshoot the reference node and double back',
        default=0.0)  # Gravity type p2p
    threshold: bpy.props.FloatProperty(
        name='Threshold', subtype='DISTANCE',
        description='Distance from the gravity point that the particle will \
                     be killed off from. A value of 0 will let the particles \
                     pass through the gravity center and loop back',
        default=0.0, min=0.0)  # Gravity type p2p
    # Blast properties
    blastradius: bpy.props.FloatProperty(
        name='Radius', subtype='DISTANCE', description='???',
        default=0.0, min=0.0)
    blastlength: bpy.props.FloatProperty(
        name='Length', subtype='DISTANCE', description='???',
        default=0.0, min=0.0)

    # Lightning properties
    lightningdelay: bpy.props.FloatProperty(
        name='Delay', subtype='TIME',
        description='???',
        default=0.0, min=0.0)
    lightningradius: bpy.props.FloatProperty(
        name='Radius', subtype='DISTANCE', description='???',
        default=0.0, min=0.0)
    lightningscale: bpy.props.FloatProperty(
        name='Scale', subtype='DISTANCE', description='???',
        default=0.0, min=0.0)

    # Inheritance
    inherit: bpy.props.BoolProperty(
        name='Inherit',
        description='Particles inherit the emitters Z axis',
        default=False, options=set())
    inheritvel: bpy.props.BoolProperty(
        name='Inherit Velocity',
        description='Particles inherit velocity from emitter object',
        default=False, options=set())
    inherit_local: bpy.props.BoolProperty(
        name='Inherit Local',
        description='Particles inherit the emitters Z axis',
        default=False, options=set())
    inherit_part: bpy.props.BoolProperty(
        name='Inherit Particle',
        description='The particle stretches depending on its speed',
        default=False, options=set())  # Combine with inherit velocity


class NVB_PG_lamp(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for lamps.
    """
    shadow: bpy.props.BoolProperty(name='Shadow',
                                   description='Whether to cast shadows',
                                   default=True, options=set())
    ambientonly: bpy.props.BoolProperty(
                name='Ambient Only',
                description='Light will be ignored for shadow casting',
                default=False, options=set())
    lightpriority: bpy.props.IntProperty(name='Lightpriority',
                                         default=5, min=1, max=5,
                                         options=set())
    fadinglight: bpy.props.BoolProperty(name='Fading light',
                                        default=True, options=set())
    isdynamic: bpy.props.BoolProperty(name='Dynamic',
                                      description='Set this to 1 for animated lights and 0 for (tile) manin lights',
                                      default=True, options=set())
    affectdynamic: bpy.props.BoolProperty(
                name='Affect Dynamic',
                description='Affect dynamic objects',
                default=True, options=set())
    negativelight: bpy.props.BoolProperty(name='Negative Light',
                                          default=False, options=set())
    uselensflares: bpy.props.BoolProperty(name='Lensflares',
                                          default=False, options=set())
    flareradius: bpy.props.FloatProperty(
                name='Flare Radius',
                default=0.0, min=0.0, max=100.0, options=set())
    flareList: bpy.props.CollectionProperty(type=NVB_PG_flare)
    flareListIdx: bpy.props.IntProperty(name='Index for flare list',
                                        default=0, options=set())


class NVB_PG_object_nfo(bpy.types.PropertyGroup):
    """Holds additional per object data needed for NFO files.

    NFO files are used ba external tools and NeverBlender to store additional
    data for mdl files.
    """    

    # Setfile: Nodes
    set_tile_pathnode: bpy.props.EnumProperty(name='Pathnode',
                                              items=nvb_def.pathnodes,
                                              default=nvb_def.pathnodes[0][0], options=set())    
    set_tile_pathnode_orientation: bpy.props.IntProperty(name="Orientation",
                                                    description="Pathnode Orientation",
                                                    default=0, min=0, max=270, step=90, 
                                                    options=set())
    set_tile_visnode_differs: bpy.props.BoolProperty(name="Differing Visibility Node",
                                                description="Use a visibility node different from pathnode",
                                                default=False, options=set())
    set_tile_visnode_orientation: bpy.props.IntProperty(name="Orientation",
                                                   description="Visibility Node Orientation",
                                                   default=0, min=0, max=270, step=90, 
                                                   options=set())
    set_tile_doornode_differs: bpy.props.BoolProperty(name="Differing Door Node",
                                                      description="Use a door node different from pathnode",
                                                      default=False, options=set())
    set_tile_doornode_orientation: bpy.props.IntProperty(name="Orientation",
                                                         description="Visibility Node Orientation",
                                                         default=0, min=0, max=270, step=90, 
                                                         options=set())  
    # Setfile: Height data                                                 
    set_tile_height_offset: bpy.props.IntProperty(name="Height Offset",
                                                  description="Z-offset to base tile floor",
                                                  default=0, soft_min=-10, soft_max=20, step=1, 
                                                  options=set())
    set_tile_height_auto: bpy.props.BoolProperty(name="Auto tile height",
                                                 description="Corner Height from Walkmesh and offset",
                                                 default=True, options=set())    
    set_tile_height: bpy.props.IntVectorProperty(name="Height",
                                                 description="Z-offset to base tile floor",
                                                 default = (0,0,0,0), soft_min=-10, soft_max=20, step=1, 
                                                 size=4, options=set())
    # Setfile: Tile Crossers
    set_tile_crosser_top: bpy.props.StringProperty(name="Top", 
                                                   description="Crosser: Top",
                                                   default="",
                                                   options=set())  
    set_tile_crosser_right: bpy.props.StringProperty(name="Right", 
                                                     description="Crosser: Right",
                                                     default="",
                                                     options=set())                                                                                                  
    set_tile_crosser_bottom: bpy.props.StringProperty(name="Bottom", 
                                                      description="Crosser: Bottom",
                                                      default="",
                                                      options=set())                                                   
    set_tile_crosser_bottom: bpy.props.StringProperty(name="Bottom", 
                                                      description="Crosser: Bottom",
                                                      default="",
                                                      options=set())
    # Setfile: Tile Neighbouring Terrains
    set_tile_terrain_topleft: bpy.props.StringProperty(name="Top Left", 
                                                       description="Terrain: Top Left",
                                                       default="",
                                                       options=set())  
    set_tile_terrain_bottomleft: bpy.props.StringProperty(name="Bottom Left", 
                                                          description="Terrain: Bottom Left",
                                                          default="",
                                                          options=set())
    set_tile_terrain_bottomright: bpy.props.StringProperty(name="Bottom Right", 
                                                           description="Terrain: Bottom Right",
                                                           default="",
                                                           options=set())
    set_tile_terrain_topright: bpy.props.StringProperty(name="Top Right", 
                                                        description="Terrain: Top Right",
                                                        default="",
                                                        options=set())


class NVB_PG_object_danglymesh(bpy.types.PropertyGroup):
    """Holds additional properties needed for danglymeshes.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for meshes, lamps and empties.
    """    
    period: bpy.props.FloatProperty(name='Period',
                                    default=1.0, min=0.0, max=32.0)
    tightness: bpy.props.FloatProperty(name='Tightness',
                                       default=1.0, min=0.0, max=32.0)
    displacement: bpy.props.FloatProperty(name='Displacement',
                                          default=0.5, min=0.0, max=32.0)
    constraints: bpy.props.StringProperty(
                name='Danglegroup',
                description='Name of the vertex group to use for the weights',
                default='', options=set())


class NVB_PG_object_animation(bpy.types.PropertyGroup):
    """TODO: Move animation stuff here and use PointerProperty.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for meshes, lamps and empties.
    """    
    pass


class NVB_PG_object_dummy(bpy.types.PropertyGroup):
    """TODO: Move dummy stuff here and use PointerProperty.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for meshes, lamps and empties.
    """    
    emptytype: bpy.props.EnumProperty(
                name='Type',
                items=[(nvb_def.Emptytype.DUMMY,
                        'Dummy',
                        'Simple dummy object', 0),
                       (nvb_def.Emptytype.REFERENCE,
                        'Reference node',
                        'Used in spells. Default value "fx_ref"', 1),
                       (nvb_def.Emptytype.PATCH,
                        'Patch node',
                        'Unknown purpose', 2),
                       (nvb_def.Emptytype.DWK,
                        'DWK Base (Door  Walkmesh)',
                        'All children are part of the walkmesh', 3),
                       (nvb_def.Emptytype.PWK,
                        'PWK Base (Placeable Walkmesh)',
                        'All children are part of the walkmesh', 4)],
                default=nvb_def.Emptytype.DUMMY, options=set())


class NVB_PG_object_auroraroot(bpy.types.PropertyGroup):
    """TODO: Move aurora root stuff here and use PointerProperty.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for meshes, lamps and empties.
    """        
    classification: bpy.props.EnumProperty(
                name='Classification',
                items=[(nvb_def.Classification.UNKNOWN,
                        'Unknown', 'Unknown classification', 0),
                       (nvb_def.Classification.TILE,
                        'Tile', 'Tiles for tilesets', 1),
                       (nvb_def.Classification.CHARACTER,
                        'Character', 'Creatures, characters or placeables', 2),
                       (nvb_def.Classification.DOOR,
                        'Door', 'Doors', 3),
                       (nvb_def.Classification.EFFECT,
                        'Effect', 'Effects', 4),
                       (nvb_def.Classification.GUI,
                        'Gui', 'Gui', 5),
                       (nvb_def.Classification.ITEM,
                        'Item', 'Items or placeables', 6),
                       (nvb_def.Classification.OTHER,
                        'Other', '', 7)                        
                       ],
                default=nvb_def.Classification.CHARACTER, options=set())
    supermodel: bpy.props.StringProperty(
        name='Supermodel',
        description='Name of the model to inherit animations from',
        default=nvb_def.null, subtype='FILE_NAME', options=set())
    animscale: bpy.props.FloatProperty(
                name='Animationscale',
                description='Animation scale for supermodel animations',
                default=1.00, min=0.0, soft_max=10.0,
                subtype='FACTOR', options=set())


class NVB_PG_object(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for meshes, lamps and empties.
    """

    nfo: bpy.props.PointerProperty(type=NVB_PG_object_nfo)
    
    # Helper properties to store additional values. Cannot be edited.
    restrot: bpy.props.FloatVectorProperty(name='Rest Pose Rotation',
                                           size=4,
                                           default=(0.0, 0.0, 0.0, 0.0),
                                           options=set())
    restloc: bpy.props.FloatVectorProperty(name='Rest Pose Location',
                                           size=3,
                                           default=(0.0, 0.0, 0.0),
                                           options=set())
    imporder: bpy.props.IntProperty(
        name='Export Order',
        description='Custom Position of this object within the MDL file',
        default=1000, options={'SKIP_SAVE'})
    # For all emptys
    emptytype: bpy.props.EnumProperty(
                name='Type',
                items=[(nvb_def.Emptytype.DUMMY,
                        'Dummy',
                        'Simple dummy object', 0),
                       (nvb_def.Emptytype.REFERENCE,
                        'Reference node',
                        'Used in spells. Default value "fx_ref"', 1),
                       (nvb_def.Emptytype.PATCH,
                        'Patch node',
                        'Unknown purpose', 2),
                       (nvb_def.Emptytype.DWK,
                        'DWK Base (Door  Walkmesh)',
                        'All children are part of the walkmesh', 3),
                       (nvb_def.Emptytype.PWK,
                        'PWK Base (Placeable Walkmesh)',
                        'All children are part of the walkmesh', 4)],
                default=nvb_def.Emptytype.DUMMY, options=set())
    # For Aurora Root
    classification: bpy.props.EnumProperty(
                name='Classification',
                items=[(nvb_def.Classification.UNKNOWN,
                        'Unknown', 'Unknown classification', 0),
                       (nvb_def.Classification.TILE,
                        'Tile', 'Tiles for tilesets', 1),
                       (nvb_def.Classification.CHARACTER,
                        'Character', 'Creatures, characters or placeables', 2),
                       (nvb_def.Classification.DOOR,
                        'Door', 'Doors', 3),
                       (nvb_def.Classification.EFFECT,
                        'Effect', 'Effects', 4),
                       (nvb_def.Classification.GUI,
                        'Gui', 'Gui', 5),
                       (nvb_def.Classification.ITEM,
                        'Item', 'Items or placeables', 6)
                       ],
                default=nvb_def.Classification.UNKNOWN, options=set())
    supermodel: bpy.props.StringProperty(
        name='Supermodel',
        description='Name of the model to inherit animations from',
        default=nvb_def.null, subtype='FILE_NAME', options=set())
    animscale: bpy.props.FloatProperty(
                name='Animationscale',
                description='Animation scale for supermodel animations',
                default=1.00, min=0.0, soft_max=10.0,
                subtype='FACTOR', options=set())
    # Animation Data (for separation)
    animList: bpy.props.CollectionProperty(type=NVB_PG_anim)
    animListIdx: bpy.props.IntProperty(name='Index for anim List',
                                       default=0, options=set())

    use_amt_events: bpy.props.BoolProperty(
        name='Keyframed Events', description='Use keyframes for events',
        default=False, options=set())
    # Animation Events for armatures only (nla mode)
    amt_event_list: bpy.props.CollectionProperty(type=NVB_PG_amt_event)
    amt_event_list_idx: bpy.props.IntProperty(name='Index for event List',
                                              default=0, options=set())

    # For reference emptys
    refmodel: bpy.props.StringProperty(name='Reference Model',
                                       description='Name of MDL file',
                                       maxlen=64,
                                       default='fx_ref', options=set())
    reattachable: bpy.props.BoolProperty(name='Reattachable',
                                         default=False, options=set())

    # Pseudo Bones Helper
    util_psb_anim_target: bpy.props.PointerProperty(
        name='Target', description='Specify target to copy animations to',
        type=bpy.types.Object, options={'SKIP_SAVE'},
        poll=NVB_psb_anim_target_poll)
    # For mesh objects
    meshtype: bpy.props.EnumProperty(
                name='Type',
                items=[(nvb_def.Meshtype.TRIMESH, 'Trimesh',
                       'Deafult type of Mesh', 0),
                       (nvb_def.Meshtype.DANGLYMESH, 'Danglymesh',
                       'desc', 1),
                       (nvb_def.Meshtype.SKIN, 'Skinmesh',
                       'desc', 2),
                       (nvb_def.Meshtype.AABB, 'AABB',
                       'Walkmesh for tilesets', 3),
                       (nvb_def.Meshtype.EMITTER, 'Emitter',
                       'desc', 4),
                       (nvb_def.Meshtype.ANIMMESH, 'Animesh',
                       'Mesh with animatable uv coordinates or vertices', 5)],
                default=nvb_def.Meshtype.TRIMESH, options=set())
    smoothgroup: bpy.props.EnumProperty(
                name='Smoothgroup',
                items=[('SEPR',
                        'Seperate', 'Each face has it\'s own group', 0),
                       ('SING',
                        'Single', 'All faces belong to the same group', 1),
                       ('AUTO',
                        'Auto', 'Generate groups from sharp edges', 2)
                       ],
                default='AUTO', options=set())
    shadow: bpy.props.BoolProperty(name='Shadow',
                                   description='Whether to cast shadows',
                                   default=False, options=set())
    render: bpy.props.BoolProperty(name='Render',
                                   description='Render object',
                                   default=True, options=set())
    tilefade: bpy.props.EnumProperty(
                name='Tilefade',
                items=[(nvb_def.Tilefade.NONE,
                        'None', 'Tilefade disabled', 0),
                       (nvb_def.Tilefade.FADE,
                        'Fade', 'Tilefade enabled', 1),
                       (nvb_def.Tilefade.BASE,
                        'Base', '???', 2),
                       (nvb_def.Tilefade.NEIGHBOUR,
                        'Neighbour', 'Tilefade if Neighbouring Tile fades', 3)
                       ],
                default=nvb_def.Tilefade.NONE, options=set())
    beaming: bpy.props.BoolProperty(name='beaming',
                                    description='Object casts beams',
                                    default=False, options=set())
    inheritcolor: bpy.props.BoolProperty(name='Inheritcolor',
                                         description='Unused',
                                         default=False, options=set())
    rotatetexture: bpy.props.BoolProperty(
                name='Rotatetexture',
                description='Automatically rotates texture to prevent seams',
                default=False, options=set())
    transparencyhint: bpy.props.IntProperty(
                name='Transparency Hint',
                description='Order of transparency evaluation',
                default=0, min=0, max=32, options=set())
    selfillumcolor: bpy.props.FloatVectorProperty(
                name='Selfilluminationcolor',
                description='Makes the object glow but does not emit light',
                subtype='COLOR_GAMMA',
                default=(0.0, 0.0, 0.0), options={'ANIMATABLE'},
                min=0.0, max=2.0, soft_min=0.0, soft_max=1.0)
    shininess: bpy.props.IntProperty(name='Shininess',
                                     description='Used with txi file',
                                     default=1, min=0, max=32, options=set())
    # For Animeshes
    aurorashapekey: bpy.props.StringProperty(
        name='Shapekey',
        description='Shape key to use for animated vertices',
        default='', options=set())

    # For danglymeshes
    period: bpy.props.FloatProperty(name='Period',
                                    default=1.0, min=0.0, max=32.0)
    tightness: bpy.props.FloatProperty(name='Tightness',
                                       default=1.0, min=0.0, max=32.0)
    displacement: bpy.props.FloatProperty(name='Displacement',
                                          default=0.5, min=0.0, max=32.0)
    constraints: bpy.props.StringProperty(
                name='Danglegroup',
                description='Name of the vertex group to use for the weights',
                default='', options=set())

    # For lamps
    lighttype: bpy.props.EnumProperty(
                name='Type',
                items=[(nvb_def.Lighttype.DEFAULT,
                        'Default', 'Simple light', 0),
                       (nvb_def.Lighttype.MAIN1,
                        'Mainlight 1', 'For tiles (Editable in toolset)', 1),
                       (nvb_def.Lighttype.MAIN2,
                        'Mainlight 2', 'For tiles (Editable in toolset)', 2)],
                default=nvb_def.Lighttype.DEFAULT, options=set())
