import neverblender.nvb.node
import neverblender.nvb.presets

class Anim():
    def __init__(self, name = 'UNNAMED'):
        self.name      = name
        self.length    = 1.0
        self.transtime = 1.0
        self.root      = nvb.presets.null

        self.nodelist = []

    def load(self, asciiAnim):
        nodeList = []
        for idx, line in enumerate(asciiAnim):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue
            if (label == 'newanim'):
                self.name = line[1]
            elif (label == 'length'):
                self.length = float(line[1])
            elif (label == 'transtime'):
                self.transtime = float(line[1])
            elif (label == 'animroot'):
                self.root = line[1]
            elif (label == 'node'):
                nodeStart = idx
            elif (label == 'endnode'):
                if (nodeStart < 0):
                    nodeList.append((nodeStart, idx))
                    nodeStart = -1
                else (label == 'node'):
                    raise MalformedMdlFile('Unexpected "endnode" at line' + idx)

        for node in nodeList:
            self.nodeList = []

    def convert(self):
        pass

