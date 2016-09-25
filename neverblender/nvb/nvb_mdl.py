"""TODO: DOC."""

import os
from datetime import datetime

import bpy

from . import nvb_node
from . import nvb_anim
from . import nvb_glob
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
        for line in asciiBlock.splitlines():
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

    def loadAsciiGeometry(self, asciiBlock, walkmesh=False):
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
            if walkmesh:
                node.parent = '!'
            self.nodes.append(node)

    def loadAsciiWalkmesh(self, asciiBlock):
        """TODO: Doc."""
        self.loadAsciiGeometry(asciiBlock, True)

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

    def loadAscii(self, asciiBlock):
        """Load an mdl from an ascii mfl file."""
        geomStart = asciiBlock.find('node ')  # Look for the first 'node'
        animStart = asciiBlock.find('newanim ')  # Look for the first 'newanim'

        if (geomStart < 0) or ((animStart > 0) and (geomStart > animStart)):
            # Something is wrong
            raise nvb_def.MalformedMdlFile('Unable to find geometry')

        self.loadAsciiHeader(asciiBlock[:geomStart-1])
        if (animStart < 0):
            # No animations
            if nvb_glob.importGeometry:
                self.loadAsciiGeometry(asciiBlock[geomStart:])
        else:
            if nvb_glob.importGeometry:
                self.loadAsciiGeometry(asciiBlock[geomStart:animStart-1])
            if nvb_glob.importAnim:
                self.loadAsciiAnimations(asciiBlock[animStart:])

    @staticmethod
    def generateAsciiHeader(asciiLines, rootDummy):
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
    def generateAsciiGeometry(asciiLines, obj):
        """TODO: DOC."""
        nodeType = nvb_utils.getNodeType(obj)
        switch = {'dummy':      nvb_node.Dummy,
                  'patch':      nvb_node.Patch,
                  'reference':  nvb_node.Reference,
                  'trimesh':    nvb_node.Trimesh,
                  'animmesh':   nvb_node.Animmesh,
                  'danglymesh': nvb_node.Danglymesh,
                  'skin':       nvb_node.Skinmesh,
                  'emitter':    nvb_node.Emitter,
                  'light':      nvb_node.Light,
                  'aabb':       nvb_node.Aabb}
        try:
            node = switch[nodeType]()
        except KeyError:
            raise nvb_def.MalformedMdlFile('Invalid node type')

        node.generateAscii(obj, asciiLines)

        childList = []
        for child in obj.children:
            childList.append((child.nvb.imporder, child))
        childList.sort(key=lambda tup: tup[0])

        for (imporder, child) in childList:
            Mdl.generateAsciiGeometry(asciiLines, child)

    @staticmethod
    def generateAsciiAnims(asciiLines, rootDummy):
        """TODO: DOC."""
        pass

    @staticmethod
    def generateAscii(asciiMdl,
                      asciiWalkmesh,
                      rootDummy,
                      exportAnims=True,
                      exportWalkmesh=True):
        """TODO: DOC."""
        Mdl.generateAsciiMdl(asciiMdl, rootDummy, exportAnims)
        if exportWalkmesh:
            Mdl.generateAsciiWalkmesh(asciiWalkmesh, rootDummy)

    @staticmethod
    def generateAsciiMeta(asciiLines):
        """Add creation time to a list of ascii lines."""
        currentTime = datetime.now()
        blendFileName = os.path.basename(bpy.data.filepath)
        if not blendFileName:
            blendFileName = 'unknown'
        asciiLines.append('# Exported from blender at ' +
                          currentTime.strftime('%A, %Y-%m-%d'))

    @staticmethod
    def generateAsciiMdl(asciiLines,
                         rootDummy,
                         exportAnims=True):
        """TODO: DOC."""
        # The Names of exported geometry nodes. We'll need this for skinmeshes
        # and animations
        validExports = []
        mdlName = rootDummy.name
        nvb_utils.getValidExports(rootDummy, validExports)

        # Creation time
        Mdl.generateAsciiMeta(asciiLines)
        # Header
        Mdl.generateAsciiHeader(asciiLines, rootDummy)
        # Geometry
        asciiLines.append('beginmodelgeom ' + mdlName)
        Mdl.generateAsciiGeometry(rootDummy, asciiLines, False)
        asciiLines.append('endmodelgeom ' + mdlName)
        # Animations
        if exportAnims:
            asciiLines.append('')
            asciiLines.append('# ANIM ASCII')
            Mdl.generateAsciiAnims(rootDummy, asciiLines)
        # The End
        asciiLines.append('donemodel ' + mdlName)
        asciiLines.append('')

    @staticmethod
    def generateAsciiWalkmesh(asciiLines,
                              rootDummy):
        """TODO: DOC."""
        # Creation time
        Mdl.generateAsciiMeta(asciiLines)

    def createObjectLinks(self, scene, options):
        """Handle parenting and linking the objects to a scene."""
        # Loop over all imported nodes
        # There may be several nodes with the same name in the mdl.
        # However, Blender object names are unique, we need to fix this.
        for node in self.nodes:
            objName = self.nodeNameResolver.findObj(node.name,
                                                    node.parent,
                                                    node.id)
            if objName:
                obj = bpy.data.objects[objName]
                if node.parent:
                    # Using '?' to specify that the parent is unknown
                    objParentName = self.nodeNameResolver.findObj(node.parent,
                                                                  '?',
                                                                  node.id)
                    if objParentName:
                        obj.parent = bpy.data.objects[objParentName]
                        obj.matrix_parent_inverse = \
                            obj.parent.matrix_world.inverted()
                    else:
                        print('    Parent: NOT found')
                else:
                    # Node without parent. Treat as rootdummy.
                    obj.nvb.supermodel = self.supermodel
                    obj.nvb.classification = self.classification
                scene.objects.link(obj)

    def createObjects(self, scene, options):
        """TODO: DOC."""
        if self.nodes:
            for node in self.nodes:
                # Creates a blender object for this node
                obj = node.createObject(options)
                # Save the imported objects for animation import
                if obj:
                    self.nodeNameResolver.insertObj(node.name,
                                                    node.parent,
                                                    node.id,
                                                    obj.name)

    def createAnimations(self, scene, options):
        """TODO: DOC."""
        rootDummy = nvb_utils.findRootDummy()
        # We will load the 'default' animation first, so it is at the front
        defaultAnims = [a for a in self.animations if a.name == 'default']
        for anim in defaultAnims:
            anim.create(rootDummy, self.nodeNameResolver, options)

        nonDefaultAnims = [a for a in self.animations if a.name != 'default']
        for anim in nonDefaultAnims:
            anim.create(rootDummy, self.nodeNameResolver, options)

    def create(self, scene, options):
        """TODO: DOC."""
        if options.importGeometry:
            self.createObjects(scene, options)
            self.createObjectLinks(scene, options)

            if options.importAnim:
                self.createAnimations(scene, options)
        else:
            # Import animations only, there is no objectDB in this case
            pass


