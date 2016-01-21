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


class Mdl():
    def __init__(self):
        self.nodeDict      = collections.OrderedDict()
        self.animDict      = dict() # No need to retain order

        self.name           = 'UNNAMED'
        self.supermodel     = nvb_def.null
        self.animscale      = 1.0
        self.classification = nvb_def.Classification.UNKNOWN

        self.validExports   = [] # needed for skinmeshes and animations


    def loadAsciiNode(self, asciiBlock):
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
                  'danglymesh': nvb_node.Danglymesh, \
                  'skin':       nvb_node.Skinmesh, \
                  'emitter':    nvb_node.Emitter, \
                  'light':      nvb_node.Light, \
                  'aabb':       nvb_node.Aabb}
        try:
            node = switch[nodeType]()
        except KeyError:
            raise nvb_def.MalformedMdlFile('Invalid node type')

        node.loadAscii(asciiBlock)
        self.addNode(node)


    def loadAsciiAnimation(self, asciiBlock):
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


    def importToScene(self, scene, imports):
        rootDummy = None
        objIdx = 0
        if ('GEOMETRY' in imports) and self.nodeDict:
            it = iter(self.nodeDict.items())

            # The first node should be the rootdummy.
            # If the first node has a parent or isn't a dummy we don't
            # even try to import the mdl
            (nodeKey, node) = next(it)
            if (type(node) == nvb_node.Dummy) and (nvb_utils.isNull(node.parentName)):
                obj                = node.addToScene(scene)
                obj.nvb.dummytype      = nvb_def.Dummytype.MDLROOT
                obj.nvb.supermodel     = self.supermodel
                obj.nvb.classification = self.classification
                rootDummy = obj

                obj.nvb.imporder = objIdx
                objIdx += 1
            else:
                raise nvb_def.MalformedMdlFile('First node has to be a dummy without a parent.')

            for (nodeKey, node) in it:
                obj = node.addToScene(scene)
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

        if ('ANIMATION' in imports) and (not nvb_glob.minimapMode):
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


    def loadAscii(self, asciiLines):
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
                       print("WARNING: Unable to read supermodel. Using default value: " + self.supermodel)

                elif (label == 'classification'):
                    try:
                        self.classification = line[1].upper()
                    except IndexError:
                        print("WARNING: Unable to read classification. Using default value: " + self.classification)

                    if self.classification not in nvb_def.Classification.ALL:
                        print("WARNING: Invalid classification '" + self.classification + "'")
                        self.classification = nvb_def.Classification.UNKNOWN
                elif (label == 'setanimationscale'):
                    try:
                        self.animscale = line[1]
                    except IndexError:
                        print("WARNING: Unable to read animationscale. Using default value: " + self.animscale)

            elif (cs == State.GEOMETRY):
                if (label == 'node'):
                    blockStart = idx
                    cs = State.GEOMETRYNODE
                if (label == 'endmodelgeom'):
                    # After this, either animations or eof
                    cs = State.ANIMATION

            elif (cs == State.GEOMETRYNODE):
                if (label == 'endnode'):
                    #node = self.parseGeometryNode(lines[blockStart:idx+1])
                    self.loadAsciiNode(asciiLines[blockStart:idx+1])
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
                        self.loadAsciiAnimation(asciiLines[blockStart:idx+1])
                        blockStart = -1
                    else:
                        raise nvb_def.MalformedMdlFile('Unexpected "doneanim" at line' + str(idx))


    def geometryToAscii(self, bObject, asciiLines, simple = False):

        nodeType = nvb_utils.getNodeType(bObject)
        switch = {'dummy':      nvb_node.Dummy, \
                  'patch':      nvb_node.Patch, \
                  'reference':  nvb_node.Reference, \
                  'trimesh':    nvb_node.Trimesh,  \
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
            self.geometryToAscii(child, asciiLines, simple)
        '''
        childList = []
        for child in bObject.children:
            childList.append((child.nvb.imporder, child))
        childList.sort(key=lambda tup: tup[0])

        for (imporder, child) in childList:
            self.geometryToAscii(child, asciiLines, simple)


    def animationsToAscii(self, asciiLines):
        for scene in bpy.data.scenes:
            animRootDummy = nvb_utils.getAnimationRootdummy(scene)
            if animRootDummy and self.validExports:
                # Check the name of the roodummy
                # if animRootDummy.name.rfind(self.validExports[0]):
                anim = nvb_anim.Animation()
                anim.toAscii(scene, animRootDummy, asciiLines, self.name)



    def generateAscii(self, asciiLines, rootDummy, exports = {'ANIMATION', 'WALKMESH'}):
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
        asciiLines.append('# Exported from blender at ' + currentTime.strftime('%A, %Y-%m-%d %H:%M'))
        asciiLines.append('filedependancy ' + blendFileName)
        asciiLines.append('newmodel ' + self.name)
        asciiLines.append('setsupermodel ' + self.name + ' ' + self.supermodel)
        asciiLines.append('classification ' + self.classification)
        asciiLines.append('setanimationscale ' + str(round(self.animscale, 2)))
        # Geometry
        asciiLines.append('beginmodelgeom ' + self.name)
        self.geometryToAscii(rootDummy, asciiLines, False)
        asciiLines.append('endmodelgeom ' + self.name)
        # Animations
        if 'ANIMATION' in exports:
            asciiLines.append('')
            asciiLines.append('# ANIM ASCII')
            self.animationsToAscii(asciiLines)
        # The End
        asciiLines.append('donemodel ' + self.name)
        asciiLines.append('')

class Xwk(Mdl):
    def __init__(self, wkmType = 'pwk'):
        Mdl.__init__(self)

        self.walkmeshType   = wkmType



    def loadAsciiAnimation(self, asciiBlock):
        pass # No animations in walkmeshes


    def loadAscii(self, asciiLines):
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
                    self.loadAsciiNode(asciiLines[blockStart:idx+1])
                    blockStart = -1
                else:
                    # "endnode" before "node"
                    raise nvb_def.MalformedMdlFile('Unexpected "endnode" at line' + str(idx))


    def generateAscii(self, asciiLines, rootDummy, exports = {'ANIMATION', 'WALKMESH'}):
        self.name = rootDummy.name

        # Header
        currentTime = datetime.now()
        asciiLines.append('# Exported from blender at ' + currentTime.strftime('%A, %Y-%m-%d %H:%M'))
        # Geometry
        for child in rootDummy.children:
            self.geometryToAscii(child, asciiLines, True)


    def importToScene(self, scene, imports = {'ANIMATION', 'WALKMESH'}):
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
            rootdummy = node.addToScene(scene)

            for (nodeKey, node) in self.nodeDict.items():
                obj = node.addToScene(scene)
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


    def geometryToAscii(self, bObject, asciiLines, simple):

        nodeType = nvb_utils.getNodeType(bObject)
        if nodeType == 'aabb':
            node = nvb_node.Aabb()
            node.toAscii(bObject, asciiLines, simple)
            return # We'll take the first aabb object
        else:
            for child in bObject.children:
                self.geometryToAscii(child, asciiLines, simple)


    def generateAscii(self, asciiLines, rootDummy, exports = {'ANIMATION', 'WALKMESH'}):
        self.name = rootDummy.name

        # Header
        currentTime   = datetime.now()
        asciiLines.append('# Exported from blender at ' + currentTime.strftime('%A, %Y-%m-%d %H:%M'))
        # Geometry = AABB
        self.geometryToAscii(rootDummy, asciiLines, True)


    def importToScene(self, scene, imports = {'ANIMATION', 'WALKMESH'}):
        pass
