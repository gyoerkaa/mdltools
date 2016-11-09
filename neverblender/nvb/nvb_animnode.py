"""TODO: DOC."""

import mathutils
import collections
import bpy

from . import nvb_def
from . import nvb_utils
from . import nvb_parse


class Node():
    """TODO: DOC."""

    def __init__(self, name='UNNAMED'):
        """TODO: DOC."""
        self.nodeidx = -1

        self.name = name
        self.parent = nvb_def.null

        # For animations using a single value as key
        self.position = None
        self.positionkey = []
        self.orientation = None
        self.orientationkey = []
        self.scale = None
        self.scalekey = []
        self.alpha = None
        self.alphakey = []
        self.selfillumcolor = None
        self.selfillumcolorkey = []
        self.color = None
        self.colorkey = []
        self.radius = None
        self.radiuskey = []
        # Emitters ... incompatible. Import as text
        self.rawascii = []

        # Animesh
        self.sampleperiod = 0.0
        self.animtverts = []
        self.animverts = []
        self.clipu = 0.0
        self.clipv = 0.0
        self.clipw = 0.0
        self.cliph = 0.0

        self.objdata = False
        self.matdata = False
        self.uvdata = False

    def __bool__(self):
        """Return false if the node is empty, i.e. no anims attached."""
        return self.objdata or self.matdata or self.rawascii

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
        nodetype = 'dummy'
        for i, line in enumerate(asciiLines):
            try:
                label = line[0].lower()
            except IndexError:
                continue  # Probably empty line, skip it
            if not l_isNumber(label):
                if label == 'node':
                    nodetype = line[1].lower()
                    self.name = nvb_utils.getAuroraString(line[2])
                elif label == 'endnode':
                    return
                elif label == 'parent':
                    self.parentName = nvb_utils.getAuroraString(line[1])
                # Animations using a single value as key
                elif label == 'position':
                    self.position = (l_float(line[1]),
                                     l_float(line[2]),
                                     l_float(line[3]))
                    self.objdata = True
                elif label == 'orientation':
                    self.orientation = (l_float(line[1]),
                                        l_float(line[2]),
                                        l_float(line[3]),
                                        l_float(line[4]))
                    self.objdata = True
                elif label == 'scale':
                    self.scale = l_float(line[1])
                    self.objdata = True
                elif label == 'alpha':
                    self.alpha = l_float(line[1])
                    self.matdata = True
                # Animeshes
                elif label == 'verts':
                    pass  # Not needed (?)
                elif label == 'tverts':
                    pass  # Not needed (?)
                elif label == 'faces':
                    pass  # Not needed (?)
                elif label == 'sampleperiod':
                    self.sampleperiod = l_float(line[1])
                elif label == 'clipu':
                    self.clipu = l_float(line[1])
                elif label == 'clipv':
                    self.clipv = l_float(line[1])
                elif label == 'clipw':
                    self.clipw = l_float(line[1])
                elif label == 'cliph':
                    self.cliph = l_float(line[1])
                elif label == 'animverts':
                    numVals = l_int(line[1])
                    nvb_parse.f3(asciiLines[i+1:i+numVals+1], self.animverts)
                elif label == 'animtverts':
                    numVals = l_int(line[1])
                    nvb_parse.f3(asciiLines[i+1:i+numVals+1], self.animtverts)
                    self.uvdata = True
                # Keyed animations
                elif label == 'positionkey':
                    numKeys = self.findEnd(asciiLines[i+1:])
                    nvb_parse.f4(asciiLines[i+1:i+numKeys+1],
                                 self.positionkey)
                    self.objdata = True
                elif label == 'orientationkey':
                    numKeys = self.findEnd(asciiLines[i+1:])
                    nvb_parse.f5(asciiLines[i+1:i+numKeys+1],
                                 self.orientationkey)
                    self.objdata = True
                elif label == 'scalekey':
                    numKeys = self.findEnd(asciiLines[i+1:])
                    nvb_parse.f2(asciiLines[i+1:i+numKeys+1],
                                 self.scalekey)
                    self.objdata = True
                elif label == 'alphakey':
                    # If this is an emitter, alphakeys are incompatible. We'll
                    # handle them later as plain text
                    numKeys = self.findEnd(asciiLines[i+1:])
                    if nodetype == 'emitter':
                        nvb_parse.txt(asciiLines[i:i+numKeys+1],
                                      self.rawascii)
                    else:
                        nvb_parse.f2(asciiLines[i+1:i+numKeys+1],
                                     self.alphakey)
                    self.matdata = True
                elif label == 'selfillumcolorkey':
                    numKeys = self.findEnd(asciiLines[i+1:])
                    nvb_parse.f4(asciiLines[i+1:i+numKeys+1],
                                 self.selfillumcolorkey)
                    self.objdata = True
                # Lights/lamps only
                elif label == 'colorkey':
                    numKeys = self.findEnd(asciiLines[i+1:])
                    nvb_parse.f4(asciiLines[i+1:i+numKeys+1], self.colorkey)
                    self.objdata = True
                elif label == 'radiuskey':
                    numKeys = self.findEnd(asciiLines[i+1:])
                    nvb_parse.f2(asciiLines[i+1:i+numKeys+1], self.radiuskey)
                    self.objdata = True
                # Some unknown label.
                # Probably keys for emitters, incompatible, save as plain text
            elif (nodetype == 'emitter') and (label[0] != '#'):
                    numKeys = self.findEnd(asciiLines[i+1:])
                    self.rawascii.extend(asciiLines[i:i+numKeys+1])

    @staticmethod
    def getCurve(action, dataPath, idx=0):
        """TODO: DOC."""
        for fc in action.fcurves:
            if (fc.data_path == dataPath) and (fc.array_index == idx):
                return fc
        fc = action.fcurves.new(data_path=dataPath, index=idx)
        return fc

    def createDataMaterial(self, mat, anim):
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
        if self.alphakey:
            for key in self.alphakey:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curve.keyframe_points.insert(frame, key[1])
        elif self.alpha is not None:
            curve.keyframe_points.insert(frameStart, self.alpha)
            curve.keyframe_points.insert(frameEnd, self.alpha)

    def createDataObject(self, obj, anim):
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
        kfOptions = {'FAST'}
        dp = 'rotation_euler'
        if (self.orientationkey):
            curveX = Node.getCurve(action, dp, 0)
            curveY = Node.getCurve(action, dp, 1)
            curveZ = Node.getCurve(action, dp, 2)
            currEul = None
            prevEul = None
            for key in self.orientationkey:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                eul = nvb_utils.nwangle2euler(key[1:5])
                currEul = nvb_utils.eulerFilter(eul, prevEul)
                prevEul = currEul
                curveX.keyframe_points.insert(frame, currEul.x, kfOptions)
                curveY.keyframe_points.insert(frame, currEul.y, kfOptions)
                curveZ.keyframe_points.insert(frame, currEul.z, kfOptions)
        elif self.orientation is not None:
            curveX = Node.getCurve(action, dp, 0)
            curveY = Node.getCurve(action, dp, 1)
            curveZ = Node.getCurve(action, dp, 2)
            eul = nvb_utils.nwangle2euler(self.orientation)
            curveX.keyframe_points.insert(frameStart, eul[0])
            curveY.keyframe_points.insert(frameStart, eul[1])
            curveZ.keyframe_points.insert(frameStart, eul[2])
            if frameStart < frameEnd:
                curveX.keyframe_points.insert(frameEnd, eul[0])
                curveY.keyframe_points.insert(frameEnd, eul[1])
                curveZ.keyframe_points.insert(frameEnd, eul[2])

        dp = 'location'
        if (self.positionkey):
            curveX = Node.getCurve(action, dp, 0)
            curveY = Node.getCurve(action, dp, 1)
            curveZ = Node.getCurve(action, dp, 2)
            for key in self.positionkey:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curveX.keyframe_points.insert(frame, key[1], kfOptions)
                curveY.keyframe_points.insert(frame, key[2], kfOptions)
                curveZ.keyframe_points.insert(frame, key[3], kfOptions)
        elif (self.position is not None):
            curveX = Node.getCurve(action, dp, 0)
            curveY = Node.getCurve(action, dp, 1)
            curveZ = Node.getCurve(action, dp, 2)
            curveX.keyframe_points.insert(frameStart, self.position[0])
            curveY.keyframe_points.insert(frameStart, self.position[1])
            curveZ.keyframe_points.insert(frameStart, self.position[2])
            if frameStart < frameEnd:
                curveX.keyframe_points.insert(frameEnd, self.position[0])
                curveY.keyframe_points.insert(frameEnd, self.position[1])
                curveZ.keyframe_points.insert(frameEnd, self.position[2])

        dp = 'scale'
        if (self.scalekey):
            curveX = Node.getCurve(action, dp, 0)
            curveY = Node.getCurve(action, dp, 1)
            curveZ = Node.getCurve(action, dp, 2)
            for key in self.scalekey:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curveX.keyframe_points.insert(frame, key[1])
                curveY.keyframe_points.insert(frame, key[1])
                curveZ.keyframe_points.insert(frame, key[1])
        elif (self.scale is not None):
            curveX = Node.getCurve(action, dp, 0)
            curveY = Node.getCurve(action, dp, 1)
            curveZ = Node.getCurve(action, dp, 2)
            curveX.keyframe_points.insert(frameStart, self.scale)
            curveY.keyframe_points.insert(frameStart, self.scale)
            curveZ.keyframe_points.insert(frameStart, self.scale)
            if frameStart < frameEnd:
                curveX.keyframe_points.insert(frameEnd, self.scale)
                curveY.keyframe_points.insert(frameEnd, self.scale)
                curveZ.keyframe_points.insert(frameEnd, self.scale)

        dp = 'nvb.selfillumcolor'
        if (self.selfillumcolorkey):
            curveR = Node.getCurve(action, dp, 0)
            curveG = Node.getCurve(action, dp, 1)
            curveB = Node.getCurve(action, dp, 2)
            for key in self.selfillumcolorkey:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curveR.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[1])
                curveG.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[2])
                curveB.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[3])
        elif (self.selfillumcolor is not None):
            curveR = Node.getCurve(action, dp, 0)
            curveG = Node.getCurve(action, dp, 1)
            curveB = Node.getCurve(action, dp, 2)
            curveR.keyframe_points.insert(frameStart, self.selfillumcolor[0])
            curveG.keyframe_points.insert(frameStart, self.selfillumcolor[1])
            curveB.keyframe_points.insert(frameStart, self.selfillumcolor[2])
            if frameStart < frameEnd:
                curveR.keyframe_points.insert(frameEnd, self.selfillumcolor[0])
                curveG.keyframe_points.insert(frameEnd, self.selfillumcolor[1])
                curveB.keyframe_points.insert(frameEnd, self.selfillumcolor[2])

        dp = 'color'
        if self.colorkey:
            curveR = Node.getCurve(action, dp, 0)
            curveG = Node.getCurve(action, dp, 1)
            curveB = Node.getCurve(action, dp, 2)
            for key in self.colorkey:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curveR.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[1])
                curveG.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[2])
                curveB.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[3])
        elif self.color:
            curveR = Node.getCurve(action, dp, 0)
            curveG = Node.getCurve(action, dp, 1)
            curveB = Node.getCurve(action, dp, 2)
            curveR.keyframe_points.insert(frameStart, self.color[0])
            curveG.keyframe_points.insert(frameStart, self.color[1])
            curveB.keyframe_points.insert(frameStart, self.color[2])
            if frameStart < frameEnd:
                curveR.keyframe_points.insert(frameEnd, self.color[0])
                curveG.keyframe_points.insert(frameEnd, self.color[1])
                curveB.keyframe_points.insert(frameEnd, self.color[2])

        dp = 'distance'
        if self.radiuskey:
            curve = Node.getCurve(action, dp)
            for key in self.radiuskey:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curve.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                             key[1])
        elif self.radius:
            curve = Node.getCurve(action, dp, 0)
            curve.keyframe_points.insert(frameStart, self.radius)
            if frameStart < frameEnd:
                curve.keyframe_points.insert(frameEnd, self.radius)

    def createDataEmitter(self, obj, anim, options):
        """TODO:Doc."""
        # Add imcompatible animations (emitters) as a text object
        if (self.rawascii):
            # Get the text file
            txt = None
            if anim.rawascii and (anim.rawascii in bpy.data.texts):
                txt = bpy.data.texts[anim.rawascii]
            if not txt:
                txt = bpy.data.texts.new(options.mdlname +
                                         '.anim.' + anim.name)
                anim.rawascii = txt.name
            # Convert nwn time to frames and write to text file
            objType = nvb_utils.getNodeType(obj)
            txt.write('  node ' + objType + ' ' + self.name)
            l_isNumber = nvb_utils.isNumber
            frameStart = anim.frameStart
            for line in self.rawascii:
                if l_isNumber(line[0]):
                    nwtime = float(line[0])
                    frame = frameStart + nvb_utils.nwtime2frame(nwtime)
                    txt.write('\n      ' +
                              str(frame) + ' ' + ' '.join(line[1:]))
                else:
                    txt.write('\n    ' + ' '.join(line))
            txt.write('\n  endnode')

    def createDataUV(self, obj, uvlayer, anim, options):
        """TODO:Doc."""
        # Sanity checks
        if not obj.data:
            return
        numUVs = len(uvlayer.data)
        if (len(self.animtverts) % numUVs) != 0:
            return
        # Get animation data, create if needed.
        animData = obj.data.animation_data
        if not animData:
            animData = obj.data.animation_data_create()
        # Get action, create if needed.
        action = animData.action
        if not action:
            action = bpy.data.actions.new(name=obj.name)
            action.use_fake_user = True
            animData.action = action
        # Insert keyframes
        frameStart = anim.frameStart
        kfOptions = {'FAST'}
        dp_prefix = 'uv_layers["' + uvlayer.name + '"].data['
        for idx, animtvert in enumerate(self.animtverts):
            dp = dp_prefix + str(idx) + '].uv'
            setIdx = idx // numUVs
            frame = frameStart + \
                (setIdx * nvb_utils.nwtime2frame(self.sampleperiod))
            curveU = Node.getCurve(action, dp, 0)
            curveV = Node.getCurve(action, dp, 1)
            curveU.keyframe_points.insert(frame, animtvert[0], kfOptions)
            curveV.keyframe_points.insert(frame, animtvert[1], kfOptions)
        pass

    def create(self, obj, anim, options):
        """TODO:Doc."""
        if self.objdata:
            self.createDataObject(obj, anim)
        if self.matdata and obj.active_material:
            self.createDataMaterial(obj.active_material, anim)
        if self.uvdata and obj.data and obj.data.uv_layers.active:
            pass
            # self.createDataUV(obj, obj.data.uv_layers.active, anim, options)
        if self.rawascii and \
           (nvb_utils.getNodeType(obj) == nvb_def.Nodetype.EMITTER):
            self.createDataEmitter(obj, anim, options)

    @staticmethod
    def getKeysFromAction(action, anim, keyDict):
        """TODO: DOC."""
        namelookup = {'rotation_euler':     'orientationkey',
                      'location':           'positionkey',
                      'scale':              'scalekey',
                      'nvb.selfillumcolor': 'selfillumcolorkey',
                      'color':              'colorkey',
                      'distance':           'radiuskey'}
        for fcurve in action.fcurves:
            axis = fcurve.array_index
            # Get the name from the data path
            dp = fcurve.data_path
            if dp in namelookup:
                nwname = namelookup[fcurve.data_path]
            else:
                # Maybe texture or material alpha
                if dp.endswith('alpha_factor') or dp.endswith('alpha'):
                    nwname = 'alphakey'
                else:
                    continue  # Can't export this one, skip it

            kfp = [p for p in fcurve.keyframe_points
                   if anim.frameStart <= p.co[0] <= anim.frameEnd]
            for p in kfp:
                frame = int(round(p.co[0]))
                keys = keyDict[nwname]
                if frame in keys:
                    values = keys[frame]
                else:
                    values = [0.0, 0.0, 0.0, 0.0]
                values[axis] = values[axis] + p.co[1]
                keys[frame] = values

    @staticmethod
    def generateAsciiKeysEmitter(obj, anim, asciiLines):
        """TODO: DOC."""
        if not (anim.rawascii or (anim.rawascii in bpy.data.texts)):
            return
        txtBlock = bpy.data.texts[anim.rawascii].as_string()
        nodeStart = txtBlock.find(obj.name)
        if nodeStart < 0:
            return
        nodeEnd = txtBlock.find('endnode', nodeStart)
        if nodeEnd < 0:
            return
        txtLines = txtBlock[nodeStart+len(obj.name):nodeEnd-1].splitlines()
        l_isNumber = nvb_utils.isNumber
        animStart = anim.frameStart
        for line in [l.strip().split() for l in txtLines]:
            try:
                label = line[0].lower()
            except IndexError:
                continue
            # Lines starting with numbers are keys
            if l_isNumber(label):
                frame = float(label)
                nwtime = round(nvb_utils.frame2nwtime(frame - animStart), 5)
                asciiLines.append('      ' + str(nwtime) + ' ' +
                                  ' '.join(line[1:]))
            else:
                asciiLines.append('    ' + ' '.join(line))

    @staticmethod
    def generateAsciiKeys(obj, anim, asciiLines):
        """TODO: DOC."""
        keyDict = {'orientationkey': collections.OrderedDict(),
                   'positionkey': collections.OrderedDict(),
                   'scalekey': collections.OrderedDict(),
                   'selfillumcolorkey': collections.OrderedDict(),
                   'colorkey': collections.OrderedDict(),
                   'radiuskey': collections.OrderedDict(),
                   'alphakey': collections.OrderedDict()}

        # Object Data
        if obj.animation_data:
            action = obj.animation_data.action
            if action:
                Node.getKeysFromAction(action, anim, keyDict)
        # Material/ texture data (= alpha keys)
        if obj.active_material and obj.active_material.animation_data:
            action = obj.active_material.animation_data.action
            if action:
                Node.getKeysFromAction(action, anim, keyDict)

        l_round = round  # For speed
        animStart = anim.frameStart

        kname = 'orientationkey'
        if len(keyDict[kname]) > 0:
            if len(keyDict[kname]) == 1:
                formatStr = '    orientation \
                            {: 6.5f} {: 6.5f} {: 6.5f} {: 6.5f}'
                key = keyDict[kname][0]
                eul = mathutils.Euler((key[0], key[1], key[2]), 'XYZ')
                val = nvb_utils.euler2nwangle(eul)
                s = formatStr.format(val[0], val[1], val[2], val[3])
                asciiLines.append(s)
            else:
                asciiLines.append('    orientationkey ' +
                                  str(len(keyDict[kname])))
                for frame, key in keyDict[kname].items():
                    time = l_round(nvb_utils.frame2nwtime(frame - animStart),
                                   5)
                    eul = mathutils.Euler((key[0], key[1], key[2]), 'XYZ')
                    val = nvb_utils.euler2nwangle(eul)
                    formatStr = '      {: 6.5f} \
                                {: 6.5f} {: 6.5f} {: 6.5f} {: 6.5f}'
                    s = formatStr.format(time, val[0], val[1], val[2], val[3])
                    asciiLines.append(s)

        kname = 'positionkey'
        if len(keyDict[kname]) > 0:
            if len(keyDict[kname]) == 1:
                formatStr = '    position {: 6.5f} {: 6.5f} {: 6.5f}'
                key = keyDict[kname][0]
                s = formatStr.format(key[0], key[1], key[2])
                asciiLines.append(s)
            else:
                asciiLines.append('    positionkey ' +
                                  str(len(keyDict[kname])))
                for frame, key in keyDict[kname].items():
                    time = l_round(nvb_utils.frame2nwtime(frame - animStart),
                                   5)
                    formatStr = '      {: 6.5f} {: 6.5f} {: 6.5f} {: 6.5f}'
                    s = formatStr.format(time, key[0], key[1], key[2])
                    asciiLines.append(s)

        kname = 'scalekey'
        if len(keyDict[kname]) > 0:
            asciiLines.append('    ' + kname + ' ' + str(len(keyDict[kname])))
            for frame, key in keyDict[kname].items():
                time = l_round(nvb_utils.frame2nwtime(frame - animStart), 5)
                s = '      {: 6.5f} {: 6.5f}'.format(time, key[0])
                asciiLines.append(s)

        kname = 'selfillumcolorkey'
        if len(keyDict[kname]) > 0:
            asciiLines.append('    ' + kname + ' ' + str(len(keyDict[kname])))
            for frame, key in keyDict[kname].items():
                time = l_round(nvb_utils.frame2nwtime(frame - animStart), 5)
                formatStr = '      {: 6.5f} {: 3.2f} {: 3.2f} {: 3.2f}'
                s = formatStr.format(time, key[0], key[1], key[2])
                asciiLines.append(s)

        kname = 'colorkey'
        if len(keyDict[kname]) > 0:
            asciiLines.append('    ' + kname + ' ' + str(len(keyDict[kname])))
            for frame, key in keyDict[kname].items():
                time = l_round(nvb_utils.frame2nwtime(frame - animStart), 5)
                formatStr = '      {: 6.5f} {: 3.2f} {: 3.2f} {: 3.2f}'
                s = formatStr.format(time, key[0], key[1], key[2])
                asciiLines.append(s)

        kname = 'radiuskey'
        if len(keyDict[kname]) > 0:
            asciiLines.append('    ' + kname + ' ' + str(len(keyDict[kname])))
            for frame, key in keyDict[kname].items():
                time = l_round(nvb_utils.frame2nwtime(frame - animStart), 5)
                s = '      {: 6.5f} {: 6.5f}'.format(time, key[0])
                asciiLines.append(s)

        kname = 'alphakey'
        if len(keyDict[kname]) > 0:
            asciiLines.append('    ' + kname + ' ' + str(len(keyDict[kname])))
            for frame, key in keyDict[kname].items():
                time = l_round(nvb_utils.frame2nwtime(frame - animStart), 5)
                s = '      {: 6.5f} {: 3.2f}'.format(time, key[0])
                asciiLines.append(s)

    @staticmethod
    def generateAscii(obj, anim, asciiLines):
        """TODO:Doc."""
        if not obj:
            return
        # Type + Name
        asciiLines.append('  node ' +
                          nvb_utils.getNodeType(obj) + ' ' + obj.name)
        # Parent
        if obj.parent:
            asciiLines.append('    parent ' + obj.parent.name)
        else:
            asciiLines.append('    parent null')
        Node.generateAsciiKeysEmitter(obj, anim, asciiLines)
        Node.generateAsciiKeys(obj, anim, asciiLines)
        asciiLines.append('  endnode')
