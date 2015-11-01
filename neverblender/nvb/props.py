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


def nvb_update_lighttype_prop(self, context):
    '''
    Renames lamp acording to match selected light type
    '''
    select_object = context.object
    if (select_object) and (select_object.type == 'LAMP'):
        try:
            if (select_object.auroraprops.lighttype == 'NONE'):
                pass
            elif (select_object.auroraprops.lighttype == 'MAINLIGHT1'):
                pass
            elif (select_object.auroraprops.lighttype == 'MAINLIGHT2'):
                pass
            elif (select_object.auroraprops.lighttype == 'SOURCELIGHT1'):
                pass
            elif (select_object.auroraprops.lighttype == 'SOURCELIGHT2'):
                pass
        except:
            pass


def nvb_update_lifeexp_prop(self, context):
    pass


class ParticlePropertyGroup(bpy.types.PropertyGroup):
    # For Emitters

    birthrate     = bpy.props.IntProperty(name = 'Birthrate', description = 'Birthrate', default = 10, min = 0)

    # Inheritance props
    inherit       = bpy.props.BoolProperty(name = 'Inherit', description = 'Inherit', default = False)
    inherit_vel   = bpy.props.BoolProperty(name = 'Velocity', description = 'Inherit Velocity', default = False)
    inherit_local = bpy.props.BoolProperty(name = 'Local', description = '???', default = False)
    inherit_part  = bpy.props.BoolProperty(name = 'Part', description = '???', default = False)

    # Blast props
    blastradius = bpy.props.FloatProperty(name = 'Radius', description = 'Radius', default = 0.0, min = 0.0)
    blastlength = bpy.props.FloatProperty(name = 'Length', description = 'Length', default = 0.0, min = 0.0)

    # Particle props
    colorstart  = bpy.props.FloatVectorProperty(name = 'Color start',
                                                description = 'Color start',
                                                subtype = 'COLOR_GAMMA',
                                                default = (1.0, 1.0, 1.0),
                                                min = 0.0, max = 1.0,
                                                soft_min = 0.0, soft_max = 1.0)
    colorend    = bpy.props.FloatVectorProperty(name = 'Color end',
                                                description = 'Color end',
                                                subtype = 'COLOR_GAMMA',
                                                default = (1.0, 1.0, 1.0),
                                                min = 0.0, max = 1.0,
                                                soft_min = 0.0, soft_max = 1.0)
    alphastart  = bpy.props.FloatProperty(name = 'Alpha start', description = 'Alpha start', default = 1.0, min = 0.0, max = 1.0)
    alphaend    = bpy.props.FloatProperty(name = 'Alpha end', description = 'Alpha end', default = 1.0, min = 0.0, max = 1.0)
    sizestart   = bpy.props.FloatProperty(name = 'Size start', description = 'x size start', default = 1.0, min = 0.0)
    sizeend     = bpy.props.FloatProperty(name = 'Size end', description = 'x size end', default = 1.0, min = 0.0)
    sizestart_y = bpy.props.FloatProperty(name = 'Sizestart_y', description = 'y size start', default = 0.0, min = 0.0)
    sizeend_y   = bpy.props.FloatProperty(name = 'Sizeend_y', description = 'y size end', default = 0.0, min = 0.0)

    # Misc props
    lifeexp     = bpy.props.FloatProperty(name = 'Life Exp.', description = 'Life Expectancy', default = 1.0, min = 0.0, update=nvb_update_lifeexp_prop)
    istinted    = bpy.props.BoolProperty(name = 'Tinted', description = 'Tint texture with start- and end color', default = False)
    bounce      = bpy.props.BoolProperty(name = 'Bounce type', description = 'Bounce On/Off', default = False)
    random      = bpy.props.BoolProperty(name = 'Random', description = 'Random', default = False)
    splat       = bpy.props.BoolProperty(name = 'Splat', description = 'Splat', default = False)
    renderorder = bpy.props.IntProperty(name = 'Render order', description = 'Render Order', default = 0, min = 0)
    chunkname   = bpy.props.StringProperty(name = 'Name', description = 'Chunk Name', default = '')
    loop        = bpy.props.BoolProperty(name = 'Loop', description = 'Loop', default = False)
    deadspace   = bpy.props.FloatProperty(name = 'Dead space', description = '???', default = 0.0, min = 0.0)
    twosidedtex = bpy.props.BoolProperty(name = 'Two Sided Texture', description = '???', default = False)
    bounce_co   = bpy.props.FloatProperty(name = 'Coeff.', description = 'Bounce coefficient', default = 0.0, min = 0.0)
    spread      = bpy.props.FloatProperty(name = 'Spread', description = 'Spread', default = 0.0, min = 0.0)
    particlerot = bpy.props.FloatProperty(name = 'Rotation', description = 'Particle Rotation', default = 0.0, min = -360.0, max = 360.0)
    fps         = bpy.props.IntProperty(name = 'Fps', description = 'Fps', default = 24, min = 0)
    blurlength  = bpy.props.FloatProperty(name = 'Blur Length', description = 'Blur Length', default = 10.0)
    opacity     = bpy.props.FloatProperty(name = 'Opacity', default = 0.00, min = 0.00, max = 1.00)

    # Lighting props
    lightningdelay  = bpy.props.FloatProperty(name = 'Delay', description = 'Delay', default = 0.0, min = 0.0, max = 1000.0)
    lightningradius = bpy.props.FloatProperty(name = 'Radius', description = 'Radius', default = 0.0, min = 0.0, max = 1000.0)
    lightningsubdiv = bpy.props.IntProperty(name = 'Subdivs.', description = 'Subdivisions', default = 0, min = 0, max = 12)
    lightningscale  = bpy.props.FloatProperty(name = 'Scale', description = 'Scale', default = 1.0, min = 0.0, max = 1.0)

    # Emitter Style
    blend       = bpy.props.EnumProperty(name  = 'Blend',
                                         description = 'Blend type',
                                         items = [('NORMAL', 'Normal', 'Normal', 1),
                                                  ('PUNCH-THROUGH', 'Punch-Through', 'Punch-Through',2),
                                                  ('LIGHTEN', 'Lighten', 'Lighten', 3)],
                                         default = 'NORMAL')
    update      = bpy.props.EnumProperty(name  = 'Update',
                                         description = 'Update type',
                                         items = [('FOUNTAIN', 'Fountain', 'Fountain', 0),
                                                  ('SINGLE', 'Single', 'Single', 1),
                                                  ('EXPLOSION', 'Explosion', 'Explosion', 2),
                                                  ('LIGHTNING', 'Lightning', 'Lightning', 3)],
                                         default = 'FOUNTAIN')
    render      = bpy.props.EnumProperty(name  = 'Render',
                                         description = 'Render type',
                                         items = [('NORMAL', 'Normal', 'Normal', 1),
                                                  ('LINKED', 'Linked', 'Linked', 2),
                                                  ('BB2LZ', 'Billboard to local Z', 'Billboard to local Z', 3),
                                                  ('BB2WZ', 'Billboard to world Z', 'Billboard to world Z', 4),
                                                  ('AL2WZ', 'Aligned to world Z', 'Aligned  to world Z', 5),
                                                  ('AL2PD', 'Aligned to particle dir.', 'Aligned to particle direction', 6),
                                                  ('MOBLUR', 'Motion Blur', 'Motion Blur', 7)],
                                         default = 'NORMAL')
    spawntype   = bpy.props.EnumProperty(name = 'Spawn',
                                         description = 'Spawn type',
                                         items = [('NORMAL', 'Normal', 'Normal', 0),
                                                  ('TRAIL', 'Trail', 'Trail', 1)],
                                         default = 'NORMAL')

    #p2p props
    p2p         = bpy.props.IntProperty(name = 'p2p', description = '???', default = 0, min = 0)
    p2p_type    = bpy.props.EnumProperty(name = 'Type',
                                         description = '???',
                                         items = [('BEZIER', 'Bezier', 'Bezier', 0),
                                                  ('GRAVITY', 'Gravity', 'Gravity', 1)],
                                         default = 'BEZIER')
    p2p_bezier2 = bpy.props.FloatProperty(name = 'Bezier 2', description = '???', default = 0.0)
    p2p_bezier3 = bpy.props.FloatProperty(name = 'Bezier 3', description = '???', default = 0.0)

    threshold   = bpy.props.FloatProperty(name = 'Threshold', description = 'Threshold', default = 0.0)
    combinetime = bpy.props.FloatProperty(name = 'Combinetime', description = 'Combinetime', default = 0.0)


