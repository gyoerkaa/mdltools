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

    (mdlPath, mdlFilename) = os.path.split(filepath)
    options.mdlname = os.path.splitext(mdlFilename)[0]
    options.scene = bpy.context.scene

    with open(os.fsencode(filepath), 'r') as mdlfile:
        print('Neverblender: Importing ' + filepath)
        mdl = nvb_mdl.Mdl()
        asciiMdl = mdlfile.read()
        mdl.loadAscii(asciiMdl, options)

        # Try to load walkmeshes ... pwk (placeable) and dwk (door)
        if importWalkmesh:
            for wkmtype in ['pwk', 'dwk']:
                wkmFilename = options.mdlname + '.' + wkmtype
                wkmPath = os.fsencode(os.path.join(mdlPath, wkmFilename))
                try:
                    wkmFile = open(wkmPath, 'r')
                except IOError:
                    print("Neverblender: No " + wkmtype + " walkmesh found")
                else:
                    print('Neverblender: Importing ' + wkmFilename)
                    asciiWkm = wkmFile.read()
                    mdl.loadAsciiWalkmesh(asciiWkm, options)
                    wkmFile.close()

        mdl.create(options)

    return {'FINISHED'}


def saveMdl(operator, context,
            filepath='',
            exportAnimations=True,
            exportWalkmesh=True,
            exportSmoothGroups=True,
            applyModifiers=True):
    """Called from blender ui."""
    options = nvb_def.ExportOptions()
    options.exportAnim = exportAnimations
    options.exportWalkmesh = exportWalkmesh
    options.exportSmoothGroups = exportSmoothGroups
    options.applyModifiers = applyModifiers

    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')

    rootDummy = nvb_utils.findRootDummy(bpy.context.object)
    if rootDummy:
        print('Neverblender: Exporting ' + rootDummy.name)
        options.mdlname = rootDummy.name
        options.classification = rootDummy.nvb.classification
        asciiLines = []
        nvb_mdl.Mdl.generateAscii(rootDummy, asciiLines, options)
        with open(os.fsencode(filepath), 'w') as f:
            f.write('\n'.join(asciiLines))

        if options.exportWalkmesh:
            print('Neverblender: Exporting walkmesh.')
            asciiLines = []
            nvb_mdl.Mdl.generateAsciiWalkmesh(rootDummy, asciiLines, options)
            if asciiLines:
                wkmtype = '.pwk'
                if rootDummy.nvb.classification == \
                        nvb_def.Classification.DOOR:
                    wkmtype = '.dwk'
                elif rootDummy.nvb.classification == \
                        nvb_def.Classification.TILE:
                    wkmtype = '.wok'

                wkmPath = os.path.splitext(filepath)[0] + wkmtype
                with open(os.fsencode(wkmPath), 'w') as f:
                    f.write('\n'.join(asciiLines))
    else:
        return {'CANCELLED'}

    return {'FINISHED'}
