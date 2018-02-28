"""TODO: DOC."""

# Frame at which to start all animations
anim_globstart = 1
# Offset between two imported animations
anim_offset = 60
# Save order of tverts for each objects {objectName:[p1, p2, ... pN]}
tvert_order = dict()
# Shapekey name (for import)
shapekeyname = 'aurora_animesh'
# Null value for parents, textures, etc.
null = 'null'
# Predefined walkmesh materials: (material name, diffuse color) tuples
wok_materials = [('wok_NotDefined',    (0.400, 0.400, 0.400)),
                 ('wok_Dirt',          (0.610, 0.235, 0.050)),
                 ('wok_Obscuring',     (0.100, 0.100, 0.100)),
                 ('wok_Grass',         (0.000, 0.600, 0.000)),
                 ('wok_Stone',         (0.162, 0.216, 0.279)),
                 ('wok_Wood',          (0.258, 0.059, 0.007)),
                 ('wok_Water',         (0.000, 0.000, 1.000)),
                 ('wok_Nonwalk',       (1.000, 0.000, 0.000)),
                 ('wok_Transparent',   (1.000, 1.000, 1.000)),
                 ('wok_Carpet',        (1.000, 0.000, 1.000)),
                 ('wok_Metal',         (0.434, 0.552, 0.730)),
                 ('wok_Puddles',       (0.509, 0.474, 0.147)),
                 ('wok_Swamp',         (0.216, 0.216, 0.000)),
                 ('wok_Mud',           (0.091, 0.147, 0.028)),
                 ('wok_Leaves',        (1.000, 0.262, 0.000)),
                 ('wok_Lava',          (0.300, 0.000, 0.000)),
                 ('wok_BottomlessPit', (0.000, 0.000, 0.000)),
                 ('wok_DeepWater',     (0.000, 0.000, 0.216)),
                 ('wok_Door',          (0.000, 0.000, 0.000)),
                 ('wok_Snow',          (0.800, 0.800, 0.800)),
                 ('wok_Sand',          (1.000, 1.000, 0.000)),
                 ('wok_BareBones',     (0.500, 0.500, 0.100)),
                 ('wok_StoneBridge',   (0.081, 0.108, 0.139))]


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


