"""TODO: DOC."""

import bpy
from . import nvb_def


class NVB_PG_animevent(bpy.types.PropertyGroup):
    """Properties for a single event in the even list."""

    name = bpy.props.StringProperty(name='Name',
                                    description='Name for this event',
                                    default='Unnamed', options=set())
    frame = bpy.props.IntProperty(
        name='Frame',
        description='Frame at which the event should fire',
        default=1, options=set())


class NVB_PG_anim(bpy.types.PropertyGroup):
    """Properties for a single animation in the animation list."""

    name = bpy.props.StringProperty(name='Name',
                                    description='Name for this event',
                                    default='Unnamed')
    ttime = bpy.props.FloatProperty(name='Transitiontime',
                                    description='Used for for animations only',
                                    default=0.25, min=0.0)
    root = bpy.props.StringProperty(name='Root',
                                    description='Entry point of the animation',
                                    default='')
    mute = bpy.props.BoolProperty(name='Mute',
                                  description='Ignore animation during export',
                                  default=False)
    rawascii = bpy.props.StringProperty(
        name='Emitter Data',
        description='Incompatible Emitter data loaded as plain text',
        default='')
    frameStart = bpy.props.IntProperty(name='Start',
                                       description='Animation Start',
                                       default=0, min=0, options=set())
    frameEnd = bpy.props.IntProperty(name='End',
                                     description='Animation End',
                                     default=0, min=0, options=set())

    eventList = bpy.props.CollectionProperty(type=NVB_PG_animevent)
    eventListIdx = bpy.props.IntProperty(name='Index for event List',
                                         default=0, options=set())


class NVB_PG_mtrparameter(bpy.types.PropertyGroup):
    """Properties for a single parameter in the flare list."""
    ptype = bpy.props.EnumProperty(name='Type', description='Parameter type',
                                   items=[('float', 'float', 'float', 0),
                                          ('int', 'int', 'int', 1)],
                                   default='int', options=set())
    pname = bpy.props.StringProperty(name='Name',
                                     description='Parameter name',
                                     default='name', options=set())
    pvalue = bpy.props.StringProperty(name='Value',
                                      description='Parameter value',
                                      default='', options=set())


class NVB_PG_set_element(bpy.types.PropertyGroup):
    """Properties for a single flare in the flare list."""
    el_name = bpy.props.StringProperty(
        name='Supermodel', description='Name of the MDL for this tile',
        default='', options=set())
    el_size = bpy.props.StringProperty(
        name='Size', description='Size of this element (only for diplay)',
        default='', options=set())


class NVB_PG_scene(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for meshes, lamps and empties.
    """
    # Set loading (mass tile loading)
    set_filepath = bpy.props.StringProperty(name='Filepath',
                                            description='Path to SET file',
                                            default='', options=set())
    set_mode = bpy.props.EnumProperty(
        name='Set View Mode',
        items=[('GP', 'Groups', 'Display Groups', 0),
               ('TR', 'Terrains', 'Display terrain types', 1),
               ('CR', 'Crossers', 'Display crosser types', 2)],
        default='GP', options=set())
    set_group_list = bpy.props.CollectionProperty(type=NVB_PG_set_element)
    set_group_list_idx = bpy.props.IntProperty(name='SET Group list index',
                                               default=0, options=set())
    set_crosser_list = bpy.props.CollectionProperty(type=NVB_PG_set_element)
    set_crosser_list_idx = bpy.props.IntProperty(name='SET Crosser list index',
                                                 default=0, options=set())
    set_terrain_list = bpy.props.CollectionProperty(type=NVB_PG_set_element)
    set_terrain_list_idx = bpy.props.IntProperty(name='SET Terrain list index',
                                                 default=0, options=set())


class NVB_PG_material(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for meshes, lamps and empties.
    """
    ambient_color = bpy.props.FloatVectorProperty(
        subtype='COLOR_GAMMA',
        name='Ambient', description='Ambient color of the material',
        default=(1.0, 1.0, 1.0), min=0.0, max=1.0)
    ambient_intensity = bpy.props.FloatProperty(
        subtype='FACTOR', precision=3,
        name='Intensity', description='Amount of ambient color',
        default=1.0, min=0.0, max=1.0)
    renderhint = bpy.props.EnumProperty(
        name='Renderhint',
        items=[('AUTO', 'Auto', 'Depending on number of textures', 0),
               ('NONE', 'None', 'No renderhint', 1),
               ('NASM', 'NormalAndSpecMapped', 'Normal & Specular Mapped', 2)],
        default='AUTO', options=set())
    # MTR Panel
    usemtr = bpy.props.BoolProperty(name='Use MTR',
                                    description='Use external MTR file',
                                    default=False, options=set())
    mtrname = bpy.props.StringProperty(name='Name',
                                       description='Data name',
                                       default='', options=set())
    mtrsrc = bpy.props.EnumProperty(
        name='Source',
        items=[('TEXT', 'Text', 'From text block', 0),
               ('FILE', 'File', 'From file', 1)],
        default='FILE', options=set())
    mtrtext = bpy.props.StringProperty(name='Text Block',
                                       description='Blender Text Block',
                                       default='', options=set())
    mtrpath = bpy.props.StringProperty(name='Filepath',
                                       description='Path to MTR file',
                                       default='', options=set())
    # For gui editing
    shadervs = bpy.props.StringProperty(name='Vertex Shader',
                                        description='Specify Vertex shader',
                                        default='', options=set())
    shaderfs = bpy.props.StringProperty(name='Fragment Shader',
                                        description='Specify Fragment shader',
                                        default='', options=set())
    mtrparam_list = bpy.props.CollectionProperty(type=NVB_PG_mtrparameter)
    mtrparam_list_idx = bpy.props.IntProperty(name='MTR parameter list index',
                                              default=0, options=set())


class NVB_PG_flare(bpy.types.PropertyGroup):
    """Properties for a single flare in the flare list."""
    texture = bpy.props.StringProperty(name='Texture',
                                       description='Texture name',
                                       default=nvb_def.null, options=set())
    size = bpy.props.FloatProperty(name='Size', description='Flare size',
                                   default=1, min=0)
    position = bpy.props.FloatProperty(name='Position',
                                       description='Flare position',
                                       default=1, min=-1.0, max=1.0)
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
        items=[('EMT', 'Empty', 'Bone will be converted to an empty', 0),
               ('ME1', 'Mesh', 'Bone will be converted to a mesh', 1)
               ],
        default='ME1', options=set())