class ObjectPropertyGroup(bpy.types.PropertyGroup):
    '''
    This class defines all additional properties needed by the mdl file
    format. It hold the properties for meshes, lamps and empties.
    '''

    # For all objects
    wirecolor = bpy.props.FloatVectorProperty(name = 'Wirecolor',
                                              description = 'Color of the wireframe',
                                              subtype = 'COLOR_GAMMA',
                                              default = (1.0, 1.0, 1.0),
                                              min = 0.0, max = 1.0,
                                              soft_min = 0.0, soft_max = 1.0
                                              )
    shadow = bpy.props.BoolProperty(name = 'Shadow', description = 'Whether to cast shadows', default = True, update=nvb_update_shadow_prop)

    # For emptys
    dummytype      = bpy.props.EnumProperty(name = 'Type',
                                            items = [('NONE',    'None',          'Simple dummy object',                                        0), \
                                                     ('MDLROOT', 'MDL Rootdummy', 'All children are considered part of the mdl',                1), \
                                                     ('PWKROOT', 'PWK Rootdummy', 'All children are considered part of the placeable walkmesh', 2), \
                                                     ('DWKROOT', 'DWK Rootdummy', 'All children are considered part of the door walkmesh',      3), \
                                                     ('ANIBASE', 'Animation',     'All children can be animated. Must be unique.',              4), \
                                                     ('SPECIAL', 'Special',       'Special dummies. See subtype',                               5) ],
                                            default = 'NONE')
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
    newanimname      = bpy.props.StringProperty(name = 'newanimname', description = 'Name of the new animation', default = '')

    # For mdl bases in animation scenes
    in_animscene     = bpy.props.BoolProperty(name = 'In Anim. Scene', description = 'Wether this dummy is in an animationscene', default = False)
    transtime        = bpy.props.FloatProperty(name = 'Transistiontime', description = 'Used for for animations only. \n Set it for each Scene individually', default = 1.00, min = 0.0)
    animname         = bpy.props.StringProperty(name = 'Animationname', description = 'Name of the animation', default = '')

    # For meshes
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

    # For danglymeshes (are also meshes)
    period       = bpy.props.FloatProperty(name = 'Period', default = 1.0, min = 0.0, max = 32.0)
    tightness    = bpy.props.FloatProperty(name = 'Tightness', default = 1.0, min = 0.0, max = 32.0)
    displacement = bpy.props.FloatProperty(name = 'Displacement', default = 0.5, min = 0.0, max = 32.0)
    danglegroup  = bpy.props.StringProperty(name = 'Danglegroup', description = 'Name of the vertex group to use for the danglymesh', default = '')

    # For skingroups (are also meshes)
    new_skingroupname = bpy.props.StringProperty(name = 'Skingroup', description = 'Bone to create the skingroup for', default = '')

    # For lamps
    lighttype     = bpy.props.EnumProperty(name = 'Type', items=[('NONE', 'None', 'Simple light', 0), ('MAINLIGHT1', 'Mainlight 1', 'Editable in toolset', 1), ('MAINLIGHT2', 'Mainlight 2', 'Editable in toolset', 2), ('SOURCELIGHT1', 'Sourcelight 1', 'Editable in toolset', 3), ('SOURCELIGHT2', 'Sourcelight 2', 'Editable in toolset', 4)], default = 'NONE', update=nvb_update_lighttype_prop)
    lightpriority = bpy.props.IntProperty(name = 'Lightpriority', default = 5, min = 0, max = 5)
    fadinglight   = bpy.props.BoolProperty(name = 'Fading light', default = False)
    isdynamic     = bpy.props.BoolProperty(name = 'Is Dynamic', default = False)
    affectdynamic = bpy.props.BoolProperty(name = 'Affect Dynamic', description = 'Affect dynamic objects', default = False)
    flareradius   = bpy.props.FloatProperty(name = 'Flare Radius', default = 0.0, min = 0.0, max = 32.0)
