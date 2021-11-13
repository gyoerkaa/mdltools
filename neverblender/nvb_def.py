"""TODO: DOC."""

# Frame at which to start all animations
anim_globstart = 1
# Offset between two imported animations (minimum)
anim_offset = 60
# Save order of tverts for each objects {objectName:[p1, p2, ... pN]}
tvert_order = dict()
# Shapekey name (for import)
shapekeyname = 'aurora_animesh'
# Null value for parents, textures, etc.
null = 'null'
# Predefined walkmesh materials: (material name, diffuse color) tuples
wok_materials = [('wok_NotDefined',    (1.000, 1.000, 1.000, 1.0)),
                 ('wok_Dirt',          (0.580, 0.486, 0.314, 1.0)),
                 ('wok_Obscuring',     (1.000, 1.000, 0.000, 1.0)),
                 ('wok_Grass',         (0.243, 0.588, 0.125, 1.0)),
                 ('wok_Stone',         (0.400, 0.400, 0.400, 1.0)),
                 ('wok_Wood',          (0.258, 0.059, 0.007, 1.0)),
                 ('wok_Water',         (0.000, 0.745, 0.695, 1.0)),
                 ('wok_Nonwalk',       (1.000, 0.000, 0.000, 1.0)),
                 ('wok_Transparent',   (1.000, 1.000, 1.000, 1.0)),
                 ('wok_Carpet',        (0.510, 0.000, 0.502, 1.0)),
                 ('wok_Metal',         (0.624, 0.725, 0.725, 1.0)),
                 ('wok_Puddles',       (0.502, 1.000, 1.000, 1.0)),
                 ('wok_Swamp',         (0.537, 0.616, 0.000, 1.0)),
                 ('wok_Mud',           (0.286, 0.114, 0.000, 1.0)),
                 ('wok_Leaves',        (0.278, 0.357, 0.137, 1.0)),
                 ('wok_Lava',          (1.000, 0.388, 0.000, 1.0)),
                 ('wok_BottomlessPit', (0.000, 0.000, 0.000, 1.0)),
                 ('wok_DeepWater',     (0.000, 0.094, 1.000, 1.0)),
                 ('wok_Door',          (0.200, 0.200, 0.200, 1.0)),
                 ('wok_Snow',          (0.800, 0.800, 0.800, 1.0)),
                 ('wok_Sand',          (0.600, 0.600, 0.100, 1.0)),
                 ('wok_BareBones',     (0.400, 0.400, 0.200, 1.0)),
                 ('wok_StoneBridge',   (0.300, 0.300, 0.300, 1.0))]
# Animation event names (always created in list)
animation_event_names = ['cast', 'blur_end', 'blur_start', 'detonate',
                         'draw_arrow', 'draw_weapon', 'hit', 'parry',
                         'snd_footstep', 'snd_hitground']

pathnodes = [('A',  'A',  '',  0),
             ('a', 'aa', '',  1),
             ('B',  'B',  '',  2),
             ('b', 'bb', '',  3),
             ('C',  'C',  '',  4),
             ('c', 'cc', '',  5),
             ('D',  'D',  '',  6),
             ('d', 'dd', '',  7),
             ('E',  'E',  '',  8),
             ('e', 'ee', '',  9),
             ('F',  'F',  '', 10),
             ('f', 'ff', '', 11),
             ('G',  'G',  '', 12),
             ('g', 'gg', '', 13),
             ('H',  'H',  '', 14),
             ('h', 'hh', '', 15),
             ('I',  'I',  '', 16),
             ('i', 'ii', '', 17),
             ('J',  'J',  '', 18),
             ('j', 'jj', '', 19),
             ('K',  'K',  '', 20),
             ('k', 'kk', '', 21),
             ('L',  'L',  '', 22),
             ('l', 'll', '', 23),
             ('M',  'M',  '', 24),
             ('m', 'mm', '', 25),
             ('N',  'N',  '', 26),
             ('n', 'nn', '', 27),
             ('O',  'O',  '', 29),
             ('o', 'oo', '', 30),
             ('P',  'P',  '', 31),
             ('p', 'pp', '', 32),
             ('Q',  'Q',  '', 33),
             ('R',  'R',  '', 34),
             ('S',  'S',  '', 35),
             ('T',  'T',  '', 36),
             ('U',  'U',  '', 37),
             ('V',  'V',  '', 38),
             ('W',  'W',  '', 39),
             ('X',  'X',  '', 40),
             ('Y',  'Y',  '', 41),
             ('Z',  'Z',  '', 42)]


