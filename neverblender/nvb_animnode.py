"""TODO: DOC."""

import mathutils
import collections
import copy
import bpy

from . import nvb_def
from . import nvb_utils
from . import nvb_node


class Animnode():
    """TODO: DOC."""

    # Keys that go into particle system settings
    emitter_properties = nvb_node.Emitter.property_dict
    # Keys that go directly into objects
    object_properties = {'position': ('location', 3, float,
                                      ' {:>4.2f}'),
                         'orientation': ('', 4, float,  # Needs conversion
                                         ' {:>4.2f}'),
                         'scale': ('', 1, float,  # Needs conversion
                                   ' {:>4.2f}'),
                         'color': ('color', 3, float,
                                   ' {:>4.2f}'),
                         'radius': ('distance', 1, float,
                                    ' {:>4.2f}'),
                         'selfillumcolor': ('nvb.selfillumcolor', 3, float,
                                            ' {:>4.2f}'),
                         'setfillumcolor': ('nvb.selfillumcolor', 3, float,
                                            ' {:>4.2f}')}
    # Keys that go into materials
    material_properties = {'alpha': ('', 1, float,  # Needs conversion
                                     ' {:>4.2f}')}

    def __init__(self, name='UNNAMED'):
        """TODO: DOC."""
        self.nodeidx = -1
        self.nodetype = nvb_def.Nodetype.DUMMY
        self.name = name
        self.parent = nvb_def.null

        self.emitter_data = dict()
        self.material_data = dict()
        self.object_data = dict()

        # Animesh Data
        self.sampleperiod = 0.0
        self.animtverts = []
        self.animverts = []

        self.uvdata = False  # Animmesh, uv animations present
        self.shapedata = False  # Animmesh, vertex animations present

    def __bool__(self):
        """Return false if the node is empty, i.e. no anims attached."""
        return self.object_data or self.material_data or self.emitter_data

    @staticmethod
    def insert_kfp(frames, values, action, dp, dp_dim):
        """TODO: DOC."""
        if frames and values:
            fcu = [nvb_utils.get_fcurve(action, dp, i) for i in range(dp_dim)]
            kfp = [fcu[i].keyframe_points for i in range(dp_dim)]
            kfp_cnt = list(map(lambda x: len(x), kfp))
            list(map(lambda x: x.add(len(values)), kfp))
            for i, (frm, val) in enumerate(zip(frames, values)):
                for d in range(dp_dim):
                    p = kfp[d][kfp_cnt[d]+i]
                    p.co = frm, val[d]
                    p.interpolation = 'LINEAR'
            list(map(lambda c: c.update(), fcu))

    def load_ascii(self, ascii_lines, nodeidx=-1):
        """TODO: DOC."""
        def find_end(ascii_lines):
            """Find the end of a key list.

            We don't know when a list of keys of keys will end. We'll have to
            search for the first non-numeric value
            """
            l_isNumber = nvb_utils.isNumber
            return next((i for i, v in enumerate(ascii_lines)
                         if not l_isNumber(v[0])), -1)

        self.nodeidx = nodeidx
        properties_list = [  # For easier parsing
            [type(self).emitter_properties, self.emitter_data],
            [type(self).material_properties, self.material_data],
            [type(self).object_properties, self.object_data]]
        l_isNumber = nvb_utils.isNumber
        for i, line in enumerate(ascii_lines):
            try:
                label = line[0].lower()
            except (IndexError, AttributeError):
                continue  # Probably empty line, skip it
            else:
                if l_isNumber(label):
                    continue
            if label == 'node':
                self.nodetype = line[1].lower()
                self.name = nvb_utils.str2identifier(line[2])
            elif label == 'endnode':
                return
            elif label == 'parent':
                self.parentName = nvb_utils.str2identifier(line[1])
            # Animeshes
            elif label == 'sampleperiod':
                self.sampleperiod = float(line[1])
            elif label == 'animverts':
                if not self.animverts:
                    valcnt = int(line[1])
                    self.animverts = [list(map(float, v))
                                      for v in ascii_lines[i+1:i+valcnt+1]]
                    self.shapedata = True
            elif label == 'animtverts':
                if not self.animtverts:
                    valcnt = int(line[1])
                    self.animtverts = [list(map(float, v))
                                       for v in ascii_lines[i+1:i+valcnt+1]]
                    self.uvdata = True
            else:  # Check for keys
                key_name = label
                key_is_single = True
                if key_name.endswith('key'):
                    key_is_single = False
                    key_name = key_name[:-3]
                for key_def, key_data in properties_list:
                    if key_name in key_def and key_name not in key_data:
                        data_path = key_def[key_name][0]
                        data_dim = key_def[key_name][1]
                        # key_converter = key_def[key_name][2]
                        if key_is_single:
                            data = [[0.0] + list(map(float,
                                    line[1:data_dim+1]))]
                        else:
                            keycnt = find_end(ascii_lines[i+1:])
                            data = [list(map(float, v[:data_dim+1]))
                                    for v in ascii_lines[i+1:i+keycnt+1]]
                        # values = \
                        # [[float(v[0])] + list(map(key_converter, v[1:]))
                        #  for v in values]
                        key_data[key_name] = [data, data_path, data_dim]
                        break

    def create_data_material(self, obj, anim, options):
        """Creates animations in material actions."""

        def data_conversion(label, mat, vals):
            if label == 'alpha':
                if mat.active_texture:
                    # Material has a texture
                    tslotIdx = mat.active_texture_index
                    dp = 'texture_slots[' + str(tslotIdx) + '].alpha_factor'
                    dp_dim = 1
                else:
                    # No texture
                    dp = 'alpha'
                    dp_dim = 1
            return vals, dp, dp_dim

        mat = obj.active_material
        if not mat:
            return
        fps = options.scene.render.fps
        frame_start = anim.frameStart
        action = nvb_utils.get_action(mat, mat.name)
        for label, (data, data_path, data_dim) in self.material_data.items():
            frames = [fps * d[0] + frame_start for d in data]
            if not data_path:  # Needs conversion
                values, dp, dp_dim = data_conversion(
                    label, mat, [d[1:data_dim+1] for d in data])
            else:
                values = [d[1:data_dim+1] for d in data]
                dp = data_path
                dp_dim = data_dim
            Animnode.insert_kfp(frames, values, action, dp, dp_dim)

    def create_data_object(self, obj, anim, options):
        """Creates animations in object actions."""
        def data_conversion(label, obj, vals):
            if label == 'orientation':
                if obj.rotation_mode == 'AXIS_ANGLE':
                    dp = 'rotation_axis_angle'
                    dp_dim = 4
                    new_values = [[v[3], v[0], v[1], v[2]] for v in vals]
                elif obj.rotation_mode == 'QUATERNION':
                    dp = 'rotation_quaternion'
                    dp_dim = 4
                    quats = [mathutils.Quaternion(v[0:3], v[3]) for v in vals]
                    new_values = [[q.w, q.x, q.y, q.z] for q in quats]
                else:
                    dp = 'rotation_euler'
                    dp_dim = 3
                    # Run an euler filer
                    prev_eul = mathutils.Euler()
                    new_values = []
                    for v in vals:
                        quat = mathutils.Quaternion(v[0:3], v[3])
                        eul = quat.to_euler('XYZ', prev_eul)
                        #  eul = nvb_utils.eulerFilter(quat.to_euler(),
                        #  prev_eul)
                        new_values.append(eul)
                        prev_eul = eul
            elif label == 'scale':
                dp = 'scale'
                dp_dim = 3
                new_values = [[v] * dp_dim for v in vals]
            return new_values, dp, dp_dim

        fps = options.scene.render.fps
        frame_start = anim.frameStart
        action = nvb_utils.get_action(obj, obj.name)
        for label, (data, data_path, data_dim) in self.object_data.items():
            frames = [fps * d[0] + frame_start for d in data]
            if not data_path:  # Needs conversion
                values, dp, dp_dim = data_conversion(
                    label, obj, [d[1:data_dim+1] for d in data])
            else:
                values = [d[1:data_dim+1] for d in data]
                dp = data_path
                dp_dim = data_dim
            Animnode.insert_kfp(frames, values, action, dp, dp_dim)

    def create_data_emitter(self, obj, anim, options):
        """Creates animations in emitter actions."""

        part_sys = obj.particle_systems.active
        if not part_sys:
            return
        part_settings = part_sys.settings
        if not part_settings:
            return
        fps = options.scene.render.fps
        frame_start = anim.frameStart
        action = nvb_utils.get_action(part_settings, part_settings.name)
        for label, (data, data_path, data_dim) in self.emitter_data.items():
            frames = [fps * d[0] + frame_start for d in data]
            values = [d[1:data_dim+1] for d in data]
            dp = data_path
            dp_dim = data_dim
            Animnode.insert_kfp(frames, values, action, dp, dp_dim)

    def create_data_shape(self, obj, anim, animlength, options):
        """Import animated vertices as shapekeys."""
        fps = options.scene.render.fps
        if not obj.data:
            return
        # Sanity check: Sample period can't be 0
        if self.sampleperiod < 0.001:
            return
        # Sanity check: animation length has to be a multiple of
        #               sampleperiod
        if animlength % self.sampleperiod > 0.0:
            return
        numSamples = int(animlength / self.sampleperiod) + 1
        # Sanity check: Number of animtverts = number verts * numSamples
        numVerts = len(obj.data.vertices)
        if (len(self.animverts) != numVerts * numSamples):
            print("Neverblender: WARNING - animvert sample size mismatch: " +
                  obj.name)
            return
        sampleDistance = fps * self.sampleperiod
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
            curveX = nvb_utils.get_fcurve(action, dp, 0)
            curveY = nvb_utils.get_fcurve(action, dp, 1)
            curveZ = nvb_utils.get_fcurve(action, dp, 2)
            samples = self.animverts[vertIdx::numVerts]
            for sampleIdx, co in enumerate(samples):
                frame = frameStart + (sampleIdx * sampleDistance)
                curveX.keyframe_points.insert(frame, co[0], kfOptions)
                curveY.keyframe_points.insert(frame, co[1], kfOptions)
                curveZ.keyframe_points.insert(frame, co[2], kfOptions)

    def create_data_uv(self, obj, anim, animlength, options):
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
        sampleDistance = fps * self.sampleperiod

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
            curveU = nvb_utils.get_fcurve(action, dp, 0)
            curveV = nvb_utils.get_fcurve(action, dp, 1)
            samples = self.animtverts[tvertIdx::numTVerts]
            for sampleIdx, co in enumerate(samples):
                frame = frameStart + (sampleIdx * sampleDistance)
                curveU.keyframe_points.insert(frame, co[0], kfOptions)
                curveV.keyframe_points.insert(frame, co[1], kfOptions)

    @staticmethod
    def create_restpose(obj, frame=1):
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
                eul = mathutils.Quaternion(obj.nvb.restrot[:3],
                                           obj.nvb.restrot[3]).to_euler()
                insert_kfp(fcu, frame, eul, 3)
        fcu = [action.fcurves.find('location', i) for i in range(3)]
        if fcu.count(None) < 1:
            insert_kfp(fcu, frame, obj.nvb.restloc, 3)

    def create(self, obj, anim, animlength, options):
        """TODO:Doc."""
        if self.object_data:
            self.create_data_object(obj, anim, options)
        if self.material_data:
            self.create_data_material(obj, anim, options)
        if self.emitter_data:
            self.create_data_emitter(obj, anim, options)
        if self.uvdata:
            self.create_data_uv(obj, anim, animlength, options)
        if self.shapedata:
            self.create_data_shape(obj, anim, animlength, options)

    @staticmethod
    def get_keys_emitter(psy, anim, key_data, options):
        """Get keys from particle settings."""

        action = psy.animation_data.action
        if not action:
            return
        fps = options.scene.render.fps
        anim_start = anim.frameStart
        anim_end = anim.frameEnd
        # List of exportable data paths with formats and conversion functions
        exports = []
        for aur_name, (dp, dp_dim, _, aur_fstr) in \
                Animnode.emitter_properties.items():
            exports.append([aur_name, dp_dim, aur_fstr, dp, dp_dim])
        # Get keyframe data
        all_fcurves = action.fcurves
        for aur_name, aur_dim, aur_fstr, dp_name, dp_dim in exports:
            fcu = [all_fcurves.find(dp_name, i) for i in range(dp_dim)]
            if fcu.count(None) < dp_dim:  # ignore empty fcurves
                keyed_frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points
                       if anim_start <= k.co[0] <= anim_end]
                      for i in range(dp_dim)]))
                keyed_frames.sort()
                aur_values = [[fcu[i].evaluate(f) for i in range(dp_dim)]
                              for f in keyed_frames]
                aur_times = [(f - anim_start) / fps for f in keyed_frames]
                aur_keys = list(zip(aur_times, aur_values))
                key_data.append([aur_name, aur_keys, aur_dim * aur_fstr])

    @staticmethod
    def get_keys_material(mat, anim, key_data, options):
        """Get keys from material actions."""
        def get_exports(action):
            """Get a list of data paths to export."""
            # [value name, value dimension, value format,
            #  data path name, data path dimension, conversion func., default]
            exports = [['ambient', 3, ' {:>4.2f}',
                        'nvb.ambient_color', 3, None, [0.0, 0.0, 0.0]]]
            # Aplha can be animated with the following data paths
            # 1. 'texture_slots[X].alpha_factor' - which is texture slot alpha
            # 2. 'alpha' - which is material alpha
            # We only want one of those, alpha_factor takes precendence
            dp_alpha_factor = [fc.data_path for fc in action.fcurves
                               if fc.data_path.endswith('.alpha_factor')]
            if dp_alpha_factor:
                exports.append(['alpha', 1, ' {:>4.2f}',
                                dp_alpha_factor[0], 1, None, [0.0]])
            else:
                exports.append(['alpha', 1, ' {:>4.2f}',
                                'alpha', 1, None, [0.0]])
            return exports

        action = mat.animation_data.action
        if not action:
            return
        # List of exportable data paths with formats and conversion functions
        exports = get_exports(action)
        fps = options.scene.render.fps
        anim_start = anim.frameStart
        anim_end = anim.frameEnd
        # Get keyframe data
        all_fcurves = action.fcurves
        for aur_name, aur_dim, aur_fstr, dp_name, dp_dim, _, \
                default_val in exports:
            fcu = [all_fcurves.find(dp_name, i) for i in range(dp_dim)]
            if fcu.count(None) < dp_dim:  # ignore empty fcurves
                keyed_frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points
                       if anim_start <= k.co[0] <= anim_end]
                      for i in range(dp_dim)]))
                keyed_frames.sort()
                aur_values = [[fcu[i].evaluate(f) if fcu[i] else default_val[i]
                              for i in range(dp_dim)] for f in keyed_frames]
                # values = [[fcu[i].evaluate(f) for i in range(dp_dim)]
                #           for f in frames]
                aur_times = [(f - anim_start) / fps for f in keyed_frames]
                aur_keys = list(zip(aur_times, aur_values))
                key_data.append([aur_name, aur_keys, aur_dim * aur_fstr])

    @staticmethod
    def get_keys_object(obj, anim, key_data, options):
        """Get keys from object actions."""
        def get_exports(rot_mode):
            """Get a list of data paths to export."""
            # [value name, value dimension, value format,
            #  data path, data path dimension, conversion function, default]
            exports = [
                ['scale', 1, ' {:> 6.5f}',
                 'scale', 1, None, [1.0]],
                ['selfillumcolor', 3, ' {:>3.2f}',
                 'nvb.selfillumcolor', 3, None, [0.0, 0.0, 0.0]],
                ['color', 3, ' {:>3.2f}',
                 'color', 3, None, [0.0, 0.0, 0.0]],
                ['radius', 1, ' {:>6.5f}',
                 'distance', 1, None, [1.0]],
                ['position', 3, ' {:> 6.5f}',
                 'location', 3, convert_loc, [0.0, 0.0, 0.0]]]
            if obj.rotation_mode == 'AXIS_ANGLE':
                exports.append(['orientation', 4, ' {:> 6.5f}',
                                'rotation_axis_angle', 4, convert_axan,
                                [1.0, 0.0, 0.0, 0.0]])
            elif obj.rotation_mode == 'QUATERNION':
                exports.append(['orientation', 4, ' {:> 6.5f}',
                                'rotation_quaternion', 4, convert_quat,
                                [1.0, 0.0, 0.0, 0.0]])
            else:
                exports.append(['orientation', 4, ' {:> 6.5f}',
                                'rotation_euler', 3, convert_eul,
                                [0.0, 0.0, 0.0]])
            return exports

        def convert_loc(obj, kfvalues):
            pinv = obj.matrix_parent_inverse
            return [(pinv * mathutils.Matrix.Translation(v)).to_translation()
                    for v in kfvalues]

        def convert_eul(obj, kfvalues):
            pinv = obj.matrix_parent_inverse
            mats = [pinv * mathutils.Euler(v, 'XYZ').to_matrix().to_4x4()
                    for v in kfvalues]
            return [[*q.axis, q.angle] for q in
                    [m.to_quaternion() for m in mats]]

        def convert_axan(obj, kfvalues):
            pinv = obj.matrix_parent_inverse
            mats = \
                [pinv * mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4()
                 for v in kfvalues]
            return [[*q.axis, q.angle] for q in
                    [m.to_quaternion() for m in mats]]

        def convert_quat(obj, kfvalues):
            pinv = obj.matrix_parent_inverse
            mats = [pinv * mathutils.Quaternion(v).to_matrix().to_4x4()
                    for v in kfvalues]
            return [[*q.axis, q.angle] for q in
                    [m.to_quaternion() for m in mats]]

        action = obj.animation_data.action
        if not action:
            return
        # List of exportable data paths with formats and conversion functions
        exports = get_exports(obj.rotation_mode)
        fps = options.scene.render.fps
        anim_start = anim.frameStart
        anim_end = anim.frameEnd
        # Get keyframe data
        all_fcurves = action.fcurves
        for aur_name, aur_dim, aur_fstr, dp_name, dp_dim, dp_conversion, \
                default_val in exports:
            fcu = [all_fcurves.find(dp_name, i) for i in range(dp_dim)]
            if fcu.count(None) < dp_dim:  # ignore empty fcurves
                keyed_frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points
                       if anim_start <= k.co[0] <= anim_end]
                      for i in range(dp_dim) if fcu[i]]))
                keyed_frames.sort()
                # Get values at keyed frames and convert
                values = [[fcu[i].evaluate(f) if fcu[i] else default_val[i]
                           for i in range(dp_dim)] for f in keyed_frames]
                # values = [[fcu[i].evaluate(f) for i in range(dp_dim)]
                #           for f in frames]
                # Convert to the format used by MDLs
                if dp_conversion is not None:
                    aur_values = dp_conversion(obj, values)
                aur_times = [(f - anim_start) / fps for f in keyed_frames]
                aur_keys = list(zip(aur_times, aur_values))
                key_data.append([aur_name, aur_keys, aur_dim * aur_fstr])

    @staticmethod
    def generate_ascii_keys(obj, anim, asciiLines, options):
        """TODO: DOC."""
        kdata = []
        # 1. Object animation data
        if obj.animation_data:
            Animnode.get_keys_object(obj, anim, kdata, options)
        # 2. Material animation data
        mat = obj.active_material
        if mat and mat.animation_data:
            Animnode.get_keys_material(mat, anim, kdata, options)
        # 3. particle System/Emitter animation data
        part_sys = obj.particle_systems.active
        if part_sys and part_sys.settings.animation_data:
            Animnode.get_keys_emitter(part_sys.settings, anim, kdata, options)
        # Add keys to ascii lines
        time_fstr = '{:> 6.3f}'
        for key_name, keys, val_fstr in kdata:
            num_keys = len(keys)
            if num_keys > 0:  # Create a key list
                print(key_name)
                asciiLines.append('    ' + key_name + 'key ' + str(num_keys))
                fstr = '      ' + time_fstr + val_fstr
                asciiLines.extend([fstr.format(k[0], *k[1]) for k in keys])

    @staticmethod
    def generate_ascii_animesh_shapes(obj, anim, asciiLines, options,
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
                    animlength = (animEnd-animStart) / fps
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
    def generate_ascii_animesh_uv(obj, anim, asciiLines, options,
                                  numAnimVerts=0):
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
                    animlength = (animEnd-animStart) / fps
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
    def generate_ascii_animesh(obj, anim, asciiLines, options):
        """TODO:Doc."""
        if not obj.data:
            return
        # Check if the object is an animmesh:
        if (obj.type != 'MESH') or \
           (obj.nvb.meshtype != nvb_def.Meshtype.ANIMMESH):
            return
        tmpLines = []
        nvb_node.Animmesh.generateAsciiMesh(obj, tmpLines, options, True)
        asciiLines.extend(['  ' + l for l in tmpLines])
        maxsamples = -1  # Samples > 0 also means not to write metadata (again)
        maxsamples = Animnode.generate_ascii_animesh_uv(obj, anim, asciiLines,
                                                        options, maxsamples)
        Animnode.generate_ascii_animesh_shapes(obj, anim, asciiLines,
                                               options, maxsamples)

    @staticmethod
    def generate_ascii(obj, anim, asciiLines, options):
        """TODO:Doc."""
        if not obj:
            return
        # Type + Name
        node_type = nvb_utils.getNodeType(obj)
        node_name = nvb_utils.generate_node_name(obj, options.strip_trailing)
        asciiLines.append('  node ' + node_type + ' ' + node_name)
        # Parent
        if obj.parent:
            asciiLines.append('    parent ' + obj.parent.name)
        else:
            asciiLines.append('    parent null')
        Animnode.generate_ascii_animesh(obj, anim, asciiLines, options)
        Animnode.generate_ascii_keys(obj, anim, asciiLines, options)
        asciiLines.append('  endnode')
