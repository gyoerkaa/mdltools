import bpy
import neverblender.nvb.presets


def nvb_update_shadow_prop(self, context):
    '''
    Set the lamps shadow to match the aurora shadow property
    '''
    select_object = context.object
    if (select_object) and (select_object.type == 'LAMP'):
        try:
            if (select_object.auroraprops.shadow):
                select_object.data.shadow_method = 'RAY_SHADOW'
            else:
                select_object.data.shadow_method = 'NOSHADOW'
        except:
            pass


class ObjectPropertyGroup(bpy.types.PropertyGroup):
    '''
    This class defines all additional properties needed by the mdl file
    format. It hold the properties for meshes, lamps and empties.
    '''

    # For all objects

    # For all emptys
    dummytype      = bpy.props.EnumProperty(name = 'Type',
                                            items = [('NONE',      'None',                'Simple dummy object',                                        0), \
                                                     ('ANIMATION', 'Animation Rootdummy', 'An MDL Rootdummy for animation scenes',                      1), \
                                                     ('ANIBASE',   'Animation',           'All children can be animated. Must be unique.',              2), \
                                                     ('DWKROOT',   'DWK Rootdummy',       'All children are considered part of the door walkmesh',      3), \
                                                     ('MDLROOT',   'MDL Rootdummy',       'All children are considered part of the mdl',                4), \
                                                     ('PWKROOT',   'PWK Rootdummy',       'All children are considered part of the placeable walkmesh', 5), \
                                                     ('REFERENCE', 'Reference node',      'Used in spells. Points to "fx_ref" by default',              6), \
                                                     ('SPECIAL',   'Special',             'Special dummies. See subtype',                               7) ],
                                            default = 'NONE')
    # For special emptys
    dummysubtype   = bpy.props.EnumProperty(name = 'Subtype',
                                            items = [('NONE', 'None',                      'Simple dummy object',                     0), \
                                                     ('HAND', 'Hand',                      'Hand node for spells and effects',        1), \
                                                     ('HEAD', 'Head',                      'Head node for spells and effects',        2), \
                                                     ('HHIT', 'Head hit',                  'Head hit node for spells and effects',    3), \
                                                     ('IMPC', 'Impact',                    'Impact node for spells and effects',      4), \
                                                     ('GRND', 'Ground',                    'Ground node for spells and effects',      5), \
                                                     ('USE1', 'Placeable Walkmesh: Use 1', '1st node for "Use" animation',            6), \
                                                     ('USE2', 'Placeable Walkmesh: Use 2', '2nd node for "Use" animation',            7), \
                                                     ('O101', 'Door Walkmesh: Open 1 1st', 'Open 1 State, 1st node for "Use" anim',   8), \
                                                     ('O102', 'Door Walkmesh: Open 1 2nd', 'Open 1 State, 2nd node for "Use" anim',   9), \
                                                     ('O201', 'Door Walkmesh: Open 2 1st', 'Open 2 State, 1st node for "Use" anim',  10), \
                                                     ('O202', 'Door Walkmesh: Open 2 2nd', 'Open 2 State, 2nd node for "Use" anim',  11), \
                                                     ('CL01', 'Door Walkmesh: Closed 1st', 'Closed State, 1st node for "Use" anim',  12), \
                                                     ('CL02', 'Door Walkmesh: Closed 2nd', 'Closed State, 2nd node for "Use" anim',  13) ],
                                            default = 'NONE')
    # For reference emptys
    refmodel     = bpy.props.StringProperty(name = 'Reference Model', description = 'Name of another mdl file', default = 'fx_ref')
    reattachable = bpy.props.BoolProperty(name = 'Reattachable', default = False)

    # For mdl base
    supermodel     = bpy.props.StringProperty(name = 'Supermodel', description = 'Name of the supermodel', default = nvb.presets.null)
    classification = bpy.props.EnumProperty(name  = 'Classification',
                                            items = [ ('UNKNOWN', 'Unknown', 'Unknown classification', 0), \
                                                      ('TILE', 'Tile', 'Tile for a tileset', 1), \
                                                      ('CHARACTER', 'Character', 'Creature, Character', 2), \
                                                      ('DOOR', 'Door', 'Door Desc.', 3), \
                                                      ('EFFECT', 'Effect', 'Effect Desc.', 4), \
                                                      ('GUI', 'Gui', 'Gui Icons, etc.', 5), \
                                                      ('ITEM', 'Item', 'Items', 6) ],
                                            default = 'UNKNOWN' )
    animationscale = bpy.props.FloatProperty(name = 'Animationscale', default = 1.00, min = 0.0)

    # Minimap generation
    minimapzoffset   = bpy.props.FloatProperty(name = 'Minimap Z Offset', default = 0.00, min = 0.00)
    minimapsize      = bpy.props.IntProperty(name = 'Size', default = 32, min = 16)

    # Creation and renaming of animation scenes
    newanim_name      = bpy.props.StringProperty(name = 'Animation name', description = 'Name of the new animation', default = '')

    # For mdl bases in animation scenes
    in_animscene     = bpy.props.BoolProperty(name = 'In Anim. Scene', description = 'Wether this dummy is in an animationscene', default = False)
    transtime        = bpy.props.FloatProperty(name = 'Transistiontime', description = 'Used for for animations only. \n Set it for each Scene individually', default = 1.00, min = 0.0)
    animname         = bpy.props.StringProperty(name = 'Animationname', description = 'Name of the animation', default = '')

    # For meshes
    wirecolor = bpy.props.FloatVectorProperty(name = 'Wirecolor',
                                              description = 'Color of the wireframe',
                                              subtype = 'COLOR_GAMMA',
                                              default = (1.0, 1.0, 1.0),
                                              min = 0.0, max = 1.0,
                                              soft_min = 0.0, soft_max = 1.0)
    shadow = bpy.props.BoolProperty(name = 'Shadow', description = 'Whether to cast shadows', default = True, update=nvb_update_shadow_prop)

    meshtype         = bpy.props.EnumProperty(name = 'Type',
                                              items = [ ('TRIMESH', 'Trimesh', '0 desc', 0), \
                                                        ('DANGLYMESH', 'Danglymesh', '1 desc', 1), \
                                                        ('SKIN', 'Skinmesh', '2 desc', 2), \
                                                        ('AABB', 'AABB Walkmesh', '3 desc', 3), \
                                                        ('EMITTER', 'Emitter', '4 desc', 4)], \
                                              default = 'TRIMESH' )
    tilefade         = bpy.props.IntProperty(name = 'Tilefade', default = 0)
    render           = bpy.props.BoolProperty(name = 'Render', description = 'Whether to render this object in the scene', default = True)
    beaming          = bpy.props.BoolProperty(name = 'beaming', description = 'Object casts beams (see forest tileset)', default = False)
    inheritcolor     = bpy.props.BoolProperty(name = 'Inheritcolor', description = '(Unused by NWN)', default = False)
    rotatetexture    = bpy.props.BoolProperty(name = 'Rotatetexture', description = 'Automatically rotates texture to prevent seams', default = False)
    transparencyhint = bpy.props.IntProperty(name = 'Transparency Hint', default = 0, min = 0, max = 32)
    selfillumcolor   = bpy.props.FloatVectorProperty(name = 'Selfilluminationcolor',
                                                     description = 'Self illumination color',
                                                     subtype = 'COLOR_GAMMA',
                                                     default = (0.0, 0.0, 0.0),
                                                     min = 0.0, max = 1.0,
                                                     soft_min = 0.0, soft_max = 1.0)
    ambientcolor     = bpy.props.FloatVectorProperty(name = 'Ambientcolor',
                                                     description = 'Ambient color',
                                                     subtype = 'COLOR_GAMMA',
                                                     default = (1.0, 1.0, 1.0),
                                                     min = 0.0, max = 1.0,
                                                     soft_min = 0.0, soft_max = 1.0)
    shininess        = bpy.props.IntProperty(name = 'Shininess', default = 1, min = 0, max = 32)

    # For danglymeshes
    period       = bpy.props.FloatProperty(name = 'Period', default = 1.0, min = 0.0, max = 32.0)
    tightness    = bpy.props.FloatProperty(name = 'Tightness', default = 1.0, min = 0.0, max = 32.0)
    displacement = bpy.props.FloatProperty(name = 'Displacement', default = 0.5, min = 0.0, max = 32.0)
    constraints  = bpy.props.StringProperty(name = 'Danglegroup', description = 'Name of the vertex group to use for the danglymesh', default = '')

    # For skingroups
    select_object = bpy.props.StringProperty(name = 'Bone', description = 'Name of the bone to create the skingroup for', default = '')

    # For lamps
    lighttype     = bpy.props.EnumProperty(name = 'Type', items=[('NONE', 'None', 'Simple light', 0), ('MAINLIGHT1', 'Mainlight 1', 'Editable in toolset', 1), ('MAINLIGHT2', 'Mainlight 2', 'Editable in toolset', 2), ('SOURCELIGHT1', 'Sourcelight 1', 'Editable in toolset', 3), ('SOURCELIGHT2', 'Sourcelight 2', 'Editable in toolset', 4)], default = 'NONE')
    lightpriority = bpy.props.IntProperty(name = 'Lightpriority', default = 5, min = 0, max = 5)
    fadinglight   = bpy.props.BoolProperty(name = 'Fading light', default = False)
    isdynamic     = bpy.props.BoolProperty(name = 'Is Dynamic', default = False)
    affectdynamic = bpy.props.BoolProperty(name = 'Affect Dynamic', description = 'Affect dynamic objects', default = False)
    flareradius   = bpy.props.FloatProperty(name = 'Flare Radius', default = 0.0, min = 0.0, max = 32.0)

    # For emitters
    rawascii = bpy.props.StringProperty(name = 'Text node', description = 'Name of the raw text node', default = '')
