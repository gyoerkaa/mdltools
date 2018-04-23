"""TODO: DOC."""

import os
from datetime import datetime

import bpy

from . import nvb_node
from . import nvb_anim
from . import nvb_def
from . import nvb_utils


class Mdl():
    """TODO: DOC."""

    # Helper to create nodes of matching type
    nodelookup = {nvb_def.Nodetype.DUMMY:      nvb_node.Dummy,
                  nvb_def.Nodetype.PATCH:      nvb_node.Patch,
                  nvb_def.Nodetype.REFERENCE:  nvb_node.Reference,
                  nvb_def.Nodetype.TRIMESH:    nvb_node.Trimesh,
                  nvb_def.Nodetype.ANIMMESH:   nvb_node.Animmesh,
                  nvb_def.Nodetype.DANGLYMESH: nvb_node.Danglymesh,
                  nvb_def.Nodetype.SKIN:       nvb_node.Skinmesh,
                  nvb_def.Nodetype.EMITTER:    nvb_node.Emitter,
                  nvb_def.Nodetype.LIGHT:      nvb_node.Light,
                  nvb_def.Nodetype.AABB:       nvb_node.Aabb}

    def __init__(self):
        """TODO: DOC."""
        # Header Data
        self.name = 'UNNAMED'
        self.supermodel = nvb_def.null
        self.animscale = 1.0
        self.classification = nvb_def.Classification.UNKNOWN
        # Geometry
        self.mdlnodes = []
        self.pwknodes = []
        self.dwknodes = []
        # Animations
        self.animations = []
        # Resolve non-unique node names
        self.noderesolver = nvb_utils.NodeResolver()

    def readAsciiHeader(self, asciiBlock):
        """TODO: DOC."""
        asciiLines = [l.strip().split() for l in asciiBlock.splitlines()]
        for line in asciiLines:
            try:
                label = line[0].lower()
            except (IndexError, AttributeError):
                continue  # Probably empty line, skip it
            if (label == 'newmodel'):
                try:
                    self.name = line[1]
                except (ValueError, IndexError):
                    print("Neverblender: WARNING - Unable to read model name.")
            elif (label == 'setsupermodel'):
                try:  # should be ['setsupermodel', modelname, supermodelname]
                    self.supermodel = line[2]
                except (ValueError, IndexError):
                    print("Neverblender: WARNING - Unable to read supermodel. \
                           Using default value " + self.supermodel)
            elif (label == 'classification'):
                try:
                    self.classification = line[1].lower()
                except (ValueError, IndexError):
                    print("Neverblender: WARNING - Unable to read \
                           classification. \
                           Using Default value " + self.classification)
                if self.classification not in nvb_def.Classification.ALL:
                    print("Neverblender: WARNING - Invalid classification \
                           '" + self.classification + "'")
                    self.classification = nvb_def.Classification.UNKNOWN
            elif (label == 'setanimationscale'):
                try:
                    self.animscale = line[1]
                except (ValueError, IndexError):
                    print("Neverblender: WARNING - Unable to read \
                           animationscale. \
                           Using default value " + self.animscale)

    def readAsciiWalkmesh(self, asciiBlock, wkmtype, options):
        """TODO: DOC."""
        if options.importWalkmesh:
            geomStart = asciiBlock.find('node ')  # Look for the first 'node'
            if (geomStart < 0):  # Most likely empty walkmesh file
                print("Neverblender: WARNING: Unable to read walkmesh data")
                return
            if wkmtype == 'pwk':
                Mdl.readAsciiGeometry(asciiBlock[geomStart:], self.pwknodes)
            elif wkmtype == 'dwk':
                Mdl.readAsciiGeometry(asciiBlock[geomStart:], self.dwknodes)

    @staticmethod
    def readAsciiGeometry(asciiBlock, nodelist):
        """TODO: DOC."""
        dlm = 'node '
        asciiNodeList = [dlm+block for block in asciiBlock.split(dlm) if block]
        for idx, asciiNode in enumerate(asciiNodeList):
            asciiLines = [l.strip().split() for l in asciiNode.splitlines()]
            node = None
            nodeType = ''
            nodeName = 'UNNAMED'
            # Read node type
            try:
                nodeType = asciiLines[0][1].lower()
            except (IndexError, AttributeError):
                raise nvb_def.MalformedMdlFile('Unable to read node type')
            # Read node name
            try:
                nodeName = asciiLines[0][2].lower()
            except (IndexError, AttributeError):
                raise nvb_def.MalformedMdlFile('Unable to read node name')
            # Create an object with that type and name
            try:
                node = Mdl.nodelookup[nodeType](nodeName)
            except KeyError:
                raise nvb_def.MalformedMdlFile('Invalid node type')
            # Parse the rest and add to node list
            node.loadAscii(asciiLines, idx)
            nodelist.append(node)

    @staticmethod
    def readAsciiAnimation(asciiBlock):
        """Load a single animation from an ascii animation block."""
        anim = nvb_anim.Animation()
        anim.loadAscii(asciiBlock)
        return anim

    def readAsciiAnimations(self, asciiBlock):
        """Load all animations from an ascii mdl block."""
        dlm = 'newanim '  # Split animations using 'newanim' as delimiter
        animList = [dlm+block for block in asciiBlock.split(dlm) if block]
        self.animations = list(map(Mdl.readAsciiAnimation, animList))

    def readAscii(self, asciiBlock, options):
        """Load an mdl from an ascii mfl file."""
        geomStart = asciiBlock.find('node ')  # Look for the first 'node'
        animStart = asciiBlock.find('newanim ')  # Look for the first 'newanim'

        if (animStart > 0) and (geomStart > animStart):
            raise nvb_def.MalformedMdlFile('Animations before geometry')
        if (geomStart < 0):
            raise nvb_def.MalformedMdlFile('Unable to find geometry')

        self.readAsciiHeader(asciiBlock[:geomStart-1])
        # Import Geometry
        if (animStart > 0):
            # Animations present, exclude them for geometry loading
            Mdl.readAsciiGeometry(asciiBlock[geomStart:animStart],
                                  self.mdlnodes)
        else:
            Mdl.readAsciiGeometry(asciiBlock[geomStart:], self.mdlnodes)
        # Import Animations
        if options.importAnimations and (animStart > 0):
            self.readAsciiAnimations(asciiBlock[animStart:])

    @staticmethod
    def generateAsciiHeader(mdlRoot, asciiLines, options):
        """TODO: DOC."""
        blendfile = os.path.basename(bpy.data.filepath)
        if not blendfile:
            blendfile = 'unknown'
        mdlname = mdlRoot.name
        mdlclass = mdlRoot.nvb.classification.upper()
        mdlsuper = mdlRoot.nvb.supermodel
        mdlanimscale = mdlRoot.nvb.animscale

        asciiLines.append('filedependancy ' + blendfile)
        asciiLines.append('newmodel ' + mdlname)
        asciiLines.append('setsupermodel ' + mdlname + ' ' + mdlsuper)
        asciiLines.append('classification ' + mdlclass)
        asciiLines.append('setanimationscale ' + str(round(mdlanimscale, 2)))

    @staticmethod
    def generateAsciiGeometry(obj, asciiLines, options):
        """TODO: DOC."""
        if nvb_utils.isWkmRoot(obj):
            return
        nodeType = nvb_utils.getNodeType(obj)
        try:
            node = Mdl.nodelookup[nodeType]
        except KeyError:
            raise nvb_def.MalformedMdlFile('Invalid node type')

        node.generateAscii(obj, asciiLines, options, False)
        # Sort children to restore original order before import
        # (important for supermodels/animations to work)
        children = [c for c in obj.children]
        children.sort(key=lambda c: c.nvb.imporder)
        for c in children:
            Mdl.generateAsciiGeometry(c, asciiLines, options)

    @staticmethod
    def generateAsciiAnimations(mdlRoot, asciiLines, options):
        """TODO: DOC."""
        if mdlRoot.nvb.animList:
            asciiLines.append('')
            asciiLines.append('# ANIM ASCII')
            for anim in mdlRoot.nvb.animList:
                nvb_anim.Animation.generateAscii(mdlRoot, anim,
                                                 asciiLines, options)

    @staticmethod
    def generateAsciiMeta(mdlRoot, asciiLines, options):
        """Add creation time to a list of ascii lines."""
        currentTime = datetime.now()
        blendFileName = os.path.basename(bpy.data.filepath)
        if not blendFileName:
            blendFileName = 'unknown'
        asciiLines.append('# Exported from blender at ' +
                          currentTime.strftime('%A, %Y-%m-%d'))

    @staticmethod
    def generateAscii(mdlRoot, asciiLines, options):
        """TODO: DOC."""
        # The Names of exported geometry nodes. We'll need this for skinmeshes
        # and animations
        mdlName = mdlRoot.name
        # Creation time, etc
        Mdl.generateAsciiMeta(mdlRoot, asciiLines, options)
        # Header
        Mdl.generateAsciiHeader(mdlRoot, asciiLines, options)
        # Geometry
        asciiLines.append('beginmodelgeom ' + mdlName)
        Mdl.generateAsciiGeometry(mdlRoot, asciiLines, options)
        asciiLines.append('endmodelgeom ' + mdlName)
        # Animations
        if options.exportAnimations:
            Mdl.generateAsciiAnimations(mdlRoot, asciiLines, options)
        # The End
        asciiLines.append('donemodel ' + mdlName)
        asciiLines.append('')

    @staticmethod
    def generateAsciiWalkmesh(mdlRoot, asciiLines, wkmtype, options):
        """TODO: DOC."""
        wkmObjects = []
        if wkmtype == nvb_def.Walkmeshtype.WOK:
            # Walkmesh for tiles: Append only AABB mesh
            wok = nvb_utils.findAABB(mdlRoot)
            if wok:
                wkmObjects.append(wok)
        else:
            # Walkmesh for doors: Append all children of the walkmesh root
            wkmRoot = nvb_utils.findWkmRoot(mdlRoot, wkmtype)
            if wkmRoot:
                wkmObjects = [c for c in wkmRoot.children]
        # Abort if there is nothing to write
        if not wkmObjects:
            return
        # Creation time
        Mdl.generateAsciiMeta(mdlRoot, asciiLines, options)
        # Write Data
        for obj in wkmObjects:
            nodeType = nvb_utils.getNodeType(obj)
            try:
                node = Mdl.nodelookup[nodeType]
            except KeyError:
                print("Neverblender: WARNING - Unable to get node type.")
            else:
                node.generateAscii(obj, asciiLines, options, True)

    def createObjectLinks(self, nodelist, noderesolver, options):
        """Handles parenting and linking of objects to a scene."""
        def getRoot(obj):
            """Return the root of  obj."""
            while obj:
                if obj.parent is None:
                    return obj
                obj = obj.parent
            return None

        obj = None
        for node in nodelist:
            obj = noderesolver.get_obj(node.name, node.nodeidx)
            if obj:
                if node.parent:  # obj == rootobj:
                    parentobj = noderesolver.get_obj_parent(node.parent,
                                                            node.nodeidx)
                    obj.parent = parentobj
                else:
                    obj.parent = None
                    obj.nvb.supermodel = self.supermodel
                    obj.nvb.classification = self.classification
                options.scene.objects.link(obj)
            else:
                print('Neverblender: WARNING - Invalid object ' +
                      node.name)
        return getRoot(obj)

    @staticmethod
    def createObjects(nodelist, noderesolver, options):
        """TODO: DOC."""
        for node in nodelist:
            obj = node.createObject(options)
            # Save the imported objects for animation import
            if obj:
                noderesolver.insert_obj(node.name, node.nodeidx, obj.name)
            else:
                print('Neverblender: WARNING - Invalid node: ' + node.name)

    @staticmethod
    def createAnimations(animationlist, mdlroot, noderesolver, options):
        """TODO: DOC."""
        # Load the 'default' animation first, so it is at the front
        anims = [a for a in animationlist if a.name == 'default']
        for a in anims:
            a.create(mdlroot, noderesolver, options)
        # Load the rest of the anims
        anims = [a for a in animationlist if a.name != 'default']
        for a in anims:
            a.create(mdlroot, noderesolver, options)

    def create(self, options):
        """TODO: DOC."""
        def insertWalkmeshRoot(mdlnodes, wkmnodes, wkmtype, options):
            """Generate a root node as parent for all walkmesh objects."""
            # Get root node
            if wkmtype not in nvb_def.Walkmeshtype.IMPORT:
                print('Neverblender: WARNING - Invalid walkmesh type: '
                      + wkmtype)
                return
            # Generate name
            parentNames = set([n.parent for n in wkmnodes])
            rootName = ''
            if len(parentNames) >= 1:
                # All nodes in the walkmesh SHOULD have the same parent
                rootName = next(iter(parentNames))
                if len(parentNames) > 1:
                    # Multiple parents (Walkmesh is technically invalid)
                    # Try to solve the issue by re-parenting
                    for node in wkmnodes:
                        node.parent = rootName
            else:
                # This shouldn't happen really
                rootName = options.mdlname + '_' + wkmtype
                for node in wkmnodes:
                    node.parent = rootName
            wkmroot = nvb_node.Dummy(rootName)
            if wkmtype == nvb_def.Walkmeshtype.DWK:
                wkmroot.emptytype = nvb_def.Emptytype.DWK
            else:
                wkmroot.emptytype = nvb_def.Emptytype.PWK
            wkmnodes.insert(0, wkmroot)

        if options.customfps:
            options.scene.render.fps = options.fps
        # Create mdl objects
        mdlresolver = nvb_utils.NodeResolver()
        Mdl.createObjects(self.mdlnodes, mdlresolver, options)
        mdlroot = self.createObjectLinks(self.mdlnodes, mdlresolver, options)
        # Create pwk objects
        if self.pwknodes:
            wkmresolver = nvb_utils.NodeResolver()
            insertWalkmeshRoot(self.mdlnodes, self.pwknodes,
                               nvb_def.Walkmeshtype.PWK, options)
            Mdl.createObjects(self.pwknodes, wkmresolver, options)
            wkmroot = self.createObjectLinks(self.pwknodes, wkmresolver,
                                             options)
            wkmroot.parent = mdlroot
            del wkmresolver
        # Create dwk objects
        if self.dwknodes:
            wkmresolver = nvb_utils.NodeResolver()
            insertWalkmeshRoot(self.mdlnodes, self.dwknodes,
                               nvb_def.Walkmeshtype.DWK, options)
            Mdl.createObjects(self.dwknodes, wkmresolver, options)
            wkmroot = self.createObjectLinks(self.dwknodes, wkmresolver,
                                             options)
            wkmroot.parent = mdlroot
            del wkmresolver
        # Create animations
        if options.importAnimations:
            self.createAnimations(self.animations,
                                  mdlroot, mdlresolver, options)
