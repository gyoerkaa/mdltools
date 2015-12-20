import bpy

from . import nvb_presets
from . import nvb_utils


class Keys():
    def __init__(self):
        self.position       = []
        self.orientation    = []
        self.selfillumcolor = []
        self.alpha          = []
        # Lights/lamps
        self.color  = []
        self.radius = []
        # Emitters ... incompatible. Import as text
        self.txt = ''

    def hasAlpha():
        return not self.alpha


class Node():
    def __init__(self, name = 'UNNAMED'):
        self.name     = name
        self.nodeType = 'DUMMY'
        self.parent   = nvb_presets.null
        self.position    = (0.0, 0.0, 0.0)
        self.orientation = (0.0, 0.0, 0.0, 0.0)
        self.scale       = 1.0

        self.keys    = Keys()
        self.isEmpty = True


    def __bool__(self):
        '''
        Return false if the node is empty, i.e. it has no anims attached
        '''
        return not self.isEmpty


    def parseKeys3f(self, asciiBlock):
        '''
        Parse animation keys containing 3 floats (not counting the time value)
        '''
        lfloat = float
        keyList = []
        for line in asciiBlock:
            keys.append(   (lfloat(line[0]),
                            lfloat(line[1]),
                            lfloat(line[2]),
                            lfloat(line[3])) )
        self.isEmpty = False
        return keyList


    def parseKeys4f(self, asciiBlock):
        '''
        Parse animation keys containing 4 floats (not counting the time value)
        '''
        lfloat = float
        keyList = []
        for line in asciiBlock:
            keys.append(   (lfloat(line[0]),
                            lfloat(line[1]),
                            lfloat(line[2]),
                            lfloat(line[3]),
                            lfloat(line[4])) )
        self.isEmpty = False
        return keyList


    def parseKeys1f(self, asciiBlock):
        '''
        Parse animation keys containing 1 float (not counting the time value)
        '''
        lfloat = float
        keyList = []
        for line in asciiBlock:
            keys.append(   (lfloat(line[0]),
                            lfloat(line[1])) )
        self.isEmpty = False
        return keyList


    def parse(self, asciiBlock):
        lfloat = float
        for idx, line in enumerate(asciiBlock):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue
            if   (label  == 'node'):
                self.nodeType = line[1].upper()
                self.name     = line[2].lower()
            elif (label  == 'endnode'):
                return
            elif (label  == 'parent'):
                self.parent = line[1].lower()
            elif (label  == 'position'):
                self.position = (lfloat(line[1]),
                                 lfloat(line[2]),
                                 lfloat(line[3]) )
                self.isEmpty = False
            elif (label  == 'orientation'):
                self.orientation = (lfloat(line[1]),
                                    lfloat(line[2]),
                                    lfloat(line[3]),
                                    lfloat(line[4]) )
                self.isEmpty = False
            elif (label  == 'scale'):
                self.scale = lfloat(line[1])
                self.isEmpty = False
            elif (label  == 'positionkey'):
                numKeys = int(line[1])
                self.keys.position = self.parseKeys3f(asciiBlock[idx+1:idx+numKeys+1])
            elif (label  == 'orientationkey'):
                numKeys = int(line[1])
                self.keys.orientation = self.parseKeys4f(asciiBlock[idx+1:idx+numKeys+1])
            elif (label  == 'alphakey'):
                numKeys = int(line[1])
                self.keys.alpha = self.parseKeys1f(asciiBlock[idx+1:idx+numKeys+1])
            elif (label  == 'selfillumcolorkey'):
                numKeys = int(line[1])
                self.keys.selfillumcolor = self.parseKeys3f(asciiBlock[idx+1:idx+numKeys+1])
            # Lights/lamps only
            elif (label  == 'colorkey'):
                numKeys = int(line[1])
                self.keys.selfillumcolor = self.parseKeys3f(asciiBlock[idx+1:idx+numKeys+1])
            elif (label  == 'radiuskey'):
                numKeys = int(line[1])
                self.keys.radius = self.parseKeys1f(asciiBlock[idx+1:idx+numKeys+1])
            # The rest is likely emitter stuff = incompatible with blender.
            # Import as text.
            else:
                self.isEmpty = False
                self.keyList.txt = self.txt + '\n' + ' '.join(line)


    def addAnimToObject(self, targetObject):
        '''
        Add the animations in this node to target object
        '''
        pass