class MalformedMdlFile(Exception):
    """TODO: DOC."""

    def __init__(self, value):
        """TODO: DOC."""
        self.parameter = value

    def __str__(self):
        """TODO: DOC."""
        return repr(self.parameter)


"""
class Animtype():

    UNDEFINED  = 'undefined'
    PLSTAB     = 'plstab'
    PLCLOSEL   = 'plclosel'
    PLCLOSER   = 'plcloser'
    PLREACH    = 'plreach'
    PLPARRYL   = 'plparryl'
    PLPARRYR   = 'plparryr'
    WALK       = 'walk'
    KDBCK      = 'kdbck'
    KDBCKPS    = 'kdbckps'
    KDBCKDMG   = 'kdbckdmg'
    KDBCKDIE   = 'kdbckdie'
    DEADBCK    = 'deadbck'
    GUTOKDB    = 'gutokdb'
    GUSTANDB   = 'gustandb'
    RUN        = 'run'
    PAUSE1     = 'pause1'
    PAUSE2     = 'pause2'
    TAUNT      = 'taunt'
    SITCROSS   = 'sitcross'
    SITCROSSPS = 'sitcrossps'
    BOW        = 'bow'
    TALKFORCE  = 'tlkforce'
    PLPAUSE1   = 'plpause1'
    SITDOWN    = 'sitdown'
    SIT        = 'sit'
    CUSTOM01   = 'custom1'
    CUSTOM02   = 'custom2'
    CUSTOM03   = 'custom3'
    CUSTOM04   = 'custom4'
    CUSTOM05   = 'custom5'
    CUSTOM06   = 'custom6'
    CUSTOM07   = 'custom7'
    CUSTOM08   = 'custom8'
    CUSTOM09   = 'custom9'
    CUSTOM10   = 'custom10'
"""


class Meshtype():
    """TODO: DOC."""

    TRIMESH = 'trimesh'
    DANGLYMESH = 'danglymesh'
    SKIN = 'skin'
    AABB = 'aabb'
    EMITTER = 'emitter'
    ANIMMESH = 'animmesh'

    ALL = {TRIMESH, DANGLYMESH, SKIN, AABB, EMITTER, ANIMMESH}


class Emptytype():
    """TODO: DOC."""

    DUMMY = 'dummy'
    REFERENCE = 'reference'
    PATCH = 'patch'
    PWK = 'pwk'
    DWK = 'dwk'

    ALL = {DUMMY, REFERENCE, PATCH, PWK, DWK}


class Renderhint():
    NORMALANDSPECMAPPED = 'normalandspecmapped'


class Nodetype(Emptytype, Meshtype):
    """TODO: Doc."""

    LIGHT = 'light'

    ALL = {LIGHT} | Emptytype.ALL | Meshtype.ALL


class Walkmeshtype():
    """TODO: Doc."""

    WOK = 'wok'
    PWK = 'pwk'
    DWK = 'dwk'

    IMPORT = {PWK, DWK}
    ALL = {WOK, PWK, DWK}


class Tilefade():
    """TODO: DOC."""

    NONE = '0'
    FADE = '1'
    BASE = '2'
    NEIGHBOUR = '4'

    ALL = {NONE, FADE, BASE, NEIGHBOUR}


class Classification():
    """Classification of mdl file."""

    UNKNOWN = 'unknown'
    TILE = 'tile'
    CHARACTER = 'character'
    DOOR = 'door'
    EFFECT = 'effect'
    GUI = 'gui'
    ITEM = 'item'
    OTHER = 'other'
    
    ALL = {UNKNOWN, TILE, CHARACTER, DOOR, EFFECT, GUI, ITEM, OTHER}


