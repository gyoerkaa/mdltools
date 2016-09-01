import os
import collections
import enum
from datetime import datetime

import bpy

from . import nvb_node
from . import nvb_anim
from . import nvb_glob
from . import nvb_def
from . import nvb_utils


class ObjectDB(collections.OrderedDict):
    def insertLoadedObj(self, nodeName, parentName, nodePos, loadedName):
        if nodeName in self:
            self[nodeName].append((parentName, nodePos, loadedName))
        else:
            self[nodeName] = [(parentName, nodePos, loadedName)]

    def getLoadedName(self, nodeName, parentName = '', nodePos = -1):
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
                    pm  = None
                    for potentialMatch in self[nodeName]:
                        if (potentialMatch[1] < nodePos) and \
                           (potentialMatch[1] > pmp):
                            pmp = potentialMatch[1]
                            pm  = potentialMatch[2]
                    match = pm
            else:
                # Only a single object with the name (ideal case)
                match = self[nodeName][2]

        return match


class Mdl():
    def __init__(self):
        # Header Data
        self.name           = 'UNNAMED'
        self.supermodel     = nvb_def.null
        self.animscale      = 1.0
        self.classification = nvb_def.Classification.UNKNOWN
        # Geometry
        self.nodes = []
        # Animations
        self.anims = []
        # Diction
        createdObjects = ObjectDB()


    def loadAsciiHeader(self, asciiData):
        asciiLines = asciiData.split('\n')
        for line in asciiLines:
            try:
                label = line[0]
            except IndexError:
                # Probably empty line or whatever, just skip it
                continue

            if (label == 'newmodel'):
                try:
                    self.name = line[1]
                except IndexError:
                    print("Neverblender - WARNING: Unable to read model name.")
            elif (label == 'setsupermodel'):
                try:
                    # line should be ['setsupermodel', modelname, supermodelname]
                    self.supermodel = line[2]
                except IndexError:
                    print("Neverblender - WARNING: Unable to read supermodel. Default value " + self.supermodel)
            elif (label == 'classification'):
                try:
                    self.classification = line[1].upper()
                except IndexError:
                    print("Neverblender - WARNING: Unable to read classification. Default value " + self.classification)

                if self.classification not in nvb_def.Classification.ALL:
                    print("Neverblender - WARNING: Invalid classification '" + self.classification + "'")
                    self.classification = nvb_def.Classification.UNKNOWN
            elif (label == 'setanimationscale'):
                try:
                    self.animscale = line[1]
                except IndexError:
                    print("Neverblender - WARNING: Unable to read animationscale. Default value " + self.animscale)


    def loadAsciiGeometry(self, asciiData):
        for asciiNode in asciiData.split('node '):
            lines = [l.strip().split() for l in asciiNode.splitlines()]
            node = None
            nodeType = ''
            nodeName = 'UNNAMED'

            # Read node Name
            try:
                nodeName = lines[0][1].lower()
            except (IndexError, AttributeError):
                raise nvb_def.MalformedMdlFile('Unable to read node name')

            # Read node type
            try:
                nodeType = lines[0][0].lower()
            except (IndexError, AttributeError):
                raise nvb_def.MalformedMdlFile('Unable to read node type')

            # Create an object with that node type
            switch = {'dummy':      nvb_node.Dummy, \
                      'patch':      nvb_node.Patch, \
                      'reference':  nvb_node.Reference, \
                      'trimesh':    nvb_node.Trimesh,  \
                      'animmesh':   nvb_node.Animmesh,  \
                      'danglymesh': nvb_node.Danglymesh, \
                      'skin':       nvb_node.Skinmesh, \
                      'emitter':    nvb_node.Emitter, \
                      'light':      nvb_node.Light, \
                      'aabb':       nvb_node.Aabb}
            try:
                node = switch[nodeType](nodeName)
            except KeyError:
                raise nvb_def.MalformedMdlFile('Invalid node type')

            # Parse and add to node list
            node.loadAscii(lines)
            self.nodes.append(node)


    def loadAsciiAnims(self, asciiData):
        # Split into animations first
        for asciiAnim in asciiData.split('newanim '):
            # Now split the animations into header + nodes
            anim          = None
            animName      = 'UNNAMED'
            animDataStart = -1

            # Read animation Name
            try:
                animName = lines[0][0].lower()
            except (IndexError, AttributeError):
                raise nvb_def.MalformedMdlFile('Unable to read animation name')

            animDataStart = asciiData.find('node ')

            anim = nvb_anim.Animation(animName)
            anim.loadAsciiHeader(asciiData[:animDataStart-1])
            anim.loadAsciiNodes(asciiData[animDataStart:])
            self.animations.append(anim)


    def loadAscii(self, asciiData):
        headBlock = []
        geomBlock = []
        animBlock = []

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


    def generateAsciiHeader(self):
        pass


    def generateAsciiGeometry(self):
        pass


    def generateAsciiAnims(self):
        pass


    def generateAscii(self):
        pass


    def createObjectLinks(self, scene):
        '''
        Handles parenting and linking the objects to a scene
        '''
        for objList in self.createdObjects:
            for obj in objList:
                loadedName = obj[0] # Unique name of the object in blender
                parentName = obj[1] # Name of the parent in the mdl
                nodePos    = obj[2] # Position of the node in the mdl

                # Check if the parent exists
                if (nvb_utils.isNull(parentName)):
                    # Node without parent. Must be the root dummy.
                    obj.nvb.dummytype      = nvb_def.Dummytype.MDLROOT
                    obj.nvb.supermodel     = self.supermodel
                    obj.nvb.classification = self.classification
                elif parentName in self.createdObjects:
                    parentLoadedName = self.createdObjects.getLoadedName(parentName,
                                                                         '',
                                                                         nodePos)
                    if parentLoadedName:
                        obj.parent                = bpy.data.objects[parentLoadedName]
                        obj.matrix_parent_inverse = obj.parent.matrix_world.inverted()
                    else:
                        #TODO...or not todo?
                        pass
                else:
                    # Parent doesn't exist.
                    raise nvb_def.MalformedMdlFile(node.name + ' has no parent ' + node.parentName)
                scene.objects.link(obj)


    def createObjects(self):
        if self.nodes:
            for node in self.nodes:
                # Creates a blender object for this node
                obj = node.createObject()
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


    def createAnimations(self):
        for anim in self.animations:
            pass


    def create(self, scene):
        nodePos = 0
        if nvb_glob.importGeometry:
            self.createObjects()
            self.createObjectLinks(scene)

            if nvb_glob.importAnims:
                self.createAnimations()
        else:
            # Import animations only, there is no objectDB in this case
            pass



