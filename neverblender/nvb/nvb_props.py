"""TODO: DOC."""

import bpy
from . import nvb_def


def nvb_update_shadow_prop(self, context):
    """Set the lamps shadow to match the aurora shadow property."""
    obj = context.object
    if obj and (obj.type == 'LAMP'):
        try:
            if (obj.nvb.shadow):
                obj.data.shadow_method = 'RAY_SHADOW'
            else:
                obj.data.shadow_method = 'NOSHADOW'
        except:
            pass


class NVB_PG_ANIMEVENT(bpy.types.PropertyGroup):
    """Properties for a single event in the even list."""

    name = bpy.props.StringProperty(
                name='Name',
                description='Name for this event',
                default='Unnamed')

    frame = bpy.props.IntProperty(
                name='Frame',
                description='Frame at which the event should fire',
                default=1)


class NVB_PG_ANIM(bpy.types.PropertyGroup):
    """Properties for a single animation in the animation list."""

    name = bpy.props.StringProperty(
                name='Name',
                description='Name for this event',
                default='Unnamed')
    ttime = bpy.props.FloatProperty(
                name='Transitiontime',
                description='Used for for animations only',
                default=1, min=0)
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
    markerEnd = bpy.props.StringProperty(
                name='End Marker',
                description='End marker in the timeline',
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

    eventList = bpy.props.CollectionProperty(type=NVB_PG_ANIMEVENT)
    eventListIdx = bpy.props.IntProperty(
        name='Index for event List',
        default=0)


class NVB_PG_FLARE(bpy.types.PropertyGroup):
    """Properties for a single flare in the flare list."""

    texture = bpy.props.StringProperty(name='Texture',
                                       description='Texture name',
                                       default=nvb_def.null)
    size = bpy.props.FloatProperty(name='Size',
                                   description='Flare size',
                                   default=1)
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


class NVB_PG_OBJECT(bpy.types.PropertyGroup):
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

    # For all emptys
    emptytype = bpy.props.EnumProperty(
                name='Type',
                items=[(nvb_def.Emptytype.DUMMY,
                        'Dummy', 'Simple dummy object', 0),
                       (nvb_def.Emptytype.REFERENCE,
                        'Reference node', 'Used in spells. \
                         Default value "fx_ref"', 1),
                       (nvb_def.Emptytype.PATCH,
                        'Patch node', 'Unknown purpose', 2)],
                default=nvb_def.Emptytype.DUMMY)
    # For MDL Rootdummy
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
    dummytype = bpy.props.EnumProperty(
                name='Type',
                items=[(nvb_def.Dummytype.DEFAULT,
                        'None', 'Simple dummy object', 0),
                       (nvb_def.Dummytype.HAND,
                        'Hand', 'Hand node for vfx', 1),
                       (nvb_def.Dummytype.HEAD,
                        'Head', 'Head node for vfx', 2),
                       (nvb_def.Dummytype.HEAD_HIT,
                        'Head hit', 'Head hit node for vfx', 3),
                       (nvb_def.Dummytype.IMPACT,
                        'Impact', 'Impact node for vfx', 4),
                       (nvb_def.Dummytype.GROUND,
                        'Ground', 'Ground node for vfx', 5),
                       (nvb_def.Dummytype.USE1,
                        'Use 1', '1st Node for placeable "Use"', 6),
                       (nvb_def.Dummytype.USE2,
                        'Use 2', '2nd Node for placeable "Use"', 7),
                       (nvb_def.Dummytype.OPEN1_01,
                        'DWK: Open 1 1st', '1st node for door "Use"', 8),
                       (nvb_def.Dummytype.OPEN1_02,
                        'DWK: Open 1 2nd', '2nd node for door "Use"', 9),
                       (nvb_def.Dummytype.OPEN2_01,
                        'DWK: Open 2 1st', '1st node for door "Use"', 10),
                       (nvb_def.Dummytype.OPEN2_02,
                        'DWK: Open 2 2nd', '2nd node for door "Use"', 11),
                       (nvb_def.Dummytype.CLOSED_01,
                        'DWK: Closed 1st', '1st node for door "Use"', 12),
                       (nvb_def.Dummytype.CLOSED_01,
                        'DWK: Closed 2nd', '2nd node for door "Use"', 13)
                       ],
                default=nvb_def.Dummytype.DEFAULT)
    animscale = bpy.props.FloatProperty(
                name='Animationscale',
                description='Animation scale for all animations',
                default=1.00, min=0.0)
    # Animation Data (for being able to seperate them)
    animList = bpy.props.CollectionProperty(type=NVB_PG_ANIM)
    animListIdx = bpy.props.IntProperty(name='Index for anim List',
                                        default=0)

    # For reference emptys
    refmodel = bpy.props.StringProperty(
                name='Reference Model',
                description='Name of another mdl file',
                default='fx_ref')
    reattachable = bpy.props.BoolProperty(
                name='Reattachable',
                default=False)
    # Minimap generation
    minimapzoffset = bpy.props.FloatProperty(name='Minimap Z Offset',
                                             default=0.00,
                                             min=0.00)
    minimapsize = bpy.props.IntProperty(name='Size',
                                        default=32,
                                        min=16)

    # For mesh objects
    meshtype = bpy.props.EnumProperty(
                name='Type',
                items=[(nvb_def.Meshtype.TRIMESH, 'Trimesh', 'desc', 0),
                       (nvb_def.Meshtype.DANGLYMESH, 'Danglymesh', 'desc', 1),
                       (nvb_def.Meshtype.SKIN, 'Skinmesh', 'desc', 2),
                       (nvb_def.Meshtype.WALKMESH, 'Walkmesh', 'desc', 3),
                       (nvb_def.Meshtype.EMITTER, 'Emitter', 'desc', 4),
                       (nvb_def.Meshtype.ANIMMESH, 'Animesh', 'desc', 5)],
                default=nvb_def.Meshtype.TRIMESH)
    walkmeshtype = bpy.props.EnumProperty(
                name='Type',
                items=[(nvb_def.Walkmeshtype.PWK,
                        'Placeable', 'Placeable walkmesh', 0),
                       (nvb_def.Walkmeshtype.DWKOPEN1,
                        'Door: Open 1', 'Door walkmesh for open state 1', 1),
                       (nvb_def.Walkmeshtype.DWKOPEN2,
                        'Door: Open 2', 'Door walkmesh for open state 2', 2),
                       (nvb_def.Walkmeshtype.DWKCLOSED,
                        'Door: Closed', 'Door walkmesh for closed state', 3),
                       (nvb_def.Walkmeshtype.AABB,
                        'Tileset', 'Walkmesh for tilesets', 4)
                       ],
                default=nvb_def.Walkmeshtype.PWK)
    smoothgroup = bpy.props.EnumProperty(
                name='Smoothgroup',
                items=[('SEPR',
                        'Seperate', 'Each face has it\'s own group', 0),
                       ('SING',
                        'Single', 'All faces belong to the same group', 1),
                       ('AUTO',
                        'Auto', 'Generate groups from sharp edges', 2)
                       ],
                default='SEPR')

    shadow = bpy.props.BoolProperty(
                name='Shadow',
                description='Whether to cast shadows',
                default=True,
                update=nvb_update_shadow_prop)
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
    ambientcolor = bpy.props.FloatVectorProperty(name='Ambientcolor',
                                                 description='Ambient color',
                                                 subtype='COLOR_GAMMA',
                                                 default=(1.0, 1.0, 1.0),
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
                        'Mainlight 2', 'For tiles (Editable in toolset)', 2),
                       (nvb_def.Lighttype.SOURCE1,
                        'Sourcelight 1', 'For tiles (Editable in toolset)', 3),
                       (nvb_def.Lighttype.SOURCE2,
                        'Sourcelight 2', 'For tiles (Editable in toolset)', 4)
                       ],
                default=nvb_def.Lighttype.DEFAULT)
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
    lensflares = bpy.props.BoolProperty(
                name='Lensflares',
                default=False)
    flareradius = bpy.props.FloatProperty(
                name='Flare Radius',
                default=0.0, min=0.0, max=100.0)
    flareList = bpy.props.CollectionProperty(type=NVB_PG_FLARE)
    flareListIdx = bpy.props.IntProperty(
                name='Index for flare list',
                default=0)

    # For emitters
    rawascii = bpy.props.StringProperty(
        name='Text node',
        description='Name of the raw text node',
        default='')
