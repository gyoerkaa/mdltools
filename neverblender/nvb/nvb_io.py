"""TODO: DOC."""

import os
import bpy

from . import nvb_def
from . import nvb_mdl
from . import nvb_utils


def loadMdl(operator, context,
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
        mdl.loadAscii(asciiMdl, options)

        # Try to load walkmeshes ... pwk (placeable) and dwk (door)
        if importWalkmesh:
            (mdlPath, mdlFilename) = os.path.split(filepath)
            for wkmtype in ['pwk', 'dwk']:
                wkmPath = os.fsencode(os.path.join(
                            mdlPath,
                            os.path.splitext(mdlFilename)[0] + '.' + wkmtype))
                try:
                    wkmFile = open(wkmPath, 'r')
                except IOError:
                    print("Neverblender: No " + wkmtype + " walkmesh found")
                else:
                    asciiWkm = wkmFile.read()
                    mdl.loadAsciiWalkmesh(asciiWkm, options)
                    wkmFile.close()

        mdl.create(scene, options)

    return {'FINISHED'}


def saveMdl(operator, context,
            filepath='',
            exports={'ANIMATION', 'WALKMESH'},
            useSmoothGroups=True,
            applyModifiers=True):
    """Called from blender ui."""
    options = nvb_def.ExportOptions()
    options.exportAnim = 'ANIMATION' in exports
    options.exportWalkmesh = 'WALKMESH' in exports
    options.exportSmoothGroups = useSmoothGroups
    options.applyModifiers = applyModifiers

    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')

    rootDummy = nvb_utils.findRootDummy(bpy.context.object)
    options.classification = rootDummy.classification
    if rootDummy:
        print('Neverblender: Exporting ' + rootDummy.name)
        asciiLines = []
        nvb_mdl.Mdl.generateAscii(rootDummy, asciiLines, options)
        with open(os.fsencode(filepath), 'w') as f:
            f.write('\n'.join(asciiLines))

        if options.exportWalkmesh:
            print('Neverblender: Exporting walkmesh.')
            asciiLines = []
            nvb_mdl.Mdl.generateAsciiWalkmesh(rootDummy, asciiLines, options)

            wkmtype = '.pwk'
            if rootDummy.nvb.classification == nvb_def.classification.DOOR:
                wkmtype = '.dwk'
            elif rootDummy.nvb.classification == nvb_def.classification.TILE:
                wkmtype = '.wok'

            wkmPath = os.path.splitext(filepath)[0] + wkmtype
            with open(os.fsencode(wkmPath), 'w') as f:
                f.write('\n'.join(asciiLines))

    return {'FINISHED'}
