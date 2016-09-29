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

    def __init__(self):
        """TODO: DOC."""
        # Header Data
        self.name = 'UNNAMED'
        self.supermodel = nvb_def.null
        self.animscale = 1.0
        self.classification = nvb_def.Classification.UNKNOWN
        # Geometry
        self.nodes = []
        # Animations
        self.animations = []
        # Resolve non-unique node names
        self.nodeNameResolver = nvb_utils.NodeNameResolver()

    def getRootNode(self):
        """TODO:DOC."""
        parentlessNodes = [n for n in self.nodes if ((not n.parent) and
                           (n.nodetype == nvb_def.Nodetype.DUMMY))]
        if parentlessNodes:
            return parentlessNodes[0]
        else:
            return None

    def loadAsciiHeader(self, asciiBlock):
        """TODO: DOC."""
        asciiLines = [l.strip().split() for l in asciiBlock.splitlines()]
        for line in asciiLines:
            try:
                label = line[0].lower()
            except IndexError:
                continue  # Probably empty line, skip it
            if (label == 'newmodel'):
                try:
                    self.name = line[1]
                except IndexError:
                    print("Neverblender - WARNING: Unable to read model name.")
            elif (label == 'setsupermodel'):
                try:
                    # line should be
                    # ['setsupermodel', modelname, supermodelname]
                    self.supermodel = line[2]
                except IndexError:
                    print("Neverblender - WARNING: Unable to read supermodel. \
                           Using default value " + self.supermodel)
            elif (label == 'classification'):
                try:
                    self.classification = line[1].lower()
                except IndexError:
                    print("Neverblender - WARNING: Unable to read \
                           classification. \
                           Using Default value " + self.classification)

                if self.classification not in nvb_def.Classification.ALL:
                    print("Neverblender - WARNING: Invalid classification \
                           '" + self.classification + "'")
                    self.classification = nvb_def.Classification.UNKNOWN
            elif (label == 'setanimationscale'):
                try:
                    self.animscale = line[1]
                except IndexError:
                    print("Neverblender - WARNING: Unable to read \
                           animationscale. \
                           Using default value " + self.animscale)

    def loadAsciiWalkmeshGeometry(self, asciiBlock):
        """TODO: DOC."""
        # Helper to create nodes of matching type
        nodelookup = {'dummy':      nvb_node.Dummy,
                      'patch':      nvb_node.Patch,
                      'reference':  nvb_node.Reference,
                      'trimesh':    nvb_node.Trimesh,
                      'animmesh':   nvb_node.Animmesh,
                      'danglymesh': nvb_node.Danglymesh,
                      'skin':       nvb_node.Skinmesh,
                      'emitter':    nvb_node.Emitter,
                      'light':      nvb_node.Light,
                      'aabb':       nvb_node.Aabb}
        dlm = 'node '
        nodeList = [dlm+block for block in asciiBlock.split(dlm) if block]
        for idx, asciiNode in enumerate(nodeList):
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
                node = nodelookup[nodeType](nodeName)
            except KeyError:
                raise nvb_def.MalformedMdlFile('Invalid node type')
            # Parse the rest and add to node list
            node.loadAscii(asciiLines, idx)
            # Set Walkmesh stuff
            node.parent = '!'  # Always parent to rootdummy
            if node.nodetype == nvb_def.Nodetype.TRIMESH:
                node.meshtype = nvb_def.Meshtype.WALKMESH
                node.walkmeshtype = nvb_def.Walkmeshtype.get(node.name)
            self.nodes.append(node)

    def loadAsciiWalkmesh(self, asciiBlock, options):
        """TODO: DOC."""
        geomStart = asciiBlock.find('node ')  # Look for the first 'node'
        if options.importWalkmesh:
            if (geomStart < 0):
                # Something is wrong
                raise nvb_def.MalformedMdlFile('Unable to find geometry')
            self.loadAsciiWalkmeshGeometry(asciiBlock[geomStart:])

    def loadAsciiGeometry(self, asciiBlock):
        """TODO: DOC."""
        # Helper to create nodes of matching type
        nodelookup = {'dummy':      nvb_node.Dummy,
                      'patch':      nvb_node.Patch,
                      'reference':  nvb_node.Reference,
                      'trimesh':    nvb_node.Trimesh,
                      'animmesh':   nvb_node.Animmesh,
                      'danglymesh': nvb_node.Danglymesh,
                      'skin':       nvb_node.Skinmesh,
                      'emitter':    nvb_node.Emitter,
                      'light':      nvb_node.Light,
                      'aabb':       nvb_node.Aabb}
        dlm = 'node '
        nodeList = [dlm+block for block in asciiBlock.split(dlm) if block]
        for idx, asciiNode in enumerate(nodeList):
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
                node = nodelookup[nodeType](nodeName)
            except KeyError:
                raise nvb_def.MalformedMdlFile('Invalid node type')
            # Parse the rest and add to node list
            node.loadAscii(asciiLines, idx)
            self.nodes.append(node)

    @staticmethod
    def loadAsciiAnimation(asciiBlock):
        """Load a single animation from an ascii mdl block."""
        anim = nvb_anim.Animation()
        anim.loadAscii(asciiBlock)
        return anim

    def loadAsciiAnimations(self, asciiBlock):
        """Load all animations from an ascii mdl block."""
        # Split into animations using 'newanim' as delimiter
        dlm = 'newanim '
        animList = [dlm+block for block in asciiBlock.split(dlm) if block]
        self.animations = list(map(Mdl.loadAsciiAnimation, animList))

    def loadAscii(self, asciiBlock, options):
        """Load an mdl from an ascii mfl file."""
        geomStart = asciiBlock.find('node ')  # Look for the first 'node'
        animStart = asciiBlock.find('newanim ')  # Look for the first 'newanim'

        if (animStart > 0) and (geomStart > animStart):
            raise nvb_def.MalformedMdlFile('Animations before geometry')
        if (geomStart < 0):
            raise nvb_def.MalformedMdlFile('Unable to find geometry')

        self.loadAsciiHeader(asciiBlock[:geomStart-1])
        # Import Geometry
        if options.importGeometry:
            if (animStart > 0):
                # Animations present, skip them
                self.loadAsciiGeometry(asciiBlock[geomStart:animStart])
            else:
                self.loadAsciiGeometry(asciiBlock[geomStart:])
        # Import Animations
        if options.importAnim and (animStart > 0):
            self.loadAsciiAnimations(asciiBlock[animStart:])

    @staticmethod
    def generateAsciiHeader(rootDummy, asciiLines, options):
        """TODO: DOC."""
        blendfile = os.path.basename(bpy.data.filepath)
        mdlname = rootDummy.nvb.name
        mdlclass = rootDummy.nvb.classification
        mdlsuper = rootDummy.nvb.animscale
        mdlanimscale = rootDummy.nvb.animscale

        asciiLines.append('filedependancy ' + blendfile)
        asciiLines.append('newmodel ' + mdlname)
        asciiLines.append('setsupermodel ' + mdlname + ' ' + mdlsuper)
        asciiLines.append('classification ' + mdlclass)
        asciiLines.append('setanimationscale ' + str(round(mdlanimscale, 2)))

    @staticmethod
    def generateAsciiGeometry(obj, asciiLines, options):
        """TODO: DOC."""
        nodeType = nvb_utils.getNodeType(obj)
        nodelookup = {'dummy':      nvb_node.Dummy,
                      'patch':      nvb_node.Patch,
                      'reference':  nvb_node.Reference,
                      'trimesh':    nvb_node.Trimesh,
                      'animmesh':   nvb_node.Animmesh,
                      'danglymesh': nvb_node.Danglymesh,
                      'skin':       nvb_node.Skinmesh,
                      'emitter':    nvb_node.Emitter,
                      'light':      nvb_node.Light,
                      'aabb':       nvb_node.Aabb}
        if nodeType == nvb_def.Nodetype.WALKMESH:
            pass
        try:
            node = nodelookup[nodeType]()
        except KeyError:
            raise nvb_def.MalformedMdlFile('Invalid node type')

        node.generateAscii(obj, asciiLines)

        childList = []
        for child in obj.children:
            childList.append((child.nvb.imporder, child))
        childList.sort(key=lambda tup: tup[0])

        for (imporder, child) in childList:
            Mdl.generateAsciiGeometry(child, asciiLines, options)

    @staticmethod
    def generateAsciiAnimations(rootDummy, asciiLines, options):
        """TODO: DOC."""
        for anim in rootDummy.nvb.animList:
            nvb_anim.Animation.generateAscii(rootDummy, anim,
                                             asciiLines, options)

    @staticmethod
    def generateAsciiMeta(rootDummy, asciiLines, options):
        """Add creation time to a list of ascii lines."""
        currentTime = datetime.now()
        blendFileName = os.path.basename(bpy.data.filepath)
        if not blendFileName:
            blendFileName = 'unknown'
        asciiLines.append('# Exported from blender at ' +
                          currentTime.strftime('%A, %Y-%m-%d'))

    @staticmethod
    def generateAscii(rootDummy, asciiLines, options):
        """TODO: DOC."""
        # The Names of exported geometry nodes. We'll need this for skinmeshes
        # and animations
        mdlName = rootDummy.name
        # Creation time
        Mdl.generateAsciiMeta(rootDummy, asciiLines, options)
        # Header
        Mdl.generateAsciiHeader(rootDummy, asciiLines, options)
        # Geometry
        asciiLines.append('beginmodelgeom ' + mdlName)
        Mdl.generateAsciiGeometry(rootDummy, asciiLines, options)
        asciiLines.append('endmodelgeom ' + mdlName)
        # Animations
        if options.exportAnims:
            asciiLines.append('')
            asciiLines.append('# ANIM ASCII')
            Mdl.generateAsciiAnimations(rootDummy, asciiLines, options)
        # The End
        asciiLines.append('donemodel ' + mdlName)
        asciiLines.append('')

    @staticmethod
    def generateAsciiWalkmesh(rootDummy, asciiLines, options):
        """TODO: DOC."""
        # mdlName = rootDummy.name

        # Creation time
        Mdl.generateAsciiMeta(asciiLines)

    def createObjectLinks(self, options):
        """Handle parenting and linking the objects to a scene."""
        # We'll need this for objects with missing parents (or walkmeshes)
        rootNode = self.getRootNode()
        if rootNode:
            rootObjName = self.nodeNameResolver.findObj(rootNode.name, '')
            rootObj = bpy.data.objects[rootObjName]
        # Loop over all imported nodes
        # There may be several nodes with the same name in the mdl.
        # However, Blender object names are unique, we need to fix this.
        for node in self.nodes:
            objName = self.nodeNameResolver.findObj(node.name,
                                                    node.parent,
                                                    node.nodeidx)
            if objName:
                obj = bpy.data.objects[objName]
                if node.parent:
                    if node.parent == '!':
                        obj.parent = rootObj
                        obj.matrix_parent_inverse = \
                            obj.parent.matrix_world.inverted()
                    else:
                        # Using '?' to specify that the parent is unknown
                        objParentName = self.nodeNameResolver.findObj(
                                node.parent,
                                '?',
                                node.nodeidx)
                        if objParentName:
                            obj.parent = bpy.data.objects[objParentName]

                else:
                    # Node without parent (empty string or 'null').
                    # Treat as rootdummy.
                    obj.nvb.supermodel = self.supermodel
                    obj.nvb.classification = self.classification
                options.scene.objects.link(obj)

    def createObjects(self, options):
        """TODO: DOC."""
        options.scene.render.fps = nvb_def.anim_fps
        if self.nodes:
            for node in self.nodes:
                # Creates a blender object for this node
                obj = node.createObject(options)
                # Save the imported objects for animation import
                if obj:
                    self.nodeNameResolver.insertObj(node.name,
                                                    node.parent,
                                                    node.nodeidx,
                                                    obj.name)
                else:
                    print('INTERNAL ERROR')

    def createAnimations(self, options):
        """TODO: DOC."""
        rootDummy = nvb_utils.findRootDummy(bpy.context.object)
        # We will load the 'default' animation first, so it is at the front
        defaultAnims = [a for a in self.animations if a.name == 'default']
        for anim in defaultAnims:
            anim.create(rootDummy, self.nodeNameResolver, options)

        nonDefaultAnims = [a for a in self.animations if a.name != 'default']
        for anim in nonDefaultAnims:
            anim.create(rootDummy, self.nodeNameResolver, options)

    def create(self, options):
        """TODO: DOC."""
        if options.importGeometry:
            self.createObjects(options)
            self.createObjectLinks(options)

            if options.importAnim:
                self.createAnimations(options)
        else:
            # Import animations only, there is no objectDB in this case
            pass
