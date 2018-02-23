"""TODO: DOC."""

import os
import bpy

from . import nvb_def
from . import nvb_mdl
from . import nvb_utils


def loadMdl(operator, context, options):
    """Called from blender ui."""
    (mdlPath, mdlFilename) = os.path.split(options.filepath)
    options.mdlname = os.path.splitext(mdlFilename)[0]

    with open(os.fsencode(options.filepath), 'r') as mdlfile:
        mdl = nvb_mdl.Mdl()
        asciiMdl = mdlfile.read()
        mdl.readAscii(asciiMdl, options)
        # Try to load walkmeshes ... pwk (placeable) and dwk (door)
        if options.importWalkmesh:
            for wkmtype in nvb_def.Walkmeshtype.IMPORT:
                wkmFilename = options.mdlname + '.' + wkmtype
                wkmPath = os.fsencode(os.path.join(mdlPath, wkmFilename))
                try:
                    wkmFile = open(wkmPath, 'r')
                except IOError:
                    pass  # There is no such file
                else:
                    asciiWkm = wkmFile.read()
                    mdl.readAsciiWalkmesh(asciiWkm, wkmtype, options)
                    wkmFile.close()
        mdl.create(options)

    return {'FINISHED'}


def saveMdl(operator, context, options):
    """Called from blender ui."""
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')

    rootDummy = nvb_utils.findRootDummy(bpy.context.object)
    if rootDummy:
        options.mdlname = rootDummy.name
        options.classification = rootDummy.nvb.classification
        asciiLines = []
        nvb_mdl.Mdl.generateAscii(rootDummy, asciiLines, options)
        with open(os.fsencode(options.filepath), 'w') as f:
            f.write('\n'.join(asciiLines))
        if options.exportWalkmesh:
            # Get walkmesh type
            wkmtype = nvb_def.Walkmeshtype.PWK
            if rootDummy.nvb.classification == nvb_def.Classification.DOOR:
                wkmtype = nvb_def.Walkmeshtype.DWK
            elif rootDummy.nvb.classification == nvb_def.Classification.TILE:
                wkmtype = nvb_def.Walkmeshtype.WOK
            # Only write to file if there is actually any data
            asciiLines = []
            nvb_mdl.Mdl.generateAsciiWalkmesh(rootDummy, asciiLines,
                                              wkmtype, options)
            if asciiLines:
                wkmPath = os.path.splitext(options.filepath)[0] + '.' + wkmtype
                with open(os.fsencode(wkmPath), 'w') as f:
                    f.write('\n'.join(asciiLines))
            else:
                pass
    else:
        return {'CANCELLED'}

    return {'FINISHED'}
