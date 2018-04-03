"""TODO: DOC."""

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
                elif label == 'position':
                    self.position = [float(v) for v in line[1:4]]
                    self.objdata = True
                elif label == 'positionkey':
                    numkeys = self.findEnd(asciiLines[i+1:])
                    nvb_parse.f4(asciiLines[i+1:i+numkeys+1],
                                 self.positionkey)
                    self.objdata = True
                elif label == 'orientation':
                    self.orientation = [float(v) for v in line[1:5]]
                    self.objdata = True
                elif label == 'orientationkey':
                    numkeys = self.findEnd(asciiLines[i+1:])
                    nvb_parse.f5(asciiLines[i+1:i+numkeys+1],
                                 self.orientationkey)
                    self.objdata = True
                elif label == 'scale':
                    self.scale = l_float(line[1])
                    self.objdata = True
                elif label == 'scalekey':
                    numkeys = self.findEnd(asciiLines[i+1:])
                    nvb_parse.f2(asciiLines[i+1:i+numkeys+1],
                                 self.scalekey)
                    self.objdata = True
                elif label == 'alpha':
                    self.alpha = l_float(line[1])
                    self.matdata = True
                elif label == 'alphakey':
                    # If this is an emitter, alphakeys are incompatible. We'll
                    # handle them later as plain text
                    numkeys = self.findEnd(asciiLines[i+1:])
                    if nodetype == 'emitter':
                        nvb_parse.txt(asciiLines[i:i+numkeys+1],
                                      self.rawdata)
                    else:
                        nvb_parse.f2(asciiLines[i+1:i+numkeys+1],
                                     self.alphakey)
                    self.matdata = True
                elif (label == 'selfillumcolor' or
                      label == 'setfillumcolor'):
                    self.selfillumcolor = [float(v) for v in line[1:4]]
                    self.objdata = True
                elif (label == 'selfillumcolorkey' or
                      label == 'setfillumcolorkey'):
                    numkeys = self.findEnd(asciiLines[i+1:])
                    nvb_parse.f4(asciiLines[i+1:i+numkeys+1],
                                 self.selfillumcolorkey)
                    self.objdata = True
                # Animeshes
                elif label == 'sampleperiod':
                    self.sampleperiod = l_float(line[1])
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
                # Lights/lamps only
                elif label == 'color':
                    self.color = [float(v) for v in line[1:4]]
                    self.objdata = True
                elif label == 'colorkey':
                    numkeys = self.findEnd(asciiLines[i+1:])
                    nvb_parse.f4(asciiLines[i+1:i+numkeys+1], self.colorkey)
                    self.objdata = True
                elif label == 'radius':
                    self.radius = l_float(line[1])
                    self.objdata = True
                elif label == 'radiuskey':
                    numkeys = self.findEnd(asciiLines[i+1:])
                    nvb_parse.f2(asciiLines[i+1:i+numkeys+1], self.radiuskey)
                    self.objdata = True
                # Some unknown label.
                # Probably keys for emitters, incompatible, save as plain text
                elif (nodetype == 'emitter') and (label[0] != '#'):
                    numkeys = self.findEnd(asciiLines[i+1:])
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
        fc = action.fcurves.find(data_path, index)
        if not fc:
            fc = action.fcurves.new(data_path=data_path, index=index)
        return fc

    def createDataMaterial(self, mat, anim, options):
        """TODO: DOC."""
        fps = options.scene.render.fps
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
                frame = fps * key[0] + frameStart
                curve.keyframe_points.insert(frame, key[1])
        elif self.alpha is not None:
            curve.keyframe_points.insert(frameStart, self.alpha)
            curve.keyframe_points.insert(frameEnd, self.alpha)

    def createDataObject(self, obj, anim, options):
        """TODO: DOC."""
        def create_values(frames, values, action, dp, dp_dim):
            """TODO: DOC."""
            if frames and values:
                fcu = [Animnode.getCurve(action, dp, i) for i in range(dp_dim)]
                kfp = [fcu[i].keyframe_points for i in range(dp_dim)]
                nkfp = list(map(lambda x: len(x), kfp))
                list(map(lambda x: x.add(len(values)), kfp))
                for i in range(len(values)):
                    frm = frames[i]
                    val = values[i]
                    for j in range(dp_dim):
                        p = kfp[j][nkfp[j]+i]
                        p.co = frm, val[j]
                        p.interpolation = 'LINEAR'
                list(map(lambda c: c.update(), fcu))

        fps = options.scene.render.fps
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

        if self.orientationkey or self.orientation is not None:
            values = []
            frames = [fps * k[0] + frameStart for k in self.orientationkey]
            # Set up animation
            if options.rotmode == 'AXIS_ANGLE':
                dp = 'rotation_axis_angle'
                dp_dim = 4
                if frames:  # Keyed animation
                    values = [[k[4], k[1], k[2], k[3]]
                              for k in self.orientationkey]
                else:  # "Static" animation (single value)
                    v = self.orientation
                    frames.append(frameStart)
                    values.append([v[3], v[0], v[1], v[2]])
                    if frameStart < frameEnd:
                        frames.append(frameEnd)
                        values.append([v[3], v[0], v[1], v[2]])
            elif options.rotmode == 'QUATERNION':
                dp = 'rotation_quaternion'
                dp_dim = 4
                if frames:  # Keyed animation
                    quats = [mathutils.Quaternion(k[1:4], k[4])
                             for k in self.orientationkey]
                    values = [[q.w, q.x, q.y, q.z] for q in quats]
                else:  # "Static" animation (single value)
                    v = mathutils.Quaternion(
                        self.orientation[:3], self.orientation[3])
                    frames.append(frameStart)
                    values.append([v.w, v.x, v.y, v.z])
                    if frameStart < frameEnd:
                        frames.append(frameEnd)
                        values.append([v.w, v.x, v.y, v.z])
            else:
                dp = 'rotation_euler'
                dp_dim = 3
                if frames:  # Keyed animation
                    # Run an euler filer
                    prev_eul = 0
                    for k in self.orientationkey:
                        eul = nvb_utils.eulerFilter(
                            nvb_utils.nwangle2euler(k[1:5]), prev_eul)
                        values.append(eul)
                        prev_eul = eul
                else:  # "Static" animation (single value)
                    v = nvb_utils.nwangle2euler(self.orientation)
                    frames.append(frameStart)
                    values.append(v)
                    if frameEnd > frameStart:
                        frames.append(frameEnd)
                        values.append(v)
            # Generate animation
            create_values(frames, values, action, dp, dp_dim)

        if self.positionkey or self.position is not None:
            values = []
            frames = [fps * k[0] + frameStart for k in self.positionkey]
            dp = 'location'
            dp_dim = 3
            if frames:  # Keyed animation
                values = [k[1:4] for k in self.positionkey]
            else:  # "Static" animation (single value)
                v = self.position
                frames.append(frameStart)
                values.append(v)
                if frameEnd > frameStart:
                    frames.append(frameEnd)
                    values.append(v)
            create_values(frames, values, action, dp, dp_dim)

        if self.scalekey or self.scale is not None:
            values = []
            frames = [fps * k[0] + frameStart for k in self.scalekey]
            dp = 'scale'
            dp_dim = 3  # but only a single value in mdl
            if frames:  # Keyed animation
                values = [[k] * dp_dim for k in self.scalekey]
            else:  # "Static" animation (single value)
                v = [self.scale] * dp_dim
                frames.append(frameStart)
                values.append(v)
                if frameEnd > frameStart:
                    frames.append(frameEnd)
                    values.append(v)
            create_values(frames, values, action, dp, dp_dim)

        if self.selfillumcolorkey or self.selfillumcolor is not None:
            values = []
            frames = [fps * k[0] + frameStart for k in self.selfillumcolorkey]
            dp = 'nvb.selfillumcolor'
            dp_dim = 3
            if frames:  # Keyed animation
                values = [k for k in self.selfillumcolorkey]
            else:  # "Static" animation (single value)
                v = self.selfillumcolor
                frames.append(frameStart)
                values.append(v)
                if frameEnd > frameStart:
                    frames.append(frameEnd)
                    values.append(v)
            create_values(frames, values, action, dp, dp_dim)

        if self.colorkey or self.color is not None:
            values = []
            frames = [fps * k[0] + frameStart for k in self.colorkey]
            dp = 'color'
            dp_dim = 3
            if frames:  # Keyed animation
                values = [k for k in self.colorkey]
            else:  # "Static" animation (single value)
                v = self.color
                frames.append(frameStart)
                values.append(v)
                if frameEnd > frameStart:
                    frames.append(frameEnd)
                    values.append(v)
            create_values(frames, values, action, dp, dp_dim)

        if self.radiuskey or self.radius is not None:
            values = []
            frames = [fps * k[0] + frameStart for k in self.radiuskey]
            dp = 'distance'
            dp_dim = 1
            if frames:  # Keyed animation
                values = [k for k in self.radiuskey]
            else:  # "Static" animation (single value)
                v = self.radius
                frames.append(frameStart)
                values.append(v)
                if frameEnd > frameStart:
                    frames.append(frameEnd)
                    values.append(v)
            create_values(frames, values, action, dp, dp_dim)

    def createDataRaw(self, obj, anim, options):
        """Add incompatible animations (usually emitters) as plain text."""
        # Get or create the text object
        fps = options.scene.render.fps
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
                    frame = fps * float(key[0])
                    values = [float(v) for v in key[1:]]
                    formatStr = '    {: >4d}' + \
                                ' '.join(['{: > 8.5f}']*len(values)) + '\n'
                    s = formatStr.format(frame, *values)
                    txt.write(s)
            else:
                # Single unknown value
                txt.write('  ' + ' '.join(label) + '\n')
        txt.write('endnode\n')

    def createDataShape(self, obj, anim, animlength, options):
        """Import animated vertices as shapekeys."""
        fps = options.scene.render.fps
        if not obj.data:
            return
        # Sanity check: Sample period can't be 0
        if self.sampleperiod <= 0.00001:
            return
        # Sanity check: animation length has to be a multiple of
        #               sampleperiod
        if animlength % self.sampleperiod > 0.0:
            return
        numSamples = int(animlength / self.sampleperiod) + 1
        print(numSamples)
        # Sanity check: Number of animtverts = number verts * numSamples
        numVerts = len(obj.data.vertices)
        print(numVerts)
        print(len(self.animverts))
        if (len(self.animverts) != numVerts * numSamples):
            print("Neverblender: WARNING - animvert sample size mismatch: " +
                  obj.name)
            return
        sampleDistance = nvb_utils.nwtime2frame(self.sampleperiod, fps)
        # Get the shape key name
        if obj.nvb.aurorashapekey:
            shapekeyname = obj.nvb.aurorashapekey
        else:
            shapekeyname = nvb_def.shapekeyname
        # Create a basis shapekey
        obj.shape_key_add(name='basis', from_mix=False)
        # Get or create the shape key to hold the animation
        if obj.data.shape_keys and \
           shapekeyname in obj.data.shape_keys.key_blocks:
            keyBlock = obj.data.shape_keys.key_blocks[shapekeyname]
        else:
            keyBlock = obj.shape_key_add(name=shapekeyname,
                                         from_mix=False)
            keyBlock.value = 1.0
            obj.active_shape_key_index = 1
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

    def createDataUV(self, obj, anim, animlength, options):
        """Import animated texture coordinates."""
        fps = options.scene.render.fps
        if not obj.data:
            return
        if not obj.data.uv_layers.active:
            return
        uvlayer = obj.data.uv_layers.active
        # Check if the original uv/tvert order was saved
        if obj.data.name not in nvb_def.tvert_order:
            return
        tvert_order = [v for sl in nvb_def.tvert_order[obj.data.name]
                       for v in sl]
        # Sanity check: Sample period can't be 0
        if self.sampleperiod <= 0.00001:
            return
        # Sanity check: animation length has to be a multiple of
        #               sampleperiod
        if animlength % self.sampleperiod > 0.0:
            return
        numSamples = int(animlength / self.sampleperiod) + 1
        # Sanity check: Number of animtverts = number tverts * numSamples
        numTVerts = len(tvert_order)
        if (len(self.animtverts) != numTVerts * numSamples):
            print("Neverblender: WARNING - animtvert sample size mismatch: " +
                  obj.name)
            return
        sampleDistance = nvb_utils.nwtime2frame(self.sampleperiod, fps)

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
        for uvIdx, tvertIdx in enumerate(tvert_order):
            dp = dpPrefix + str(uvIdx) + '].uv'
            curveU = Animnode.getCurve(action, dp, 0)
            curveV = Animnode.getCurve(action, dp, 1)
            samples = self.animtverts[tvertIdx::numTVerts]
            for sampleIdx, co in enumerate(samples):
                frame = frameStart + (sampleIdx * sampleDistance)
                curveU.keyframe_points.insert(frame, co[0], kfOptions)
                curveV.keyframe_points.insert(frame, co[1], kfOptions)

    @staticmethod
    def createRestPose(obj, frame=1):
        """TODO: DOC."""

        def insert_kfp(fcurves, frame, val, dim):
            """TODO: DOC."""
            for j in range(dim):
                fcurves[j].keyframe_points.insert(frame, val[j], {'FAST'})
        # Get animation data
        animData = obj.animation_data
        if not animData:
            return  # No data = no animation = no need for rest pose
        # Get action
        action = animData.action
        if not action:
            return  # No action = no animation = no need for rest pose
        if obj.rotation_mode == 'AXIS_ANGLE':
            dp = 'rotation_axis_angle'
            fcu = [action.fcurves.find(dp, i) for i in range(4)]
            if fcu.count(None) < 1:
                rr = obj.nvb.restrot
                insert_kfp(fcu, frame, [rr[3], rr[0], rr[1], rr[2]], 4)
        if obj.rotation_mode == 'QUATERNION':
            dp = 'rotation_quaternion'
            fcu = [action.fcurves.find(dp, i) for i in range(4)]
            if fcu.count(None) < 1:
                rr = obj.nvb.restrot
                q = mathutils.Quaternion((rr[0], rr[1], rr[2]), rr[3])
                insert_kfp(fcu, frame, [q.w, q.x, q.y, q.z], 4)
        else:
            dp = 'rotation_euler'
            fcu = [action.fcurves.find(dp, i) for i in range(3)]
            if fcu.count(None) < 1:
                eul = nvb_utils.nwangle2euler(obj.nvb.restrot)
                insert_kfp(fcu, frame, eul, 3)
        fcu = [action.fcurves.find('location', i) for i in range(3)]
        if fcu.count(None) < 1:
            insert_kfp(fcu, frame, obj.nvb.restloc, 3)

    def create(self, obj, anim, animlength, options):
        """TODO:Doc."""
        if self.objdata:
            self.createDataObject(obj, anim, options)
        if self.matdata and obj.active_material:
            self.createDataMaterial(obj.active_material, anim, options)
        if self.uvdata:
            self.createDataUV(obj, anim, animlength, options)
        if self.shapedata:
            self.createDataShape(obj, anim, animlength, options)
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
    def generateAsciiRawData(obj, anim, asciiLines, options):
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
        fps = options.scene.render.fps
        for line in [l.strip().split() for l in txtLines]:
            try:
                label = line[0].lower()
            except IndexError:
                continue
            # Lines starting with numbers are keys
            if l_isNumber(label):
                frame = float(label)
                nwtime = round(nvb_utils.frame2nwtime(frame, fps), 5)
                values = [float(v) for v in line[1:]]
                formatStr = '      {: >6.5f}' + \
                            ' '.join(['{: > 6.5f}']*len(values))
                s = formatStr.format(nwtime, *values)
                asciiLines.append(s)
            else:
                asciiLines.append('    ' + ' '.join(line))

    @staticmethod
    def getKeysMaterial(mat, anim, key_data, options):
        """TODO: DOC."""
        action = mat.animation_data.action
        if not action:
            return
        # Build data paths
        exports = [['ambient', 3, ' {: >3.2f}', 3, 'nvb.ambient_color']]
        # Aplha can be animated with the following data paths
        # 1. 'texture_slots[X].alpha_factor' - which is texture slot alpha
        # 2. 'alpha' - which is material alpha
        # We only want one of those, alpha_factor takes precendence
        dp_alpha_factor = [fc.data_path for fc in action.fcurves
                           if fc.data_path.endswith('.alpha_factor')]
        if dp_alpha_factor:
            exports.append(['alpha', 1, ' {: >3.2f}', dp_alpha_factor[0]])
        else:
            exports.append(['alpha', 1, ' {: >3.2f}', 'alpha'])
        fps = options.scene.render.fps
        # Get keyframe data
        fcurves = action.fcurves
        for key_name, val_dim, val_fstr, dp_dim, dp in exports:
            fcu = [fcurves.find(dp, i) for i in range(dp_dim)]
            frames = list(set().union(
                *[[k.co[0] for k in fcu[i].keyframe_points]
                  for i in range(dp_dim)]))
            frames.sort()
            values = [[fcu[i].evaluate(f) for i in range(dp_dim)]
                      for f in frames]
            times = [nvb_utils.frame2nwtime(f, fps) for f in frames]
            keys = list(zip(times, values))
            key_data.append([key_name, keys, val_dim * val_fstr])

    @staticmethod
    def getKeysObject(obj, anim, key_data, options):
        """TODO: DOC."""
        def convert_loc(obj, key_values):
            pass

        def convert_eul(obj, key_values):
            pass

        def convert_axan(obj, key_values):
            pass

        def convert_quat(obj, key_values):
            pass

        action = obj.animation_data.action
        if not action:
            return
        # Build data paths
        exports = [
            ['scale', 1, ' {: > 6.5f}', 1, 'scale', None],
            ['selfillumcolor', 3, ' {: >3.2f}', 3, 'nvb.selfillumcolor', None],
            ['color', 3, ' {: >3.2f}', 3, 'color', None],
            ['radius', 1, ' {: >6.5f}', 1, 'distance', None],
            ['position', 3, ' {: > 6.5f}', 3, 'location', convert_loc]]
        if obj.rotation_mode == 'AXIS_ANGLE':
            exports.append(['orientation', 4, ' {: > 6.5f}',
                            4, 'rotation_axis_angle', convert_axan])
        elif obj.rotation_mode == 'QUATERNION':
            exports.append(['orientation', 4, ' {: > 6.5f}',
                            4, 'rotation_quaternion', convert_quat])
        else:
            exports.append(['orientation', 4, ' {: > 6.5f}',
                            4, 'rotation_euler', convert_eul])
        fps = options.scene.render.fps
        # Get keyframe data
        fcurves = action.fcurves
        for key_name, val_dim, val_fstr, dp_dim, dp, convert_func in exports:
            fcu = [fcurves.find(dp, i) for i in range(dp_dim)]
            if fcu.count(None) < 1:
                # Get keyed frames
                frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points]
                      for i in range(dp_dim)]))
                frames.sort()
                # Get values at keyed frames and convert
                values = [[fcu[i].evaluate(f) for i in range(dp_dim)]
                          for f in frames]
                if convert_func is not None:
                    convert_func(obj, values)
                times = [nvb_utils.frame2nwtime(f, fps) for f in frames]
                keys = list(zip(times, values))
                key_data.append([key_name, keys, val_dim * val_fstr])
        """
        # Add rotation keys, depending on object rotation mode
        keys = []
        if obj.rotation_mode == 'AXIS_ANGLE':
            dp_dim = 4
            fcu = [fcurves.find('rotation_axis_angle', i)
                   for i in range(dp_dim)]
            if fcu.count(None) < 1:
                keyed_frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points]
                      for i in range(dp_dim)]))
                keyed_frames.sort()
                keys = [[f, *[fcu[i].evaluate(f) for i in range(dp_dim)]]
                        for f in keyed_frames]
                # Apply parent_inverse
        elif obj.rotation_mode == 'QUATERNION':
            dp_dim = 4
            fcu = [fcurves.find('rotation_quaternion', i)
                   for i in range(dp_dim)]
            if fcu.count(None) < 1:
                keyed_frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points]
                      for i in range(dp_dim)]))
                keyed_frames.sort()
                keys = [[f, *[fcu[i].evaluate(f) for i in range(dp_dim)]]
                        for f in keyed_frames]
                # Apply parent_inverse
        else:  # Rotation Mode == Euler ('XYZ', 'YXZ', ...)
            dp_dim = 3
            fcu = [fcurves.find('rotation_euler', i)
                   for i in range(dp_dim)]
            if fcu.count(None) < 1:
                keyed_frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points]
                      for i in range(dp_dim)]))
                keyed_frames.sort()
                keys = [[f, *[fcu[i].evaluate(f) for i in range(dp_dim)]]
                        for f in keyed_frames]
                # Apply parent_inverse
        # Convert to nwn axis angle
        # TODO
        key_data.append(['orientation', keys, 4 * ' {: > 6.5f}'])
        # Add location keys and apply parent_inverse
        dp_dim = 3
        fcu = [fcurves.find('location', i) for i in range(dp_dim)]
        if fcu:
            keyed_frames = \
                list(set().union(*[[k.co[0] for k in fcu[i].keyframe_points]
                                   for i in range(dp_dim)]))
            keyed_frames.sort()
            keys = [[f, *[fcu[i].evaluate(f) for i in range(dp_dim)]]
                    for f in keyed_frames]
            # Apply parent_inverse
            key_data.append(['position', keys, 3 * ' {: > 6.5f}'])
        """

    @staticmethod
    def generateAsciiKeys2(obj, anim, asciiLines, options):
        """TODO: DOC."""
        kdata = []
        # 1. Object animation data
        if obj.animation_data:
            Animnode.getKeysObject(obj, anim, kdata, options)
        # 2. Material animation data
        if obj.active_material and obj.active_material.animation_data:
            Animnode.getKeysMaterial(obj.active_material, anim, kdata, options)
        # Add keys to ascii lines
        time_fstr = '{: >6.5f}'
        for key_name, keys, val_fstr in kdata:
            num_keys = len(keys)
            if num_keys > 1:
                # Create a key list
                asciiLines.append('    ' + key_name + 'key ' + str(num_keys))
                fstr = '      ' + time_fstr + val_fstr
                asciiLines.extend([fstr.format(*k) for k in keys])
            elif num_keys == 1:
                # Create only a single value
                fstr = '    ' + key_name + val_fstr
                asciiLines.append(fstr.format(*keys[0]))

    @staticmethod
    def generateAsciiKeys(obj, anim, asciiLines, options):
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
        # Adjust coordinates, remove parent inverse
        # mat_pinv = obj.matrix_parent_inverse
        # Cache values for speed
        animStart = anim.frameStart
        fps = options.scene.render.fps
        # Rotation
        keyList = keyDict['orientationkey']
        if len(keyList) == 1:
            fstr = '    ' + \
                'orientation {: > 6.5f} {: > 6.5f} {: > 6.5f} {: > 6.5f}'
            key = keyList.popitem()[1]
            eul = mathutils.Euler((key[0], key[1], key[2]), 'XYZ')
            val = nvb_utils.euler2nwangle(eul)
            asciiLines.append(fstr.format(*val))
        elif len(keyList) > 1:
            asciiLines.append('    orientationkey ' + str(len(keyList)))
            fstr = '      ' + \
                '{: >6.5f} {: > 6.5f} {: > 6.5f} {: > 6.5f} {: > 6.5f}'
            for frame, key in keyList.items():
                time = nvb_utils.frame2nwtime(frame - animStart, fps)
                eul = mathutils.Euler((key[0], key[1], key[2]), 'XYZ')
                val = nvb_utils.euler2nwangle(eul)
                asciiLines.append(fstr.format(time, *val))
        # Location
        keyList = keyDict['positionkey']
        if len(keyList) == 1:
            fstr = '    position {: > 6.5f} {: > 6.5f} {: > 6.5f}'
            key = keyList.popitem()[1]
            s = fstr.format(key[0], key[1], key[2])
            asciiLines.append(s)
        elif len(keyList) > 1:
            asciiLines.append('    positionkey ' + str(len(keyList)))
            fstr = '      {: >6.5f} {: > 6.5f} {: > 6.5f} {: > 6.5f}'
            for frame, key in keyList.items():
                time = nvb_utils.frame2nwtime(frame - animStart, fps)
                asciiLines.append(fstr.format(time, key[0], key[1], key[2]))
        # Scale
        keyList = keyDict['scalekey']
        if len(keyList) == 1:
            fstr = '    scale {: >6.5f}'
            key = keyList.popitem()[1]
            asciiLines.append(fstr.format(key[0]))
        elif len(keyList) > 1:
            asciiLines.append('    scalekey ' + str(len(keyList)))
            fstr = '      {: >6.5f} {: >6.5f}'
            for frame, key in keyList.items():
                time = nvb_utils.frame2nwtime(frame - animStart, fps)
                asciiLines.append(fstr.format(time, key[0]))
        # Self illumination color
        keyList = keyDict['selfillumcolorkey']
        if len(keyList) == 1:
            fstr = '    selfillumcolor {: >3.2f} {: >3.2f} {: >3.2f}'
            key = keyList.popitem()[1]
            asciiLines.append(fstr.format(key[0], key[1], key[2]))
        elif len(keyList) > 1:
            asciiLines.append('    selfillumcolorkey ' + str(len(keyList)))
            fstr = '      {: >6.5f} {: > 3.2f} {: > 3.2f} {: > 3.2f}'
            for frame, key in keyList.items():
                time = nvb_utils.frame2nwtime(frame - animStart, fps)
                asciiLines.append(fstr.format(time, key[0], key[1], key[2]))
        # Lamp color
        keyList = keyDict['colorkey']
        if len(keyList) == 1:
            fstr = '    color {: >3.2f} {: >3.2f} {: >3.2f}'
            key = keyList.popitem()[1]
            asciiLines.append(fstr.format(key[0], key[1], key[2]))
        elif len(keyList) > 1:
            asciiLines.append('    colorkey ' + str(len(keyList)))
            fstr = '      {: >6.5f} {: >3.2f} {: >3.2f} {: >3.2f}'
            for frame, key in keyList.items():
                time = nvb_utils.frame2nwtime(frame - animStart, fps)
                asciiLines.append(fstr.format(time, key[0], key[1], key[2]))
        # Lamp radius
        keyList = keyDict['radiuskey']
        if len(keyList) == 1:
            fstr = '    radius {: >6.5f}'
            key = keyList.popitem()[1]
            asciiLines.append(fstr.format(key[0]))
        elif len(keyList) > 1:
            asciiLines.append('    radiuskey ' + str(len(keyList)))
            fstr = '      {: >6.5f} {: >6.5f}'
            for frame, key in keyList.items():
                time = nvb_utils.frame2nwtime(frame - animStart, fps)
                asciiLines.append(fstr.format(time, key[0]))
        # Alpha value
        keyList = keyDict['alphakey']
        if len(keyList) == 1:
            fstr = '    alpha {: >3.2f}'
            key = keyList.popitem()[1]
            asciiLines.append(fstr.format(key[0]))
        elif len(keyList) > 1:
            asciiLines.append('    alphakey ' + str(len(keyList)))
            fstr = '      {: >6.5f} {: >3.2f}'
            for frame, key in keyList.items():
                time = nvb_utils.frame2nwtime(frame - animStart, fps)
                asciiLines.append(fstr.format(time, key[0]))

    @staticmethod
    def generateAsciiAnimeshShapes(obj, anim, asciiLines, options,
                                   numAnimUVs=0):
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
        mesh = obj.to_mesh(options.scene,
                           options.applyModifiers,
                           options.meshConvert)
        # Cache values for speed
        animStart = anim.frameStart
        animEnd = anim.frameEnd
        fps = options.scene.render.fps
        vertexList = [[v.co[0], v.co[1], v.co[2]] for v in mesh.vertices]
        if obj.data.shape_keys.animation_data:
            # Get the animation data
            action = obj.data.shape_keys.animation_data.action
            if action:
                dpPrefix = 'key_blocks["' + keyBlock.name + '"].data['
                tf = len(dpPrefix)
                keys = collections.OrderedDict()  # {frame:values}
                for fcurve in action.fcurves:
                    dp = fcurve.data_path
                    if dp.startswith(dpPrefix):
                        vertexIdx = int(dp[tf:-4])
                        axis = fcurve.array_index
                        kfp = [p for p in fcurve.keyframe_points
                               if animStart <= p.co[0] <= animEnd]
                        for p in kfp:
                            frame = int(round(p.co[0]))
                            if frame in keys:
                                values = keys[frame]
                            else:
                                values = copy.deepcopy(vertexList)
                            values[vertexIdx][axis] = p.co[1]
                            keys[frame] = values
                # Misc data
                numVerts = len(vertexList)
                numAnimVerts = sum([len(l) for _, l in keys.items()])
                if numAnimUVs > 0:
                    numSamples = min(numAnimUVs, len(keys))
                    # Sanity check
                    if numAnimVerts != numSamples * numVerts:
                        print("Neverblender: " +
                              "WARNING - anim verts/tverts mismatch: " +
                              obj.name + " (using min value)")
                    # We can recover from here, but results may be wrong
                else:
                    numSamples = len(keys)
                    # Sanity check
                    if numAnimVerts != numSamples * numVerts:
                        print("Neverblender: " +
                              "WARNING - animvert sample size mismatch: " +
                              obj.name)
                        return
                    animlength = nvb_utils.frame2nwtime(animEnd-animStart, fps)
                    sampleperiod = animlength / (numSamples-1)
                    # Add some meta data
                    asciiLines.append('    sampleperiod ' +
                                      str(round(sampleperiod, 5)))
                # Create ascii representation and add it to the output
                asciiLines.append('    animverts ' + str(numAnimVerts))
                for frame, key in keys.items():
                    fstr = '      {: 6.3f} {: 6.3f} {: 6.3f}'
                    asciiLines.extend([fstr.format(*v) for v in key])
                asciiLines.append('    endlist')
                return numSamples
        return -1

    @staticmethod
    def generateAsciiAnimeshUV(obj, anim, asciiLines, options, numAnimVerts=0):
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
        # Cache values for speed
        animStart = anim.frameStart
        animEnd = anim.frameEnd
        fps = options.scene.render.fps
        if obj.data.animation_data:
            # Get the animation data from the object data
            # (not from the object itself!)
            action = obj.data.animation_data.action
            if action:
                # Get the correct data path
                uvname = obj.data.uv_layers.active.name
                dpPrefix = 'uv_layers["' + uvname + '"].data['
                tf = len(dpPrefix)
                keys = collections.OrderedDict()  # {frame:values}
                for fcurve in action.fcurves:
                    dp = fcurve.data_path
                    if dp.startswith(dpPrefix):
                        uvIdx = int(dp[tf:-4])
                        axis = fcurve.array_index
                        kfp = [p for p in fcurve.keyframe_points
                               if animStart <= p.co[0] <= animEnd]
                        for p in kfp:
                            frame = int(round(p.co[0]))
                            if frame in keys:
                                values = keys[frame]
                            else:
                                values = copy.deepcopy(tessfaceUVList)
                            values[uvIdx][axis] = p.co[1]
                            keys[frame] = values
                # Misc data for export
                numUVs = len(tessfaceUVList)
                numAnimUVs = sum([len(l) for f, l in keys.items()])
                if numAnimVerts > 0:
                    numSamples = min(numAnimVerts, len(keys))
                    # Sanity check
                    if numAnimUVs != numSamples * numUVs:
                        print("Neverblender: " +
                              "WARNING - anim verts/tverts mismatch: " +
                              obj.name + " (using default min value)")
                    # We can recover from here, but results may be wrong
                else:
                    numSamples = len(keys)
                    # Sanity check
                    if numAnimUVs != numSamples * numUVs:
                        print("Neverblender: " +
                              "WARNING - animvert sample size mismatch: " +
                              obj.name)
                        return
                    animlength = nvb_utils.frame2nwtime(animEnd-animStart, fps)
                    sampleperiod = animlength / (numSamples-1)
                    # Add meta data
                    asciiLines.append('    sampleperiod ' +
                                      str(round(sampleperiod, 5)))
                # Create ascii representation and add it to the output
                asciiLines.append('    animtverts ' + str(numAnimUVs))
                for frame, key in keys.items():
                    fstr = '      {: 6.3f} {: 6.3f}  0'
                    asciiLines.extend([fstr.format(*v) for v in key])
                asciiLines.append('    endlist')
                return numSamples
        return -1

    @staticmethod
    def generateAsciiAnimmesh(obj, anim, asciiLines, options):
        """TODO:Doc."""
        if not obj.data:
            return
        # Check if the object is an animmesh:
        if (obj.type != 'MESH') or \
           (obj.nvb.meshtype != nvb_def.Meshtype.ANIMMESH):
            return
        tmpLines = []
        nvb_node.Animmesh.generateAsciiMesh(obj, tmpLines,
                                            options, True)
        asciiLines.extend(['  '+l for l in tmpLines])
        maxsamples = -1  # Samples > 0 also means not to write metadata (again)
        maxsamples = Animnode.generateAsciiAnimeshUV(obj, anim, asciiLines,
                                                     options, maxsamples)
        Animnode.generateAsciiAnimeshShapes(obj, anim, asciiLines,
                                            options, maxsamples)

    @staticmethod
    def generateAscii(obj, anim, asciiLines, options):
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
        Animnode.generateAsciiAnimmesh(obj, anim, asciiLines, options)
        Animnode.generateAsciiRawData(obj, anim, asciiLines, options)
        Animnode.generateAsciiKeys(obj, anim, asciiLines, options)
        asciiLines.append('  endnode')
