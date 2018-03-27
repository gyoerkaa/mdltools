"""TODO: DOC."""

from . import nvb_utils
from . import nvb_animnode


class Animation():
    """TODO: DOC."""

    def __init__(self, name='UNNAMED'):
        """TODO: DOC."""
        self.name = name
        self.length = 1.0
        self.transtime = 1.0
        self.animroot = ''
        self.events = []
        self.nodes = []

    @staticmethod
    def createRestPose(obj, frame=1):
        """TODO: DOC."""
        nvb_animnode.Animnode.createRestPose(obj, frame)

    def create(self, rootDummy, noderesolver, options):
        """Create animations with a list of imported objects."""
        # Add new animation to list
        fps = options.scene.render.fps
        newAnim = nvb_utils.createAnimListItem(rootDummy)
        newAnim.name = self.name
        newAnim.ttime = self.transtime
        newAnim.root = self.animroot
        newAnim.frameEnd = newAnim.frameStart + \
            nvb_utils.nwtime2frame(self.length, fps)
        # Add events for new animation
        for ev in self.events:
            newEvent = newAnim.eventList.add()
            newEvent.name = ev[1]
            newEvent.frame = newAnim.frameStart + \
                nvb_utils.nwtime2frame(ev[0], fps)
        # Load the animation into the objects/actions
        for node in self.nodes:
            obj = noderesolver.get_obj(node.name, node.nodeidx)
            if obj:
                node.create(obj, newAnim, self.length, options)
                if options.restpose:
                    Animation.createRestPose(obj, newAnim.frameStart-5)

    def loadAsciiAnimHeader(self, asciiBlock):
        """TODO: DOC."""
        asciiLines = [l.strip().split() for l in asciiBlock.splitlines()]
        for line in asciiLines:
            try:
                label = line[0].lower()
            except (IndexError, AttributeError):
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
                except (ValueError, IndexError):
                    self.animroot = ''
            elif (label == 'event'):
                self.events.append((float(line[1]), line[2]))

    def loadAsciiAnimNodes(self, asciiData):
        """TODO: DOC."""
        dlm = 'node '
        nodeList = [dlm+block for block in asciiData.split(dlm) if block != '']
        for idx, asciiNode in enumerate(nodeList):
            asciiLines = [l.strip().split() for l in asciiNode.splitlines()]
            node = nvb_animnode.Animnode()
            node.loadAscii(asciiLines, idx)
            self.nodes.append(node)

    def loadAscii(self, asciiData):
        """Load an animation from a block from an ascii mdl file."""
        animNodesStart = asciiData.find('node ')
        if (animNodesStart > -1):
            self.loadAsciiAnimHeader(asciiData[:animNodesStart-1])
            self.loadAsciiAnimNodes(asciiData[animNodesStart:])
        else:
            print('Neverblender - WARNING: Failed to load an animation.')

    @staticmethod
    def generateAsciiNodes(obj, anim, asciiLines, options):
        """TODO: Doc."""
        nvb_animnode.Animnode.generateAscii(obj, anim, asciiLines, options)

        # Sort children to restore original order before import
        # (important for supermodels/animations to work)
        children = [c for c in obj.children]
        children.sort(key=lambda c: c.nvb.imporder)
        for c in children:
            Animation.generateAsciiNodes(c, anim, asciiLines, options)

    @staticmethod
    def generateAscii(rootDummy, anim, asciiLines, options):
        """TODO: Doc."""
        if anim.mute:
            # Don't export mute animations
            return

        animLength = nvb_utils.frame2nwtime(anim.frameEnd-anim.frameStart,
                                            options.scene.render.fps)
        asciiLines.append('newanim ' + anim.name + ' ' + rootDummy.name)
        asciiLines.append('  length ' + str(round(animLength, 5)))
        asciiLines.append('  transtime ' + str(round(anim.ttime, 3)))
        if anim.root:
            asciiLines.append('  animroot ' + anim.root)
        else:
            asciiLines.append('  animroot ' + rootDummy.name)

        for event in anim.eventList:
            eventTime = nvb_utils.frame2nwtime(event.frame-anim.frameStart,
                                               options.scene.render.fps)
            asciiLines.append('  event ' + str(round(eventTime, 5)) + ' ' +
                              event.name)

        Animation.generateAsciiNodes(rootDummy, anim, asciiLines, options)

        asciiLines.append('doneanim ' + anim.name + ' ' + rootDummy.name)
        asciiLines.append('')