class Wkm(Mdl):
    """TODO: DOC."""

    def __init__(self, wkmtype):
        """TODO: DOC."""
        Mdl.__init__(self)

        self.walkmeshType = wkmtype

    def createObjectLinks(self, scene, options):
        """TODO: DOC."""
        # We'll be adding an extra dummy and parent all objects with missing
        # parents to it (which should be all of them)
        wkmRootNode = nvb_node.dummy(self.name + ' ' + self.walkmeshType)
        # TODO: Set subtype
        wkmRootObj = wkmRootNode.createObject()
        scene.objects.link(wkmRootObj)

        for objList in self.nodeNameResolver:
            for obj in objList:
                # loadedName = obj[0]  # Unique name of the object in blender
                parentName = obj[1]  # Name of the parent in the mdl
                nodePos = obj[2]  # Position of the node in the mdl

                # Check if the parent exists
                if (nvb_utils.isNull(parentName)):
                    # Node without parent. Must be the root dummy.
                    obj.nvb.dummytype = nvb_def.Dummytype.MDLROOT
                    obj.nvb.supermodel = self.supermodel
                    obj.nvb.classification = self.classification
                elif parentName in self.nodeNameResolver:
                    parentLoadedName = self.nodeNameResolver.getLoadedName(
                        parentName,
                        '',
                        nodePos)
                    if parentLoadedName:
                        obj.parent = bpy.data.objects[parentLoadedName]
                        obj.matrix_parent_inverse = \
                            obj.parent.matrix_world.inverted()
                    else:
                        # TODO...or not todo?
                        pass
                else:
                    # Parent doesn't exist. use our custom one
                    obj.parent = wkmRootObj
                    obj.matrix_parent_inverse = \
                        wkmRootObj.parent.matrix_world.inverted()
                scene.objects.link(obj)
