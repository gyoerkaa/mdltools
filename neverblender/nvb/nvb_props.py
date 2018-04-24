"""TODO: DOC."""

import bpy
from . import nvb_def


class NVB_PG_animevent(bpy.types.PropertyGroup):
    """Properties for a single event in the even list."""

    name = bpy.props.StringProperty(
                name='Name',
                description='Name for this event',
                default='Unnamed')

    frame = bpy.props.IntProperty(
                name='Frame',
                description='Frame at which the event should fire',
                default=1)


class NVB_PG_anim(bpy.types.PropertyGroup):
    """Properties for a single animation in the animation list."""

    name = bpy.props.StringProperty(
                name='Name',
                description='Name for this event',
                default='Unnamed')
    ttime = bpy.props.FloatProperty(
                name='Transitiontime',
                description='Used for for animations only',
                default=0.25, min=0.0)
    root = bpy.props.StringProperty(
                name='Root',
                description='Entry point of the animation',
                default='')
    mute = bpy.props.BoolProperty(
                name='Mute',
                description='Ignore animation during export',
                default=False)
    markerStart = bpy.props.StringProperty(
                name='Start Marker',
                description='Start marker in the timeline',
                default='')
    rawascii = bpy.props.StringProperty(
                name='Emitter Data',
                description='Incompatible Emitter data loaded as plain text',
                default='')
    frameStart = bpy.props.IntProperty(
                name='Start',
                description='Animation Start',
                default=0,
                min=0)
    frameEnd = bpy.props.IntProperty(
                name='End',
                description='Animation End',
                default=0,
                min=0)

    eventList = bpy.props.CollectionProperty(type=NVB_PG_animevent)
    eventListIdx = bpy.props.IntProperty(
        name='Index for event List',
        default=0)


class NVB_PG_mtrparameter(bpy.types.PropertyGroup):
    """Properties for a single parameter in the flare list."""
    ptype = bpy.props.EnumProperty(
        name='Type',
        description='Parameter type',
        items=[('float', 'float', 'float', 0),
               ('int', 'int', 'int', 1)],
        default='int')
    pname = bpy.props.StringProperty(name='Name',
                                     description='Parameter name',
                                     default='name')
    pvalue = bpy.props.StringProperty(name='Value',
                                      description='Parameter value',
                                      default='')