class Dummytype():
    """TODO: DOC."""

    DEFAULT = 'DEFAULT'
    HAND = 'HAND'
    HEAD = 'HEAD'
    HEAD_HIT = 'HHIT'
    IMPACT = 'IMPC'
    GROUND = 'GRND'
    USE1 = 'USE1'
    USE2 = 'USE2'
    OPEN1_01 = 'O101'
    OPEN1_02 = 'O102'
    OPEN2_01 = 'O201'
    OPEN2_02 = 'O202'
    CLOSED_01 = 'CL01'
    CLOSED_02 = 'CL02'

    WALKMESH = {USE1, USE2,
                OPEN1_01, OPEN1_02, OPEN2_01, OPEN2_01, CLOSED_01, CLOSED_02}

    suffix2type = [('dwk_use01', USE1),
                   ('pwk_use01', USE1),
                   ('dwk_use02', USE2),
                   ('pwk_use02', USE2),
                   ('hand',      HAND),
                   ('head',      HEAD),
                   ('head_hit',  HEAD_HIT),
                   ('hhit',      HEAD_HIT),
                   ('impact',    IMPACT),
                   ('impc',      IMPACT),
                   ('ground',    GROUND),
                   ('grnd',      GROUND),
                   ('open1_01',  OPEN1_01),
                   ('open1_02',  OPEN1_02),
                   ('open2_01',  OPEN2_01),
                   ('open2_02',  OPEN2_02),
                   ('closed_01', CLOSED_01),
                   ('closed_02', CLOSED_02)]

    pwktype2suffix = {DEFAULT:  '',
                      HAND:     'hand',
                      HEAD:     'head',
                      HEAD_HIT: 'head_hit',
                      IMPACT:   'impact',
                      GROUND:   'ground',
                      USE1:     'pwk_use01',
                      USE2:     'pwk_use02'}

    dwktype2suffix = {DEFAULT:   '',
                      HAND:      'hand',
                      HEAD:      'head',
                      HEAD_HIT:  'hhit',
                      IMPACT:    'impc',
                      GROUND:    'grnd',
                      USE1:      'dwk_use01',
                      USE2:      'dwk_use02',
                      OPEN1_01:  'dp_open1_01',
                      OPEN1_02:  'dp_open1_02',
                      OPEN2_01:  'dp_open2_01',
                      OPEN2_02:  'dp_open2_02',
                      CLOSED_01: 'dp_closed_01',
                      CLOSED_02: 'dp_closed_02'}

    @classmethod
    def generateSuffix(cls, obj, classification):
        """TODO: Doc."""
        suffix = ''
        if obj.type == 'EMPTY' and obj.nvb.emptytype == Emptytype.DUMMY:
            if classification == Classification.DOOR:
                if obj.nvb.dummytype in cls.dwktype2suffix:
                    suffix = cls.dwktype2suffix[obj.nvb.dummytype]
            elif classification == Classification.TILE:
                # No changes for tiles
                pass
            else:
                # Everything else counts as placeable
                if obj.nvb.dummytype in cls.pwktype2suffix:
                    suffix = cls.pwktype2suffix[obj.nvb.dummytype]
        return suffix

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
    def get(cls, nodeName):
        """Deprecated, use getType instead."""
        print('Neverblender: Deprecated function')
        for suffix in cls.suffix2type:
            if nodeName.endswith(suffix[0]):
                return suffix[1]
        return cls.DEFAULT

    @classmethod
    def isWalkmesh(cls, dummyType):
        """TODO: Doc."""
        return dummyType in cls.WALKMESH


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

    suffix_list = ['wg_open1', 'wg_open2', 'wg_closed']

    @classmethod
    def generateSuffix(cls, obj, classification):
        """TODO: Doc."""
        suffix = ''
        if obj.type == 'MESH' and obj.nvb.meshtype == Meshtype.WALKMESH:
            if classification == Classification.DOOR:
                suffix = cls.suffix_dwk[obj.nvb.meshtype]
            elif classification == Classification.TILE:
                return ''  # No changes for tiles
            else:
                # Everything else counts as placeable
                suffix = 'pwk'
        else:
            return suffix

    @classmethod
    def getType(cls, nodeName):
        """TODO: Doc."""
        for suffix in cls.suffix_list:
            if nodeName.endswith(suffix[0]):
                return suffix[1]
        return cls.PWK


class Tilefade():
    """TODO: DOC."""

    NONE = '0'
    FADE = '1'
    BASE = '2'
    NEIGHBOUR = '4'

    ALL = {NONE, FADE, BASE, NEIGHBOUR}


class Classification():
    """TODO: DOC."""

    UNKNOWN = 'unknown'
    TILE = 'tile'
    CHARACTER = 'character'
    DOOR = 'door'
    EFFECT = 'effect'
    GUI = 'gui'
    ITEM = 'item'

    ALL = {UNKNOWN, TILE, CHARACTER, DOOR, EFFECT, GUI, ITEM}


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
        self.filepath = ''
        self.scene = None
        self.mdlname = 'unnamed'
        self.mtrdb = dict()
        # What to import
        self.importAnimations = True
        self.importWalkmesh = True
        self.importSmoothGroups = True
        self.importNormals = True
        self.importMaterials = True
        # Additional options for textures and materials
        self.materialLoadMTR = True
        self.materialAutoMerge = True
        self.textureDefaultRoles = True
        self.texturePath = ''
        self.textureSearch = False
        # Blender Settings
        self.customfps = True
        self.fps = 30
        # for batch processing
        self.minimapMode = False
        self.minimapSkipFade = False


class ExportOptions():
    """Holds all export options."""

    def __init__(self):
        """TODO: DOC."""
        self.filepath = ''
        self.scene = None
        self.mdlname = 'unnamed'
        self.classification = Classification.UNKNOWN
        # Misc options
        self.exportAnimations = True
        self.exportWalkmesh = True
        self.exportSmoothGroups = True
        self.exportNormals = False
        # UV Map Settings
        self.uvmapAutoJoin = True
        self.uvmapMode = 'REN'
        self.uvmapOrder = 'AL0'
        # Additional options for textures and materials
        self.materialUseMTR = False
        # Blender Settings
        self.applyModifiers = True
        self.meshConvert = 'RENDER'
