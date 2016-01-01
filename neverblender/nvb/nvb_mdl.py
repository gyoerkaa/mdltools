import os
import math
import collections
import warnings
from datetime import datetime

import bpy

from . import nvb_node
from . import nvb_anim
from . import nvb_def
from . import nvb_glob


class Mdl():
    def __init__(self):
        self.nodeDict  = collections.OrderedDict()
        self.animDict  = dict() # No need to retain order
        self.rootDummy = None

        self.name           = 'UNNAMED'
        self.supermodel     = nvb_def.null
        self.animScale      = 1.0
        self.classification = 'UNKNOWN'


    def addAsciiNode(self, asciiBlock):
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

        node.getFromAscii(asciiBlock)
        self.addNode(node)


    def addAsciiAnimation(self, asciiBlock):
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


    def addMdlToScene(self, scene):

        if ('GEOMETRY' in nvb_glob.imports) and self.nodeDict:
            it = iter(self.nodeDict.items())

            # The first node should be the rootdummy.
            # If the first node has a parent or isn't a dummy we don't
            # even try to import the mdl
            (nodeKey, node) = next(it)
            if (type(node) == nvb_node.Dummy) and (node.parentName == nvb_def.null):
                obj               = node.addToScene(scene)
                obj.nvb.dummytype = 'MDLROOT'
                self.rootDummy = obj
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

        if ('ANIMATION' in nvb_glob.imports) and (not nvb_glob.minimapMode):
            # Search for the rootDummy if not already present
            if not self.rootDummy:
                for obj in scene.objects:
                    if (obj.type == 'EMPTY') and (obj.nvb.dummytype == 'MDLROOT'):
                        self.rootDummy = obj
                        break
                # Still none ? Don't try to import anims then
                if not self.rootDummy:
                    return

            for (animName, anim) in self.animDict.items():
                anim.addAnimToScene(scene, self.rootDummy)


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


    def generateAscii(self, rootDummyName = ''):
        if rootDummyName in bpy.data.objects:
            rootDummy = bpy.data.objects[rootDummyName]
        else:
            rootDummy = nvb.utils.getRootdummy()

        current_time = datetime.now()

        # The Names of exported geometry nodes. We'll need this for skinmeshes
        # and animations
        validExports = []
        nvb_utils.getValidExports(rootDummy, validExports)

        lines = []
        # Header
        lines.append('# Exported from blender at ' + current_time.strftime('%A, %Y-%m-%d %H:%M'))
        lines.append('filedependancy ' + os.path.basename(bpy.data.filepath))
        lines.append('newmodel ' + rootDummy.name)
        lines.append('setsupermodel ' + rootDummy.name + ' ' + rootDummy.nvb.supermodel)
        lines.append('classification ' + rootDummy.nvb.classification)
        lines.append('setanimationscale ' + str(round(rootDummy.nvb.animscale, 2)))
        # Geometry
        lines.append('beginmodelgeom ' + rootDummy.name)
        self.geometryToAscii(rootDummy, asciiLines, validExports)
        lines.append('endmodelgeom ' + rootDummy.name)
        # Animations
        lines.append('ANIM ASCII')
        self.animationsToAscii(rootDummy, asciiLines, validExports)
        # The End
        lines.append('donemodel ' + rootDummy.name)


class Xwk(Mdl):
    def __init__(self, name = 'UNNAMED', wtype = 'pwk'):
        self.nodeDict     = collections.OrderedDict()
        self.rootdummy    = None
        self.name         = name
        self.walkmeshType = wtype


    def addAsciiAnimation(self, asciiBlock):
        pass # No animations in walkmeshes


    def setWalkmeshType(self, wtype):
        self.walkmeshType = wtype


    def addMdlToScene(self, scene):
        if ('WALKMESH' in nvb_glob.imports) and self.nodeDict:
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
                print(nameList)
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
