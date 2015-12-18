import os

from . import nvb_glob
from . import nvb_parser


def load(operator,
         context,
         filepath = '',
         imports = {'GEOMETRY', 'ANIMATION', 'WALKMESH'},
         useShadingGroups = True,
         textureSingle = True,
         textureSearch = False,
         minimapMode = False):
    '''
    Called from blender ui
    '''
    nvb_glob.imports          = imports
    nvb_glob.usePltTextures   = False
    nvb_glob.useShadingGroups = useShadingGroups
    nvb_glob.minimapMode      = minimapMode

    nvb_glob.texturePath   = os.path.dirname(filepath)
    nvb_glob.textureSingle = textureSingle
    nvb_glob.textureSearch = textureSearch

    parser = nvb_parser.Parser()
    parser.load(filepath)

    return {'FINISHED'}

def save():
    pass
