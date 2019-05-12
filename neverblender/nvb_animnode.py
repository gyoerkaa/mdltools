"""TODO: DOC."""

import math

import mathutils
import collections
import copy
import bpy

from . import nvb_def
from . import nvb_utils
from . import nvb_node
from .nvb_materialnode import Materialnode


class Animnode():
    """TODO: DOC."""

    # Keys that go into particle system settings
    emitter_properties = nvb_node.Emitter.property_dict
    # Keys that go directly into objects
    object_properties = {'position': ('', 3, float,  # Needs conversion
                                      ' {:> 6.5f}'),
                         'orientation': ('', 4, float,  # Needs conversion
                                         ' {:> 6.5f}'),
                         'scale': ('', 1, float,  # Needs conversion
                                   ' {:> 6.5f}'),
                         'color': ('color', 3, float,
                                   ' {:>4.2f}'),
                         'radius': ('distance', 1, float,
                                    ' {:>6.5f}')}
    # Keys that go into materials
    material_properties = {'alpha': ('', 1, float,  # Needs conversion
                                     ' {:>4.2f}'),
                           'selfillumcolor': ('', 3, float,
                                              ' {:>4.2f}'),
                           'setfillumcolor': ('', 3, float,
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
    def insert_kfp(frames, values, action, dp, dp_dim, action_group=None):
        """TODO: DOC."""
        if frames and values:
            fcu = [nvb_utils.get_fcurve(action, dp, i, action_group)
                   for i in range(dp_dim)]
            kfp_list = [fcu[i].keyframe_points for i in range(dp_dim)]
            kfp_cnt = list(map(lambda x: len(x), kfp_list))
            list(map(lambda x: x.add(len(values)), kfp_list))
            for i, (frm, val) in enumerate(zip(frames, values)):
                for d in range(dp_dim):
                    p = kfp_list[d][kfp_cnt[d]+i]
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

        def data_conversion(label, material_out, vals):
            """TODO: Doc."""
            if label == 'alpha':
                socket0 = Materialnode.find_alpha_socket(material_out)
                dp = socket0.path_from_id("default_value")
                dp_dim = 1
            elif label in ['selfillumcolor', 'setfillumcolor']:
                socket1 = Materialnode.find_emissive_socket(material_out)
                socket0 = Materialnode.get_color_socket(socket1)
                dp = socket0.path_from_id("default_value")
                dp_dim = 3
            return vals, dp, dp_dim

        blender_mat = obj.active_material
        blendet_mat_out = Materialnode.get_output_node(blender_mat)
        if not blendet_mat_out:
            return
        node_tree = blender_mat.node_tree
        if not node_tree:
            return
        fps = options.scene.render.fps
        frame_start = anim.frameStart
        action = nvb_utils.get_action(node_tree, blender_mat.name)
        for label, (data, data_path, data_dim) in self.material_data.items():
            frames = [round(fps * d[0], 3) + frame_start for d in data]
            if not data_path:  # Needs conversion
                values, dp, dp_dim = data_conversion(
                    label, blendet_mat_out, [d[1:data_dim+1] for d in data])
            else:
                values = [d[1:data_dim+1] for d in data]
                dp = data_path
                dp_dim = data_dim
            Animnode.insert_kfp(frames, values, action, dp, dp_dim)

    def create_data_object(self, obj, anim, options):
        """Creates animations in object actions."""
        def data_conversion(label, obj, vals, options):
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
            elif label == 'position':
                scl = options.anim_scale
                dp = 'location'
                dp_dim = 3
                if scl:
                    new_values = [[l * scl for l in loc] for loc in vals]
                else:
                    new_values = vals
            elif label == 'scale':
                dp = 'scale'
                dp_dim = 3
                new_values = [[v] * dp_dim for v in vals]
            return new_values, dp, dp_dim

        fps = options.scene.render.fps
        frame_start = anim.frameStart
        action = nvb_utils.get_action(obj, options.mdlname + '.' + obj.name)
        for label, (data, data_path, data_dim) in self.object_data.items():
            frames = [round(fps * d[0], 3) + frame_start for d in data]
            if not data_path:  # Needs conversion
                values, dp, dp_dim = data_conversion(
                    label, obj, [d[1:data_dim+1] for d in data], options)
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
            frames = [round(fps * d[0], 3) + frame_start for d in data]
            values = [d[1:data_dim+1] for d in data]
            dp = data_path
            dp_dim = data_dim
            if dp.startswith('nvb'):  # Group custom properties
                Animnode.insert_kfp(frames, values, action, dp, dp_dim,
                                    'Aurora Emitter')
            else:
                Animnode.insert_kfp(frames, values, action, dp, dp_dim)

    def create_data_shape(self, obj, anim, animlength, options):
        """Import animated vertices as shapekeys."""
        fps = options.scene.render.fps
        frame_start = anim.frameStart
        if not obj.data:
            return
        # Sanity check: Sample period can't be 0
        if self.sampleperiod < 0.001:
            return
        # Sanity check: animation length has to be a multiple of
        #               sampleperiod
        if animlength % self.sampleperiod > 0.0:
            return
        sample_cnt = int(animlength / self.sampleperiod) + 1
        # Sanity check: Number of animtverts = number verts * numSamples
        vert_cnt = len(obj.data.vertices)
        if (len(self.animverts) != vert_cnt * sample_cnt):
            print("Neverblender: WARNING - animvert sample size mismatch: " +
                  obj.name)
            return
        # Add Basis key holding original mesh data
        shape_keys = obj.data.shape_keys
        if not shape_keys or 'Basis' not in shape_keys.key_blocks:
            sk = obj.shape_key_add(name='Basis', from_mix=False)
            shape_keys = obj.data.shape_keys  # Might be created now
            shape_keys.name = options.mdlname + '.' + obj.name + '.sk'
        shape_keys.use_relative = False
        # Add absolute shape Keys
        sk_frame_list = []
        for idx in range(sample_cnt):
            sk_name = anim.name + str(idx)
            sk = obj.shape_key_add(name=sk_name, from_mix=False)
            sk_frame_list.append(sk.frame)
            sk_values = self.animverts[idx*vert_cnt:(idx+1)*vert_cnt]
            sk_values = [c for coords in sk_values for c in coords]
            sk.data.foreach_set('co', sk_values)
        # Get action, create one if necessary
        action = nvb_utils.get_action(shape_keys, shape_keys.name)
        # Insert keyframes
        kfOptions = {'FAST'}
        sample_dist = fps * self.sampleperiod
        fcu = nvb_utils.get_fcurve(action, 'eval_time', 0)
        for idx, eval_time in enumerate(sk_frame_list):
            kfp_frame = frame_start + (idx * sample_dist)
            fcu.keyframe_points.insert(kfp_frame, eval_time, options=kfOptions)
        fcu.update()

    def create_data_uv(self, obj, anim, animlength, options):
        """Import animated texture coordinates."""

        uvlayer = obj.data.uv_layers.active
        if not uvlayer:
            return
        fps = options.scene.render.fps
        # Sanity check: Sample period can't be 0
        if self.sampleperiod <= 0.00001:
            return
        # Sanity check: animation length has to be a multiple of
        #               sampleperiod
        if animlength % self.sampleperiod > 0.0:
            return
        num_samples = int(animlength / self.sampleperiod) + 1
        # Sanity check: Number of animtverts = number tverts * numSamples
        num_uvs = len(uvlayer.data)
        if (len(self.animtverts) != num_uvs * num_samples):
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
        dp_fstr = '"uv_layers["' + uvlayer.name + '"].data[{:d}].uv'
        # uvIdx = order in blender, tvertIdx = order in mdl
        for loop_idx, uv_idx in enumerate(uvlayer.data):
            dp = dp_fstr.format(loop_idx)
            curveU = nvb_utils.get_fcurve(action, dp, 0)
            curveV = nvb_utils.get_fcurve(action, dp, 1)
            samples = self.animtverts[loop_idx::num_uvs]
            for sampleIdx, co in enumerate(samples):
                frame = frameStart + (sampleIdx * sampleDistance)
                curveU.keyframe_points.insert(frame, co[0], options=kfOptions)
                curveV.keyframe_points.insert(frame, co[1], options=kfOptions)

    @staticmethod
    def create_restpose(obj, frame=1):
        """TODO: DOC."""
        def insert_kfp(fcurves, frame, val, dim):
            """TODO: DOC."""
            for j in range(dim):
                fcurves[j].keyframe_points.insert(frame, val[j],
                                                  options={'FAST'})
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
            fcu = [action.fcurves.find(data_path=dp, index=i)
                   for i in range(4)]
            if fcu.count(None) < 1:
                rr = obj.nvb.restrot
                insert_kfp(fcu, frame, [rr[3], rr[0], rr[1], rr[2]], 4)
        if obj.rotation_mode == 'QUATERNION':
            dp = 'rotation_quaternion'
            fcu = [action.fcurves.find(data_path=dp, index=i)
                   for i in range(4)]
            if fcu.count(None) < 1:
                rr = obj.nvb.restrot
                q = mathutils.Quaternion((rr[0], rr[1], rr[2]), rr[3])
                insert_kfp(fcu, frame, [q.w, q.x, q.y, q.z], 4)
        else:
            dp = 'rotation_euler'
            fcu = [action.fcurves.find(data_path=dp, index=i)
                   for i in range(3)]
            if fcu.count(None) < 1:
                eul = mathutils.Quaternion(obj.nvb.restrot[:3],
                                           obj.nvb.restrot[3]).to_euler()
                insert_kfp(fcu, frame, eul, 3)
        fcu = [action.fcurves.find(data_path='location', index=i)
               for i in range(3)]
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
        for aur_name, aur_dim, aur_fstr, dp, dp_dim in exports:
            fcu = [all_fcurves.find(data_path=dp, index=i)
                   for i in range(dp_dim)]
            if fcu.count(None) < dp_dim:  # ignore empty fcurves
                keyed_frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points
                       if anim_start <= round(k.co[0], 5) <= anim_end]
                      for i in range(dp_dim)]))
                keyed_frames.sort()
                aur_values = [[fcu[i].evaluate(f) for i in range(dp_dim)]
                              for f in keyed_frames]
                aur_times = [(f - anim_start) / fps for f in keyed_frames]
                aur_keys = list(zip(aur_times, aur_values))
                key_data.append([aur_name, aur_keys, aur_dim * aur_fstr])

    @staticmethod
    def get_keys_material(obj, anim, key_data, options):
        """Get keys from material actions."""
        def get_exports(action, material_out):
            """Get a list of data paths to export."""

            # [value name, value dimension, value format,
            #  data path name, data path dimension, conversion func., default]
            exports = []
            # Aplha value
            socket0 = Materialnode.find_alpha_socket(material_out)
            dp = socket0.path_from_id("default_value")
            exports.append(['alpha', 1, ' {:>4.2f}',
                            dp, 1, None, [1.0]])
            # Self Illumination color
            socket1 = Materialnode.find_emissive_socket(material_out)
            socket0 = Materialnode.get_color_socket(socket1)
            dp = socket0.path_from_id("default_value")
            exports.append(['selfillumcolor', 3, ' {:>4.2f}',
                            dp, 3, None, [0.0, 0.0, 0.0]])
            return exports

        # Get the active blender material and output node
        blend_mat = obj.active_material
        if not blend_mat:
            return
        blend_mat_out = Materialnode.get_output_node(blend_mat)
        if not blend_mat_out:
            return
        # Get the action from which to export keyframes
        try:
            action = blend_mat.node_tree.animation_data.action
        except AttributeError:
            return
        # Grab animation meta data
        fps = options.scene.render.fps
        anim_start = anim.frameStart
        anim_end = anim.frameEnd
        # List of exportable data paths with formats and conversion functions
        exports = get_exports(action, blend_mat_out)
        # Get keyframe data
        all_fcurves = action.fcurves
        for aur_name, aur_dim, aur_fstr, dp, dp_dim, _, \
                default_val in exports:
            fcu = [all_fcurves.find(data_path=dp, index=i)
                   for i in range(dp_dim)]
            if fcu.count(None) < dp_dim:  # ignore empty fcurves
                keyed_frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points
                       if anim_start <= round(k.co[0], 5) <= anim_end]
                      for i in range(dp_dim)]))
                keyed_frames.sort()
                aur_values = [[fcu[i].evaluate(f) if fcu[i] else default_val[i]
                              for i in range(aur_dim)] for f in keyed_frames]
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
                ['selfillumcolor', 3, ' {:>4.2f}',
                 'nvb.selfillumcolor', 3, None, [0.0, 0.0, 0.0]],
                ['color', 3, ' {:>4.2f}',
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
            return [(pinv @ mathutils.Matrix.Translation(v)).to_translation()
                    for v in kfvalues]

        def convert_eul(obj, kfvalues):
            pinv = obj.matrix_parent_inverse
            mats = [pinv @ mathutils.Euler(v, 'XYZ').to_matrix().to_4x4()
                    for v in kfvalues]
            return [[*q.axis, q.angle] for q in
                    [m.to_quaternion() for m in mats]]

        def convert_axan(obj, kfvalues):
            pinv = obj.matrix_parent_inverse
            mats = \
                [pinv @ mathutils.Quaternion(v[1:], v[0]).to_matrix().to_4x4()
                 for v in kfvalues]
            return [[*q.axis, q.angle] for q in
                    [m.to_quaternion() for m in mats]]

        def convert_quat(obj, kfvalues):
            pinv = obj.matrix_parent_inverse
            mats = [pinv @ mathutils.Quaternion(v).to_matrix().to_4x4()
                    for v in kfvalues]
            return [[*q.axis, q.angle] for q in
                    [m.to_quaternion() for m in mats]]

        # Get the action from which to export from
        try:
            action = obj.animation_data.action
        except AttributeError:
            return
        # Grab animation meta data
        fps = options.scene.render.fps
        anim_start = anim.frameStart
        anim_end = anim.frameEnd
        # List of exportable data paths with formats and conversion functions
        exports = get_exports(obj.rotation_mode)
        # Get keyframe data
        all_fcurves = action.fcurves
        for aur_name, aur_dim, aur_fstr, dp, dp_dim, dp_conversion, \
                default_val in exports:
            fcu = [all_fcurves.find(data_path=dp, index=i)
                   for i in range(dp_dim)]
            if fcu.count(None) < dp_dim:  # ignore empty fcurves
                keyed_frames = list(set().union(
                    *[[k.co[0] for k in fcu[i].keyframe_points
                       if anim_start <= round(k.co[0], 5) <= anim_end]
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
                else:
                    aur_values = values
                aur_times = [(f - anim_start) / fps for f in keyed_frames]
                aur_keys = list(zip(aur_times, aur_values))
                key_data.append([aur_name, aur_keys, aur_dim * aur_fstr])

    @staticmethod
    def generate_ascii_keys(obj, anim, asciiLines, options):
        """TODO: DOC."""
        key_data = []

        # 1. Object animation data
        Animnode.get_keys_object(obj, anim, key_data, options)
        # 2. Material animation data
        Animnode.get_keys_material(obj, anim, key_data, options)
        # 3. particle System/Emitter animation data
        part_sys = obj.particle_systems.active
        if part_sys and part_sys.settings.animation_data:
            Animnode.get_keys_emitter(part_sys.settings,
                                      anim,
                                      key_data,
                                      options)
        # Add keys to ascii lines
        time_fstr = '{:> 6.3f}'
        for key_name, keys, val_fstr in key_data:
            num_keys = len(keys)
            if num_keys > 0:  # Create a key list
                asciiLines.append('    ' + key_name + 'key ' + str(num_keys))
                fstr = '      ' + time_fstr + val_fstr
                asciiLines.extend([fstr.format(k[0], *k[1]) for k in keys])
                asciiLines.append('    endlist')

    @staticmethod
    def generate_ascii_animesh_shapes(obj, anim, ascii_lines, options,
                                      required_samples=0):
        """Add data for animated vertices."""

        # Must be absolute shapekeys
        shape_keys = obj.data.shape_keys
        if not shape_keys or shape_keys.use_relative:
            return -1
        # There need to be key blocks
        key_blocks = obj.data.shape_keys.key_blocks
        if not key_blocks:
            return -1
        # Get the action from which to export from
        try:
            action = shape_keys.animation_data.action
        except AttributeError:
            return -1
        # Get eval time fcurve
        fcu = action.fcurves.find(data_path='eval_time', index=0)
        if not fcu:
            return -1

        # Cache values for speed
        anim_start = anim.frameStart
        anim_end = anim.frameEnd
        fps = options.scene.render.fps

        eval_times = [k.co[1] for k in fcu.keyframe_points
                      if anim_start <= round(k.co[0], 5) <= anim_end]
        # rel_kb = [(kb.frame, kb.data) for kb in key_blocks if not kb.mute]
        anim_verts = []
        for et in eval_times:
            shape_key0 = next((kb for kb in reversed(key_blocks) if kb.frame <= et), None)
            shape_key1 = next((kb for kb in key_blocks if kb.frame >= et), shape_key0)
            interval = [shape_key0.frame, shape_key1.frame]
            factor = [et/sum(interval), 1.0-et/sum(interval)]
            values = [(factor[0] * d0.co) + (factor[1] * d1.co) for d0, d1 in zip(shape_key0.data, shape_key1.data)]
            anim_verts.append(values)

        # Misc data for export
        num_samples = len(eval_times)
        num_verts = len(anim_verts[0])
        if required_samples > 0:
            # Not necessary to add meta data
            # BUT: Sanity check
            if required_samples != num_samples:
                print("Neverblender: " +
                        "WARNING - anim verts/tverts mismatch: " +
                        obj.name)
                return -1
        else:
            # Add meta data
            ascii_lines.append('    clipu 0.0')
            ascii_lines.append('    clipv 0.0')
            ascii_lines.append('    clipw 1.0')
            ascii_lines.append('    cliph 1.0')

            anim_length = (anim_end - anim_start) / fps
            sample_period = anim_length / (num_samples - 1)
            ascii_lines.append('    sampleperiod ' +
                               str(round(sample_period, 5)))
        # Create ascii representation and add it to the output
        ascii_lines.append('    animverts ' + str(num_samples * num_verts))
        fstr = '     ' + 3 * ' {: 8.5f}'
        for av in anim_verts:
            ascii_lines.extend([fstr.format(*v) for v in av])
        ascii_lines.append('    endlist')

        return num_samples

    @staticmethod
    def generate_ascii_animesh_uv(obj, anim, asciiLines, options,
                                  numAnimVerts=0):
        """Add data for animated texture coordinates."""
        return -1
        """
        if not obj.active_material:
            return
        if not obj.active_material.active_texture:
            return
        if not obj.data.uv_layers.active:
            return
        # Original uv data. Needed to fill in values for unanimated uv's.
        obj.data.update()
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
        """

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
        nvb_node.Animmesh.generateAsciiMesh(obj, tmpLines, options)
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
        parent_name = nvb_utils.generate_node_name(obj.parent,
                                                   options.strip_trailing)
        asciiLines.append('    parent ' + parent_name)
        Animnode.generate_ascii_animesh(obj, anim, asciiLines, options)
        Animnode.generate_ascii_keys(obj, anim, asciiLines, options)
        asciiLines.append('  endnode')