class Lighttype():
    """TODO: DOC."""

    DEFAULT = 'DEFAULT'
    MAIN1 = 'MAIN1'
    MAIN2 = 'MAIN2'
    SOURCE1 = 'SOURCE1'
    SOURCE2 = 'SOURCE2'

    ALL = {DEFAULT, MAIN1, MAIN2, SOURCE1, SOURCE2}

    suffix2type = [('ml1', MAIN1),
                   ('ml2', MAIN2)]

    type2suffix = {DEFAULT:   '',
                   MAIN1:     'ml1',
                   MAIN2:     'ml2'}

    @classmethod
    def getSuffix(cls, obj):
        """TODO: Doc."""
        objName = obj.name
        for suffix in cls.suffix2type:
            if objName.endswith(suffix[0]):
                return suffix[1]
        return ''

    @classmethod
    def getType(cls, nodeName):
        """TODO: Doc."""
        for suffix in cls.suffix2type:
            if nodeName.endswith(suffix[0]):
                return suffix[1]
        return cls.DEFAULT

    @classmethod
    def generateSuffix(cls, obj):
        """TODO: Doc."""
        suffix = ''
        if obj.type == 'LAMP':
            if obj.nvb.lighttype in cls.type2suffix:
                suffix = cls.type2suffix[obj.nvb.lighttype]
        return suffix


class ImportOptions():
    """Holds all import options."""

    def __init__(self):
        """TODO: DOC."""
        self.mdlname = "unnamed"
        self.mtrdb = dict()

        # Hidden settings and properties for internal use
        self.filepath = ""
        self.scene = None
        self.collection = None
        self.hide_lights = True
        self.hide_fading = True
        self.dummy_type = 'PLAIN_AXES'
        self.dummy_size = 1.0
        self.placement = 'SPIRAL'
        self.mdl_location = (0.0, 0.0, 0.0)
        # Handling of binary models
        self.compiler_use = False
        self.compiler_path = ""
        self.compiler_command = ""
        # Geometry
        self.geom_import = True
        self.geom_smoothgroups = True
        self.geom_normals = True
        self.geom_walkmesh = True
        self.geom_mesh_validation = False
        # Materials and textures
        self.mat_import = True
        self.mat_automerge = True
        self.mat_shader = ""
        self.mat_use_mtr = True
        self.tex_search = False
        self.mat_displacement_mode = 'BUMP'  # 'DISPLACEMENT' or 'BUMP'
        self.mat_ignore_mdl_diffuse_color = False
        self.mat_ignore_mdl_specular_color = True
        self.mat_ignore_mdl_ambient_color = True
        self.mat_ignore_selfillum_color = False
        self.mat_ignore_selfillum_texture = False
        # Animation Settings
        self.anim_import = True
        self.anim_fps_use = True
        self.anim_fps = 30
        self.anim_restpose = True
        self.anim_ignore_existing = False
        self.anim_scale = None  # use None, instead of 1.0
        # Blender Settings
        self.rotmode = 'XYZ'
        self.fix_uvs = False
        self.collections_use = True


class ExportOptions():
    """Holds all export options."""

    def __init__(self):
        """TODO: DOC."""
        self.filepath = ""
        self.mdlname = "unnamed"
        self.scene = None
        self.collection = None
        self.depsgraph = None
        self.export_metadata = True
        self.mtr_list = set()
        self.classification = Classification.UNKNOWN
        # Geometry
        self.geom_walkmesh = True
        self.geom_smoothgroups = True
        self.geom_smoothgroups_binary = True
        self.geom_smoothgroups_distinct_verts = False
        self.geom_normals = False
        self.geom_smoothing_split = False
        self.geom_smoothing_group = False
        # Materials and textures
        self.mat_mtr_generate = True
        self.mat_mtr_ref = 'bitmap'
        self.mat_diffuse_ref = 'bitmap'
        # Misc options
        self.anim_export = True        
        # UV Map  settings
        self.uv_merge = True
        self.uv_level = 'REN'
        self.uv_order = 'AL0'
        # Blender Settings
        self.apply_modifiers = True
        self.mesh_convert = 'RENDER'
        self.batch_mode = 'OFF'
        self.strip_trailing = False