class Mdl2():
    def __init__(self):
        self.nodeDict = collections.OrderedDict()
        self.animDict = dict() # No need to retain order

        self.nodes = collections.OrderedDict()
        self.anims = dict()

        self.name           = 'UNNAMED'
        self.supermodel     = nvb_def.null
        self.animscale      = 1.0
        self.classification = nvb_def.Classification.UNKNOWN

        self.validExports   = [] # needed for skinmeshes and animations


    def parseNode(self, asciiBlock):
        if asciiBlock is None:
            raise nvb_def.MalformedMdlFile('Empty Node')

        nodeType = ''
        try:
            nodeType = asciiBlock[0][1].lower()
        except (IndexError, AttributeError):
            raise nvb_def.MalformedMdlFile('Invalid node type')

        switch = {'dummy':      nvb_node.Dummy, \
                  'patch':      nvb_node.Patch, \
                  'reference':  nvb_node.Reference, \
                  'trimesh':    nvb_node.Trimesh,  \
                  'animmesh':   nvb_node.Animmesh,  \
                  'danglymesh': nvb_node.Danglymesh, \
                  'skin':       nvb_node.Skinmesh, \
                  'emitter':    nvb_node.Emitter, \
                  'light':      nvb_node.Light, \
                  'aabb':       nvb_node.Aabb}
        try:
            node = switch[nodeType]()
        except KeyError:
            raise nvb_def.MalformedMdlFile('Invalid node type')

        node.parse(asciiBlock)
        self.addNode(node)


    def parseAnimation(self, asciiBlock):
        if asciiBlock is None:
            raise nvb_def.MalformedMdlFile('Empty Animation')

        animation = nvb_anim.Animation()
        animation.getAnimFromAscii(asciiBlock)

        self.addAnimation(animation)


    def addNode(self, newNode):
        # Blender requires unique object names. Names in mdls are only
        # unique for a parent, i.e. another object with the same name but
        # with a different parent may exist.
        # We'd need to save all names starting from root to resolve
        # this, but that's too much effort.
        # ParentName + Name should be enough.
        if newNode:
            key = newNode.parentName + newNode.name
            if key in self.nodeDict:
                #TODO: Should probably raise an exception
                pass
            else:
                self.nodeDict[key] = newNode


    def addAnimation(self, anim):
        if anim:
            if anim.name in self.animDict:
                #TODO: Should probably raise an exception
                pass
            else:
                self.animDict[anim.name] = anim


    def load(self, scene):
        rootDummy = None
        objIdx = 0
        if (nvb_glob.importGeometry) and self.nodeDict:
            it = iter(self.nodeDict.items())

            # The first node should be the rootdummy.
            # If the first node has a parent or isn't a dummy we don't
            # even try to import the rest
            (nodeKey, node) = next(it)
            if (type(node) == nvb_node.Dummy) and (nvb_utils.isNull(node.parentName)):
                obj = node.load(scene)
                obj.nvb.dummytype      = nvb_def.Dummytype.MDLROOT
                obj.nvb.supermodel     = self.supermodel
                obj.nvb.classification = self.classification
                rootDummy = obj

                obj.nvb.imporder = objIdx
                objIdx += 1
            else:
                raise nvb_def.MalformedMdlFile('First node has to be a dummy without a parent.')

            for (nodeKey, node) in it:
                obj = node.load(scene)
                obj.nvb.imporder = objIdx
                objIdx += 1
                if (nvb_utils.isNull(node.parentName)):
                    # Node without parent and not the mdl root.
                    raise nvb_def.MalformedMdlFile(node.name + ' has no parent.')
                else:
                    # Check if such an object exists
                    if node.parentName in bpy.data.objects:
                        obj.parent                = bpy.data.objects[node.parentName]
                        obj.matrix_parent_inverse = obj.parent.matrix_world.inverted()
                    else:
                        # Node with invalid parent.
                        raise nvb_def.MalformedMdlFile(node.name + ' has no parent ' + node.parentName)

        # Attempt to import animations
        # Search for the rootDummy if not already present
        if not rootDummy:
            for obj in scene.objects:
                if nvb_utils.isRootDummy(obj, nvb_def.Dummytype.MDLROOT):
                    rootDummy = obj
                    break
            # Still none ? Don't try to import anims then
            if not rootDummy:
                return

        for (animName, anim) in self.animDict.items():
            anim.addAnimToScene(scene, rootDummy)


    def parse(self, asciiLines):
        State = enum.Enum('State', 'START HEADER GEOMETRY GEOMETRYNODE ANIMATION')
        cs    = State.START
        blockStart = -1
        for idx, line in enumerate(asciiLines):
            try:
                label = line[0]
            except IndexError:
                # Probably empty line or whatever, just skip it
                continue

            if (cs == State.START):
                if (label == 'newmodel'):
                    try:
                        self.name = line[1]
                    except IndexError:
                        raise nvb_def.MalformedMdlFile('Model has no name')
                    cs = State.HEADER

            elif (cs == State.HEADER):
                if (label == 'beginmodelgeom'):
                    # After this, a list of nodes has to follow
                    cs = State.GEOMETRY
                elif (label == 'setsupermodel'):
                    try:
                        # line should be ['setsupermodel', modelname, supermodelname]
                        self.supermodel = line[2]
                    except IndexError:
                        print("Neverblender - WARNING: Unable to read supermodel. Default value " + self.supermodel)

                elif (label == 'classification'):
                    try:
                        self.classification = line[1].upper()
                    except IndexError:
                        print("Neverblender - WARNING: Unable to read classification. Default value " + self.classification)

                    if self.classification not in nvb_def.Classification.ALL:
                        print("Neverblender - WARNING: Invalid classification '" + self.classification + "'")
                        self.classification = nvb_def.Classification.UNKNOWN
                elif (label == 'setanimationscale'):
                    try:
                        self.animscale = line[1]
                    except IndexError:
                        print("Neverblender - WARNING: Unable to read animationscale. Default value " + self.animscale)

            elif (cs == State.GEOMETRY):
                if (label == 'node'):
                    if nvb_glob.importGeometry:
                        blockStart = idx
                        cs = State.GEOMETRYNODE
                if (label == 'endmodelgeom'):
                    # After this, either animations or eof.
                    # Or maybe we don't want animations at all.
                    if (nvb_glob.importAnim is not 'NON') and (not nvb_glob.minimapMode):
                        cs = State.ANIMATION
                    else:
                        return

            elif (cs == State.GEOMETRYNODE):
                if (label == 'endnode'):
                    #node = self.parseGeometryNode(lines[blockStart:idx+1])
                    self.parseNode(asciiLines[blockStart:idx+1])
                    blockStart = -1
                    cs = State.GEOMETRY
                elif (label == 'node'):
                    raise nvb_def.MalformedMdlFile('Unexpected "endnode" at line' + str(idx))

            elif (cs == State.ANIMATION):
                if (label == 'newanim'):
                    if (blockStart < 0):
                        blockStart = idx
                    else:
                        raise nvb_def.MalformedMdlFile('Unexpected "newanim" at line' + str(idx))
                if (label == 'doneanim'):
                    if (blockStart > 0):
                        self.parseAnimation(asciiLines[blockStart:idx+1])
                        blockStart = -1
                    else:
                        raise nvb_def.MalformedMdlFile('Unexpected "doneanim" at line' + str(idx))


    def generateGeomBlock(self, bObject, asciiLines, simple = False):

        nodeType = nvb_utils.getNodeType(bObject)
        switch = {'dummy':      nvb_node.Dummy, \
                  'patch':      nvb_node.Patch, \
                  'reference':  nvb_node.Reference, \
                  'trimesh':    nvb_node.Trimesh,  \
                  'animmesh':   nvb_node.Animmesh, \
                  'danglymesh': nvb_node.Danglymesh, \
                  'skin':       nvb_node.Skinmesh, \
                  'emitter':    nvb_node.Emitter, \
                  'light':      nvb_node.Light, \
                  'aabb':       nvb_node.Aabb}
        try:
            node = switch[nodeType]()
        except KeyError:
            raise nvb_def.MalformedMdlFile('Invalid node type')

        node.toAscii(bObject, asciiLines, self.validExports, self.classification, simple)

        '''
        for child in bObject.children:
            self.generateGeomBlock(child, asciiLines, simple)
        '''
        childList = []
        for child in bObject.children:
            childList.append((child.nvb.imporder, child))
        childList.sort(key=lambda tup: tup[0])

        for (imporder, child) in childList:
            self.generateGeomBlock(child, asciiLines, simple)


    def generateAnimBlock(self, rootDummy, asciiLines):
        for animItem in rootDummy.nvb.animList:
            anim = nvb_anim.Animation()
            anim.save(asciiLines,
                      rootDummy,
                      bpy.context.scene,
                      animItem)
        '''
        for scene in bpy.data.scenes:
            animRootDummy = nvb_utils.getAnimationRootdummy(scene)
            if animRootDummy and self.validExports:
                # Check the name of the roodummy
                # if animRootDummy.name.rfind(self.validExports[0]):
                anim = nvb_anim.Animation()
                anim.toAscii(scene, animRootDummy, asciiLines, self.name)
        '''


    def generate(self, asciiLines, rootDummy, exports = {'ANIMATION', 'WALKMESH'}):
        self.name           = rootDummy.name
        self.classification = rootDummy.nvb.classification
        self.supermodel     = rootDummy.nvb.supermodel
        self.animscale      = rootDummy.nvb.animscale

        # The Names of exported geometry nodes. We'll need this for skinmeshes
        # and animations
        nvb_utils.getValidExports(rootDummy, self.validExports)

        # Header
        currentTime   = datetime.now()
        blendFileName = os.path.basename(bpy.data.filepath)
        if not blendFileName:
            blendFileName = 'unknown'
        asciiLines.append('# Exported from blender at ' + currentTime.strftime('%A, %Y-%m-%d'))
        asciiLines.append('filedependancy ' + blendFileName)
        asciiLines.append('newmodel ' + self.name)
        asciiLines.append('setsupermodel ' + self.name + ' ' + self.supermodel)
        asciiLines.append('classification ' + self.classification)
        asciiLines.append('setanimationscale ' + str(round(self.animscale, 2)))
        # Geometry
        asciiLines.append('beginmodelgeom ' + self.name)
        self.generateGeomBlock(rootDummy, asciiLines, False)
        asciiLines.append('endmodelgeom ' + self.name)
        # Animations
        if 'ANIMATION' in exports:
            asciiLines.append('')
            asciiLines.append('# ANIM ASCII')
            self.generateAnimBlock(rootDummy, asciiLines)
        # The End
        asciiLines.append('donemodel ' + self.name)
        asciiLines.append('')


