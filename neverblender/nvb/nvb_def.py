"""TODO: DOC."""

import collections

# Null value for parents, textures, etc.
null = 'null'
# Where to start all animations
anim_globstart = 1
# offset between two imported animations
anim_offset = 60
# Some presets
anim_fps = 30
# Predefined walkmesh materials
wok_materials = [['wok_NotDefined',    (0.400, 0.400, 0.400), 0.0],
                 ['wok_Dirt',          (0.610, 0.235, 0.050), 0.0],
                 ['wok_Obscuring',     (0.100, 0.100, 0.100), 0.5],
                 ['wok_Grass',         (0.000, 0.600, 0.000), 0.0],
                 ['wok_Stone',         (0.162, 0.216, 0.279), 0.0],
                 ['wok_Wood',          (0.258, 0.059, 0.007), 0.0],
                 ['wok_Water',         (0.000, 0.000, 1.000), 0.0],
                 ['wok_Nonwalk',       (1.000, 0.000, 0.000), 0.0],
                 ['wok_Transparent',   (1.000, 1.000, 1.000), 1.0],
                 ['wok_Carpet',        (1.000, 0.000, 1.000), 0.0],
                 ['wok_Metal',         (0.434, 0.552, 0.730), 1.0],
                 ['wok_Puddles',       (0.509, 0.474, 0.147), 0.0],
                 ['wok_Swamp',         (0.216, 0.216, 0.000), 0.0],
                 ['wok_Mud',           (0.091, 0.147, 0.028), 0.0],
                 ['wok_Leaves',        (1.000, 0.262, 0.000), 0.0],
                 ['wok_Lava',          (0.300, 0.000, 0.000), 0.3],
                 ['wok_BottomlessPit', (0.000, 0.000, 0.000), 0.0],
                 ['wok_DeepWater',     (0.000, 0.000, 0.216), 0.0],
                 ['wok_Door',          (0.000, 0.000, 0.000), 0.0],
                 ['wok_Snow',          (0.800, 0.800, 0.800), 0.0],
                 ['wok_Sand',          (1.000, 1.000, 0.000), 0.0],
                 ['wok_BareBones',     (0.500, 0.500, 0.100), 0.0],
                 ['wok_StoneBridge',   (0.081, 0.108, 0.139), 0.0]]


class ImportOptions():
    """TODO: DOC."""

    importGeometry = True
    importWalkmesh = True
    importSmoothGroups = True
    importAnim = 'STD'
    importSupermodel = False
    # Options for textures and materials
    materialMode = 'SIN'
    texturePath = ''
    textureSearch = False
    # for minimap generator
    minimapMode = False
    minimapSkipFade = False


class ExportOptions():
    """TODO: DOC."""

    exportAnim = True
    exportWalkmesh = True
    exportSmoothGroups = True

    meshConvert = 'RENDER'
    applyModifiers = True


class MalformedMdlFile(Exception):
    """TODO: DOC."""

    def __init__(self, value):
        """TODO: DOC."""
        self.parameter = value

    def __str__(self):
        """TODO: DOC."""
        return repr(self.parameter)


class Animtype():
    """TODO: DOC."""

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


class Dummytype():
    """TODO: DOC."""

    NONE = 'NONE'
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

    SUFFIX_LIST = [('use01',     USE1),
                   ('use02',     USE2),
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

    SUFFIX_PWK = {NONE:     '',
                  HAND:     'hand',
                  HEAD:     'head',
                  HEAD_HIT: 'head_hit',
                  IMPACT:   'impact',
                  GROUND:   'ground',
                  USE1:     'use01',
                  USE2:     'use02'}

    SUFFIX_DWK = {NONE:      '',
                  HAND:      'hand',
                  HEAD:      'head',
                  HEAD_HIT:  'hhit',
                  IMPACT:    'impc',
                  GROUND:    'grnd',
                  USE1:      'use01',
                  USE2:      'use02',
                  OPEN1_01:  'open1_01',
                  OPEN1_02:  'open1_02',
                  OPEN2_01:  'open2_01',
                  OPEN2_02:  'open2_02',
                  CLOSED_01: 'closed_01',
                  CLOSED_02: 'closed_02'}


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

    ALL = {DUMMY, REFERENCE, PATCH}


class Nodetype(Emptytype, Meshtype):
    """TODO: Doc."""

    LIGHT = 'LIGHT'

    ALL = {LIGHT} | Emptytype.ALL | Meshtype.ALL


class Tilefade():
    """TODO: DOC."""

    NONE = '0'
    FADE = '1'
    BASE = '2'
    NEIGHBOUR = '4'

    ALL = {NONE, FADE, BASE, NEIGHBOUR}


class Classification():
    """TODO: DOC."""

    UNKNOWN = 'UNKNOWN'
    TILE = 'TILE'
    CHARACTER = 'CHARACTER'
    DOOR = 'DOOR'
    EFFECT = 'EFFECT'
    GUI = 'GUI'
    ITEM = 'ITEM'

    ALL = {UNKNOWN, TILE, CHARACTER, DOOR, EFFECT, GUI, ITEM}


class Light():
    """TODO: DOC."""

    DEFAULT = 'DEFAULT'
    MAINLIGHT1 = 'MAIN1'
    MAINLIGHT2 = 'MAIN2'
    TILELIGHT1 = 'MAIN1'
    TILELIGHT2 = 'MAIN2'

    ALL = {DEFAULT, MAINLIGHT1, MAINLIGHT2, TILELIGHT1, TILELIGHT2}
