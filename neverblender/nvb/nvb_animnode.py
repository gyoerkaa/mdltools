import mathutils
import collections
import bpy

from . import nvb_def
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
        self.rawascii = ''

    def hasAlpha(self):
        return self.alpha


class Node():
    def __init__(self, name = 'UNNAMED'):
        self.name       = name
        self.nodetype   = 'dummy'
        self.parentName = nvb_def.null

        self.keys    = Keys()
        self.isEmpty = True


    def __bool__(self):
        '''
        Return false if the node is empty, i.e. it has no anims attached
        '''
        return not self.isEmpty


    def parseKeys3f(self, asciiBlock, keyList):
        '''
        Parse animation keys containing 3 floats (not counting the time value)
        '''
        l_float = float
        for line in asciiBlock:
            keyList.append((l_float(line[0]),
                            l_float(line[1]),
                            l_float(line[2]),
                            l_float(line[3])) )
        self.isEmpty = False


    def parseKeys4f(self, asciiBlock, keyList):
        '''
        Parse animation keys containing 4 floats (not counting the time value)
        '''
        l_float = float
        for line in asciiBlock:
            keyList.append((l_float(line[0]),
                            l_float(line[1]),
                            l_float(line[2]),
                            l_float(line[3]),
                            l_float(line[4])) )
        self.isEmpty = False


    def parseKeys1f(self, asciiBlock, keyList):
        '''
        Parse animation keys containing 1 float (not counting the time value)
        '''
        l_float = float
        for line in asciiBlock:
            keyList.append((l_float(line[0]),
                            l_float(line[1])) )
        self.isEmpty = False


    def parseKeysIncompat(self, asciiBlock):
        '''
        Parse animation keys incompatible with blender. They will be saved
        as plain text.
        '''
        for line in asciiBlock:
            self.keys.rawascii = self.keys.rawascii + '\n' + ' '.join(line)
        self.isEmpty = False


    def findEnd(self, asciiBlock):
        '''
        We don't know when a list of keys of keys will end. We'll have to
        search for the first non-numeric value
        '''
        l_isNumber = nvb_utils.isNumber
        return next((i for i, v in enumerate(asciiBlock) if not l_isNumber(v[0])), -1)


    def getNodeFromAscii(self, asciiBlock):
        l_float    = float
        l_isNumber = nvb_utils.isNumber
        for idx, line in enumerate(asciiBlock):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue
            if   label == 'node':
                self.nodeType = line[1].lower()
                self.name     = line[2].lower()
            elif label == 'endnode':
                return
            elif label == 'endlist':
                # Can't rely on that being here. We have our own way to get
                # the end of a key list
                pass
            elif label == 'parent':
                self.parentName = line[1].lower()
            elif label == 'position':
                # position: 1 key, positionkey: >= 1 key (probably)
                self.parseKeys3f(asciiBlock[idx+1:idx+1], self.keys.position)
                self.isEmpty = False
            elif label == 'orientation':
                # orientation: 1 key, orientationkey: >= 1 key (probably)
                self.parseKeys4f(asciiBlock[idx+1:idx+1], self.keys.orientation)
                self.isEmpty = False
            elif label == 'positionkey':
                numKeys = self.findEnd(asciiBlock[idx+1:])
                self.parseKeys3f(asciiBlock[idx+1:idx+numKeys+1], self.keys.position)
            elif label == 'orientationkey':
                numKeys = self.findEnd(asciiBlock[idx+1:])
                self.parseKeys4f(asciiBlock[idx+1:idx+numKeys+1], self.keys.orientation)
            elif label == 'alphakey':
                # If this is an emitter, alphakeys are incompatible
                numKeys = self.findEnd(asciiBlock[idx+1:])
                if self.nodeType == 'emitter':
                    self.parseKeysIncompat(asciiBlock[idx:idx+numKeys+1])
                else:
                    self.parseKeys1f(asciiBlock[idx+1:idx+numKeys+1], self.keys.alpha)
            elif label == 'selfillumcolorkey':
                numKeys = self.findEnd(asciiBlock[idx+1:])
                self.parseKeys3f(asciiBlock[idx+1:idx+numKeys+1], self.keys.selfillumcolor)
            # Lights/lamps only
            elif label == 'colorkey':
                numKeys = self.findEnd(asciiBlock[idx+1:])
                self.parseKeys3f(asciiBlock[idx+1:idx+numKeys+1], self.keys.color)
            elif label == 'radiuskey':
                numKeys = self.findEnd(asciiBlock[idx+1:])
                self.parseKeys1f(asciiBlock[idx+1:idx+numKeys+1], self.keys.radius)
            # Some unknown text.
            # Probably keys for emitters = incompatible with blender. Import as text.
            elif not l_isNumber(line[0]):
                numKeys = self.findEnd(asciiBlock[idx+1:])
                self.parseKeysIncompat(asciiBlock[idx:idx+numKeys+1])


    def addAnimToMaterial(self, targetMaterial, animName = ''):
        if self.keys.alpha:
            actionName           = animName + '.' + targetMaterial.name
            action               = bpy.data.actions.new(name=actionName)
            action.use_fake_user = True

            # Set alpha channels
            # This should influence the material alpha value
            curve = action.fcurves.new(data_path='texture_slots[0].alpha_factor')
            for key in self.keys.alpha:
                curve.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]), key[1])

            targetMaterial.animation_data_create()
            targetMaterial.animation_data.action = action


    def addAnimToObject(self, targetObject, animName = ''):
        '''
        Add the animations in this node to target object
        '''
        actionName           = animName + '.' + targetObject.name
        action               = bpy.data.actions.new(name=actionName)
        action.use_fake_user = True

        if (self.keys.orientation):
            curveX = action.fcurves.new(data_path='rotation_euler', index=0)
            curveY = action.fcurves.new(data_path='rotation_euler', index=1)
            curveZ = action.fcurves.new(data_path='rotation_euler', index=2)
            for key in self.keys.orientation:
                frame = nvb_utils.nwtime2frame(key[0])
                eul   = nvb_utils.nwangle2euler(key[1:])
                curveX.keyframe_points.insert(frame, eul[0])
                curveY.keyframe_points.insert(frame, eul[1])
                curveZ.keyframe_points.insert(frame, eul[2])

        # Set location channels if there are location keys
        if (self.keys.position):
            curveX = action.fcurves.new(data_path='location', index=0)
            curveY = action.fcurves.new(data_path='location', index=1)
            curveZ = action.fcurves.new(data_path='location', index=2)
            for key in self.keys.position:
                frame = nvb_utils.nwtime2frame(key[0])
                curveX.keyframe_points.insert(frame, key[1])
                curveY.keyframe_points.insert(frame, key[2])
                curveZ.keyframe_points.insert(frame, key[3])

        # Set selfillumcolor channels if there are selfillumcolor keys
        if (self.keys.selfillumcolor):
            curveR = action.fcurves.new(data_path='nvb.selfillumcolor', index=0)
            curveG = action.fcurves.new(data_path='nvb.selfillumcolor', index=1)
            curveB = action.fcurves.new(data_path='nvb.selfillumcolor', index=2)

            for key in self.keys.selfillumcolor:
                frame = nvb_utils.nwtime2frame(key[0])
                curveR.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]), key[1])
                curveG.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]), key[2])
                curveB.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]), key[3])

        # For lamps: Set color channels
        if (self.keys.color):
            curveR = action.fcurves.new(data_path='color', index=0)
            curveG = action.fcurves.new(data_path='color', index=1)
            curveB = action.fcurves.new(data_path='color', index=2)

            for key in self.keys.color:
                frame = nvb_utils.nwtime2frame(key[0])
                curveR.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]), key[1])
                curveG.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]), key[2])
                curveB.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]), key[3])

        # For lamps: Set radius channels. Impert as distance
        if (self.keys.radius):
            curve = action.fcurves.new(data_path='distance', index=0)
            for key in self.keys.radius:
                frame = nvb_utils.nwtime2frame(key[0])
                curve.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]), key[1])

        # Add imcompatible animations (emitters) as a text object
        if (self.keys.rawascii):
            txt = bpy.data.texts.new(targetObject.name)
            txt.write(self.keys.rawascii)
            targetObject.nvb.rawascii = txt.name

        # For Materials: Add animation for materials (only alpha atm)
        if targetObject.active_material:
            self.addAnimToMaterial(targetObject.active_material, animName)

        targetObject.animation_data_create()
        targetObject.animation_data.action = action


    def getKeysFromAction(self, action, keyDict):

            for fcurve in action.fcurves:
                # Get the sub dict for this particlar type of fcurve
                axis     = fcurve.array_index
                dataPath = fcurve.data_path
                name     = ''
                if   dataPath == 'rotation_euler':
                    name = 'orientationkey'
                elif dataPath == 'rotation_axis_angle':
                    pass
                elif dataPath == 'location':
                    name = 'positionkey'
                elif dataPath == 'scale':
                    name = 'scalekey'
                elif dataPath == 'nvb.selfillumcolor':
                    name = 'selfillumcolorkey'
                elif dataPath == 'color': # Lamps/Lights
                    name = 'colorkey'
                elif dataPath == 'distance': # Lamps/Lights
                    name = 'radiuskey'
                elif dataPath.endswith('alpha_factor'): # Texture alpha_factor
                    name = 'alphakey'

                for kfp in fcurve.keyframe_points:
                    frame = int(round(kfp.co[0]))
                    keys  = keyDict[name]
                    if frame in keys:
                        values = keys[frame]
                    else:
                        values = [0.0, 0.0, 0.0, 0.0]
                    values[axis] = values[axis] + kfp.co[1]
                    keys[frame] = values


    def addKeysToAscii(self, obj, asciiLines):
        keyDict =  {'orientationkey'    : collections.OrderedDict(), \
                    'positionkey'       : collections.OrderedDict(), \
                    'scalekey'          : collections.OrderedDict(), \
                    'selfillumcolorkey' : collections.OrderedDict(), \
                    'colorkey'          : collections.OrderedDict(), \
                    'radiuskey'         : collections.OrderedDict(), \
                    'alphakey'          : collections.OrderedDict() }

        # Object Data
        if obj.animation_data:
            action = obj.animation_data.action
            self.getKeysFromAction(action, keyDict)

        # Material/ texture data (= texture alpha_factor)
        if obj.active_material and obj.active_material.animation_data:
            action = obj.animation_data.action
            self.getKeysFromAction(action, keyDict)

        l_str   = str
        l_round = round
        name = 'orientationkey'
        if   keyDict[name]:
            asciiLines.append('    ' + name + ' ' + l_str(len(keyDict[name])))
            for frame, key in keyDict[name].items():
                eul  = mathutils.Euler((key[0], key[1], key[2]), 'XYZ')
                val  = nvb_utils.euler2nwangle(eul)
                time = nvb_utils.frame2nwtime(frame)
                asciiLines.append('      ' + l_str(l_round(time, 5)) + ' ' +
                                             l_str(l_round(val[0], 5)) + ' ' +
                                             l_str(l_round(val[1], 5)) + ' ' +
                                             l_str(l_round(val[2], 5)) + ' ' +
                                             l_str(l_round(val[3], 5)) )
        name = 'positionkey'
        if keyDict[name]:
            asciiLines.append('    ' + name + ' ' + l_str(len(keyDict[name])))
            for frame, key in keyDict[name].items():
                time = nvb_utils.frame2nwtime(frame)
                asciiLines.append('      ' + l_str(l_round(time, 5)) + ' ' +
                                             l_str(l_round(key[0], 5)) + ' ' +
                                             l_str(l_round(key[1], 5)) + ' ' +
                                             l_str(l_round(key[2], 5)) )
        name = 'scalekey'
        if keyDict[name]:
            asciiLines.append('    ' + name + ' ' + l_str(len(keyDict[name])))
            for frame, key in keyDict[name].items():
                time = nvb_utils.frame2nwtime(frame)
                asciiLines.append('      ' + l_str(l_round(time, 5)) + ' ' +
                                             l_str(l_round(key[0], 5)) )
        name = 'selfillumcolorkey'
        if keyDict[name]:
            asciiLines.append('    ' + name + ' ' + l_str(len(keyDict[name])))
            for frame, key in keyDict[name].items():
                time = nvb_utils.frame2nwtime(frame)
                asciiLines.append('      ' + l_str(l_round(time, 5)) + ' ' +
                                             l_str(l_round(key[0], 2)) + ' ' +
                                             l_str(l_round(key[1], 2)) + ' ' +
                                             l_str(l_round(key[2], 2)) )
        name = 'colorkey'
        if keyDict[name]:
            asciiLines.append('    ' + name + ' ' + l_str(len(keyDict[name])))
            for frame, key in keyDict[name].items():
                time = nvb_utils.frame2nwtime(frame)
                asciiLines.append('      ' + l_str(l_round(time, 5)) + ' ' +
                                             l_str(l_round(key[0], 2)) + ' ' +
                                             l_str(l_round(key[1], 2)) + ' ' +
                                             l_str(l_round(key[2], 2)) )
        name = 'radiuskey'
        if keyDict[name]:
            asciiLines.append('    ' + name + ' ' + l_str(len(keyDict[name])))
            for frame, key in keyDict[name].items():
                time = nvb_utils.frame2nwtime(frame)
                asciiLines.append('      ' + l_str(l_round(time, 5)) + ' ' +
                                             l_str(l_round(key[0], 5)) )
        name = 'alphakey'
        if keyDict[name]:
            asciiLines.append('    ' + name + ' ' + l_str(len(keyDict[name])))
            for frame, key in keyDict[name].items():
                time = nvb_utils.frame2nwtime(frame)
                asciiLines.append('      ' + l_str(l_round(time, 5)) + ' ' +
                                             l_str(l_round(key[0], 2)) )


    def getOriginalName(self, nodeName, animName):
        '''
        A bit messy due to compatibility
        '''
        if nodeName.endswith(animName):
            orig = nodeName[:len(nodeName)-len(animName)]
            if orig.endswith('.'):
                return orig[:len(orig)-1]
            else:
                return orig

        # Try to separate the name by '.'
        orig = nodeName.rpartition('.')[0]
        if orig:
            return orig

        # Couldn't find anything ? Return the string itself
        return nodeName


    def toAscii(self, bObject, asciiLines, animName):
        trueName   = self.getOriginalName(bObject.name, animName)
        trueParent = nvb_def.null
        if bObject.parent:
            trueParent = self.getOriginalName(bObject.parent.name, animName)
        asciiLines.append('  node dummy ' + trueName)
        asciiLines.append('    parent ' + trueParent)
        self.addKeysToAscii(bObject, asciiLines)
        asciiLines.append('  endnode')
