import os
import bpy

from . import nvb_glob
from . import nvb_parser
from . import nvb_mdl


def loadMdl(operator,
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


def saveMdl(operator,
         context,
         filepath = '',
         exports = {'GEOMETRY', 'ANIMATION', 'WALKMESH'},
         useShadingGroups = True,
         applyModifiers = True,
         ):
    '''
    Called from blender ui
    '''
    nvb_glob.exports          = exports
    nvb_glob.useShadingGroups = useShadingGroups
    nvb_glob.applyModifiers   = applyModifiers

    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')

    mdl = nvb_mdl.Mdl()
    mdl.generateAscii()

    if 'WALKMESH' in exports:
        xwk = nvb_mdl.Xwk()
        xwk.generateAscii()

    return {'FINISHED'}
