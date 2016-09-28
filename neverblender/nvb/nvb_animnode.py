"""TODO: DOC."""

import mathutils
import collections
import bpy

from . import nvb_def
from . import nvb_utils
from . import nvb_parse


class Keys():
    """TODO: DOC."""

    def __init__(self):
        """TODO: DOC."""
        self.position = []
        self.orientation = []
        self.scale = []
        self.selfillumcolor = []
        self.alpha = []
        # Lights/lamps
        self.color = []
        self.radius = []
        # Emitters ... incompatible. Import as text
        self.rawascii = []

    def hasAlpha(self):
        """TODO: DOC."""
        return len(self.alpha) > 0


class Node():
    """TODO: DOC."""

    def __init__(self, name='UNNAMED'):
        """TODO: DOC."""
        self.nodetype = 'dummy'
        self.nodeidx = -1

        self.name = name
        self.parent = nvb_def.null

        # For animations using a single value as key
        self.position = None
        self.orientation = None
        self.scale = None
        self.alpha = None
        # For animations using keys
        self.keys = Keys()
        # Animesh
        self.sampleperiod = None
        self.animtverts = []
        self.animverts = []
        self.clip = [0.0, 0.0, 0.0, 0.0]

        self.isEmpty = True

    def __bool__(self):
        """Return false if the node is empty, i.e. no anims attached."""
        return not self.isEmpty

    def findEnd(self, asciiBlock):
        """Find the end of a key list.

        We don't know when a list of keys of keys will end. We'll have to
        search for the first non-numeric value
        """
        l_isNumber = nvb_utils.isNumber
        return next((i for i, v in enumerate(asciiBlock)
                     if not l_isNumber(v[0])), -1)

    def loadAscii(self, asciiLines, nodeidx=-1):
        """TODO: DOC."""
        l_float = float
        l_int = int
        l_isNumber = nvb_utils.isNumber
        self.nodeidx = nodeidx
        for i, line in enumerate(asciiLines):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue
            if label == 'node':
                self.nodeType = line[1].lower()
                self.name = nvb_utils.getAuroraString(line[2])
            elif label == 'endnode':
                return
            elif label == 'endlist':
                # Can't rely on that being here. We have our own way to get
                # the end of a key list
                pass
            elif label == 'parent':
                self.parentName = nvb_utils.getAuroraString(line[1])
            # Animations using a single value as key
            elif label == 'position':
                self.position = (l_float(line[1]),
                                 l_float(line[2]),
                                 l_float(line[3]))
                self.isEmpty = False
            elif label == 'orientation':
                self.orientation = (l_float(line[1]),
                                    l_float(line[2]),
                                    l_float(line[3]),
                                    l_float(line[4]))
                self.isEmpty = False
            elif label == 'scale':
                self.scale = l_float(line[1])
                self.isEmpty = False
            elif label == 'alpha':
                self.alpha = l_float(line[1])
                self.isEmpty = False
            # Animeshes
            elif label == 'sampleperiod':
                self.sampleperiod = l_float(line[1])
                # self.isEmpty = False # might still be empty
            elif label == 'clipu':
                self.clip[0] = l_float(line[1])
                # self.isEmpty = False # might still be empty
            elif label == 'clipv':
                self.clip[1] = l_float(line[1])
                # self.isEmpty = False # might still be empty
            elif label == 'clipw':
                self.clip[2] = l_float(line[1])
                # self.isEmpty = False # might still be empty
            elif label == 'cliph':
                self.clip[3] = l_float(line[1])
                # self.isEmpty = False # might still be empty
            elif label == 'animverts':
                numVals = l_int(line[1])
                nvb_parse.f3(asciiLines[i+1:i+numVals+1], self.animverts)
                self.isEmpty = False
            elif label == 'animtverts':
                numVals = l_int(line[1])
                nvb_parse.f3(asciiLines[i+1:i+numVals+1], self.animtverts)
                self.isEmpty = False
            # Keyed animations
            elif label == 'positionkey':
                numKeys = self.findEnd(asciiLines[i+1:])
                nvb_parse.f4(asciiLines[i+1:i+numKeys+1],
                             self.keys.position)
                self.isEmpty = False
            elif label == 'orientationkey':
                numKeys = self.findEnd(asciiLines[i+1:])
                nvb_parse.f5(asciiLines[i+1:i+numKeys+1],
                             self.keys.orientation)
                self.isEmpty = False
            elif label == 'scalekey':
                numKeys = self.findEnd(asciiLines[i+1:])
                nvb_parse.f2(asciiLines[i+1:i+numKeys+1],
                             self.keys.scale)
                self.isEmpty = False
            elif label == 'alphakey':
                # If this is an emitter, alphakeys are incompatible. We'll
                # handle them later as plain text
                numKeys = self.findEnd(asciiLines[i+1:])
                if self.nodeType == 'emitter':
                    nvb_parse.txt(asciiLines[i:i+numKeys+1],
                                  self.keys.rawascii)
                else:
                    nvb_parse.f2(asciiLines[i+1:i+numKeys+1],
                                 self.keys.alpha)
                self.isEmpty = False
            elif label == 'selfillumcolorkey':
                numKeys = self.findEnd(asciiLines[i+1:])
                nvb_parse.f4(asciiLines[i+1:i+numKeys+1],
                             self.keys.selfillumcolor)
                self.isEmpty = False
            # Lights/lamps only
            elif label == 'colorkey':
                numKeys = self.findEnd(asciiLines[i+1:])
                nvb_parse.f4(asciiLines[i+1:i+numKeys+1], self.keys.color)
                self.isEmpty = False
            elif label == 'radiuskey':
                numKeys = self.findEnd(asciiLines[i+1:])
                nvb_parse.f2(asciiLines[i+1:i+numKeys+1], self.keys.radius)
                self.isEmpty = False
            # Some unknown label.
            # Probably keys for emitters, incompatible, save as plain text
            elif not l_isNumber(line[0]):
                numKeys = self.findEnd(asciiLines[i+1:])
                self.keys.rawascii.extend(asciiLines[i:i+numKeys+1])
                self.isEmpty = False

    @staticmethod
    def getCurve(action, dataPath, idx=0):
        """TODO: DOC."""
        for fc in action.fcurves:
            if (fc.data_path == dataPath) and (fc.array_index == idx):
                return fc
        fc = action.fcurves.new(data_path=dataPath, index=idx)
        return fc

    def createDataMat(self, mat, anim):
        """TODO: DOC."""
        # Add everything to a single action.
        frameStart = anim.frameStart
        frameEnd = anim.frameEnd
        # Get animation data, create if needed.
        animData = mat.animation_data
        if not animData:
            animData = mat.animation_data_create()
        # Get action, create if needed.
        action = animData.action
        if not action:
            action = bpy.data.actions.new(name=mat.name)
            action.use_fake_user = True
            animData.action = action

        # If there is a texture, use texture alpha for animations
        if mat.active_texture:
            # Material has a texture
            # data_path = material.texture_slots[x].alpha_factor
            tslotIdx = mat.active_texture_index
            dp = 'texture_slots[' + str(tslotIdx) + '].alpha_factor'
        else:
            # No texture.
            # data_path = material.alpha
            dp = 'alpha'
        curve = Node.getCurve(action, dp)
        if self.keys.alpha:
            for key in self.keys.alpha:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curve.keyframe_points.insert(frame, key[1])
        elif self.alpha is not None:
            curve.keyframe_points.insert(frameStart, self.alpha)
            curve.keyframe_points.insert(frameEnd, self.alpha)

    def createDataObj(self, obj, anim):
        """TODO: DOC."""
        # Add everything to a single action.
        frameStart = anim.frameStart
        frameEnd = anim.frameEnd
        # Get animation data, create if needed.
        animData = obj.animation_data
        if not animData:
            animData = obj.animation_data_create()
        # Get action, create if needed.
        action = animData.action
        if not action:
            action = bpy.data.actions.new(name=obj.name)
            action.use_fake_user = True
            animData.action = action

        # Set rotation channels if there are rotation keys
        if (self.keys.orientation):
            dp = 'rotation_euler'
            curveX = Node.getCurve(action, dp, 0)
            curveY = Node.getCurve(action, dp, 1)
            curveZ = Node.getCurve(action, dp, 2)
            currEul = None
            prevEul = None
            for key in self.keys.orientation:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                eul = nvb_utils.nwangle2euler(key[1:5])
                currEul = nvb_utils.eulerFilter(eul, prevEul)
                prevEul = currEul
                curveX.keyframe_points.insert(frame, currEul.x)
                curveY.keyframe_points.insert(frame, currEul.y)
                curveZ.keyframe_points.insert(frame, currEul.z)
        elif self.orientation is not None:
            dp = 'rotation_euler'
            curveX = Node.getCurve(action, dp, 0)
            curveY = Node.getCurve(action, dp, 1)
            curveZ = Node.getCurve(action, dp, 2)
            eul = nvb_utils.nwangle2euler(self.orientation)
            curveX.keyframe_points.insert(frameStart, eul[0])
            curveY.keyframe_points.insert(frameStart, eul[1])
            curveZ.keyframe_points.insert(frameStart, eul[2])
            if frameStart != frameEnd:
                curveX.keyframe_points.insert(frameEnd, eul[0])
                curveY.keyframe_points.insert(frameEnd, eul[1])
                curveZ.keyframe_points.insert(frameEnd, eul[2])
        # Set location channels if there are location keys
        if (self.keys.position):
            dp = 'location'
            curveX = Node.getCurve(action, dp, 0)
            curveY = Node.getCurve(action, dp, 1)
            curveZ = Node.getCurve(action, dp, 2)
            for key in self.keys.position:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curveX.keyframe_points.insert(frame, key[1])
                curveY.keyframe_points.insert(frame, key[2])
                curveZ.keyframe_points.insert(frame, key[3])
        elif (self.position is not None):
            dp = 'location'
            curveX = Node.getCurve(action, dp, 0)
            curveY = Node.getCurve(action, dp, 1)
            curveZ = Node.getCurve(action, dp, 2)
            curveX.keyframe_points.insert(frameStart, self.position[0])
            curveY.keyframe_points.insert(frameStart, self.position[1])
            curveZ.keyframe_points.insert(frameStart, self.position[2])

        # Set scale channels if there are scale keys
        if (self.keys.scale):
            dp = 'scale'
            curveX = Node.getCurve(action, dp, 0)
            curveY = Node.getCurve(action, dp, 1)
            curveZ = Node.getCurve(action, dp, 2)
            for key in self.keys.scale:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curveX.keyframe_points.insert(frame, key[1])
                curveY.keyframe_points.insert(frame, key[1])
                curveZ.keyframe_points.insert(frame, key[1])
        elif (self.scale is not None):
            dp = 'scale'
            curveX = Node.getCurve(action, dp, 0)
            curveY = Node.getCurve(action, dp, 1)
            curveZ = Node.getCurve(action, dp, 2)
            curveX.keyframe_points.insert(frameStart, self.scale)
            curveY.keyframe_points.insert(frameStart, self.scale)
            curveZ.keyframe_points.insert(frameStart, self.scale)

        # Set selfillumcolor channels if there are selfillumcolor keys
        if (self.keys.selfillumcolor):
            dp = 'nvb.selfillumcolor'
            curveR = Node.getCurve(action, dp, 0)
            curveG = Node.getCurve(action, dp, 1)
            curveB = Node.getCurve(action, dp, 2)

            for key in self.keys.selfillumcolor:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curveR.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[1])
                curveG.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[2])
                curveB.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[3])

        # For lamps: Set color channels
        if (self.keys.color):
            dp = 'color'
            curveR = Node.getCurve(action, dp, 0)
            curveG = Node.getCurve(action, dp, 1)
            curveB = Node.getCurve(action, dp, 2)

            for key in self.keys.color:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curveR.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[1])
                curveG.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[2])
                curveB.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[3])

        # For lamps: Set radius channels. Import as distance
        if (self.keys.radius):
            dp = 'distance'
            curve = Node.getCurve(action, dp)
            for key in self.keys.radius:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curve.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                             key[1])

    def createDataEmit(self, obj, anim, options):
        """TODO:Doc."""
        # Add imcompatible animations (emitters) as a text object
        if (self.keys.rawascii):
            # Get the text file
            txt = None
            if anim.rawascii and (anim.rawascii in bpy.data.texts):
                txt = bpy.data.texts[anim.rawascii]
            if not txt:
                txt = bpy.data.texts.new(options.mdlname +
                                         '.anim.' + anim.name)
                anim.rawascii = txt.name
            # Convert nwn time to frames and write to text file
            txt.write('  node ' + self.nodetype + ' ' + self.name)
            l_isNumber = nvb_utils.isNumber
            frameStart = anim.frameStart
            for line in self.keys.rawascii:
                if l_isNumber(line[0]):
                    nwtime = float(line[0])
                    frame = frameStart + nvb_utils.nwtime2frame(nwtime)
                    txt.write('\n      ' +
                              str(frame) + ' ' + ' '.join(line[1:]))
                else:
                    txt.write('\n    ' + ' '.join(line))
            txt.write('\n  endnode')

    def create(self, obj, anim, options):
        """TODO:Doc."""
        if self.isEmpty:
            return
        self.createDataObj(obj, anim)
        if obj.active_material:
            self.createDataMat(obj.active_material, anim)
        if nvb_utils.getNodeType(obj) == nvb_def.Nodetype.EMITTER:
            self.createDataEmit(obj, anim, options)

    @staticmethod
    def generateAsciiKeys(obj, anim, asciiLines):
        """TODO: DOC."""
        pass

    @staticmethod
    def generateAsciiKeysEmitter(obj, anim, asciiLines):
        """TODO: DOC."""
        pass

    @staticmethod
    def generateAscii(obj, anim, asciiLines):
        """TODO:Doc."""
        if not obj:
            return
        # Type + Name
        nodeType = nvb_utils.getNodeType(obj)
        asciiLines.append('  node ' + nodeType + ' ' + obj.name)
        # Parent
        if obj.parent:
            asciiLines.append('    parent ' + obj.parent.name)
        else:
            asciiLines.appent('    parent null')
        # Animation Data
        if nodeType == nvb_def.Meshtype.EMITTER:
            Node.generateAsciiKeysEmitter(obj, anim, asciiLines)
        Node.generateAsciiKeys(obj, anim, asciiLines)
        asciiLines.append('  endnode')

    def getKeysFromAction(self, action, keyDict):
        """TODO: DOC."""
        for fcurve in action.fcurves:
            # Get the sub dict for this particlar type of fcurve
            axis = fcurve.array_index
            dataPath = fcurve.data_path
            name = ''
            if dataPath == 'rotation_euler':
                name = 'orientationkey'
            elif dataPath == 'rotation_axis_angle':
                pass
            elif dataPath == 'location':
                name = 'positionkey'
            elif dataPath == 'scale':
                name = 'scalekey'
            elif dataPath == 'nvb.selfillumcolor':
                name = 'selfillumcolorkey'
            elif dataPath == 'color':  # Lamps/Lights
                name = 'colorkey'
            elif dataPath == 'distance':  # Lamps/Lights
                name = 'radiuskey'
            elif dataPath.endswith('alpha_factor'):  # Texture alpha_factor
                name = 'alphakey'
            elif dataPath.endswith('alpha'):  # Material alpha
                name = 'alphakey'

            for kfp in fcurve.keyframe_points:
                frame = int(round(kfp.co[0]))
                keys = keyDict[name]
                if frame in keys:
                    values = keys[frame]
                else:
                    values = [0.0, 0.0, 0.0, 0.0]
                values[axis] = values[axis] + kfp.co[1]
                keys[frame] = values

    def addKeysToAsciiIncompat(self, obj, asciiLines):
        """TODO: DOC."""
        if obj.nvb.meshtype != nvb_def.Meshtype.EMITTER:
            return
        if obj.nvb.rawascii not in bpy.data.texts:
            return
        txt = bpy.data.texts[obj.nvb.rawascii]
        txtLines = [l.split() for l in txt.as_string().split('\n')]
        for line in txtLines:
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue
            if (label == 'node') or (label == 'endnode') or \
               (label == 'parent') or (label == 'position'):
                # We don't need any of this
                pass
            else:
                # We'll take everything that doesn't start with a #
                if label[0] != '#':
                    if nvb_utils.isNumber(label):
                        asciiLines.append('      ' + ' '.join(line))
                    else:
                        asciiLines.append('    ' + ' '.join(line))

    def addKeysToAscii(self, animObj, originalObj, asciiLines):
        """TODO: DOC."""
        keyDict = {'orientationkey': collections.OrderedDict(),
                   'positionkey': collections.OrderedDict(),
                   'scalekey': collections.OrderedDict(),
                   'selfillumcolorkey': collections.OrderedDict(),
                   'colorkey': collections.OrderedDict(),
                   'radiuskey': collections.OrderedDict(),
                   'alphakey': collections.OrderedDict()}

        # Object Data
        if animObj.animation_data:
            action = animObj.animation_data.action
            if action:
                self.getKeysFromAction(action, keyDict)

        # Material/ texture data (= texture alpha_factor)
        if animObj.active_material and animObj.active_material.animation_data:
            action = animObj.active_material.animation_data.action
            if action:
                self.getKeysFromAction(action, keyDict)

        l_str = str
        l_round = round

        name = 'orientationkey'
        if len(keyDict[name]) > 1:
            asciiLines.append('    ' + name + ' ' + l_str(len(keyDict[name])))
            for frame, key in keyDict[name].items():
                time = l_round(nvb_utils.frame2nwtime(frame), 5)
                eul = mathutils.Euler((key[0], key[1], key[2]), 'XYZ')
                val = nvb_utils.euler2nwangle(eul)
                formatString = '      {: 6.5f} {: 6.5f} \
                    {: 6.5f} {: 6.5f} {: 6.5f}'
                s = formatString.format(time, val[0], val[1], val[2], val[3])
                asciiLines.append(s)
        elif len(keyDict[name]) == 1:
            # Only a single key
            frame, key = keyDict[name].popitem()
            eul = mathutils.Euler((key[0], key[1], key[2]), 'XYZ')
            val = nvb_utils.euler2nwangle(eul)
            formatString = '    orientation \
                            {: 8.5f} {: 8.5f} {: 8.5f} {: 8.5f}'
            s = formatString.format(val[0], val[1], val[2], val[3])
            asciiLines.append(s)

        name = 'positionkey'
        if len(keyDict[name]) > 1:
            asciiLines.append('    ' + name + ' ' + l_str(len(keyDict[name])))
            for frame, key in keyDict[name].items():
                time = l_round(nvb_utils.frame2nwtime(frame), 5)
                formatString = '      {: 6.5f} {: 6.5f} {: 6.5f} {: 6.5f}'
                s = formatString.format(time, key[0], key[1], key[2])
                asciiLines.append(s)
        elif len(keyDict[name]) == 1:
            # Only a single key
            frame, key = keyDict[name].popitem()
            formatString = '    position {: 8.5f} {: 8.5f} {: 8.5f}'
            s = formatString.format(key[0], key[1], key[2])
            asciiLines.append(s)

        name = 'scalekey'
        if keyDict[name]:
            asciiLines.append('    ' + name + ' ' + l_str(len(keyDict[name])))
            for frame, key in keyDict[name].items():
                time = l_round(nvb_utils.frame2nwtime(frame), 5)
                s = '      {: 6.5f} {: 6.5f}'.format(time, key[0])
                asciiLines.append(s)

        name = 'selfillumcolorkey'
        if keyDict[name]:
            asciiLines.append('    ' + name + ' ' + l_str(len(keyDict[name])))
            for frame, key in keyDict[name].items():
                time = l_round(nvb_utils.frame2nwtime(frame), 5)
                formatString = '      {: 6.5f} {: 3.2f} {: 3.2f} {: 3.2f}'
                s = formatString.format(time, key[0], key[1], key[2])
                asciiLines.append(s)

        name = 'colorkey'
        if keyDict[name]:
            asciiLines.append('    ' + name + ' ' + l_str(len(keyDict[name])))
            for frame, key in keyDict[name].items():
                time = l_round(nvb_utils.frame2nwtime(frame), 5)
                formatString = '      {: 6.5f} {: 3.2f} {: 3.2f} {: 3.2f}'
                s = formatString.format(time, key[0], key[1], key[2])
                asciiLines.append(s)

        name = 'radiuskey'
        if keyDict[name]:
            asciiLines.append('    ' + name + ' ' + l_str(len(keyDict[name])))
            for frame, key in keyDict[name].items():
                time = l_round(nvb_utils.frame2nwtime(frame), 5)
                s = '      {: 6.5f} {: 6.5f}'.format(time, key[0])
                asciiLines.append(s)

        name = 'alphakey'
        if len(keyDict[name]) > 1:
            asciiLines.append('    ' + name + ' ' + l_str(len(keyDict[name])))
            for frame, key in keyDict[name].items():
                time = l_round(nvb_utils.frame2nwtime(frame), 5)
                s = '      {: 6.5f} {: 3.2f}'.format(time, key[0])
                asciiLines.append(s)
        elif len(keyDict[name]) == 1:
            # Only a single key
            frame, key = keyDict[name].popitem()
            s = '    alpha {: 3.2f}'.format(key[0])
            asciiLines.append(s)

    def toAscii(self, animObj, asciiLines, animName):
        """TODO: DOC."""
        originalName = self.getOriginalName(animObj.name, animName)
        originalObj = bpy.data.objects[originalName]

        originalParent = nvb_def.null
        if animObj.parent:
            originalParent = self.getOriginalName(animObj.parent.name,
                                                  animName)

        if originalObj.nvb.meshtype == nvb_def.Meshtype.EMITTER:
            asciiLines.append('  node emitter ' + originalName)
            asciiLines.append('    parent ' + originalParent)
            self.addKeysToAsciiIncompat(animObj, asciiLines)
        else:
            asciiLines.append('  node dummy ' + originalName)
            asciiLines.append('    parent ' + originalParent)
        self.addKeysToAscii(animObj, originalObj, asciiLines)
        asciiLines.append('  endnode')
