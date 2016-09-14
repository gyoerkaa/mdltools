"""TODO: DOC."""

import os
import collections
from datetime import datetime

import bpy

from . import nvb_node
from . import nvb_anim
from . import nvb_glob
from . import nvb_def
from . import nvb_utils


class ObjectDB(collections.OrderedDict):
    """TODO: DOC."""

    def insertLoadedObj(self, nodeName, parentName, nodePos, loadedName):
        """TODO: DOC."""
        if nodeName in self:
            self[nodeName].append((parentName, nodePos, loadedName))
        else:
            self[nodeName] = [(parentName, nodePos, loadedName)]

    def getLoadedName(self, nodeName, parentName='', nodePos=-1):
        """TODO: DOC."""
        match = None
        if nodeName in self:
            if len(self[nodeName]) > 1:
                # Multiple objects with the same name.
                # This is bad, but we'll try to resolve it.
                # 1. check for same parents
                if parentName:
                    for potentialMatch in self[nodeName]:
                        if (parentName == potentialMatch[0]):
                            match = potentialMatch[2]
                            break
                # 2. Use the nearest node with lower position
                if (nodePos >= 0) and not match:
                    pmp = -1
                    pm = None
                    for potentialMatch in self[nodeName]:
                        if (potentialMatch[1] < nodePos) and \
                           (potentialMatch[1] > pmp):
                            pmp = potentialMatch[1]
                            pm = potentialMatch[2]
                    match = pm
            else:
                # Only a single object with the name (ideal case)
                match = self[nodeName][2]

        return match


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
        self.anims = []
        # Diction
        self.createdObjects = ObjectDB()

    def loadAsciiHeader(self, asciiData):
        """TODO: DOC."""
        asciiLines = asciiData.split('\n')
        for line in asciiLines:
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line, skip it
                continue

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
                    self.classification = line[1].upper()
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

    def loadAsciiGeometry(self, asciiData):
        """TODO: DOC."""
        for asciiNode in asciiData.split('node '):
            lines = [l.strip().split() for l in asciiNode.splitlines()]
            node = None
            nodeType = ''
            nodeName = 'UNNAMED'

            # Read node type
            try:
                nodeType = lines[0][0].lower()
            except (IndexError, AttributeError):
                raise nvb_def.MalformedMdlFile('Unable to read node type')

            # Read node Name
            try:
                nodeName = lines[0][1].lower()
            except (IndexError, AttributeError):
                raise nvb_def.MalformedMdlFile('Unable to read node name')

            # Create an object with that node type
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
                node = switch[nodeType](nodeName)
            except KeyError:
                raise nvb_def.MalformedMdlFile('Invalid node type')

            # Parse and add to node list
            node.loadAscii(lines)
            self.nodes.append(node)

    def loadAsciiAnims(self, asciiData):
        """TODO: DOC."""
        # Split into animations first
        for asciiAnim in asciiData.split('newanim '):
            # Now split the animations into header + nodes
            anim = None

            anim = nvb_anim.Animation()
            anim.loadAscii(asciiData)
            self.animations.append(anim)

    def loadAscii(self, asciiData):
        """TODO: DOC."""
        geomStart = asciiData.find('node ')
        animStart = asciiData.find('newanim ')

        if (geomStart < 0):
            # Something is wrong
            raise nvb_def.MalformedMdlFile('Unable to find geometry')

        self.loadAsciiHeader(asciiData[:geomStart-1])
        if (animStart < 0):
            # No animations
            if nvb_glob.importGeometry:
                self.loadAsciiGeometry(asciiData[geomStart:])
        else:
            if nvb_glob.importGeometry:
                self.loadAsciiGeometry(asciiData[geomStart:animStart-1])
            if nvb_glob.importAnim:
                self.loadAsciiGeometry(asciiData[animStart:])

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
    def generateAsciiGeometry(asciiLines, bObject, simple=False):
        """TODO: DOC."""
        nodeType = nvb_utils.getNodeType(bObject)
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

        node.generateAscii(bObject, asciiLines, simple)

        '''
        for child in bObject.children:
            self.generateGeomBlock(child, asciiLines, simple)
        '''
        childList = []
        for child in bObject.children:
            childList.append((child.nvb.imporder, child))
        childList.sort(key=lambda tup: tup[0])

        for (imporder, child) in childList:
            Mdl.generateAsciiGeometry(child, asciiLines, simple)

    @staticmethod
    def generateAsciiAnims():
        """TODO: DOC."""
        pass

    @staticmethod
    def generateAscii(asciiLines,
                      rootDummy,
                      exportAnim=True,
                      exportWalkmesh=True):
        """TODO: DOC."""
        # The Names of exported geometry nodes. We'll need this for skinmeshes
        # and animations
        validExports = []
        mdlName = rootDummy.name
        nvb_utils.getValidExports(rootDummy, validExports)

        currentTime = datetime.now()
        blendFileName = os.path.basename(bpy.data.filepath)
        if not blendFileName:
            blendFileName = 'unknown'
        asciiLines.append('# Exported from blender at ' +
                          currentTime.strftime('%A, %Y-%m-%d'))

        # Header
        Mdl.generateAsciiHeader(rootDummy)

        # Geometry
        asciiLines.append('beginmodelgeom ' + mdlName)
        Mdl.generateAsciiGeometry(rootDummy, asciiLines, False)
        asciiLines.append('endmodelgeom ' + mdlName)

        # Animations
        if exportAnim:
            asciiLines.append('')
            asciiLines.append('# ANIM ASCII')
            Mdl.generateAsciiAnims(rootDummy, asciiLines)

        # The End
        asciiLines.append('donemodel ' + mdlName)
        asciiLines.append('')

    def createObjectLinks(self, scene):
        """Handle parenting and linking the objects to a scene."""
        for objList in self.createdObjects:
            for obj in objList:
                parentName = obj[1]  # Name of the parent in the mdl
                nodePos = obj[2]  # Position of the node in the mdl

                # Check if the parent exists
                if (nvb_utils.isNull(parentName)):
                    # Node without parent. Must be the root dummy.
                    obj.nvb.dummytype = nvb_def.Dummytype.MDLROOT
                    obj.nvb.supermodel = self.supermodel
                    obj.nvb.classification = self.classification
                elif parentName in self.createdObjects:
                    parentLoadedName = self.createdObjects.getLoadedName(
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
                    # Parent doesn't exist.
                    raise nvb_def.MalformedMdlFile(obj.name +
                                                   ' has no parent ' +
                                                   obj.parentName)
                scene.objects.link(obj)

    def createObjects(self, options):
        """TODO: DOC."""
        if self.nodes:
            nodePos = 0
            for node in self.nodes:
                # Creates a blender object for this node
                obj = node.createObject(options)
                # Save the order of nodes. We'll need to restore it during
                # export.
                obj.nvb.order = nodePos
                nodePos += 1
                # Save the imported objects for animation import
                if obj:
                    self.createdObjects.insertLoadedObj(node.name,
                                                        node.parent,
                                                        nodePos,
                                                        obj.name)

    def createAnimations(self, options):
        """TODO: DOC."""
        for anim in self.animations:
            pass

    def create(self, scene, options):
        """TODO: DOC."""
        if nvb_glob.importGeometry:
            self.createObjects(options)
            self.createObjectLinks(scene)

            if nvb_glob.importAnims:
                self.createAnimations(options)
        else:
            # Import animations only, there is no objectDB in this case
            pass


class Wkm(Mdl):
    """TODO: DOC."""

    def __init__(self, wkmtype):
        """TODO: DOC."""
        Mdl.__init__(self)

        self.walkmeshType = wkmtype

    def createObjectLinks(self, scene):
        """TODO: DOC."""
        # We'll be adding an extra dummy and parent all objects with missing
        # parents to it (which should be all of them)
        wkmRootNode = nvb_node.dummy(self.name + ' ' + self.walkmeshType)
        # TODO: Set subtype
        wkmRootObj = wkmRootNode.createObject()
        scene.objects.link(wkmRootObj)

        for objList in self.createdObjects:
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
                elif parentName in self.createdObjects:
                    parentLoadedName = self.createdObjects.getLoadedName(
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
