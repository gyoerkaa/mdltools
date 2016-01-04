import os
import bpy

from . import nvb_glob
from . import nvb_mdl
from . import nvb_utils


def findRootDummy():
    # Look for a rootdummy:
    # 1. Current selected object ?
    # 2. Search 'Empty' objects in the current scene
    # 4. Search all objects

    obj = bpy.context.object
    # Selected object
    if nvb_utils.isRootDummy(obj):
        return obj
    else:
        # Search objects in active scene
        if nvb_glob.scene:
            for obj in nvb_glob.scene.objects:
                if nvb_utils.isRootDummy(obj):
                    return obj
        # Search all data
        for ob in bpy.data.objects:
            if nvb_utils.isRootDummy(obj):
                return obj

    return None


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
    nvb_glob.usePltTextures   = False
    nvb_glob.useShadingGroups = useShadingGroups
    nvb_glob.minimapMode      = minimapMode

    nvb_glob.texturePath   = os.path.dirname(filepath)
    nvb_glob.textureSingle = textureSingle
    nvb_glob.textureSearch = textureSearch

    #parser = nvb_parser.Parser()
    #parser.load(filepath)
    scene = bpy.context.scene

    fp = os.fsencode(filepath)
    asciiLines = [line.strip().split() for line in open(fp, 'r')]

    mdl = nvb_mdl.Mdl()
    mdl.loadAscii(asciiLines)
    mdl.importToScene(scene, imports)

    # Try to load walkmeshes ... pwk (placeable) and dwk (door)
    # If the files are and the option is activated we'll import them
    if 'WALKMESH' in imports:
        filetypes = ['pwk', 'dwk']
        (wkPath, wkFilename) = os.path.split(filepath)
        for wkType in filetypes:
            wkFilepath = os.path.join(wkPath, os.path.splitext(wkFilename)[0] + '.' + wkType)
            fp = os.fsencode(wkFilepath)
            try:
                asciiLines = [line.strip().split() for line in open(fp, 'r')]
                xwk = nvb_mdl.Xwk()
                xwk.loadAscii(asciiLines)
                xwk.importToScene(scene, imports)
            except IOError:
                print("Neverblender: No walkmesh found at " + wkFilepath)

    return {'FINISHED'}


def saveMdl(operator,
         context,
         filepath = '',
         exports = {'ANIMATION', 'WALKMESH'},
         useShadingGroups = True,
         applyModifiers = True,
         ):
    '''
    Called from blender ui
    '''
    nvb_glob.exports          = exports
    nvb_glob.useShadingGroups = useShadingGroups
    nvb_glob.applyModifiers   = applyModifiers
    nvb_glob.scene            = bpy.context.scene

    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')

    rootDummy = findRootDummy()
    if rootDummy:
        mdl = nvb_mdl.Mdl()
        asciiLines = []
        mdl.generateAscii(asciiLines)
        with open(os.fsencode(filepath), 'w') as f:
            f.write('\n'.join(asciiLines))

        if 'WALKMESH' in exports:
            xwk = nvb_mdl.Xwk()
            xwk.generateAscii()

    return {'FINISHED'}
