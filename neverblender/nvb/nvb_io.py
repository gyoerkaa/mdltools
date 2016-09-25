"""TODO: DOC."""

import os
import bpy

from . import nvb_glob
from . import nvb_def
from . import nvb_mdl
from . import nvb_utils


def getExportMdl():
    """TODO: DOC."""
    # Look for a rootdummy:
    # 1. Current selected object ?
    # 2. Search 'Empty' objects in the current scene
    # 4. Search all objects

    obj = bpy.context.object
    # Selected object
    if nvb_utils.isRootDummy(obj, nvb_def.Dummytype.MDLROOT):
        return obj
    else:
        # Search objects in active scene
        if nvb_glob.scene:
            for obj in nvb_glob.scene.objects:
                if nvb_utils.isRootDummy(obj, nvb_def.Dummytype.MDLROOT):
                    return obj
        # Search all data
        for obj in bpy.data.objects:
            if nvb_utils.isRootDummy(obj, nvb_def.Dummytype.MDLROOT):
                return obj

    return None


def loadMdl(operator,
            context,
            filepath='',
            importGeometry=True,
            importWalkmesh=True,
            importSmoothGroups=True,
            importAnim='STD',
            importSupermodel=False,
            materialMode='SIN',
            textureSearch=False,
            minimapMode=False,
            minimapSkipFade=False):
    """Called from blender ui."""
    options = nvb_def.ImportOptions()
    options.importGeometry = importGeometry
    options.importSmoothGroups = importSmoothGroups
    options.importAnim = importAnim
    options.importSupermodel = importSupermodel

    options.materialMode = materialMode
    options.texturePath = os.path.dirname(filepath)
    options.textureSearch = textureSearch

    options.minimapMode = minimapMode
    options.minimapSkipFade = minimapSkipFade

    scene = bpy.context.scene

    with open(os.fsencode(filepath), 'r') as mdlfile:
        print('Neverblender: Importing ' + filepath)
        mdl = nvb_mdl.Mdl()
        asciiMdl = mdlfile.read()
        mdl.loadAscii(asciiMdl)

        # Try to load walkmeshes ... pwk (placeable) and dwk (door)
        if importWalkmesh:
            (mdlPath, mdlFilename) = os.path.split(filepath)
            for wkmtype in ['pwk', 'dwk']:
                wkmPath = os.fsencode(os.path.join(
                            mdlPath,
                            os.path.splitext(mdlFilename)[0] + '.' + wkmtype))
                try:
                    wkmfile = open(wkmPath, 'r')
                except IOError:
                    print("Neverblender: No " + wkmtype + " walkmesh found")
                else:
                    asciiWkm = wkmfile.read()
                    mdl.loadAsciiWalkmesh(asciiWkm)
                    wkmfile.close()

        mdl.create(scene, options)

    return {'FINISHED'}


def saveMdl(operator,
            context,
            mdlFilepath='',
            exports={'ANIMATION', 'WALKMESH'},
            useSmoothGroups=True,
            applyModifiers=True):
    """Called from blender ui."""
    nvb_glob.exports = exports
    nvb_glob.exportSmoothGroups = useSmoothGroups
    nvb_glob.applyModifiers = applyModifiers
    nvb_glob.scene = bpy.context.scene

    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')

    mdlRoot = getExportMdl()
    if mdlRoot:
        print('Neverblender: Exporting ' + mdlRoot.name)
        mdl = nvb_mdl.Mdl()
        asciiLines = []
        mdl.generateAscii(asciiLines, mdlRoot)
        with open(os.fsencode(mdlFilepath), 'w') as f:
            f.write('\n'.join(asciiLines))

        if 'WALKMESH' in exports:
            print('Neverblender: Exporting walkmesh.')
            asciiLines = []
            nvb_mdl.generateAsciiWalkmesh(asciiLines, mdlRoot)

            wkmFileExt = '.pwk'
            if mdlRoot.nvb.classification == nvb_def.classification.DOOR:
                wkmFileExt = '.dwk'
            elif mdlRoot.nvb.classification == nvb_def.classification.TILE:
                wkmFileExt = '.wok'

            wkmFilepath = os.path.splitext(mdlFilepath)[0] + wkmFileExt
            with open(os.fsencode(wkmFilepath), 'w') as f:
                f.write('\n'.join(asciiLines))

    return {'FINISHED'}