class Wkm(Mdl):
    def __init__(self, wkmtype)
        Mdl.__init__(self)

        self.walkmeshType   = wkmtype


    def createObjectLinks(self, scene):
        # We'll be adding an extra dummy and parent all objects with missing
        # parents to it (which should be all of them)
        wkmRootNode = nvb_node.dummy(self.name + ' ' + wkmtype)
        #TODO: Set subtype
        wkmRootObj  = wkmRootNode.createObject()
        scene.objects.link(wkmRootObj)

        for objList in self.createdObjects:
            for obj in objList:
                loadedName = obj[0] # Unique name of the object in blender
                parentName = obj[1] # Name of the parent in the mdl
                nodePos    = obj[2] # Position of the node in the mdl

                # Check if the parent exists
                if (nvb_utils.isNull(parentName)):
                    # Node without parent. Must be the root dummy.
                    obj.nvb.dummytype      = nvb_def.Dummytype.MDLROOT
                    obj.nvb.supermodel     = self.supermodel
                    obj.nvb.classification = self.classification
                elif parentName in self.createdObjects:
                    parentLoadedName = self.createdObjects.getLoadedName(parentName,
                                                                         '',
                                                                         nodePos)
                    if parentLoadedName:
                        obj.parent                = bpy.data.objects[parentLoadedName]
                        obj.matrix_parent_inverse = obj.parent.matrix_world.inverted()
                    else:
                        #TODO...or not todo?
                        pass
                else:
                    # Parent doesn't exist. use our custom one
                    obj.parent                = wkmRootObj
                    obj.matrix_parent_inverse = wkmRootObj.parent.matrix_world.inverted()
                scene.objects.link(obj)