class NVB_PG_emitter(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    This class defines all additional properties needed by the mdl file
    format for emitters.
    """
    birthrate = bpy.props.IntProperty(name='birthrate',
                                      default=1)
    texture = bpy.props.StringProperty(name='Texture',
                                       description='Texture name',
                                       default=nvb_def.null, options=set())
    grid = bpy.props.IntVectorProperty(name='grid', description='Texture grid',
                                       subtype='XYZ', size=2,
                                       default=(0, 0), options=set())
    twosidedtex = bpy.props.BoolProperty(
        name='Two Sided Texture',
        description='Use external MTR file',
        default=False, options=set())
    colorstart = bpy.props.FloatVectorProperty(
        name='Color Start', description='Particle color at birth',
        subtype='COLOR_GAMMA',
        default=(1.0, 1.0, 1.0), min=0.0, max=1.0)
    colorend = bpy.props.FloatVectorProperty(
        name='Color Start', description='Particle color at death',
        subtype='COLOR_GAMMA',
        default=(1.0, 1.0, 1.0), min=0.0, max=1.0)
    alphastart = bpy.props.FloatProperty(
        name='Alpha Start', description='Particle color at birth',
        default=1, min=0.0, max=1.0)
    alphaend = bpy.props.FloatProperty(
        name='Alpha Start', description='Particle color at birth',
        default=1, min=0.0, max=1.0)


class NVB_PG_lamp(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for lamps.
    """
    shadow = bpy.props.BoolProperty(name='Shadow',
                                    description='Whether to cast shadows',
                                    default=True, options=set())
    ambientonly = bpy.props.BoolProperty(
                name='Ambient Only',
                description='Light will be ignored for shadow casting',
                default=False, options=set())
    lightpriority = bpy.props.IntProperty(name='Lightpriority',
                                          default=3, min=1, max=5,
                                          options=set())
    fadinglight = bpy.props.BoolProperty(name='Fading light',
                                         default=False, options=set())
    isdynamic = bpy.props.BoolProperty(name='Is Dynamic',
                                       default=False, options=set())
    affectdynamic = bpy.props.BoolProperty(
                name='Affect Dynamic',
                description='Affect dynamic objects',
                default=False, options=set())
    negativelight = bpy.props.BoolProperty(name='Negative Light',
                                           default=False, options=set())
    uselensflares = bpy.props.BoolProperty(name='Lensflares',
                                           default=False, options=set())
    flareradius = bpy.props.FloatProperty(
                name='Flare Radius',
                default=0.0, min=0.0, max=100.0, options=set())
    flareList = bpy.props.CollectionProperty(type=NVB_PG_flare)
    flareListIdx = bpy.props.IntProperty(name='Index for flare list',
                                         default=0, options=set())


class NVB_PG_object(bpy.types.PropertyGroup):
    """Holds additional properties needed for the mdl file format.

    This class defines all additional properties needed by the mdl file
    format. It hold the properties for meshes, lamps and empties.
    """

    # Helper properties to store additional values. Cannot be edited.
    restrot = bpy.props.FloatVectorProperty(name='Rest Pose Rotation',
                                            size=4,
                                            default=(0.0, 0.0, 0.0, 0.0),
                                            options=set())
    restloc = bpy.props.FloatVectorProperty(name='Rest Pose Location',
                                            size=3,
                                            default=(0.0, 0.0, 0.0),
                                            options=set())
    imporder = bpy.props.IntProperty(
        name='Position in MDL',
        description='Position of this object in the MDL file',
        default=1000, options={'SKIP_SAVE'})
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
                default=nvb_def.Emptytype.DUMMY, options=set())
    # For Aurora Root
    supermodel = bpy.props.StringProperty(
        name='Supermodel',
        description='Name of the model to inherit animations from',
        default=nvb_def.null, options=set())
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
                default=nvb_def.Classification.UNKNOWN, options=set())
    animscale = bpy.props.FloatProperty(
                name='Animationscale',
                description='Animation scale for all animations',
                default=1.00, min=0.0, options=set())
    # Animation Data (for being able to seperate them)
    animList = bpy.props.CollectionProperty(type=NVB_PG_anim)
    animListIdx = bpy.props.IntProperty(name='Index for anim List',
                                        default=0, options=set())

    # For reference emptys
    refmodel = bpy.props.StringProperty(name='Reference Model',
                                        description='Name of MDL file',
                                        default='fx_ref', options=set())
    reattachable = bpy.props.BoolProperty(name='Reattachable',
                                          default=False, options=set())
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
        default=nvb_def.Walkmeshtype.PWK, options={'SKIP_SAVE'})
    # Armature Helper
    helper_amt_source = bpy.props.EnumProperty(
        name='Source',
        description='Source to take objects from',
        items=[('ALL', 'All', 'All objects in the mdl', 0),
               ('ACT', 'Active', 'Active object and its children', 1),
               ],
        default='ALL', options={'SKIP_SAVE'})
    helper_amt_connect = bpy.props.BoolProperty(
        name='Auto Connect',
        description='Connect bones when possible',
        default=True, options={'SKIP_SAVE'})
    helper_amt_animcopy = bpy.props.BoolProperty(
        name='Copy Animations',
        description='Copy animations to newly created meshes',
        default=True, options={'SKIP_SAVE'})
    helper_amt_animode = bpy.props.EnumProperty(
        name='Animations',
        description='Transfer animations to newly created armature',
        items=[('OFF', 'None', 'No animations transfer', 0),
               ('KFP', 'Keyframes', 'Copy keyframes', 1),
               ('CON', 'Constraints', 'Create constraints', 2),
               ],
        default='KFP', options={'SKIP_SAVE'})

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
                default=nvb_def.Meshtype.TRIMESH, options=set())
    smoothgroup = bpy.props.EnumProperty(
                name='Smoothgroup',
                items=[('SEPR',
                        'Seperate', 'Each face has it\'s own group', 0),
                       ('SING',
                        'Single', 'All faces belong to the same group', 1),
                       ('AUTO',
                        'Auto', 'Generate groups from sharp edges', 2)
                       ],
                default='AUTO', options=set())
    shadow = bpy.props.BoolProperty(name='Shadow',
                                    description='Whether to cast shadows',
                                    default=True, options=set())
    render = bpy.props.BoolProperty(name='Render',
                                    description='Render object',
                                    default=True, options=set())
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
                default=nvb_def.Tilefade.NONE, options=set())
    beaming = bpy.props.BoolProperty(name='beaming',
                                     description='Object casts beams',
                                     default=False, options=set())
    inheritcolor = bpy.props.BoolProperty(name='Inheritcolor',
                                          description='Unused',
                                          default=False, options=set())
    rotatetexture = bpy.props.BoolProperty(
                name='Rotatetexture',
                description='Automatically rotates texture to prevent seams',
                default=False, options=set())
    transparencyhint = bpy.props.IntProperty(
                name='Transparency Hint',
                description='Order of transparency evaluation',
                default=0, min=0, max=32, options=set())
    selfillumcolor = bpy.props.FloatVectorProperty(
                name='Selfilluminationcolor',
                description='Makes the object glow but does not emit light',
                subtype='COLOR_GAMMA',
                default=(0.0, 0.0, 0.0), options={'ANIMATABLE'},
                min=0.0, max=1.0, soft_min=0.0, soft_max=1.0)
    shininess = bpy.props.IntProperty(name='Shininess',
                                      description='Used with txi file',
                                      default=1, min=0, max=32, options=set())
    # For Animeshes
    aurorashapekey = bpy.props.StringProperty(
        name='Shapekey',
        description='Shape key to use for animated vertices',
        default='', options=set())
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
                default='', options=set())
    # For skingroups
    skingroup_obj = bpy.props.StringProperty(
                name='Bone',
                description='Name of the bone to create the skingroup for',
                default='', options=set())
    # For lamps
    lighttype = bpy.props.EnumProperty(
                name='Type',
                items=[(nvb_def.Lighttype.DEFAULT,
                        'Default', 'Simple light', 0),
                       (nvb_def.Lighttype.MAIN1,
                        'Mainlight 1', 'For tiles (Editable in toolset)', 1),
                       (nvb_def.Lighttype.MAIN2,
                        'Mainlight 2', 'For tiles (Editable in toolset)', 2)],
                default=nvb_def.Lighttype.DEFAULT, options=set())
    # For emitters
    rawascii = bpy.props.StringProperty(
        name='Text node',
        description='Name of the raw text node',
        default='', options=set())