class NVB_PG_material(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for meshes, lamps and empties.
    """
    ambient_color = bpy.props.FloatVectorProperty(
        name='Ambient',
        description='Ambient color of the material',
        subtype='COLOR_GAMMA',
        default=(1.0, 1.0, 1.0),
        min=0.0, max=1.0,
        soft_min=0.0, soft_max=1.0)
    ambient_intensity = bpy.props.FloatProperty(
        subtype='FACTOR',
        name='Intensity',
        description='Amount of ambient color',
        precision=3,
        default=1.0,
        min=0.0, max=1.0,
        soft_min=0.0, soft_max=1.0)
    ambient_shader = bpy.props.EnumProperty(
        name='Ambient Shader Model',
        description='Ambient Shader Model',
        items=[('LAMBERT', 'Lambert', 'Use a Lambertian shader', 0)],
        default='LAMBERT')
    use_ambient_ramp = bpy.props.BoolProperty(
        name='Ramp',
        description='Toggle ambient ramp options',
        default=False)
    renderhint = bpy.props.EnumProperty(
        name='Renderhint',
        items=[('AUTO', 'Auto', 'Depending on number of textures', 0),
               ('NONE', 'None', 'No renderhint', 1),
               ('NASM', 'NormalAndSpecMapped', 'Normal & Specular Mapped', 2)],
        default='AUTO')
    # MTR Panel
    usemtr = bpy.props.BoolProperty(name='Use MTR',
                                    description='Use external MTR file',
                                    default=False)
    mtrname = bpy.props.StringProperty(name='Name',
                                       description='Data name',
                                       default='')
    mtrsrc = bpy.props.EnumProperty(
        name='Source',
        items=[('TEXT', 'Text', 'From text block', 0),
               ('FILE', 'File', 'From file', 1)],
        default='FILE')
    mtrtext = bpy.props.StringProperty(name='Text Block',
                                       description='Blender Text Block',
                                       default='')
    mtrpath = bpy.props.StringProperty(name='Filepath',
                                       description='Path to MTR file',
                                       default='')
    # For gui editing
    shadervs = bpy.props.StringProperty(name='Vertex Shader',
                                        description='Specify Vertex shader',
                                        default='')
    shaderfs = bpy.props.StringProperty(name='Fragment Shader',
                                        description='Specify Fragment shader',
                                        default='')
    mtrparam_list = bpy.props.CollectionProperty(type=NVB_PG_mtrparameter)
    mtrparam_list_idx = bpy.props.IntProperty(name='Index for parameter list',
                                              default=0)


class NVB_PG_flare(bpy.types.PropertyGroup):
    """Properties for a single flare in the flare list."""
    texture = bpy.props.StringProperty(name='Texture',
                                       description='Texture name',
                                       default=nvb_def.null)
    size = bpy.props.FloatProperty(name='Size',
                                   description='Flare size',
                                   default=1,
                                   min=0)
    position = bpy.props.FloatProperty(name='Position',
                                       description='Flare position',
                                       default=1,
                                       min=-1.0, max=1.0)
    colorshift = bpy.props.FloatVectorProperty(name='Colorshift',
                                               description='Colorshift',
                                               subtype='COLOR_GAMMA',
                                               default=(0.0, 0.0, 0.0),
                                               min=-1.0, max=1.0,
                                               soft_min=0.0, soft_max=1.0)


class NVB_PG_bone(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for bones.
    """
    # Armature Helper
    helper_amt_ctype = bpy.props.EnumProperty(
        name='Source',
        items=[('EMT', 'Empty', 'Bone will be converted to an empty.', 0),
               ('ME1', 'Mesh', 'Bone will be converted to a mesh.', 1)
               ],
        default='ME1')


class NVB_PG_lamp(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for lamps.
    """
    shadow = bpy.props.BoolProperty(
                name='Shadow',
                description='Whether to cast shadows',
                default=True)
    ambientonly = bpy.props.BoolProperty(
                name='Ambient Only',
                description='Light will be ignored for shadow casting',
                default=False)
    lightpriority = bpy.props.IntProperty(
                name='Lightpriority',
                default=3, min=1, max=5)
    fadinglight = bpy.props.BoolProperty(
                name='Fading light',
                default=False)
    isdynamic = bpy.props.BoolProperty(
                name='Is Dynamic',
                default=False)
    affectdynamic = bpy.props.BoolProperty(
                name='Affect Dynamic',
                description='Affect dynamic objects',
                default=False)
    negativelight = bpy.props.BoolProperty(
                name='Negative Light',
                default=False)
    uselensflares = bpy.props.BoolProperty(
                name='Lensflares',
                default=False)
    flareradius = bpy.props.FloatProperty(
                name='Flare Radius',
                default=0.0, min=0.0, max=100.0)
    flareList = bpy.props.CollectionProperty(type=NVB_PG_flare)
    flareListIdx = bpy.props.IntProperty(
                name='Index for flare list',
                default=0)


class NVB_PG_object(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for meshes, lamps and empties.
    """

    # For all objects
    wirecolor = bpy.props.FloatVectorProperty(
                name='Wirecolor',
                description='Color of the wireframe, Unused',
                subtype='COLOR_GAMMA',
                default=(1.0, 1.0, 1.0),
                min=0.0, max=1.0,
                soft_min=0.0, soft_max=1.0)

    # Helper properties to store additional values. Cannot be edited.
    imporder = bpy.props.IntProperty(name='Original position in MDL',
                                     default=0)
    restrot = bpy.props.FloatVectorProperty(name='Rest Pose Rotation',
                                            size=4,
                                            default=(0.0, 0.0, 0.0, 0.0))
    restloc = bpy.props.FloatVectorProperty(name='Rest Pose Location',
                                            size=3,
                                            default=(0.0, 0.0, 0.0))
    # For all emptys
    emptytype = bpy.props.EnumProperty(
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
                        'DWK Root (Door  Walkmesh)',
                        'All children are part of the walkmesh', 3),
                       (nvb_def.Emptytype.PWK,
                        'PWK Root (Placeable Walkmesh)',
                        'All children are part of the walkmesh', 4)],
                default=nvb_def.Emptytype.DUMMY)
    # For Aurora Root
    supermodel = bpy.props.StringProperty(
        name='Supermodel',
        description='Name of the model to inherit animations from',
        default=nvb_def.null)
    classification = bpy.props.EnumProperty(
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
                default=nvb_def.Classification.UNKNOWN)
    animscale = bpy.props.FloatProperty(
                name='Animationscale',
                description='Animation scale for all animations',
                default=1.00, min=0.0)
    # Animation Data (for being able to seperate them)
    animList = bpy.props.CollectionProperty(type=NVB_PG_anim)
    animListIdx = bpy.props.IntProperty(name='Index for anim List',
                                        default=0)

    # For reference emptys
    refmodel = bpy.props.StringProperty(name='Reference Model',
                                        description='Name of MDL file',
                                        default='fx_ref')
    reattachable = bpy.props.BoolProperty(name='Reattachable',
                                          default=False)

    # Minimap Helper
    minimapzoffset = bpy.props.FloatProperty(name='Minimap Z Offset',
                                             default=0.00,
                                             min=0.00)
    minimapsize = bpy.props.IntProperty(name='Size',
                                        default=32,
                                        min=16)
    # Object & Dummy Helper
    helper_node_mdltype = bpy.props.EnumProperty(
        name='Type',
        items=[(nvb_def.Walkmeshtype.PWK,
                'Placeable', 'Setup objects for placeables', 0),
               (nvb_def.Walkmeshtype.DWK,
                'Door', 'Setup objects for doors', 1),
               # (nvb_def.Walkmeshtype.TILE,
               # 'Tile', 'Setup objects for tiles', 2),
               ],
        default=nvb_def.Walkmeshtype.PWK)
    helper_scale_fac = bpy.props.FloatVectorProperty(name='Scale',
                                                     description='Scale',
                                                     subtype='XYZ',
                                                     default=(1.0, 1.0, 1.0))
    # Armature Helper
    helper_amt_source = bpy.props.EnumProperty(
        name='Source',
        items=[('ALL', 'All', 'All objects in the mdl.', 0),
               ('ACT', 'Active', 'Active object and its children.', 1),
               ],
        default='ALL')
    helper_amt_connect = bpy.props.BoolProperty(
        name='Auto Connect',
        description='Automatically connect bones when possible',
        default=True)
    helper_amt_copyani = bpy.props.BoolProperty(
        name='Copy Animations',
        description='Copy animations to the created armature',
        default=True)

    # For mesh objects
    meshtype = bpy.props.EnumProperty(
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
                default=nvb_def.Meshtype.TRIMESH)
    smoothgroup = bpy.props.EnumProperty(
                name='Smoothgroup',
                items=[('SEPR',
                        'Seperate', 'Each face has it\'s own group', 0),
                       ('SING',
                        'Single', 'All faces belong to the same group', 1),
                       ('AUTO',
                        'Auto', 'Generate groups from sharp edges', 2)
                       ],
                default='AUTO')
    shadow = bpy.props.BoolProperty(
                name='Shadow',
                description='Whether to cast shadows',
                default=True)
    render = bpy.props.BoolProperty(
                name='Render',
                description='Whether to render this object in the scene',
                default=True)
    tilefade = bpy.props.EnumProperty(
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
                default=nvb_def.Tilefade.NONE)
    beaming = bpy.props.BoolProperty(
                name='beaming',
                description='Object casts beams (?)',
                default=False)
    inheritcolor = bpy.props.BoolProperty(
                name='Inheritcolor',
                description='Unused (?)',
                default=False)
    rotatetexture = bpy.props.BoolProperty(
                name='Rotatetexture',
                description='Automatically rotates texture to prevent seams',
                default=False)
    transparencyhint = bpy.props.IntProperty(
                name='Transparency Hint',
                description='Order of transparency evaluation',
                default=0,
                min=0, max=32)
    selfillumcolor = bpy.props.FloatVectorProperty(
                name='Selfilluminationcolor',
                description='Makes the object glow but does not emit light',
                subtype='COLOR_GAMMA',
                default=(0.0, 0.0, 0.0),
                min=0.0, max=1.0,
                soft_min=0.0, soft_max=1.0)
    shininess = bpy.props.IntProperty(name='Shininess',
                                      description='Used with txi file',
                                      default=1, min=0, max=32)
    # For Animeshes
    aurorashapekey = bpy.props.StringProperty(
        name='Shapekey',
        description='Shape key to use for animated vertices',
        default='')
    # For danglymeshes
    period = bpy.props.FloatProperty(name='Period',
                                     default=1.0, min=0.0, max=32.0)
    tightness = bpy.props.FloatProperty(name='Tightness',
                                        default=1.0, min=0.0, max=32.0)
    displacement = bpy.props.FloatProperty(name='Displacement',
                                           default=0.5, min=0.0, max=32.0)
    constraints = bpy.props.StringProperty(
                name='Danglegroup',
                description='Name of the vertex group to use for the weights',
                default='')
    # For skingroups
    skingroup_obj = bpy.props.StringProperty(
                name='Bone',
                description='Name of the bone to create the skingroup for',
                default='')
    # For lamps
    lighttype = bpy.props.EnumProperty(
                name='Type',
                items=[(nvb_def.Lighttype.DEFAULT,
                        'Default', 'Simple light', 0),
                       (nvb_def.Lighttype.MAIN1,
                        'Mainlight 1', 'For tiles (Editable in toolset)', 1),
                       (nvb_def.Lighttype.MAIN2,
                        'Mainlight 2', 'For tiles (Editable in toolset)', 2)],
                default=nvb_def.Lighttype.DEFAULT)
    # For emitters
    rawascii = bpy.props.StringProperty(
        name='Text node',
        description='Name of the raw text node',
        default='')