class Xwk(Mdl):
    def __init__(self, wkmType = 'pwk'):
        Mdl.__init__(self)

        self.walkmeshType   = wkmType



    def parseAnimation(self, asciiBlock):
        pass # No animations in walkmeshes


    def parse(self, asciiLines):
        # Parse the walkmesh
        blockStart = -1
        for idx, line in enumerate(asciiLines):
            try:
                label = line[0]
            except IndexError:
                # Probably empty line or whatever, just skip it
                continue
            if (label == 'node'):
                blockStart = idx
            elif (label == 'endnode'):
                if (blockStart > 0):
                    self.parseNode(asciiLines[blockStart:idx+1])
                    blockStart = -1
                else:
                    # "endnode" before "node"
                    raise nvb_def.MalformedMdlFile('Unexpected "endnode" at line' + str(idx))


    def generate(self, asciiLines, rootDummy, exports = {'ANIMATION', 'WALKMESH'}):
        self.name = rootDummy.name

        # Header
        currentTime = datetime.now()
        asciiLines.append('# Exported from blender at ' + currentTime.strftime('%A, %Y-%m-%d'))
        # Geometry
        for child in rootDummy.children:
            self.generateGeomBlock(child, asciiLines, True)


    def load(self, scene):
        if self.nodeDict:
            # Walkmeshes have no rootdummys. We need to create one ourselves

            # Look for the node parents for the list of parents. They should
            # all have the same name
            nameList = []
            for (nodeKey, node) in self.nodeDict.items():
                if (nvb_utils.isNull(node.parentName)):
                    # Node without
                    raise nvb_def.MalformedMdlFile(node.name + ' has no parent.')
                else:
                    if node.parentName not in nameList:
                        nameList.append(node.parentName)
            if len(nameList) == 1:
                self.name = nameList[0]
            else:
                raise nvb_def.MalformedMdlFile('Invalid parents in walkmesh.')

            node = nvb_node.Dummy(self.name + '_' + self.walkmeshType)
            if self.walkmeshType == 'dwk':
                node.dummytype = nvb_def.Dummytype.DWKROOT
            else:
                node.dummytype = nvb_def.Dummytype.PWKROOT
            node.name = self.name
            rootdummy = node.load(scene)

            for (nodeKey, node) in self.nodeDict.items():
                obj = node.load(scene)
                # Check if such an object exists
                if node.parentName in bpy.data.objects:
                    obj.parent                = bpy.data.objects[node.parentName]
                    obj.matrix_parent_inverse = obj.parent.matrix_world.inverted()
                else:
                    # Node with invalid parent.
                    raise nvb_def.MalformedMdlFile(node.name + ' has no parent ' + node.parentName)


class Wok(Xwk):
    def __init__(self, name = 'UNNAMED', wkmType = 'wok'):
        self.nodeDict       = collections.OrderedDict()
        self.name           = name
        self.walkmeshType   = 'wok'
        self.classification = nvb_def.Classification.UNKNOWN


    def generateGeomBlock(self, bObject, asciiLines, simple):

        nodeType = nvb_utils.getNodeType(bObject)
        if nodeType == 'aabb':
            node = nvb_node.Aabb()
            node.toAscii(bObject, asciiLines, simple)
            return # We'll take the first aabb object
        else:
            for child in bObject.children:
                self.generateGeomBlock(child, asciiLines, simple)


    def generate(self, asciiLines, rootDummy, exports = {'ANIMATION', 'WALKMESH'}):
        self.name = rootDummy.name

        # Header
        currentTime   = datetime.now()
        asciiLines.append('# Exported from blender at ' + currentTime.strftime('%A, %Y-%m-%d'))
        # Geometry = AABB
        self.generateGeomBlock(rootDummy, asciiLines, True)


    def load(self, scene):
        pass
