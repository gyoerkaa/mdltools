import collections
import enum
from datetime import datetime

import bpy

from . import nvb_node
from . import nvb_anim
from . import nvb_def
from . import nvb_glob



class Mdl():
    def __init__(self):
        self.nodeDict      = collections.OrderedDict()
        self.animDict      = dict() # No need to retain order

        self.name           = 'UNNAMED'
        self.supermodel     = nvb_def.null
        self.animscale      = 1.0
        self.classification = 'UNKNOWN'


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

        animation = nvb_anim.AnimationBlock()
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

        if ('GEOMETRY' in imports) and self.nodeDict:
            it = iter(self.nodeDict.items())

            # The first node should be the rootdummy.
            # If the first node has a parent or isn't a dummy we don't
            # even try to import the mdl
            (nodeKey, node) = next(it)
            if (type(node) == nvb_node.Dummy) and (node.parentName == nvb_def.null):
                obj               = node.addToScene(scene)
                obj.nvb.dummytype = 'MDLROOT'
                rootDummy = obj
            else:
                raise nvb_def.MalformedMdlFile('First node has to be a dummy without a parent.')

            for (nodeKey, node) in it:
                obj = node.addToScene(scene)
                if (node.parentName == nvb_def.null):
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
                    if (obj.type == 'EMPTY') and (obj.nvb.dummytype == 'MDLROOT'):
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


    def geometryToAscii(self, bObject, asciiLines, validExports):

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

        node.addToAscii(bObject, asciiLines, validExports)

        for child in bObject.children:
            geometryToAscii(child, asciiLines, validExports)


    def animationsToAscii(self, nodeList, asciiLines, validExports):
        for scene in bpy.data.scenes:
            animRootDummy = nvb_utils.getAnimationRootdummy(scene)
            if animRootDummy:
                # TODO
                pass


    def generateAscii(self, asciiLines, rootDummy, exports = {'ANIMATION', 'WALKMESH'}):
        self.name           = rootDummy.name
        self.classification = rootDummy.nvb.classification
        self.supermodel     = rootDummy.nvb.supermodel
        self.animscale      = rootDummy.nvb.animscale

        # The Names of exported geometry nodes. We'll need this for skinmeshes
        # and animations
        validExports = []
        nvb_utils.getValidExports(rootDummy, validExports)

        # Header
        currentTime = datetime.now()
        asciiLines.append('# Exported from blender at ' + currentTime.strftime('%A, %Y-%m-%d %H:%M'))
        asciiLines.append('filedependancy ' + os.path.basename(bpy.data.filepath))
        asciiLines.append('newmodel ' + self.name)
        asciiLines.append('setsupermodel ' + self.name + ' ' + self.supermodel)
        asciiLines.append('classification ' + self.classification)
        asciiLines.append('setanimationscale ' + str(round(self.animscale, 2)))
        # Geometry
        asciiLines.append('beginmodelgeom ' + self.name)
        self.geometryToAscii(rootDummy, asciiLines, validExports)
        asciiLines.append('endmodelgeom ' + self.name)
        # Animations
        asciiLines.append('# ANIM ASCII')
        self.animationsToAscii(rootDummy, asciiLines, validExports)
        # The End
        asciiLines.append('donemodel ' + self.name)


class Xwk(Mdl):
    def __init__(self, name = 'UNNAMED', wtype = 'pwk'):
        self.nodeDict     = collections.OrderedDict()
        self.rootdummy    = None
        self.name         = name
        self.walkmeshType = wtype


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


    def setWalkmeshType(self, wtype):
        self.walkmeshType = wtype


    def importToScene(self, scene, imports):
        if ('WALKMESH' in imports) and self.nodeDict:
            # Walkmeshes have no rootdummys. We need to create one ourselves

            # Look for the node parents for the list of parents. They should
            # all be the same
            nameList = []
            for (nodeKey, node) in self.nodeDict.items():
                if (node.parentName == nvb_def.null):
                    # Node without
                    raise nvb_def.MalformedMdlFile(node.name + ' has no parent.')
                else:
                    if node.parentName not in nameList:
                        nameList.append(node.parentName)
            if len(nameList) == 1:
                self.name = nameList[0]
            else:
                raise nvb_def.MalformedMdlFile('Invalid parents in walkmesh.')

            if self.walkmeshType == 'dwk':
                node = nvb_node.Dummy(self.name + '_dwk')
                node.dummytype = 'DWKROOT'
            else:
                node = nvb_node.Dummy(self.name + '_pwk')
                node.dummytype = 'PWKROOT'
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
