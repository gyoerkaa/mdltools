"""TODO: DOC."""

import math
import mathutils
import collections
import copy
import bpy

from . import nvb_def
from . import nvb_utils
from . import nvb_parse
from . import nvb_node


class Animnode():
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
        self.rawdata = []

        # Animesh
        self.sampleperiod = 0.0
        self.animtverts = []
        self.animverts = []
        self.clipu = 0.0
        self.clipv = 0.0
        self.clipw = 0.0
        self.cliph = 0.0

        self.objdata = False  # Object animations present (loc, rot, scale ...)
        self.matdata = False  # Material animations present
        self.uvdata = False  # Animmesh, uv animations present
        self.shapedata = False  # Animmesh, vertex animations present

    def __bool__(self):
        """Return false if the node is empty, i.e. no anims attached."""
        return self.objdata or self.matdata or self.rawdata

    def findEnd(self, asciiBlock):
        """Find the end of a key list.

        We don't know when a list of keys of keys will end. We'll have to
        search for the first non-numeric value
        """
        l_isNumber = nvb_utils.isNumber
        return next((i for i, v in enumerate(asciiBlock)
                     if not l_isNumber(v[0])), -1)

    @staticmethod
    def eulerFilter(currEul, prevEul):
        """TODO: DOC."""
        def distance(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])

        def flip(e):
            f = e.copy()
            f[0] += math.pi
            f[1] *= -1
            f[1] += math.pi
            f[2] += math.pi
            return f

        def flipDiff(a, b):
            while abs(a - b) > math.pi:
                if a < b:
                    b -= 2 * math.pi
                else:
                    b += 2 * math.pi
            return b

        if not prevEul:
            # Nothing to compare to, return original value
            return currEul

        eul = currEul.copy()
        eul[0] = flipDiff(prevEul[0], eul[0])
        eul[1] = flipDiff(prevEul[1], eul[1])
        eul[2] = flipDiff(prevEul[2], eul[2])

        # Flip current euler
        flipEul = flip(eul)
        flipEul[0] = flipDiff(prevEul[0], flipEul[0])
        flipEul[1] = flipDiff(prevEul[1], flipEul[1])
        flipEul[2] = flipDiff(prevEul[2], flipEul[2])

        currDist = distance(prevEul, eul)
        flipDist = distance(prevEul, flipEul)

        if flipDist < currDist:
            return flipEul
        else:
            return eul

    def loadAscii(self, asciiLines, nodeidx=-1):
        """TODO: DOC."""
        self.animtverts = []
        self.animverts = []

        l_float = float
        l_int = int
        l_isNumber = nvb_utils.isNumber
        self.nodeidx = nodeidx
        nodetype = 'dummy'
        for i, line in enumerate(asciiLines):
            try:
                label = line[0].lower()
            except (IndexError, AttributeError):
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
                    self.position = tuple([float(v) for v in line[1:4]])
                    self.objdata = True
                elif label == 'orientation':
                    self.orientation = tuple([float(v) for v in line[1:5]])
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
                    if not self.animverts:
                        numVals = l_int(line[1])
                        nvb_parse.f3(asciiLines[i+1:i+numVals+1],
                                     self.animverts)
                        self.shapedata = True
                elif label == 'animtverts':
                    if not self.animtverts:
                        numVals = l_int(line[1])
                        nvb_parse.f3(asciiLines[i+1:i+numVals+1],
                                     self.animtverts)
                        self.uvdata = True
                # Keyed animations
                elif label == 'positionkey':
                    numkeys = nvb_utils.findEnd(asciiLines[i+1:])
                    nvb_parse.f4(asciiLines[i+1:i+numkeys+1],
                                 self.positionkey)
                    self.objdata = True
                elif label == 'orientationkey':
                    numkeys = nvb_utils.findEnd(asciiLines[i+1:])
                    nvb_parse.f5(asciiLines[i+1:i+numkeys+1],
                                 self.orientationkey)
                    self.objdata = True
                elif label == 'scalekey':
                    numkeys = nvb_utils.findEnd(asciiLines[i+1:])
                    nvb_parse.f2(asciiLines[i+1:i+numkeys+1],
                                 self.scalekey)
                    self.objdata = True
                elif label == 'alphakey':
                    # If this is an emitter, alphakeys are incompatible. We'll
                    # handle them later as plain text
                    numkeys = nvb_utils.findEnd(asciiLines[i+1:])
                    if nodetype == 'emitter':
                        nvb_parse.txt(asciiLines[i:i+numkeys+1],
                                      self.rawdata)
                    else:
                        nvb_parse.f2(asciiLines[i+1:i+numkeys+1],
                                     self.alphakey)
                    self.matdata = True
                elif label == 'selfillumcolorkey':
                    numkeys = nvb_utils.findEnd(asciiLines[i+1:])
                    nvb_parse.f4(asciiLines[i+1:i+numkeys+1],
                                 self.selfillumcolorkey)
                    self.objdata = True
                # Lights/lamps only
                elif label == 'colorkey':
                    numkeys = nvb_utils.findEnd(asciiLines[i+1:])
                    nvb_parse.f4(asciiLines[i+1:i+numkeys+1], self.colorkey)
                    self.objdata = True
                elif label == 'radiuskey':
                    numkeys = nvb_utils.findEnd(asciiLines[i+1:])
                    nvb_parse.f2(asciiLines[i+1:i+numkeys+1], self.radiuskey)
                    self.objdata = True
                # Some unknown label.
                # Probably keys for emitters, incompatible, save as plain text
                elif (nodetype == 'emitter') and (label[0] != '#'):
                    numkeys = nvb_utils.findEnd(asciiLines[i+1:])
                    if numkeys > 1:
                        # Set of unknown keys
                        self.rawdata.append([label,
                                            asciiLines[i+1:i+numkeys+1]])
                    elif numkeys == 1:
                        # Single unknown key
                        self.rawdata.append([label, [asciiLines[i+1]]])
                    else:
                        # Single unknown value
                        self.rawdata.append([' '.join(line), []])

    @staticmethod
    def getCurve(action, data_path, index=0):
        """TODO: DOC."""
        # for fc in action.fcurves:
        #     if (fc.data_path == dataPath) and (fc.array_index == idx):
        #         return fc
        fc = action.fcurves.find(data_path, index)
        if not fc:
            fc = action.fcurves.new(data_path=data_path, index=index)
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
        curve = Animnode.getCurve(action, dp)
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

        dp = 'rotation_euler'
        if (self.orientationkey):
            curves = [Animnode.getCurve(action, dp, i) for i in range(3)]
            kfp = [curves[i].keyframe_points for i in range(3)]
            nkfp = list(map(lambda x: len(x), kfp))
            list(map(lambda x: x.add(len(self.orientationkey)), kfp))
            curr_eul = 0
            prev_eul = 0
            for i in range(len(self.orientationkey)):
                frame = frameStart + \
                    nvb_utils.nwtime2frame(self.orientationkey[i][0])
                eul = nvb_utils.nwangle2euler(self.orientationkey[i][1:5])
                curr_eul = Animnode.eulerFilter(eul, prev_eul)
                prev_eul = curr_eul
                for j in range(3):
                    tp = kfp[j][nkfp[j]+i]
                    tp.co = frame, curr_eul[j]
                    tp.interpolation = 'LINEAR'
                    tp.handle_left_type = 'AUTO_CLAMPED'
                    tp.handle_right_type = 'AUTO_CLAMPED'
            list(map(lambda x: x.update(), curves))

        elif self.orientation is not None:
            curveX = Animnode.getCurve(action, dp, 0)
            curveY = Animnode.getCurve(action, dp, 1)
            curveZ = Animnode.getCurve(action, dp, 2)
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
            curves = [Animnode.getCurve(action, dp, i) for i in range(3)]
            kfp = [curves[i].keyframe_points for i in range(3)]
            nkfp = list(map(lambda x: len(x), kfp))
            list(map(lambda x: x.add(len(self.positionkey)), kfp))
            for i in range(len(self.positionkey)):
                frame = frameStart + \
                    nvb_utils.nwtime2frame(self.positionkey[i][0])
                val = self.positionkey[i][1:4]
                for j in range(3):
                    tp = kfp[j][nkfp[j]+i]
                    tp.co = frame, val[j]
                    tp.interpolation = 'LINEAR'
                    tp.handle_left_type = 'AUTO_CLAMPED'
                    tp.handle_right_type = 'AUTO_CLAMPED'
            list(map(lambda x: x.update(), curves))

        elif (self.position is not None):
            curveX = Animnode.getCurve(action, dp, 0)
            curveY = Animnode.getCurve(action, dp, 1)
            curveZ = Animnode.getCurve(action, dp, 2)
            curveX.keyframe_points.insert(frameStart, self.position[0])
            curveY.keyframe_points.insert(frameStart, self.position[1])
            curveZ.keyframe_points.insert(frameStart, self.position[2])
            if frameStart < frameEnd:
                curveX.keyframe_points.insert(frameEnd, self.position[0])
                curveY.keyframe_points.insert(frameEnd, self.position[1])
                curveZ.keyframe_points.insert(frameEnd, self.position[2])

        dp = 'scale'
        if (self.scalekey):
            curveX = Animnode.getCurve(action, dp, 0)
            curveY = Animnode.getCurve(action, dp, 1)
            curveZ = Animnode.getCurve(action, dp, 2)
            for key in self.scalekey:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curveX.keyframe_points.insert(frame, key[1])
                curveY.keyframe_points.insert(frame, key[1])
                curveZ.keyframe_points.insert(frame, key[1])
        elif (self.scale is not None):
            curveX = Animnode.getCurve(action, dp, 0)
            curveY = Animnode.getCurve(action, dp, 1)
            curveZ = Animnode.getCurve(action, dp, 2)
            curveX.keyframe_points.insert(frameStart, self.scale)
            curveY.keyframe_points.insert(frameStart, self.scale)
            curveZ.keyframe_points.insert(frameStart, self.scale)
            if frameStart < frameEnd:
                curveX.keyframe_points.insert(frameEnd, self.scale)
                curveY.keyframe_points.insert(frameEnd, self.scale)
                curveZ.keyframe_points.insert(frameEnd, self.scale)

        dp = 'nvb.selfillumcolor'
        if (self.selfillumcolorkey):
            curveR = Animnode.getCurve(action, dp, 0)
            curveG = Animnode.getCurve(action, dp, 1)
            curveB = Animnode.getCurve(action, dp, 2)
            for key in self.selfillumcolorkey:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curveR.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[1])
                curveG.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[2])
                curveB.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[3])
        elif (self.selfillumcolor is not None):
            curveR = Animnode.getCurve(action, dp, 0)
            curveG = Animnode.getCurve(action, dp, 1)
            curveB = Animnode.getCurve(action, dp, 2)
            curveR.keyframe_points.insert(frameStart, self.selfillumcolor[0])
            curveG.keyframe_points.insert(frameStart, self.selfillumcolor[1])
            curveB.keyframe_points.insert(frameStart, self.selfillumcolor[2])
            if frameStart < frameEnd:
                curveR.keyframe_points.insert(frameEnd, self.selfillumcolor[0])
                curveG.keyframe_points.insert(frameEnd, self.selfillumcolor[1])
                curveB.keyframe_points.insert(frameEnd, self.selfillumcolor[2])

        dp = 'color'
        if self.colorkey:
            curveR = Animnode.getCurve(action, dp, 0)
            curveG = Animnode.getCurve(action, dp, 1)
            curveB = Animnode.getCurve(action, dp, 2)
            for key in self.colorkey:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curveR.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[1])
                curveG.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[2])
                curveB.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                              key[3])
        elif self.color:
            curveR = Animnode.getCurve(action, dp, 0)
            curveG = Animnode.getCurve(action, dp, 1)
            curveB = Animnode.getCurve(action, dp, 2)
            curveR.keyframe_points.insert(frameStart, self.color[0])
            curveG.keyframe_points.insert(frameStart, self.color[1])
            curveB.keyframe_points.insert(frameStart, self.color[2])
            if frameStart < frameEnd:
                curveR.keyframe_points.insert(frameEnd, self.color[0])
                curveG.keyframe_points.insert(frameEnd, self.color[1])
                curveB.keyframe_points.insert(frameEnd, self.color[2])

        dp = 'distance'
        if self.radiuskey:
            curve = Animnode.getCurve(action, dp)
            for key in self.radiuskey:
                frame = frameStart + nvb_utils.nwtime2frame(key[0])
                curve.keyframe_points.insert(nvb_utils.nwtime2frame(key[0]),
                                             key[1])
        elif self.radius:
            curve = Animnode.getCurve(action, dp, 0)
            curve.keyframe_points.insert(frameStart, self.radius)
            if frameStart < frameEnd:
                curve.keyframe_points.insert(frameEnd, self.radius)

    def createDataRaw(self, obj, anim, options):
        """Add incompatible animations (usually emitters) as plain text."""
        # Get or create the text object
        txt = None
        if anim.rawascii and (anim.rawascii in bpy.data.texts):
            txt = bpy.data.texts[anim.rawascii]
        if not txt:
            txt = bpy.data.texts.new(options.mdlname +
                                     '.anim.' + anim.name)
            txt.use_fake_user = True
            anim.rawascii = txt.name
        # Convert nwn time to frames and write to text object
        txt.write('node ' + nvb_utils.getNodeType(obj) +
                  ' ' + self.name + '\n')
        for label, keyList in self.rawdata:
            if keyList:
                # List of unknown keys
                txt.write('  ' + label + ' ' + str(len(keyList)) + '\n')
                for key in keyList:
                    nwtime = float(key[0])
                    values = [float(v) for v in key[1:]]
                    frame = nvb_utils.nwtime2frame(nwtime)
                    formatStr = '    {: >4d}' + \
                                ' '.join(['{: > 8.5f}']*len(values)) + '\n'
                    s = formatStr.format(frame, *values)
                    txt.write(s)
            else:
                # Single unknown value
                txt.write('  ' + ' '.join(label) + '\n')
        txt.write('endnode\n')

    def createDataShape(self, obj, anim, options):
        """Import animated vertices as shapekeys."""
        if not obj.data:
            return
        numVerts = len(obj.data.vertices)
        # Sanity check: Number of animated verts should be a mupltiple of the
        # number of verts
        if (len(self.animverts) % numVerts > 0):
            print("Neverblender: WARNING - Sample size mismatch (" +
                  "animesh " + obj.name + ")")
            return
        numSamples = len(self.animverts) // numVerts
        if numSamples == 1:
            sampleDistance = 0
        elif numSamples > 1:
            sampleDistance = \
                nvb_utils.nwtime2frame(self.sampleperiod) // (numSamples-1)
        else:
            print("Neverblender: WARNING - No samples (" +
                  "animesh " + obj.name + ")")
            return
        # Get the shape key name
        if obj.nvb.aurorashapekey:
            shapekeyname = obj.nvb.aurorashapekey
        else:
            shapekeyname = nvb_def.shapekeyname
        # Get or create the shape key to hold the animation
        if obj.data.shape_keys and \
           shapekeyname in obj.data.shape_keys.key_blocks:
            keyBlock = obj.data.shape_keys.key_blocks[shapekeyname]
        else:
            keyBlock = obj.shape_key_add(name=shapekeyname,
                                         from_mix=False)
            obj.nvb.aurorashapekey = keyBlock.name
        # Get animation data, create it if necessary
        animData = obj.data.shape_keys.animation_data
        if not animData:
            animData = obj.data.shape_keys.animation_data_create()
        # Get action, create one if necessary
        action = animData.action
        if not action:
            action = bpy.data.actions.new(name=obj.name)
            action.use_fake_user = True
            animData.action = action
        # Insert keyframes
        # We need to create three curves for each vert, one for each coordinate
        kfOptions = {'FAST'}
        frameStart = anim.frameStart
        dpPrefix = 'key_blocks["' + keyBlock.name + '"].data['
        for vertIdx in range(numVerts):
            dp = dpPrefix + str(vertIdx) + '].co'
            curveX = Animnode.getCurve(action, dp, 0)
            curveY = Animnode.getCurve(action, dp, 1)
            curveZ = Animnode.getCurve(action, dp, 2)
            samples = self.animverts[vertIdx::numVerts]
            for sampleIdx, co in enumerate(samples):
                frame = frameStart + (sampleIdx * sampleDistance)
                curveX.keyframe_points.insert(frame, co[0], kfOptions)
                curveY.keyframe_points.insert(frame, co[1], kfOptions)
                curveZ.keyframe_points.insert(frame, co[2], kfOptions)

    def createDataUV(self, obj, anim, options):
        """Import animated texture coordinates."""
        if not obj.data:
            return
        if not obj.data.uv_layers.active:
            return
        uvlayer = obj.data.uv_layers.active
        # Check if the original uv/tvert order was saved
        if uvlayer.name not in nvb_def.tvert_order:
            return
        tvert_order = [v for sl in nvb_def.tvert_order[uvlayer.name]
                       for v in sl]
        numTVerts = len(tvert_order)
        # Sanity check: Number of animated uvs/tverts has to be multiple of
        # the number of uvs
        if (len(self.animtverts) % numTVerts > 0):
            print("Neverblender: WARNING - Sample size mismatch (" +
                  "animesh " + obj.name + ")")
            return
        numSamples = len(self.animtverts) // numTVerts
        if numSamples == 1:
            sampleDistance = 0
        elif numSamples > 1:
            sampleDistance = \
                nvb_utils.nwtime2frame(self.sampleperiod) // (numSamples-1)
        else:
            print("Neverblender: WARNING - No samples (" +
                  "animesh " + obj.name + ")")
            return
        # Get animation data, create it if necessary
        animData = obj.data.animation_data
        if not animData:
            animData = obj.data.animation_data_create()
        # Get action, create one if necessary
        action = animData.action
        if not action:
            action = bpy.data.actions.new(name=obj.name)
            action.use_fake_user = True
            animData.action = action
        # Insert keyframes
        # We need to create two curves for each uv, one for each coordinate
        kfOptions = {'FAST'}
        frameStart = anim.frameStart
        dpPrefix = 'uv_layers["' + uvlayer.name + '"].data['
        # uvIdx = order in blender, tvertIdx = order in mdl
        print(tvert_order)
        for uvIdx, tvertIdx in enumerate(tvert_order):
            dp = dpPrefix + str(uvIdx) + '].uv'
            curveU = Animnode.getCurve(action, dp, 0)
            curveV = Animnode.getCurve(action, dp, 1)
            samples = self.animtverts[tvertIdx::numTVerts]
            for sampleIdx, co in enumerate(samples):
                frame = frameStart + (sampleIdx * sampleDistance)
                curveU.keyframe_points.insert(frame, co[0], kfOptions)
                curveV.keyframe_points.insert(frame, co[1], kfOptions)

    def create(self, obj, anim, options):
        """TODO:Doc."""
        if self.objdata:
            self.createDataObject(obj, anim)
        if self.matdata and obj.active_material:
            self.createDataMaterial(obj.active_material, anim)
        if self.uvdata:
            self.createDataUV(obj, anim, options)
        if self.shapedata:
            self.createDataShape(obj, anim, options)
        if self.rawdata and \
           (nvb_utils.getNodeType(obj) == nvb_def.Nodetype.EMITTER):
            self.createDataRaw(obj, anim, options)

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
    def generateAsciiRawData(obj, anim, asciiLines):
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
        render_fps = bpy.context.scene.render.fps
        for line in [l.strip().split() for l in txtLines]:
            try:
                label = line[0].lower()
            except IndexError:
                continue
            # Lines starting with numbers are keys
            if l_isNumber(label):
                frame = float(label)
                nwtime = round(nvb_utils.frame2nwtime(frame, render_fps), 5)
                values = [float(v) for v in line[1:]]
                formatStr = '      {: >6.5f}' + \
                            ' '.join(['{: > 6.5f}']*len(values))
                s = formatStr.format(nwtime, *values)
                asciiLines.append(s)
            else:
                asciiLines.append('    ' + ' '.join(line))

    @staticmethod
    def getKeysFromMatAction(action, anim, exports):
        """TODO: DOC."""
        for fcurve in action.fcurves:
            # ai = fcurve.array_index
            # Get the name from the data path
            dp = fcurve.data_path
            if dp.endswith('alpha_factor') or dp.endswith('alpha'):
                pass  # nwname = 'alphakey'

    @staticmethod
    def getKeysFromObjAction(action, anim, exports):
        """TODO: DOC."""
        pass
        """
        export_dp = {'rotation_euler', 'location', 'scale',
                     'nvb.selfillumcolor',
                     'color', 'distance'}
        dp_dict = dict()
        test12_dp = {'rotation_euler':     [[], 'orientationkey'],
                     'location':           [[], 'positionkey'],
                     'scale':              [[], 'scalekey'],
                     'nvb.selfillumcolor': [[], 'selfillumcolorkey'],
                     'color':              [[], 'colorkey'],
                     'distance':           [[], 'radiuskey']}
        for fcurve in action.fcurves:
            # Get all compatible fcurves
            dp = fcurve.data_path
            ai = fcurve.array_index

            if dp in export_dp:
                nwname = export_dp[dp][1]
        """

    @staticmethod
    def generateAsciiKeys2(obj, anim, asciiLines):
        """TODO: DOC."""
        exports = [['orientationkey', collections.OrderedDict()],
                   ['positionkey', collections.OrderedDict()],
                   ['scalekey', collections.OrderedDict()],
                   ['selfillumcolorkey', collections.OrderedDict()],
                   ['colorkey', collections.OrderedDict()],
                   ['radiuskey', collections.OrderedDict()],
                   ['alphakey', collections.OrderedDict()]]
        # 1. Object animation data
        if obj.animation_data:
            action = obj.animation_data.action
            if action:
                Animnode.getKeysFromObjAction(action, anim, exports)
        # 2. Material animation data
        if obj.active_material and obj.active_material.animation_data:
            action = obj.active_material.animation_data.action
            if action:
                Animnode.getKeysFromMatAction(action, anim, exports)

        # astart = anim.frameStart
        # rfps = bpy.context.scene.render.fps
        for exp in exports:
            pass  # keys = exp[1]

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

        # Get animation data from object
        if obj.animation_data:
            action = obj.animation_data.action
            if action:
                Animnode.getKeysFromAction(action, anim, keyDict)
        # Get animation data from Material/ texture data (= alpha keys only)
        if obj.active_material and obj.active_material.animation_data:
            action = obj.active_material.animation_data.action
            if action:
                Animnode.getKeysFromAction(action, anim, keyDict)

        animStart = anim.frameStart
        render_fps = bpy.context.scene.render.fps
        kname = 'orientationkey'
        if len(keyDict[kname]) > 0:
            keyList = keyDict[kname]
            if len(keyList) == 1:
                fstr = '    ' + \
                    'orientation {: > 6.5f} {: > 6.5f} {: > 6.5f} {: > 6.5f}'
                key = keyList.popitem()[1]
                eul = mathutils.Euler((key[0], key[1], key[2]), 'XYZ')
                val = nvb_utils.euler2nwangle(eul)
                s = fstr.format(*val)
                asciiLines.append(s)
            else:
                fstr = '      ' + \
                    '{: >6.5f} {: > 6.5f} {: > 6.5f} {: > 6.5f} {: > 6.5f}'
                asciiLines.append('    orientationkey ' + str(len(keyList)))
                for frame, key in keyList.items():
                    time = nvb_utils.frame2nwtime(frame - animStart,
                                                  render_fps)
                    eul = mathutils.Euler((key[0], key[1], key[2]), 'XYZ')
                    val = nvb_utils.euler2nwangle(eul)
                    s = fstr.format(time, *val)
                    asciiLines.append(s)

        kname = 'positionkey'
        if len(keyDict[kname]) > 0:
            keyList = keyDict[kname]
            if len(keyList) == 1:
                fstr = '    position {: > 6.5f} {: > 6.5f} {: > 6.5f}'
                key = keyList.popitem()[1]
                s = fstr.format(key[0], key[1], key[2])
                asciiLines.append(s)
            else:
                fstr = '      ' + \
                    '{: >6.5f} {: > 6.5f} {: > 6.5f} {: > 6.5f}'
                asciiLines.append('    positionkey ' + str(len(keyList)))
                for frame, key in keyList.items():
                    time = nvb_utils.frame2nwtime(frame - animStart,
                                                  render_fps)
                    s = fstr.format(time, key[0], key[1], key[2])
                    asciiLines.append(s)

        kname = 'scalekey'
        if len(keyDict[kname]) > 0:
            keyList = keyDict[kname]
            if len(keyList) == 1:
                fstr = '    scale {: >6.5f}'
                key = keyList.popitem()[1]
                s = fstr.format(key[0])
                asciiLines.append(s)
            else:
                fstr = '      {: >6.5f} {: >6.5f}'
                asciiLines.append('    ' + kname + ' ' + str(len(keyList)))
                for frame, key in keyList.items():
                    time = nvb_utils.frame2nwtime(frame - animStart,
                                                  render_fps)
                    s = fstr.format(time, key[0])
                    asciiLines.append(s)

        kname = 'selfillumcolorkey'
        if len(keyDict[kname]) > 0:
            keyList = keyDict[kname]
            if len(keyList) == 1:
                fstr = '    selfillumcolor {: >3.2f} {: >3.2f} {: >3.2f}'
                key = keyList.popitem()[1]
                s = fstr.format(key[0], key[1], key[2])
                asciiLines.append(s)
            else:
                fstr = '      {: >6.5f} {: > 3.2f} {: > 3.2f} {: > 3.2f}'
                asciiLines.append('    ' + kname + ' ' + str(len(keyList)))
                for frame, key in keyList.items():
                    time = nvb_utils.frame2nwtime(frame - animStart,
                                                  render_fps)
                    s = fstr.format(time, key[0], key[1], key[2])
                    asciiLines.append(s)

        kname = 'colorkey'
        if len(keyDict[kname]) > 0:
            keyList = keyDict[kname]
            asciiLines.append('    ' + kname + ' ' + str(len(keyList)))
            formatStr = '      {: >6.5f} {: >3.2f} {: >3.2f} {: >3.2f}'
            for frame, key in keyList.items():
                time = nvb_utils.frame2nwtime(frame - animStart, render_fps)
                s = formatStr.format(time, key[0], key[1], key[2])
                asciiLines.append(s)

        kname = 'radiuskey'
        if len(keyDict[kname]) > 0:
            keyList = keyDict[kname]
            asciiLines.append('    ' + kname + ' ' + str(len(keyList)))
            formatStr = '      {: >6.5f} {: >6.5f}'
            for frame, key in keyList.items():
                time = nvb_utils.frame2nwtime(frame - animStart, render_fps)
                s = formatStr.format(time, key[0])
                asciiLines.append(s)

        kname = 'alphakey'
        if len(keyDict[kname]) > 0:
            keyList = keyDict[kname]
            asciiLines.append('    ' + kname + ' ' + str(len(keyList)))
            formatStr = '      {: >6.5f} {: >3.2f}'
            for frame, key in keyList.items():
                time = nvb_utils.frame2nwtime(frame - animStart, render_fps)
                s = formatStr.format(time, key[0])
                asciiLines.append(s)

    @staticmethod
    def generateAsciiAnimmeshShapes(obj, anim, asciiLines):
        """Add data for animated vertices."""
        shapekeyname = obj.nvb.aurorashapekey
        if not shapekeyname:
            return
        if not obj.data.shape_keys:
            # No animated vertices here
            return
        if shapekeyname not in obj.data.shape_keys.key_blocks:
            # No animated vertices here
            return
        keyBlock = obj.data.shape_keys.key_blocks[shapekeyname]
        # Original vertex data. Needed to fill in values for unanimated
        # vertices.
        mesh = obj.to_mesh(bpy.context.scene,
                           True,
                           'RENDER')
        # vertexList = mesh.vertices[[f.uv1, f.uv2, f.uv3] for f in tf_uv]
        vertexList = [[v.co[0], v.co[1], v.co[2]] for v in mesh.vertices]
        if obj.data.shape_keys.animation_data:
            # Get the animation data
            action = obj.data.shape_keys.animation_data.action
            if action:
                dpPrefix = 'key_blocks["' + keyBlock.name + '"].data['
                tf = len(dpPrefix)
                samplingStart = anim.frameStart
                samplingEnd = anim.frameEnd
                keys = collections.OrderedDict()  # {frame:values}
                for fcurve in action.fcurves:
                    dp = fcurve.data_path
                    if dp.startswith(dpPrefix):
                        vertexIdx = int(dp[tf:-4])
                        axis = fcurve.array_index
                        kfp = [p for p in fcurve.keyframe_points
                               if anim.frameStart <= p.co[0] <= anim.frameEnd]
                        for p in kfp:
                            frame = int(round(p.co[0]))
                            samplingStart = min(frame, samplingStart)
                            samplingEnd = max(frame, samplingEnd)
                            if frame in keys:
                                values = keys[frame]
                            else:
                                values = copy.deepcopy(vertexList)
                            values[vertexIdx][axis] = p.co[1]
                            keys[frame] = values

                # Create ascii representation and add it to the output
                sumKeys = sum([len(l) for f, l in keys.items()])
                if (sumKeys % len(vertexList) == 0):
                    asciiLines.append('    clipu 0.0')
                    asciiLines.append('    clipv 0.0')
                    asciiLines.append('    clipw 1.0')
                    asciiLines.append('    cliph 1.0')
                    samplePeriod = nvb_utils.frame2nwtime(
                        samplingEnd-samplingStart,
                        bpy.context.scene.render.fps)
                    asciiLines.append('    sampleperiod ' +
                                      str(round(samplePeriod, 5)))
                    asciiLines.append('    animverts ' + str(sumKeys))
                    for frame, key in keys.items():
                        for val in key:
                            formatStr = '      {: 6.3f} {: 6.3f} {: 6.3f}'
                            s = formatStr.format(val[0], val[1], val[2])
                            asciiLines.append(s)
                    asciiLines.append('    endlist')

    @staticmethod
    def generateAsciiAnimmeshUV(obj, anim, asciiLines):
        """Add data for animated texture coordinates."""
        if not obj.active_material:
            return
        if not obj.active_material.active_texture:
            return
        if not obj.data.uv_layers.active:
            return
        # Original uv data. Needed to fill in values for unanimated uv's.
        obj.data.update(calc_tessface=True)
        tf_uv = obj.data.tessface_uv_textures.active.data
        tessfaceUVList = [[f.uv1, f.uv2, f.uv3] for f in tf_uv]
        tessfaceUVList = [[uv.x, uv.y] for f in tessfaceUVList for uv in f]

        if obj.data.animation_data:
            # Get the animation data from the object data
            # (not from the object itself!)
            action = obj.data.animation_data.action
            if action:
                # Get the correct data path
                uvname = obj.data.uv_layers.active.name
                dpPrefix = 'uv_layers["' + uvname + '"].data['
                tf = len(dpPrefix)
                samplingStart = anim.frameStart
                samplingEnd = anim.frameEnd
                keys = collections.OrderedDict()  # {frame:values}
                for fcurve in action.fcurves:
                    dp = fcurve.data_path
                    if dp.startswith(dpPrefix):
                        uvIdx = int(dp[tf:-4])
                        axis = fcurve.array_index
                        kfp = [p for p in fcurve.keyframe_points
                               if anim.frameStart <= p.co[0] <= anim.frameEnd]
                        for p in kfp:
                            frame = int(round(p.co[0]))
                            samplingStart = min(frame, samplingStart)
                            samplingEnd = max(frame, samplingEnd)
                            if frame in keys:
                                values = keys[frame]
                            else:
                                values = copy.deepcopy(tessfaceUVList)
                            values[uvIdx][axis] = p.co[1]
                            keys[frame] = values
                # Create ascii representation and add it to the output
                sumKeys = sum([len(l) for f, l in keys.items()])
                if (sumKeys % len(tessfaceUVList) == 0):
                    asciiLines.append('    clipu 0.0')
                    asciiLines.append('    clipv 0.0')
                    asciiLines.append('    clipw 1.0')
                    asciiLines.append('    cliph 1.0')
                    samplePeriod = nvb_utils.frame2nwtime(
                        samplingEnd-samplingStart,
                        bpy.context.scene.render.fps)
                    asciiLines.append('    sampleperiod ' +
                                      str(round(samplePeriod, 5)))
                    asciiLines.append('    animtverts ' + str(sumKeys))
                    for frame, key in keys.items():
                        for val in key:
                            formatStr = '      {: 6.3f} {: 6.3f}  0'
                            s = formatStr.format(val[0], val[1])
                            asciiLines.append(s)
                    asciiLines.append('    endlist')

    @staticmethod
    def generateAsciiAnimmeshData(obj, anim, asciiLines):
        """TODO:Doc."""
        if not obj.data:
            return
        # Check if the object is an animmesh:
        if (obj.type != 'MESH') or \
           (obj.nvb.meshtype != nvb_def.Meshtype.ANIMMESH):
            return
        options = nvb_def.ExportOptions()
        tmpLines = []
        nvb_node.Animmesh.generateAsciiMesh(obj, tmpLines,
                                            options, True)
        asciiLines.extend(['  '+l for l in tmpLines])
        Animnode.generateAsciiAnimmeshUV(obj, anim, asciiLines)
        Animnode.generateAsciiAnimmeshShapes(obj, anim, asciiLines)

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
        Animnode.generateAsciiAnimmeshData(obj, anim, asciiLines)
        Animnode.generateAsciiRawData(obj, anim, asciiLines)
        Animnode.generateAsciiKeys(obj, anim, asciiLines)
        asciiLines.append('  endnode')
