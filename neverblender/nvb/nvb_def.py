# Null value for parents, textures, etc.
null = 'null'


class MalformedMdlFile(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)

'''
class Classification(enum.Enum):
    UNKNOWN   = ('Unknown',   'Unknown classification',              0)
    TILE      = ('Tile',      'Tiles for a tileset',                 1)
    CHARACTER = ('Character', 'Creatures, characters or placeables', 2)
    DOOR      = ('Door',      'Doors',                               3)
    EFFECT    = ('Effect',    'Effects',                             4)
    GUI       = ('Gui',       'Gui',                                 5)
    ITEM      = ('Item',      'Items or placeables',                 6)

    def __init__(self, uiName, uiDesc, idx):
        self.uiName = uiName
        self.uiDesc = uiDesc
        self.idx    = idx

    @property
    def uiEnumItem(self):
        return (self.name, self.uiName, self.uiDesc, self.idx)

    @property
    def ascii(self):
        return (self.name, self.uiName, self.uiDesc, self.idx)
'''

# Some presets
fps = 30
shadingGroupName = 'shadegr_'
wok_materials = [ ['wok_NotDefined'    , (0.400, 0.400, 0.400), 0.0], \
                  ['wok_Dirt'          , (0.610, 0.235, 0.050), 0.0], \
                  ['wok_Obscuring'     , (0.100, 0.100, 0.100), 0.5], \
                  ['wok_Grass'         , (0.000, 0.600, 0.000), 0.0], \
                  ['wok_Stone'         , (0.162, 0.216, 0.279), 0.0], \
                  ['wok_Wood'          , (0.258, 0.059, 0.007), 0.0], \
                  ['wok_Water'         , (0.000, 0.000, 1.000), 0.0], \
                  ['wok_Nonwalk'       , (1.000, 0.000, 0.000), 0.0], \
                  ['wok_Transparent'   , (1.000, 1.000, 1.000), 1.0], \
                  ['wok_Carpet'        , (1.000, 0.000, 1.000), 0.0], \
                  ['wok_Metal'         , (0.434, 0.552, 0.730), 1.0], \
                  ['wok_Puddles'       , (0.509, 0.474, 0.147), 0.0], \
                  ['wok_Swamp'         , (0.216, 0.216, 0.000), 0.0], \
                  ['wok_Mud'           , (0.091, 0.147, 0.028), 0.0], \
                  ['wok_Leaves'        , (1.000, 0.262, 0.000), 0.0], \
                  ['wok_Lava'          , (0.300, 0.000, 0.000), 0.3], \
                  ['wok_BottomlessPit' , (0.000, 0.000, 0.000), 0.0], \
                  ['wok_DeepWater'     , (0.000, 0.000, 0.216), 0.0], \
                  ['wok_Door'          , (0.000, 0.000, 0.000), 0.0], \
                  ['wok_Snow'          , (0.800, 0.800, 0.800), 0.0], \
                  ['wok_Sand'          , (1.000, 1.000, 0.000), 0.0], \
                  ['wok_BareBones'     , (0.500, 0.500, 0.100), 0.0], \
                  ['wok_StoneBridge'   , (0.081, 0.108, 0.139), 0.0] ]
