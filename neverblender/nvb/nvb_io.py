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
            importAnimations=True,
            importSupermodel=False,
            materialMode='SIN',
            textureSearch=False,
            minimapMode=False,
            minimapSkipFade=False):
    """Called from blender ui."""
    options = nvb_def.ImportOptions()
    options.importGeometry = importGeometry
    options.importSmoothGroups = importSmoothGroups
    options.importAnimations = importAnimations
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
        print('Neverblender: Loading ' + options.mdlname + ' ...')
        mdl = nvb_mdl.Mdl()
        asciiMdl = mdlfile.read()
        mdl.loadAscii(asciiMdl, options)
        print('Neverblender: ... done')
        # Try to load walkmeshes ... pwk (placeable) and dwk (door)
        if importWalkmesh:
            for wkmtype in ['pwk', 'dwk']:
                wkmFilename = options.mdlname + '.' + wkmtype
                wkmPath = os.fsencode(os.path.join(mdlPath, wkmFilename))
                try:
                    wkmFile = open(wkmPath, 'r')
                except IOError:
                    pass  # There is no such file
                else:
                    print('Neverblender: Loading ' + wkmFilename)
                    asciiWkm = wkmFile.read()
                    mdl.loadAsciiWalkmesh(asciiWkm, options)
                    wkmFile.close()
                    print('Neverblender: ... done')
        print('Neverblender: Creating objects ...')
        mdl.create(options)
        print('Neverblender: ... done')

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
        print('Neverblender: Exporting ' + rootDummy.name + ' ...')
        options.mdlname = rootDummy.name
        options.classification = rootDummy.nvb.classification
        asciiLines = []
        nvb_mdl.Mdl.generateAscii(rootDummy, asciiLines, options)
        with open(os.fsencode(filepath), 'w') as f:
            f.write('\n'.join(asciiLines))
        print('Neverblender: ... done')
        if options.exportWalkmesh:
            print('Neverblender: Exporting walkmesh ...')
            # Get walkmesh type
            wkmtype = '.pwk'
            if rootDummy.nvb.classification == \
                    nvb_def.Classification.DOOR:
                wkmtype = '.dwk'
            elif rootDummy.nvb.classification == \
                    nvb_def.Classification.TILE:
                wkmtype = '.wok'
            print('Neverblender: ... detected type: ' + wkmtype + ' ...')
            # Only write to file if there is actually any data
            asciiLines = []
            nvb_mdl.Mdl.generateAsciiWalkmesh(rootDummy, asciiLines, options)
            if asciiLines:
                wkmPath = os.path.splitext(filepath)[0] + wkmtype
                with open(os.fsencode(wkmPath), 'w') as f:
                    f.write('\n'.join(asciiLines))
                print('Neverblender: ... done')
            else:
                print('Neverblender: ... no nodes found')
    else:
        return {'CANCELLED'}

    return {'FINISHED'}
