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
        self.restpose = True
        self.rotmode = 'XYZ'
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
