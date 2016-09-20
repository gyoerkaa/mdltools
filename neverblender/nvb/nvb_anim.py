"""TODO: DOC."""

import bpy

from . import nvb_def
from . import nvb_utils
from . import nvb_animnode


class Animation():
    """TODO: DOC."""

    def __init__(self, name='UNNAMED'):
        """TODO: DOC."""
        self.name = name
        self.length = 1.0
        self.transtime = 1.0
        self.animroot = nvb_def.null
        self.events = []
        self.nodes = []

        self.frameStart = 0
        self.frameEnd = 0

    def create(self, objectDB):
        """TODO: DOC."""
        if objectDB:
            self.createWithDB(objectDB)
        else:
            self.createIndy()

    def createWithDB(self, objectDB):
        """Create animations with a list of imported objects."""
        pass

    def createIndy(self):
        """Create animation without previosly imported objects."""
        pass

    def loadAsciiAnimHeader(self, asciiData):
        """TODO: DOC."""
        lines = asciiData.splitlines()
        for line in lines:
            try:
                label = line[0].lower()
            except IndexError:
                continue  # Probably empty line, skip it
            if (label == 'newanim'):
                self.name = nvb_utils.getAuroraString(line[1])
            elif (label == 'length'):
                self.length = float(line[1])
            elif (label == 'transtime'):
                self.transtime = float(line[1])
            elif (label == 'animroot'):
                try:
                    self.animroot = line[1]
                except:
                    self.animroot = ''
            elif (label == 'event'):
                self.events.append((float(line[1]), line[2]))

    def loadAsciiAnimNodes(self, asciiData):
        """TODO: DOC."""
        dlm = 'node '
        nodeList = [dlm+block for block in asciiData.split(dlm) if block != '']
        asciiLines = [l.strip().split() for l in nodeList.splitlines()]
        for idx, line in enumerate(asciiLines):
            node = nvb_animnode.Node()
            node.loadAscii(line, idx)
            self.nodes.append(node)

    def loadAscii(self, asciiData):
        """Load an animation from a block from an ascii mdl file."""
        animNodesStart = asciiData.find('node ')
        if (animNodesStart > -1):
            self.loadAsciiAnimHeader(asciiData[:animNodesStart-1])
            self.loadAsciiAnimNodes(asciiData[animNodesStart:])
        else:
            print('Neverblender - WARNING: Failed to load an animation.')

    def addAnimation(self, rootDummy):
        """TODO: DOC."""
        # Check for valid rootdummy
        if not rootDummy:
            return

        # Check if an animation with this name is already present
        animStartFrame = 0
        for anim in rootDummy.nvb.animList:
            animStartFrame = anim.frameEnd
            if anim.name == self.name:
                print('Neverblender - Warning: Animation ' + self.name + ' already exisits')
                return
        animStartFrame = animStartFrame + nvb_def.anim_distance

        # Add new animation to list
        newAnim = rootDummy.nvb.animList.add()
        newAnim.name = self.name
        newAnim.ttime = self.ftranstime
        newAnim.root = self.root
        newAnim.frameStart = animStartFrame
        newAnim.frameEnd = newAnim.frameStart + nvb_utils.nwtime2frame(self.length)

        # Add events for new animation
        for impEvent in self.eventList:
            newEvent = newAnim.eventList.add()
            newEvent.name = impEvent[1]
            newEvent.frame = newAnim.frameStart + nvb_utils.nwtime2frame(impEvent[0])

        self.addAnimationData(rootDummy, newAnim.frameStart)

    def addAnimationData(self, obj, frameStart, parent=None):
        """TODO: DOC."""
        animNode.addAnimationDataToObject(obj,
                                          frameStart,
                                          self.name)
        if obj.active_material:
            animNode.addAnimationDataToMaterial(obj.active_material,
                                                frameStart,
                                                self.name)

        for child in obj.children:
            self.addAnimationData(child, frameStart, obj)

    def copyObjectToScene(self, scene, theOriginal, parent):
        """TODO: DOC."""
        '''
        Copy object and all it's children to scene.
        For object with simple (position, rotation) or no animations we
        create a linked copy.
        For alpha animation we'll need to copy the data too.
        '''
        theCopy = theOriginal.copy()
        theCopy.parent = parent
        theCopy.name = theOriginal.name + '.' + self.name
        theCopy.nvb.rawascii = ''

        # rootDummy ?
        objType = theOriginal.type
        if (objType == 'EMPTY') and (theOriginal.nvb.dummytype == nvb_def.Dummytype.MDLROOT):
            # We copied the root dummy, set some stuff
            theCopy.nvb.isanimation = True
            theCopy.nvb.animname = self.name
            theCopy.nvb.transtime = self.transtime
            theCopy.nvb.animroot = self.root
            self.addEventsToObject(theCopy)

        # Add animations from the animation node to the newly created object
        if theOriginal.parent:
            animNode = self.getAnimNode(theOriginal.name, theOriginal.parent.name)
        else:
            animNode = self.getAnimNode(theOriginal.name)

        deepCopy = False
        if deepCopy:
            # Always copy all data & materials.
            # Each animation has it's own data.
            if theOriginal.data:
                data = theOriginal.data.copy()
                data.name = theOriginal.name + '.' + self.name
                theCopy.data = data
                # Create a copy of the material
                if (theOriginal.active_material):
                    material = theOriginal.active_material.copy()
                    material.name = theOriginal.active_material.name + '.' + self.name
                    theCopy.active_material = material
        else:
            # Create only a single copy of data and materials which is
            # shared between animations.
            # Create an extra copy only on a on-demand basis, i.e. if there
            # are animations attached which need it.
            animDataName = nvb_def.animdataPrefix + theOriginal.name
            if (objType == 'LAMP'):
                if animDataName in bpy.data.lamps:
                    data = bpy.data.lamps[animDataName]
                else:
                    data = theOriginal.data.copy()
                    data.name = animDataName
                theCopy.data = data
            elif (objType == 'MESH'):
                if animNode.requiresUniqueData():
                    # We need to copy the material and therefore the data block
                    data = theOriginal.data.copy()
                    data.name = theOriginal.name + '.' + self.name
                    theCopy.data = data
                    if (theOriginal.active_material):
                        # Copy the material
                        material = theOriginal.active_material.copy()
                        material.name = theOriginal.active_material.name + '.' + self.name
                        theCopy.active_material = material
                        # No need to copy the textures, as the texture settings
                        # belong to the material texture slot, not the
                        # texture itself
                else:
                    if animDataName in bpy.data.meshes:
                        data = bpy.data.meshes[animDataName]
                    else:
                        data = theOriginal.data.copy()
                        data.name = animDataName
                    theCopy.data = data

        if animNode:
            '''
            # Only copy as needed
            # We need to copy the data for:
            # - Lamps
            # - Meshes & materials when there are alphakeys
            # (Textures aren't needed)
            if (objType == 'LAMP'):
                data         = theOriginal.data.copy()
                data.name    = theOriginal.name + '.' + self.name
                theCopy.data = data
            elif (objType == 'MESH'):
                if animNode.requiresUniqueData():
                    data         = theOriginal.data.copy()
                    data.name    = theOriginal.name + '.' + self.name
                    theCopy.data = data
                    # Create a copy of the material
                    if (theOriginal.active_material):
                        material      = theOriginal.active_material.copy()
                        material.name = theOriginal.active_material.name + '.' + self.name
                        theCopy.active_material = material
                        # No need to copy the textures, as the texture alpha
                        # belongs to the materials texture slot, not the
                        # texture itself
            '''
            animNode.addAnimToObject(theCopy, self.name)

        # Link copy to the anim scene
        scene.objects.link(theCopy)

        # Convert all child objects too
        for child in theOriginal.children:
            self.copyObjectToScene(scene, child, theCopy)

    def createEvents(self, rootDummy):
        """TODO: DOC."""
        for event in self.events:
            newItem = rootDummy.nvb.eventList.add()
            newItem.frame = nvb_utils.nwtime2frame(event[0])
            newItem.name = event[1]

    def generateAscii(self, bObject, asciiLines):
        """TODO: DOC."""
        node = nvb_animnode.Node()
        node.toAscii(bObject, asciiLines, self.name)

        '''
        for child in bObject.children:
            self.animNodeToAscii(child, asciiLines)
        '''
        # If this mdl was imported, we need to retain the order of the
        # objects in the original mdl file. Unfortunately this order is
        # seemingly arbitrary so we need to save it at import
        # Otherwise supermodels don't work correctly.
        childList = []
        for child in bObject.children:
            childList.append((child.nvb.imporder, child))
        childList.sort(key=lambda tup: tup[0])

        for (imporder, child) in childList:
            self.animNodeToAscii(child, asciiLines)

    def saveNode(self, asciiLines, bObject, scene):
        """TODO: DOC."""
        node = nvb_animnode.Node()
        node.save(bObject, asciiLines, self.name)

        childList = []
        for child in bObject.children:
            childList.append((child.nvb.imporder, child))
        childList.sort(key=lambda tup: tup[0])

        for (imporder, child) in childList:
            self.saveNode(child, asciiLines, bObject, scene)

    def save(self, asciiLines, scene, rootDummy, animItem):
        """TODO: DOC."""
        self.name = animItem.name
        self.transtime = animItem.ttime
        self.root = animItem.root

        self.frameStart = animItem.frameStart
        self.frameEnd = animItem.frameEnd

        self.length = nvb_utils.frame2nwtime(self.frameStart-self.frameEnd, animScene.render.fps)

        asciiLines.append('newanim ' + self.name + ' ' + rootDummy.name)
        asciiLines.append('  length ' + str(round(self.length, 5)))
        asciiLines.append('  transtime ' + str(round(self.transtime, 3)))
        asciiLines.append('  animroot ' + self.root)

        for event in animItem.eventList:
            eventTime = nvb_utils.frame2nwtime(event.frame, animScene.render.fps)
            asciiLines.append('  event ' + str(round(eventTime, 5)) + ' ' + event.name)

        self.saveNode(asciiLines, rootDummy, scene)
        asciiLines.append('doneanim ' + self.name + ' ' + rootDummy.name)
        asciiLines.append('')

    def toAscii(self, animScene, animRootDummy, asciiLines, mdlName=''):
        """TODO: DOC."""
        self.name = animRootDummy.nvb.animname
        self.length = nvb_utils.frame2nwtime(animScene.frame_end, animScene.render.fps)
        self.transtime = animRootDummy.nvb.transtime
        self.root = animRootDummy.nvb.animroot

        asciiLines.append('newanim ' + self.name + ' ' + mdlName)
        asciiLines.append('  length ' + str(round(self.length, 5)))
        asciiLines.append('  transtime ' + str(round(self.transtime, 3)))
        asciiLines.append('  animroot ' + self.root)

        for event in animRootDummy.nvb.eventList:
            eventTime = nvb_utils.frame2nwtime(event.frame, animScene.render.fps)
            asciiLines.append('  event ' + str(round(eventTime, 5)) + ' ' + event.name)

        self.animNodeToAscii(animRootDummy, asciiLines)
        asciiLines.append('doneanim ' + self.name + ' ' + mdlName)
        asciiLines.append('')
