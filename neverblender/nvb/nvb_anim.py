import collections

import bpy

from . import nvb_presets
from . import nvb_utils
from . import nvb_animnode


class MalformedMdlFile(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)


class AnimationBlock():

    def __init__(self, name = 'UNNAMED'):
        self.name      = name
        self.length    = 1.0
        self.transtime = 1.0
        self.root      = nvb_presets.null
        self.eventList = []
        self.nodeList  = collections.OrderedDict()


    def getAnimNode(self, nodeName, parentName = nvb_presets.null):
        key = parentName + nodeName
        if key in self.nodeList:
            return self.nodeList[key]
        else:
            return None


    def addAnimNode(self, asciiBlock):
        node = nvb_animnode.Node()
        node.parse(asciiBlock)
        key  = node.parentName + node.name
        if key in self.nodeList:
            #TODO: Should probably raise an exception
            pass
        else:
            self.nodeList[key] = node


    def addEvent(self, event):
        self.eventList.append(event)


    def convert(self, scene, rootDummyName = ''):
        # Create a new scene
        # Check if there is already a scene with this animation name
        animScene = None
        if (self.name not in bpy.data.scenes.keys()):
            animScene = bpy.data.scenes.new(self.name)
        else:
            animScene = bpy.data.scenes[self.name]
        animScene.render.fps    = nvb_presets.fps
        animScene.frame_start   = 0
        animScene.frame_end     = nvb_utils.nwtime2frame(self.length)
        animScene.frame_current = 0

        # Get the mdl rootdummy
        rootDummy = None
        if rootDummyName:
            # How nice, finally some help.
            rootDummy = scene.objects[rootDummyName]
        else:
            # Fine. I'll look for the rootdummy myself.
            # Better hope I pick the right one, muhahahaha.
            for (key, obj) in scene.objects.items():
                if obj.nvb.dummytype == 'MDLROOT':
                    rootDummy = obj
                    break
        if not rootDummy:
            return # Nope

        # Copy objects to the new scene:
        self.copyObjectToScene(animScene, rootDummy, None)


    def copyObjectToScene(self, scene, theOriginal, parent):
        '''
        Copy object and all it's children to scene.
        For object with simple (position, rotation) or no animations we
        create a linked copy.
        For alpha animation we'll need to copy the data too.
        '''
        theCopy        = theOriginal.copy()
        theCopy.parent = parent
        theCopy.name   = theOriginal.name + '.' + self.name

        # rootDummy ?
        objType = theOriginal.type
        if (objType == 'EMPTY'):
            if (theOriginal.nvb.dummytype == 'MDLROOT'):
                # We copied the root dummy, set some stuff
                theCopy.nvb.isanimation = True
                theCopy.nvb.animname    = self.name
                theCopy.nvb.transtime   = self.transtime
                theCopy.nvb.animroot    = self.root

                self.addEventsToObject(theCopy)

        # Add animations from the node to the new object
        if theOriginal.parent:
            animNode = self.getAnimNode(theOriginal.name, theOriginal.parent.name)
        else:
            animNode = self.getAnimNode(theOriginal.name)
        if animNode:
            # We need to copy the data for:
            # - Lamps
            # - Meshes & materials when there are alphakeys
            if (objType == 'LAMP'):
                data         = theOriginal.data.copy()
                data.name    = theOriginal.name + '.' + self.name
                theCopy.data = data
            elif (objType == 'MESH'):
                if animNode.keys.hasAlpha():
                    data         = theOriginal.data.copy()
                    data.name    = theOriginal.name + '.' + self.name
                    theCopy.data = data
                    # Create a copy of the material
                    if (theOriginal.active_material):
                        material      = theOriginal.active_material.copy()
                        material.name = material.name + '.' + self.name
                        theCopy.active_material = material
            animNode.addAnimToObject(theCopy, self.name)

        # Link copy to the anim scene
        scene.objects.link(theCopy)

        # Convert all child objects too
        for child in theOriginal.children:
            self.copyObjectToScene(scene, child, theCopy)


    def addEventsToObject(self, rootDummy):
        for event in self.eventList:
            newItem = rootDummy.nvb.eventList.add()
            newItem.frame = nvb_utils.nwtime2frame(event[0])
            newItem.name  = event[1]
