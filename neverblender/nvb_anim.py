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
        nvb_animnode.Animnode.create_restpose(obj, frame)

    def create_anim_events(self, mdl_base, anim_data, fps):
        """Unused"""
        kfp_options = {'FAST'}
        action = nvb_utils.get_action(mdl_base, mdl_base.name)
        ev_list = mdl_base.nvb.anim_event_list
        for ev_time, ev_name in self.events:
            ev_idx = nvb_utils.event_list_item_create(ev_list, ev_name)
            frame = fps * ev_time + anim_data.frameStart
            if frame <= anim_data.frameEnd:
                dp = 'nvb.anim_event_list[' + str(ev_idx) + '].fire'
                fcu = nvb_utils.get_fcurve(action, dp, 0, 'Aurora Events')
                fcu.keyframe_points.insert(frame, 0.0, kfp_options)

    def create(self, mdl_base, noderesolver, options):
        """Create animations with a list of imported objects."""
        # Check for existing animations:
        if options.anim_ignore_existing and \
                self.name in mdl_base.nvb.animList.keys():
            return
        # Add new animation to list
        fps = options.scene.render.fps
        new_anim = nvb_utils.create_anim_list_item(mdl_base)
        new_anim.name = self.name
        new_anim.ttime = self.transtime
        new_anim.root = self.animroot
        new_anim.frameEnd = fps * self.length + new_anim.frameStart
        # Old style events
        for ev_time, ev_name in self.events:
            newEvent = new_anim.eventList.add()
            newEvent.name = ev_name
            newEvent.frame = fps * ev_time + new_anim.frameStart
        # Load the animation into the objects/actions
        for node in self.nodes:
            obj = noderesolver.get_obj(node.name, node.nodeidx)
            if obj:
                node.create(obj, new_anim, self.length, options)
                if options.anim_restpose:
                    Animation.createRestPose(obj, new_anim.frameStart-5)

    def loadAsciiAnimHeader(self, ascii_data):
        """TODO: DOC."""
        ascii_lines = [l.strip().split() for l in ascii_data.splitlines()]
        for line in ascii_lines:
            try:
                label = line[0].lower()
            except (IndexError, AttributeError):
                continue  # Probably empty line, skip it
            if (label == 'newanim'):
                self.name = nvb_utils.str2identifier(line[1])
            elif (label == 'length'):
                self.length = float(line[1])
            elif (label == 'transtime'):
                self.transtime = float(line[1])
            elif (label == 'animroot'):
                try:
                    self.animroot = line[1].lower()
                except (ValueError, IndexError):
                    self.animroot = ''
            elif (label == 'event'):
                self.events.append((float(line[1]), line[2]))

    def loadAsciiAnimNodes(self, ascii_data):
        """TODO: DOC."""
        dlm = 'node '
        node_list = [dlm + s for s in ascii_data.split(dlm) if s != '']
        for idx, ascii_node in enumerate(node_list):
            ascii_lines = [l.strip().split() for l in ascii_node.splitlines()]
            node = nvb_animnode.Animnode()
            node.load_ascii(ascii_lines, idx)
            self.nodes.append(node)

    def loadAscii(self, ascii_data):
        """Load an animation from a block from an ascii mdl file."""
        animNodesStart = ascii_data.find('node ')
        if (animNodesStart > -1):
            self.loadAsciiAnimHeader(ascii_data[:animNodesStart-1])
            self.loadAsciiAnimNodes(ascii_data[animNodesStart:])
        else:
            print('Neverblender - WARNING: Failed to load an animation.')

    @staticmethod
    def generateAsciiNodes(obj, anim, ascii_lines, options):
        """TODO: Doc."""
        nvb_animnode.Animnode.generate_ascii(obj, anim, ascii_lines, options)

        # Sort children to restore original order before import
        # (important for supermodels/animations to work)
        children = [c for c in obj.children]
        children.sort(key=lambda c: c.name)
        children.sort(key=lambda c: c.nvb.imporder)
        for c in children:
            Animation.generateAsciiNodes(c, anim, ascii_lines, options)

    @staticmethod
    def generateAscii(mdl_base, anim, ascii_lines, options):
        """TODO: Doc."""
        if anim.mute:  # Don't export mute animations
            return
        fps = options.scene.render.fps
        anim_length = (anim.frameEnd - anim.frameStart) / fps
        ascii_lines.append('newanim ' + anim.name + ' ' + mdl_base.name)
        ascii_lines.append('  length ' + str(round(anim_length, 3)))
        ascii_lines.append('  transtime ' + str(round(anim.ttime, 3)))
        # Check anim root
        node_list = [mdl_base]
        nvb_utils.get_children_recursive(mdl_base, node_list)
        if anim.root and anim.root in [n.name for n in node_list]:
            ascii_lines.append('  animroot ' + anim.root)
        else:
            print('Neverblender - WARNING: Invalid Animation Root for ' +
                  anim.name)
            ascii_lines.append('  animroot ' + mdl_base.name)

        for event in anim.eventList:
            eventTime = (event.frame - anim.frameStart) / fps
            ascii_lines.append('  event ' + str(round(eventTime, 3)) + ' ' +
                               event.name)

        Animation.generateAsciiNodes(mdl_base, anim, ascii_lines, options)

        ascii_lines.append('doneanim ' + anim.name + ' ' + mdl_base.name)
        ascii_lines.append('')
