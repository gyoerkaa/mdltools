"""TODO: DOC."""

import math
import array
import copy
import os
import itertools

import mathutils
import bpy
import bmesh
from bpy_extras.io_utils import unpack_list, unpack_face_list

from . import nvb_mtr
from . import nvb_def
from . import nvb_utils
from . import nvb_parse
from . import nvb_aabb
from . import nvb_material


class Node(object):
    """TODO: DOC."""

    nodetype = 'undefined'

    def __init__(self, name='unnamed'):
        """TODO: DOC."""
        self.createdobj = ''  # Name of the corresponding object in blender
        self.nodeidx = -1  # Order in mdlfile (needs to be restored for export)

        self.name = name
        self.parent = ''
        self.position = (0.0, 0.0, 0.0)
        self.orientation = [0.0, 0.0, 0.0, 0.0]
        self.scale = 1.0
        self.wirecolor = (1.0, 1.0, 1.0)

    def __eq__(self, other):
        """TODO: DOC."""
        if isinstance(other, Node):
            return (self.name == other.name) and (self.parent == other.parent)

    def __ne__(self, other):
        """TODO: DOC."""
        return not self.__eq__(other)

    def __str__(self):
        """TODO: DOC."""
        return 'node ' + self.nodetype + ' ' + self.name

    def getIdx(self):
        """TODO: DOC."""
        return self.nodeidx

    def getName(self):
        """TODO: DOC."""
        return self.name

    def loadAsciiLine(self, itlines):
        """TODO: DOC."""
        line = None
        try:
            line = next(itlines)
        except StopIteration:
            return None
        label = ''
        try:
            label = line[0].lower()
        except (IndexError, AttributeError):
            return line  # Probably empty line or comment
        if nvb_utils.isNumber(label):
            return line
        if label == 'node':
            self.name = nvb_parse.ascii_identifier(line[2])
        elif label == 'endnode':
            return line
        elif label == 'parent':
            self.parent = nvb_parse.ascii_identifier(line[1])
        elif label == 'position':
            self.position = tuple([float(v) for v in line[1:4]])
        elif label == 'orientation':
            self.orientation = [float(v) for v in line[1:5]]
        elif label == 'scale':
            self.scale = float(line[1])
        elif label == 'wirecolor':
            self.wirecolor = tuple([float(v) for v in line[1:4]])
        return line

    def loadAscii(self, ascii_lines, nodeidx=-1):
        """TODO: DOC."""
        self.nodeidx = nodeidx
        iterable = iter(ascii_lines)
        line = True
        while line is not None:
            line = self.loadAsciiLine(iterable)

    def createObjectData(self, obj, options):
        """TODO: DOC."""
        obj.rotation_mode = options.rotmode
        nvb_utils.setObjAuroraRot(obj, self.orientation)
        obj.nvb.restrot = self.orientation
        obj.scale = (self.scale, self.scale, self.scale)
        obj.location = self.position
        obj.nvb.restloc = obj.location
        obj.nvb.imporder = self.nodeidx

    def createObject(self, options):
        """Return an object for use in blender."""
        obj = bpy.data.objects.new(self.name, None)
        self.createdobj = obj.name
        self.createObjectData(obj, options)
        return obj

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options, iswalkmesh=False):
        """TODO: DOC."""
        if obj.parent is None:  # Rootdummys get no data at all
            return
        mat = obj.matrix_parent_inverse @ obj.matrix_basis

        loc = mat.to_translation()
        asciiLines.append('  position {: 8.5f} {: 8.5f} {: 8.5f}'.format(*loc))

        rot = mat.to_quaternion()
        fstr = '  orientation {: 8.5f} {: 8.5f} {: 8.5f} {: 8.5f}'
        asciiLines.append(fstr.format(*rot.axis, rot.angle))

        scale = nvb_utils.getAuroraScale(obj)
        if not (0.998 < scale < 1.002):
            asciiLines.append('  scale {:5.3f}'.format(scale))

    @classmethod
    def generateAscii(cls, obj, asciiLines, options, iswalkmesh=False):
        """TODO: Doc."""
        node_name = nvb_utils.generate_node_name(obj, options.strip_trailing)
        asciiLines.append('node ' + cls.nodetype + ' ' + node_name)
        # Parent
        parent_name = nvb_utils.generate_node_name(obj.parent,
                                                   options.strip_trailing)
        asciiLines.append('  parent ' + parent_name)

        cls.generateAsciiData(obj, asciiLines, options, iswalkmesh)
        asciiLines.append('endnode')


class Dummy(Node):
    """TODO: Doc."""

    nodetype = nvb_def.Nodetype.DUMMY

    def __init__(self, name='unnamed'):
        """TODO: Doc."""
        Node.__init__(self, name)
        self.emptytype = nvb_def.Emptytype.DUMMY

    def loadAscii(self, asciiLines, nodeidx=-1):
        """TODO: Doc."""
        Node.loadAscii(self, asciiLines, nodeidx)

    def createObjectData(self, obj, options):
        """TODO: DOC."""
        Node.createObjectData(self, obj, options)
        obj.nvb.emptytype = self.emptytype


class Patch(Node):
    """Same as a plain Dummy."""

    nodetype = nvb_def.Nodetype.PATCH

    def __init__(self, name='UNNAMED'):
        """TODO: Doc."""
        Node.__init__(self, name)
        self.emptytype = nvb_def.Emptytype.PATCH

    def createObjectData(self, obj, options):
        """TODO: Doc."""
        Node.createObjectData(self, obj, options)
        obj.nvb.emptytype = self.emptytype


class Reference(Node):
    """Contains a reference to another mdl."""

    nodetype = nvb_def.Nodetype.REFERENCE

    def __init__(self, name='UNNAMED'):
        """TODO: Doc."""
        Node.__init__(self, name)
        self.emptytype = nvb_def.Emptytype.REFERENCE

        self.refmodel = nvb_def.null
        self.reattachable = 0

    def loadAsciiLine(self, itlines):
        """TODO: Doc."""
        line = Node.loadAsciiLine(self, itlines)
        if line:
            label = line[0].lower()
            if label == 'refmodel':
                self.refmodel = nvb_parse.ascii_identifier(line[1])
            elif label == 'reattachable':
                self.reattachable = nvb_parse.ascii_bool(line[1])
        return line

    def createObjectData(self, obj, options):
        """TODO: Doc."""
        Node.createObjectData(self, obj, options)
        obj.nvb.emptytype = self.emptytype
        obj.nvb.refmodel = self.refmodel
        obj.nvb.reattachable = self.reattachable

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options, iswalkmesh=False):
        """TODO: Doc."""
        Node.generateAsciiData(obj, asciiLines, options, iswalkmesh)
        if iswalkmesh:
            return
        asciiLines.append('  refmodel ' + obj.nvb.refmodel)
        asciiLines.append('  reattachable ' + str(int(obj.nvb.reattachable)))


class Trimesh(Node):
    """Default type of Mesh."""

    nodetype = nvb_def.Nodetype.TRIMESH

    def __init__(self, name='UNNAMED'):
        """TODO: Doc."""
        Node.__init__(self, name)
        self.meshtype = nvb_def.Meshtype.TRIMESH

        self.center = (0.0, 0.0, 0.0)  # Unused ?
        self.tilefade = 0
        self.render = True
        self.shadow = True
        self.beaming = 0
        self.inheritcolor = 0  # Unused ?
        self.transparencyhint = 0
        self.shininess = 0
        self.rotatetexture = 0
        self.material = nvb_material.Material()
        self.vertex_coords = []
        self.texture_coordinates = [[]]  # list of tex coords = uv layers
        self.facedef = []
        self.tangents = []
        self.normals = []
        self.colors = []

    def loadAsciiLine(self, itlines):
        """TODO: Doc."""
        line = Node.loadAsciiLine(self, itlines)
        if line:
            label = line[0].lower()
            if label == 'tilefade':
                self.tilefade = nvb_parse.ascii_int(line[1])
            elif label == 'render':
                self.render = nvb_parse.ascii_bool(line[1])
            elif label == 'shadow':
                self.shadow = nvb_parse.ascii_bool(line[1])
            elif label == 'beaming':
                self.beaming = int(line[1])
            elif label == 'inheritcolor':
                self.inheritcolor = int(line[1])
            elif label == 'rotatetexture':
                self.rotatetexture = int(line[1])
            elif label == 'transparencyhint':
                self.transparencyhint = nvb_parse.ascii_int(line[1])
            elif label == 'shininess':
                self.shininess = nvb_parse.ascii_int(line[1])
            elif label == 'verts':
                if not self.vertex_coords:
                    nvals = int(line[1])
                    tmp = [next(itlines) for _ in range(nvals)]
                    self.vertex_coords = [tuple(map(nvb_utils.str2float, v))
                                          for v in tmp]
            elif label == 'faces':
                if not self.facedef:
                    nvals = int(line[1])
                    tmp = [next(itlines) for _ in range(nvals)]
                    self.facedef = [list(map(int, v)) for v in tmp]
            elif label == 'normals':
                if not self.normals:
                    nvals = int(line[1])
                    tmp = [next(itlines) for _ in range(nvals)]
                    self.normals = [tuple(map(nvb_utils.str2float, v))
                                    for v in tmp]
            elif label == 'tangents':
                if not self.tangents:
                    nvals = int(line[1])
                    tmp = [next(itlines) for _ in range(nvals)]
                    self.tangents = [tuple(map(nvb_utils.str2float, v))
                                     for v in tmp]
            elif label == 'colors':
                if not self.colors:
                    nvals = int(line[1])
                    tmp = [next(itlines) for _ in range(nvals)]
                    self.colors = [tuple(map(float, v)) for v in tmp]
            elif label.startswith('tverts'):
                tvid = 0
                if label[6:]:  # might be '', which we interpret as 0
                    tvid = int(label[6:])
                    tvcnt = len(self.texture_coordinates)
                    if tvid+1 > tvcnt:
                        self.texture_coordinates.extend(
                            [[] for _ in range(tvid-tvcnt+1)])
                if not self.texture_coordinates[tvid]:
                    nvals = int(line[1])
                    tmp = [next(itlines) for _ in range(nvals)]
                    self.texture_coordinates[tvid] = \
                        [(float(v[0]), float(v[1])) for v in tmp]
            else:
                self.material.parse_ascii_line(line)
        return line

    def fix_degenerated_uvs(self):
        """Fixes degenerated UVs by adding dummy coordinates."""
        def distance(p0, p1):
            """Euclidean Distance."""
            return math.sqrt(sum([(a - b)**2 for a, b in list(zip(p0, p1))]))

        tvert_cnt = len(self.texture_coordinates[0])
        if tvert_cnt > 0:
            add_dummy_uvs = False
            for f in self.facedef:
                uvs = self.texture_coordinates[0][f[4]], \
                      self.texture_coordinates[0][f[5]], \
                      self.texture_coordinates[0][f[6]]
                min_distance = distance(uvs[0], uvs[1])
                for p0, p1 in itertools.combinations(uvs, 2):
                    min_distance = min(min_distance, distance(p0, p1))
                # tverts are too close == degenerated
                if min_distance <= 0.001:
                    add_dummy_uvs = True
                    f[4], f[5], f[6] = tvert_cnt, tvert_cnt + 1, tvert_cnt + 2
            if add_dummy_uvs:
                self.texture_coordinates[0].extend([(0, 0), (0, 1), (1, 1)])

    @staticmethod
    def create_vertex_colors(mesh, vcolors, vcname):
        """Create a color map from a per-vertex color list for the mesh."""
        # Sample data
        # vert_uvs = [(random(), random()) for i in range(len(me.vertices))]
        # me.uv_textures.new("test")
        # me.uv_layers[-1].data.foreach_set("uv",
        #     [uv for pair in [vert_uvs[l.vertex_index]
        #      for l in me.loops] for uv in pair])

        cmap = None
        if vcolors:
            cmap = mesh.vertex_colors.new(vcname)
            # Get all loops for each vertex
            vert_loop_map = {}
            for l in mesh.loops:
                if l.vertex_index in vert_loop_map:
                    vert_loop_map[l.vertex_index].append(l.index)
                else:
                    vert_loop_map[l.vertex_index] = [l.index]
            # Set color for each vertex (in every loop)
            # BUGFIX: colors have dim 4 on some systems
            #         (should be 3 as per documentation)
            color_dim = len(cmap.data[0].color)
            if color_dim > 3:
                for vidx in vert_loop_map:
                    for lidx in vert_loop_map[vidx]:
                        cmap.data[lidx].color = \
                            (*vcolors[vidx], *[0]*(color_dim-3))
            else:  # Keep the right way separate for speed
                for vidx in vert_loop_map:
                    for lidx in vert_loop_map[vidx]:
                        cmap.data[lidx].color = vcolors[vidx]
        return cmap

    @staticmethod
    def create_sharp_edges(blen_mesh, sgr_list):
        """Create sharp edges from (per face) smoothgroup list."""
        bm = bmesh.new()
        bm.from_mesh(blen_mesh)
        if hasattr(bm.edges, "ensure_lookup_table"):
            bm.edges.ensure_lookup_table()
        # Mark edge as sharp if its faces belong to different smooth groups
        for e in bm.edges:
            f = e.link_faces
            if (len(f) > 1) and (sgr_list[f[0].index] != sgr_list[f[1].index]):
                edgeIdx = e.index
                blen_mesh.edges[edgeIdx].use_edge_sharp = True
        bm.free()
        del bm

    def create_blender_mesh(self, blen_name, options):
        """TODO: Doc."""

        # Create a Blender mesh
        blen_mesh = bpy.data.meshes.new(name=blen_name)
        # Create vertices
        blen_mesh.vertices.add(len(self.vertex_coords))
        blen_mesh.vertices.foreach_set('co', unpack_list(self.vertex_coords))

        # Create faces
        face_vertex_indices = [v[0:3] for v in self.facedef]
        face_cnt = len(face_vertex_indices)
        # Loops
        blen_mesh.loops.add(face_cnt * 3)
        blen_mesh.loops.foreach_set('vertex_index',
                                    unpack_list(face_vertex_indices))
        # Polygons
        blen_mesh.polygons.add(face_cnt)
        blen_mesh.polygons.foreach_set('loop_start', range(0, face_cnt * 3, 3))
        blen_mesh.polygons.foreach_set('loop_total', (3,) * face_cnt)

        blen_mesh.validate(clean_customdata=False)
        num_blen_polygons = len(blen_mesh.polygons)

        if not blen_mesh.polygons:
            return

        # Set everything to smooth
        blen_mesh.polygons.foreach_set('use_smooth',
                                       [True] * num_blen_polygons)

        # Create material
        if self.render and options.importMaterials:
            reuse_existing = (self.nodetype != nvb_def.Nodetype.ANIMMESH)
            material = self.material.create_blender_material(
                options, reuse_existing)
            if material:
                blen_mesh.materials.append(material)
                # Set material idx (always 0, only a single material)
                blen_mesh.polygons.foreach_set('material_index',
                                               [0] * num_blen_polygons)

        # Create UV maps
        if self.facedef:
            face_uv_indices = [(f[4], f[5], f[6]) for f in self.facedef]
            # EEEKADOODLE fix - Not necessary?
            # face_uv_indices = \
            #    [(f[5], f[6], f[4]) if f[6] == 0 else (f[4], f[5], f[6])
            #     for f in self.facedef]
            face_uv_indices = unpack_list(face_uv_indices)

            for layer_idx, uv_coords in enumerate(self.texture_coordinates):
                if uv_coords:
                    face_uv_coords = [uv_coords[uvi]
                                      for uvi in face_uv_indices]
                    face_uv_coords = unpack_list(face_uv_coords)
                    uv_layer = blen_mesh.uv_layers.new(do_init=False)
                    uv_layer.name = "tverts"+str(layer_idx)
                    uv_layer.data.foreach_set('uv', face_uv_coords[:2*len(uv_layer.data)])

        # Create Vertex colors
        Trimesh.create_vertex_colors(blen_mesh, self.colors, 'colors')

        # Import smooth groups as sharp edges
        if options.importSmoothGroups:
            blen_mesh.update()
            self.create_sharp_edges(blen_mesh, [f[3] for f in self.facedef])

        if self.normals and blen_mesh.loops and options.import_normals:
            # Create normals and use them for shading
            blen_mesh.vertices.foreach_set('normal', unpack_list(self.normals))
            blen_mesh.create_normals_split()
        elif options.importSmoothGroups:
            # Use shading groups for shading
            # (single smoothgroup with value 0 means non-smooth)
            sgr_list = set([fd[3] for fd in self.facedef])
            if len(sgr_list) == 1 and sgr_list.pop() == 0:  # non-smooth
                blen_mesh.polygons.foreach_set(
                    'use_smooth', [False] * num_blen_polygons)
                blen_mesh.use_auto_smooth = False
                blen_mesh.auto_smooth_angle = 0.523599
            else:
                blen_mesh.use_auto_smooth = True
                blen_mesh.auto_smooth_angle = 1.570796
        blen_mesh.validate(clean_customdata=False)

        return blen_mesh
        """
        # Create uvmaps
        # EEEKADOODLE fix
        eeka_faceuvs = [(f[5], f[6], f[4]) if f[2] == 0 else (f[4], f[5], f[6])
                        for f in self.facedef]
        # eeka_faceuvs = [(f[4], f[5], f[6]) for f in self.facedef]
        # Save fixed uvs for animeshes
        if self.nodetype == nvb_def.Nodetype.ANIMMESH:
            if me.name not in nvb_def.tvert_order:
                nvb_def.tvert_order[me.name] = copy.deepcopy(eeka_faceuvs)
        uvlayers = []
        for idx, tvs in enumerate(self.tverts):
            if tvs:  # may be []
                uvname = me.name + '.tvert' + str(idx)
                uvlayers.append(Trimesh.createUVlayer2(me, tvs, eeka_faceuvs,
                                                       uvname, matimg))
        # if len(uvmaps) > 0 and uvmaps[0] is not None:
        #     me.uv_textures[uvmaps[0].name].active = True  # blender2.8 error!
        # Import smooth groups as sharp edges
        if options.importSmoothGroups:
            me.update()
            me.show_edge_sharp = True
            bm = bmesh.new()
            bm.from_mesh(me)
            if hasattr(bm.edges, "ensure_lookup_table"):
                bm.edges.ensure_lookup_table()
            # Mark edge as sharp if its faces belong to different smooth groups
            for e in bm.edges:
                f = e.link_faces
                if (len(f) > 1) and \
                   (self.facedef[f[0].index][3] !=
                        self.facedef[f[1].index][3]):
                    edgeIdx = e.index
                    me.edges[edgeIdx].use_edge_sharp = True
            bm.free()
            del bm

        # Import custom normals
        blen_mesh.update()
        if self.normals and blen_mesh.loops and options.import_normals:
            for l in blen_mesh.loops:
                l.normal[:] = self.normals[l.vertex_index]
            blen_mesh.validate(clean_customdata=False)
            clnors = array.array('f', [0.0] * (len(blen_mesh.loops) * 3))
            blen_mesh.loops.foreach_get('normal', clnors)
            blen_mesh.normals_split_custom_set(tuple(
                                               zip(*(iter(clnors),) * 3)))
            blen_mesh.polygons.foreach_set('use_smooth',
                                           [True] * len(blen_mesh.polygons))
            blen_mesh.use_auto_smooth = True
            # me.show_edge_sharp = True
        else:
            blen_mesh.validate()
        """

    def createObjectData(self, obj, options):
        """TODO: Doc."""
        Node.createObjectData(self, obj, options)

        obj.nvb.meshtype = self.meshtype

        obj.hide_render = not self.render
        obj.nvb.tilefade = nvb_def.Tilefade.NONE
        if (self.tilefade >= 1):
            obj.hide_render = obj.hide_render and options.hide_fading
            if self.tilefade == 1:
                obj.nvb.tilefade = nvb_def.Tilefade.FADE
            elif self.tilefade == 2:
                obj.nvb.tilefade = nvb_def.Tilefade.BASE
            elif self.tilefade == 4:
                obj.nvb.tilefade = nvb_def.Tilefade.NEIGHBOUR

        obj.nvb.shadow = self.shadow
        obj.nvb.beaming = (self.beaming >= 1)
        obj.nvb.inheritcolor = (self.inheritcolor >= 1)
        obj.nvb.rotatetexture = (self.rotatetexture >= 1)
        obj.nvb.transparencyhint = self.transparencyhint
        obj.nvb.shininess = self.shininess
        obj.color = (*self.wirecolor, 1.0)

    def createObject(self, options):
        """TODO: Doc."""
        mesh = self.create_blender_mesh(self.name, options)
        obj = bpy.data.objects.new(self.name, mesh)
        self.createObjectData(obj, options)
        return obj

    @staticmethod
    def generateAsciiMesh(obj, ascii_lines, options):
        """TODO: Doc."""

        def mesh_triangulate(mesh):
            """Triangulate a msesh using bmesh to retain sharp edges."""
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.triangulate(bm, faces=bm.faces)
            bm.to_mesh(mesh)
            bm.free()
            del bm

        def mesh_get_smoothgroups(mesh, obj, options):
            """Get the smoothing group for each face."""
            groups = []
            if (obj.nvb.smoothgroup == 'SEPR') or \
               (obj.nvb.meshtype == nvb_def.Meshtype.AABB) or \
               (not options.export_smoothgroups):
                # 0 = Do not use smoothgroups
                groups = [0] * len(mesh.polygons)
            elif (obj.nvb.smoothgroup == 'SING') or \
                 (options.export_normals):
                # All faces belong to smooth group 1
                groups = [1] * len(mesh.polygons)
            else:
                groups, _ = mesh.calc_smooth_groups()
            return groups

        def mesh_get_normals(mesh, uvmap):
            """Get normals and tangets for this mesh."""
            mesh.calc_tangents(uvmap=uvmap.name)  # calls calc_normals_split()

            # per_loop_data = [(l.vertex_index, l.normal, l.tangent, l.bitangent_sign)
            #                  for l in mesh.loops]
            # per_vertex_data = [[(n, t, b) for n, t, b in per_loop_data if i == vidx]
            #                    for vidx in range(len(mesh.vertices))]
            per_vertex_data = {l.vertex_index: (l.normal,
                                                l.tangent,
                                                l.bitangent_sign)
                               for l in mesh.loops}
            normals = [d[0] for d in per_vertex_data.values()]
            tangents = [[*d[1]] + [d[2]] for d in per_vertex_data.values()]
            return normals, tangents

        def mesh_get_uvs_to_export(mesh, uv_order='ACT'):
            """Get a list of uv layers to export."""
            uv_layer_list = []
            if mesh.uv_layers.active:
                if uv_order == 'ACT':
                    # Export active uvmap only
                    uv_layer_list = [mesh.uv_layers.active]
                elif uv_order == 'AL0':
                    # Export all, sort alphabetically
                    uv_layer_list = [uvl for uvl in mesh.uv_layers]
                    uv_layer_list.sort()
                elif uv_order == 'AL1':
                    # Export all, sort alphabetically, put active first
                    uv_active_name = mesh.uv_layers.active.name
                    uv_layer_list = [uvl for uvl in mesh.uv_layers
                                     if not uvl.name == uv_active_name]
                    uv_layer_list.sort()
                    uv_layer_list = [mesh.uv_layers.active] + uv_layer_list
            return uv_layer_list[:3]

        def mesh_get_uvs(mesh, uvl_to_export, merge_uvs=False):
            """Get UV data for this mesh."""
            sig_dig = 4
            uv_indices = [[*p.loop_indices] for p in mesh.polygons]
            # Grab the uv coordinates for all layers we have to export
            uv_coord_list = [[tuple(map(lambda x: round(x, sig_dig), d.uv))
                              for d in uvl.data] for uvl in uvl_to_export]
            # We can merge if there is only a single set of uv coordinates
            if merge_uvs:
                # Keyable tuples of per-loop uv-coords across all uv-layers
                # uv_coords = [tuple([c for lc in uvl_coords for c in lc])
                #              for uvl_coords in zip(*uv_coord_list)]
                uv_tuples = [co for co in zip(*uv_coord_list)]
                uv_tuples_unique = dict()
                idx_unique = 0
                uv_index_trans = dict()
                for idx, uv_tuple in enumerate(uv_tuples):
                    if uv_tuple in uv_tuples_unique:
                        uv_index_trans[idx] = uv_tuples_unique[uv_tuple]
                    else:
                        uv_tuples_unique[uv_tuple] = idx_unique
                        uv_index_trans[idx] = idx_unique
                        idx_unique = idx_unique + 1
                # Adjust the uv indices to unique coordinates
                uv_indices = [[uv_index_trans[i] for i in uvi]
                              for uvi in uv_indices]
                uv_coord_list = list(zip(*uv_tuples_unique.keys()))

            return uv_indices, uv_coord_list

        def mesh_get_vertex_colors(mesh):
            """Get per-vertex vertex colors as list of RGBs."""
            vcolors = mesh.vertex_colors.active
            if not vcolors:
                return []
            vcolor_data = vcolors.data
            per_loop_data = {l.vertex_index: vc.color[:3]
                             for l, vc in zip(mesh.loops, vcolor_data)}
            return per_loop_data.values()

        me = obj.to_mesh(options.depsgraph,
                         options.apply_modifiers,
                         calc_undeformed=False)
        # me.polygons.foreach_set("use_smooth", [True]*len(me.polygons))

        # Triangulate
        mesh_triangulate(me)

        # Add vertices
        me_vertices = me.vertices
        ascii_lines.append('  verts ' + str(len(me_vertices)))
        fstr = '   ' + 3 * ' {: 8.5f}'
        ascii_lines.extend([fstr.format(*v.co) for v in me_vertices])

        # Per face uv indices and a list of their coordinates
        me_face_uv = [[0, 0, 0]] * len(me.polygons)
        dig_u = 1  # digits for formatting
        if (options.uvmapMode == 'ALL') or \
           (options.uvmapMode == 'REN' and not obj.hide_render):
            # Adds scaling factor from the texture slot to uv coordinates
            # uvScale = (1.0, 1.0)
            # if obj.active_material:
            #     if obj.active_material.active_texture:

            # Find out which UV layers to export:
            uv_layer_list = mesh_get_uvs_to_export(me, options.uvmapOrder)

            # Check if we can merge uvs
            merge_uvs = ((obj.nvb.meshtype != nvb_def.Meshtype.ANIMMESH) and
                         options.uvmapAutoJoin)

            # Generate the tverts
            me_uv_coord_list = []
            if uv_layer_list:
                me_face_uv, me_uv_coord_list = mesh_get_uvs(
                    me, uv_layer_list, merge_uvs)
                dig_u = len(str(len(me_uv_coord_list[0])))

            # Write tverts to file (if any)
            if me_uv_coord_list:
                fstr = '    {: 7.4f} {: 7.4f}  0'
                # First list entry as "tverts"
                fstr_tv = '  tverts {:d}'
                coords = me_uv_coord_list[0]
                ascii_lines.append(fstr_tv.format(len(coords)))
                ascii_lines.extend([fstr.format(c[0], c[1]) for c in coords])
                # Other list entries as "tvertsN"
                fstr_tv = '  tverts{:d} {:d}'
                for idx, coords in enumerate(me_uv_coord_list[1:]):
                    ascii_lines.append(fstr_tv.format(idx+1, len(coords)))
                    ascii_lines.extend([fstr.format(c[0], c[1]) for c in coords])
                del me_uv_coord_list

                # Write normals and tangents
                if options.export_normals and not obj.hide_render:
                    normal_uv = uv_layer_list[0].name
                    me_normals, me_tangents = mesh_get_normals(me, normal_uv)

                    ascii_lines.append('  normals ' + str(len(me_normals)))
                    fstr = '   ' + 3 * ' {: 8.5f}'
                    ascii_lines.extend([fstr.format(*n) for n in me_normals])
                    del me_normals

                    ascii_lines.append('  tangents ' + str(len(me_tangents)))
                    fstr = '   ' + 3 * ' {: 8.5f}' + ' {: 3.1f}'
                    ascii_lines.extend([fstr.format(*t) for t in me_tangents])
                    del me_tangents

        # Generate Smoothgroups
        me_face_grp = mesh_get_smoothgroups(me, obj, options)
        dig_g = max(1, len(str(max(me_face_grp)))) # digits for formatting

        # Face vertex indices
        me_face_vert = [tuple(p.vertices) for p in me.polygons]
        dig_v = max(1, len(str(len(me_vertices)))) # digits for formatting

        # Face material indices
        me_face_mat = [p.material_index for p in me.polygons]
        dig_m = max(1, len(str(max(me_face_mat))))  # digits for formatting

        # Vertex color
        me_vert_colors = mesh_get_vertex_colors(me)
        if me_vert_colors:
            ascii_lines.append('  colors ' + str(len(me_vert_colors)))
            fstr = '   ' + 3 * ' {:3.2f}'
            ascii_lines.extend([fstr.format(*vc) for vc in me_vert_colors])

        # Write faces to file
        face_data = zip(me_face_vert, me_face_grp, me_face_uv, me_face_mat)
        ascii_lines.append('  faces ' + str(len(me_face_vert)))
        fstr = '   ' + \
               3 * (' {:' + str(dig_v) + 'd}') + ' {:' + str(dig_g) + 'd} ' + \
               3 * (' {:' + str(dig_u) + 'd}') + ' {:' + str(dig_m) + 'd}'
        ascii_lines.extend([fstr.format(*fd[0], fd[1], *fd[2], fd[3])
                            for fd in face_data])
        bpy.data.meshes.remove(me)

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options, iswalkmesh=False):
        """TODO: Doc."""
        Node.generateAsciiData(obj, asciiLines, options, iswalkmesh)

        if options.export_wirecolor:
            fstr = '  wirecolor' + 3 * ' {:3.2f}'
            asciiLines.append(fstr.format(*obj.color[:3]))

        if  not iswalkmesh:
            nvb_material.Material.generate_ascii(obj, asciiLines, options)
            # Shininess
            asciiLines.append('  shininess ' + str(obj.nvb.shininess))
            # Render and Shadow
            if not obj.nvb.shadow or obj.hide_render:  # Skip default value
                asciiLines.append('  render ' + str(int(not obj.hide_render)))
                asciiLines.append('  shadow ' + str(int(obj.nvb.shadow)))
            # Beaming
            val = int(obj.nvb.beaming)
            if val > 0:  # Skip default value
                asciiLines.append('  beaming ' + str(val))
            # Inherit color from parent
            val = int(obj.nvb.inheritcolor)
            if val > 0:  # Skip default value
                asciiLines.append('  inheritcolor ' + str(val))
            # Transparency hint (rendering order)
            val = obj.nvb.transparencyhint
            if val > 0:  # Skip default value
                asciiLines.append('  transparencyhint ' + str(val))
            # These two are for tiles only
            if options.classification == nvb_def.Classification.TILE:
                asciiLines.append('  rotatetexture ' +
                                  str(int(obj.nvb.rotatetexture)))
                asciiLines.append('  tilefade ' + obj.nvb.tilefade)

        Trimesh.generateAsciiMesh(obj, asciiLines, options)


class Animmesh(Trimesh):
    """Mesh with animated UV coordinates of vertices."""

    nodetype = nvb_def.Nodetype.ANIMMESH

    def __init__(self, name='UNNAMED'):
        """TODO: Doc."""
        Trimesh.__init__(self, name)
        self.meshtype = nvb_def.Meshtype.ANIMMESH


class Danglymesh(Trimesh):
    """TODO: Doc."""

    nodetype = nvb_def.Nodetype.DANGLYMESH

    def __init__(self, name='UNNAMED'):
        """TODO: Doc."""
        Trimesh.__init__(self, name)
        self.meshtype = nvb_def.Meshtype.DANGLYMESH

        self.period = 1.0
        self.tightness = 1.0
        self.displacement = 1.0
        self.constraints = []

    def loadAsciiLine(self, itlines):
        """TODO: Doc."""
        line = Trimesh.loadAsciiLine(self, itlines)
        if line:
            label = line[0].lower()
            if label == 'period':
                self.period = nvb_parse.ascii_float(line[1])
            elif label == 'tightness':
                self.tightness = nvb_parse.ascii_float(line[1])
            elif label == 'displacement':
                self.displacement = nvb_parse.ascii_float(line[1])
            elif label == 'constraints':
                if not self.constraints:
                    vcnt = int(line[1])
                    tmp = [next(itlines) for _ in range(vcnt)]
                    self.constraints = [float(v[0]) for v in tmp]
        return line

    def createConstraints(self, obj):
        """Create a vertex group for the object."""
        """
        Create a vertex group for the object to contain the vertex
        weights for the danglymesh. The weights are called "constraints"
        in NWN. Range is [0.0, 255.0] as opposed to [0.0, 1.0] in Blender
        """
        vgroup = obj.vertex_groups.new(name='constraints')
        for vertexIdx, constraint in enumerate(self.constraints):
            weight = constraint/255
            vgroup.add([vertexIdx], weight, 'REPLACE')
        obj.nvb.constraints = vgroup.name

    def createObjectData(self, obj, options):
        """TODO: Doc."""
        Trimesh.createObjectData(self, obj, options)

        obj.nvb.period = self.period
        obj.nvb.tightness = self.tightness
        obj.nvb.displacement = self.displacement
        self.createConstraints(obj)

    @staticmethod
    def generateAsciiConstraints(obj, asciiLines, options):
        """Creates a list of constraint and adds them to ascii lines."""
        vg_name = obj.nvb.constraints
        if vg_name not in obj.vertex_groups:
            print('Neverblender: WARNING - No constraints for danglymesh ' +
                  obj.name)
            weights = [0] * len(obj.data.vertices)
            asciiLines.extend(['    {: 5.1f}'.format(w) for w in weights])
            return
        vg = obj.vertex_groups[vg_name]
        vg_idx = vg.index
        vg_members = [v.index for v in obj.data.vertices
                      if vg_idx in [g.group for g in v.groups]]
        weights = [0.0] * len(obj.data.vertices)
        asciiLines.append('  constraints ' + str(len(weights)))
        for i in vg_members:
            weights[i] = vg.weight(i)*255
        asciiLines.extend(['    {: 5.1f}'.format(w) for w in weights])

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options, iswalkmesh=False):
        """TODO: Doc."""
        Trimesh.generateAsciiData(obj, asciiLines, options, iswalkmesh)
        if iswalkmesh:
            return
        asciiLines.append('  period ' + str(round(obj.nvb.period, 3)))
        asciiLines.append('  tightness ' + str(round(obj.nvb.tightness, 3)))
        asciiLines.append('  displacement ' +
                          str(round(obj.nvb.displacement, 3)))
        Danglymesh.generateAsciiConstraints(obj, asciiLines, options)


class Skinmesh(Trimesh):
    """Skinmeshes are Trimeshes where every vertex has a weight."""

    nodetype = nvb_def.Nodetype.SKIN

    def __init__(self, name='UNNAMED'):
        """TODO: Doc."""
        Trimesh.__init__(self, name)
        self.meshtype = nvb_def.Meshtype.SKIN

        self.weights = []

    def loadAsciiWeights(self, asciiLines):
        """TODO: Doc."""
        def chunker(seq, size):
            """TODO: DOC."""
            return (seq[pos:pos + size] for pos in range(0, len(seq), size))

        for line in asciiLines:
            # A line looks like this
            # [group_name, vertex_weight, group_name, vertex_weight]
            # We create a list looking like this:
            # [[group_name, vertex_weight], [group_name, vertex_weight]]
            name_weight_pairs = []
            for chunk in chunker(line, 2):
                try:
                    n = chunk[0]
                    w = chunk[1]
                except IndexError:
                    continue
                try:
                    n = nvb_parse.ascii_identifier(n)
                    w = nvb_parse.ascii_float(w)
                except ValueError:
                    continue
                if not any(gwp[0] == n for gwp in name_weight_pairs):
                    name_weight_pairs.append([n, w])
            self.weights.append(name_weight_pairs)

    def loadAsciiLine(self, itlines):
        """TODO: Doc."""
        line = Trimesh.loadAsciiLine(self, itlines)
        if line:
            label = line[0].lower()
            if label == 'weights':
                cnt = int(line[1])
                tmp = [next(itlines) for _ in range(cnt)]
                self.loadAsciiWeights(tmp)
        return line

    def createSkinGroups(self, obj):
        """TODO: Doc."""
        skinGroupDict = {}
        for vertIdx, vertMemberships in enumerate(self.weights):
            for membership in vertMemberships:
                if membership[0] in skinGroupDict:
                    skinGroupDict[membership[0]].add([vertIdx],
                                                     membership[1],
                                                     'REPLACE')
                else:
                    vgroup = obj.vertex_groups.new(name=membership[0])
                    skinGroupDict[membership[0]] = vgroup
                    vgroup.add([vertIdx], membership[1], 'REPLACE')

    def createObjectData(self, obj, options):
        """TODO: Doc."""
        Trimesh.createObjectData(self, obj, options)

        self.createSkinGroups(obj)

    @staticmethod
    def generate_ascii_weights(obj, ascii_lines, options):
        """TODO: Doc."""
        def clean_weights(weight_list):
            # Sort by weight, largest first
            cleaned_list = sorted(weight_list, reverse=True,
                                  key=lambda x: x[1])
            # Discard zero weights (< 0.001 will do)
            cleaned_list = [[w[0], round(w[1], 3)] for w in cleaned_list]
            cleaned_list = [w for w in cleaned_list if w[1] >= 0.001]
            # Only four weights are allowed
            cleaned_list = cleaned_list[:4]
            # Normalize
            s = sum([w[1] for w in cleaned_list])
            cleaned_list = [[w[0], w[1]/s] for w in cleaned_list]
            return cleaned_list
        # Only vertex groups with names matching an object qualify
        skingroups = {vg.index: vg.name for vg in obj.vertex_groups
                      if vg.name in bpy.data.objects}
        ascii_lines.append('  weights ' + str(len(obj.data.vertices)))
        fstr = '{} {:5.3f}'
        for v in obj.data.vertices:
            weights = [[skingroups[g.group], g.weight] for g in v.groups
                       if g.group in skingroups]
            weights = clean_weights(weights)
            ascii_lines.append('    ' + ' '.join([fstr.format(*w)
                                                  for w in weights]))

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options, iswalkmesh=False):
        """TODO: Doc."""
        Trimesh.generateAsciiData(obj, asciiLines, options, iswalkmesh)
        if iswalkmesh:
            return
        Skinmesh.generate_ascii_weights(obj, asciiLines, options)


class Emitter(Node):
    """TODO: Doc."""

    nodetype = nvb_def.Nodetype.EMITTER
    # mdl name: (blender data path, data dimension, conversion, mdl format)
    property_dict = \
        {'update': ('nvb.update', 1, nvb_utils.str2identifier, ' {:s}'),
         'loop': ('nvb.loop', 1, nvb_utils.str2bool, ' {:1d}'),
         'render': ('nvb.render', 1, nvb_utils.str2identifier, ' {:s}'),
         'blend': ('nvb.blend', 1, nvb_utils.str2identifier, ' {:s}'),
         'spawntype': ('nvb.spawntype', 1, nvb_utils.str2identifier, ' {:s}'),
         'renderorder': ('nvb.renderorder', 1, nvb_utils.str2int, ' {:1.0f}'),
         'birthrate': ('nvb.birthrate', 1, nvb_utils.str2int, ' {:1.0f}'),
         'lifeexp': ('nvb.lifeexp', 1, float, ' {:1.0f}'),
         'mass': ('mass', 1, float, ' {: >3.2f}'),
         'velocity': ('normal_factor', 1, float, ' {:>4.2f}'),
         'randvel': ('factor_random', 1, float, ' {:>4.2f}'),
         'particlerot': ('angular_velocity_factor', 1, float, ' {:>4.2f}'),
         'spread': ('nvb.spread', 1, float, ' {:>4.2f}'),
         'splat': ('nvb.splat', 1, nvb_utils.str2bool, ' {:1d}'),
         'affectedbywind': ('nvb.affectedbywind', 1, nvb_utils.str2bool,
                            ' {:1d}'),
         'colorstart': ('nvb.colorstart', 3, float, ' {:4.2f}'),
         'colorend': ('nvb.colorend', 3, float, ' {:4.2f}'),
         'alphastart': ('nvb.alphastart', 1, float, ' {:>4.2f}'),
         'alphaend': ('nvb.alphaend', 1, float, ' {:>4.2f}'),
         'sizestart': ('nvb.sizestart', 1, float, ' {:>4.2f}'),
         'sizeend': ('nvb.sizeend', 1, float, ' {:>4.2f}'),
         'sizestart_y': ('nvb.sizestart_y', 1, float, ' {:>4.2f}'),
         'sizeend_y': ('nvb.sizeend_y', 1, float, ' {:>4.2f}'),
         'bounce': ('nvb.bounce', 1, nvb_utils.str2bool, ' {:1d}'),
         'bounce_co': ('nvb.bounce_co', 1, float, ' {:>4.2f}'),
         'blurlength': ('nvb.blurlength', 1, float, ' {:>4.2f}'),
         'deadspace': ('nvb.deadspace', 1, float, ' {:>4.2f}'),
         # Texture
         'texture': ('nvb.texture', 1, nvb_utils.str2texture, ' {:s}'),
         'chunk': ('nvb.chunk', 1, nvb_utils.str2texture, ' {:s}'),
         'twosidedtex': ('nvb.twosidedtex', 1, nvb_utils.str2bool, ' {:1d}'),
         'm_istinted': ('nvb.m_istinted', 1, nvb_utils.str2bool, ' {:1d}'),
         # Texture animations
         'xgrid': ('nvb.xgrid', 1, nvb_utils.str2int, ' {:1.0f}'),
         'ygrid': ('nvb.ygrid', 1, nvb_utils.str2int, ' {:1.0f}'),
         'fps': ('nvb.fps', 1, float, ' {:1.0f}'),
         'framestart': ('nvb.framestart', 1, nvb_utils.str2int, ' {:1d}'),
         'frameend': ('nvb.frameend', 1, nvb_utils.str2int, ' {:1d}'),
         'random': ('nvb.random', 1, nvb_utils.str2bool, ' {:1d}'),
         # Point to Point Properties
         'p2p': ('nvb.p2p', 1, nvb_utils.str2bool, ' {:1d}'),
         'p2p_sel': ('nvb.p2p_sel', 1, nvb_utils.str2identifier, ' {:s}'),
         'bezier2': ('nvb.bezier2', 1, float, ' {:>4.2f}'),
         'bezier3': ('nvb.bezier2', 1, float, ' {:>4.2f}'),
         'combinetime': ('nvb.combinetime', 1, float, ' {:>4.2f}'),
         'grav': ('nvb.grav', 1, float, ' {:>4.2f}'),
         'drag': ('nvb.drag', 1, float, ' {:>4.2f}'),
         'threshold': ('nvb.threshold', 1, float, ' {:>4.2f}'),
         # Blast properties
         'blastradius': ('nvb.blastradius', 1, float, ' {:>4.2f}'),
         'blastlength': ('nvb.blastlength', 1, float, ' {:>4.2f}'),
         # Lightning properties
         'lightningdelay': ('nvb.lightningdelay', 1, float, ' {:>4.2f}'),
         'lightningradius': ('nvb.lightningradius', 1, float, ' {:>4.2f}'),
         'lightningscale': ('nvb.lightningscale', 1, float, ' {:>4.2f}'),
         # Inheritance Properties
         'inherit': ('nvb.inherit', 1, nvb_utils.str2bool, ' {:1d}'),
         'inheritvel': ('nvb.inheritvel', 1, nvb_utils.str2bool, ' {:1d}'),
         'inherit_local': ('nvb.inherit_local', 1, nvb_utils.str2bool,
                           ' {:1d}'),
         'inherit_part': ('nvb.inherit_part', 1, nvb_utils.str2bool, ' {:1d}')}

    def __init__(self, name='UNNAMED'):
        """TODO: Doc."""
        Node.__init__(self, name)
        self.meshtype = nvb_def.Meshtype.EMITTER

        self.xsize = 10  # emitter mesh size (in cm)
        self.ysize = 10  # emitter mesh size (in cm)
        self.blender_data = []
        self.blender_data_nvb = []

        self.vertex_coords = [(1.0,  1.0, 0.0),
                              (1.0, -1.0, 0.0),
                              (-1.0, -1.0, 0.0),
                              (-1.0,  1.0, 0.0)]
        self.facedef = [(0, 1, 0)]

    def loadAsciiLine(self, itlines):
        """TODO: Doc."""
        line = Node.loadAsciiLine(self, itlines)
        if line:
            label = line[0].lower()
            if label == 'xsize':  # emitter mesh size (in cm)
                self.xsize = float(line[1])
            elif label == 'ysize':  # emitter mesh size (in cm)
                self.ysize = float(line[1])
            else:
                if label in type(self).property_dict:
                    data_path, dim, convert, _ = self.property_dict[label]
                    if dim > 1:
                        value = tuple(list(map(convert, line[1:dim+1])))
                    else:
                        value = convert(line[1].lower())
                    self.blender_data.append((data_path, value))
        return line

    def create_particle_system(self, obj, options):
        part_mod = obj.modifiers.new(name='particles', type='PARTICLE_SYSTEM')
        part_sys_settings = part_mod.particle_system.settings
        for data_path, value in self.blender_data:
            if data_path.startswith("nvb."):
                part_sys_settings.nvb.__setattr__(data_path[4:], value)
            else:
                part_sys_settings.__setattr__(data_path, value)
        # Set particle type to chunk if chunk is defined and not null
        if nvb_utils.str2identifier(part_sys_settings.nvb.chunk):
            part_sys_settings.nvb.particletype == 'chunk'
        else:
            part_sys_settings.nvb.particletype == 'texture'
        part_sys_settings.count = 0  # for now

    def create_blender_mesh(self, objName, options):
        """TODO: Doc."""
        # Create the mesh itself
        blen_mesh = bpy.data.meshes.new(objName)
        # Create vertices
        blen_mesh.vertices.add(len(self.vertex_coords))
        blen_mesh.vertices.foreach_set('co', unpack_list(self.vertex_coords))
        # Create faces
        face_vids = [v[0:3] for v in self.facedef]  # face vertex indices
        face_cnt = len(face_vids)
        blen_mesh.polygons.add(face_cnt)
        blen_mesh.loops.add(face_cnt * 3)
        blen_mesh.polygons.foreach_set('loop_start', range(0, face_cnt * 3, 3))
        blen_mesh.polygons.foreach_set('loop_total', (3,) * face_cnt)
        blen_mesh.loops.foreach_set('vertex_index', unpack_list(face_vids))
        blen_mesh.update()

        em_size = (max(self.xsize/100, 0), max(self.ysize/100, 0))
        scale_mat = mathutils.Matrix.Scale(em_size[0], 4, [1, 0, 0]) @ \
            mathutils.Matrix.Scale(em_size[1], 4, [0, 1, 0])
        blen_mesh.transform(scale_mat)

        blen_mesh.validate()
        blen_mesh.update()

        return blen_mesh

    def createObjectData(self, obj, options):
        """TODO: Doc."""
        Node.createObjectData(self, obj, options)

        obj.nvb.meshtype = self.meshtype
        self.create_particle_system(obj, options)

    def createObject(self, options):
        """TODO: Doc."""
        mesh = self.create_blender_mesh(self.name, options)
        obj = bpy.data.objects.new(self.name, mesh)
        obj.nvb.imporder = self.nodeidx
        obj.hide_render = True
        self.createObjectData(obj, options)
        return obj

    @classmethod
    def generate_ascii_emitter(cls, obj, ascii_lines, options):
        """Adds emitter paramters to ascii lines."""
        def form_prop(prop_name, value):
            """Format an emitter property for export."""
            _, dp_dim, _, val_fstr = Emitter.property_dict[prop_name]
            if dp_dim > 1:
                fstr = '  ' + prop_name + dp_dim * val_fstr
                return fstr.format(*value)
            else:
                fstr = '  ' + prop_name + val_fstr
                return fstr.format(value)

        part_sys = obj.particle_systems.active
        if not part_sys:
            return
        part_set = part_sys.settings
        if not part_set:
            return

        ascii_lines.append('xsize ' + str(obj.dimensions.x*100))
        ascii_lines.append('ysize ' + str(obj.dimensions.y*100))
        # Emitter Properties
        ascii_lines.append(form_prop('update', part_set.nvb.update))
        ascii_lines.append(form_prop('render', part_set.nvb.render))
        ascii_lines.append(form_prop('blend', part_set.nvb.blend))
        ascii_lines.append(form_prop('spawntype', part_set.nvb.spawntype))
        ascii_lines.append(form_prop('renderorder', part_set.nvb.renderorder))
        if part_set.nvb.update == 'single':
                    ascii_lines.append(form_prop('loop', part_set.nvb.loop))

        # Particle properties
        ascii_lines.append(form_prop('birthrate', part_set.nvb.birthrate))
        ascii_lines.append(form_prop('lifeexp', part_set.nvb.lifeexp))
        ascii_lines.append(form_prop('mass', part_set.mass))
        ascii_lines.append(form_prop('velocity', part_set.normal_factor))
        ascii_lines.append(form_prop('randvel', part_set.factor_random))
        ascii_lines.append(form_prop('particlerot',
                                     part_set.angular_velocity_factor))
        ascii_lines.append(form_prop('spread', part_set.nvb.spread))
        ascii_lines.append(form_prop('splat', part_set.nvb.splat))
        ascii_lines.append(form_prop('affectedbywind',
                                     part_set.nvb.affectedbywind))
        ascii_lines.append(form_prop('colorstart', part_set.nvb.colorstart))
        ascii_lines.append(form_prop('colorend', part_set.nvb.colorend))
        ascii_lines.append(form_prop('alphastart', part_set.nvb.alphastart))
        ascii_lines.append(form_prop('alphaend', part_set.nvb.alphaend))
        ascii_lines.append(form_prop('sizestart', part_set.nvb.sizestart))
        ascii_lines.append(form_prop('sizeend', part_set.nvb.sizeend))
        ascii_lines.append(form_prop('sizestart_y', part_set.nvb.sizestart_y))
        ascii_lines.append(form_prop('sizeend_y', part_set.nvb.sizeend_y))
        ascii_lines.append(form_prop('bounce', part_set.nvb.bounce))
        ascii_lines.append(form_prop('bounce_co', part_set.nvb.bounce_co))
        # TODO: Check only needed if spawn=trail?
        ascii_lines.append(form_prop('blurlength', part_set.nvb.blurlength))
        # TODO: Check only needed if update=fountain?
        ascii_lines.append(form_prop('deadspace', part_set.nvb.deadspace))

        # Texture/ Chunk Properties
        if part_set.nvb.particletype == 'chunk':
            ascii_lines.append(form_prop('chunk', part_set.nvb.chunk))
        else:  # 'texture'
            ascii_lines.append(form_prop('texture', part_set.nvb.texture))
            ascii_lines.append(form_prop('twosidedtex',
                                         part_set.nvb.twosidedtex))
            ascii_lines.append(form_prop('m_istinted',
                                         part_set.nvb.m_istinted))
            ascii_lines.append(form_prop('xgrid', part_set.nvb.xgrid))
            ascii_lines.append(form_prop('ygrid', part_set.nvb.ygrid))
            ascii_lines.append(form_prop('fps', part_set.nvb.fps))
            ascii_lines.append(form_prop('framestart',
                                         part_set.nvb.framestart))
            ascii_lines.append(form_prop('frameend', part_set.nvb.frameend))
            ascii_lines.append(form_prop('random', part_set.nvb.random))

        # Point to Point Properties
        ascii_lines.append(form_prop('p2p', part_set.nvb.p2p))
        if part_set.nvb.p2p:
            ascii_lines.append(form_prop('p2p_sel', part_set.nvb.p2p_sel))
            if part_set.nvb.p2p_sel == '1':  # Bezier
                ascii_lines.append(form_prop('bezier2', part_set.nvb.bezier2))
                ascii_lines.append(form_prop('bezier3', part_set.nvb.bezier3))
                ascii_lines.append(form_prop('combinetime',
                                             part_set.nvb.combinetime))
            elif part_set.nvb.p2p_sel == '2':  # Gravity
                ascii_lines.append(form_prop('grav', part_set.nvb.grav))
                ascii_lines.append(form_prop('drag', part_set.nvb.drag))
                ascii_lines.append(form_prop('threshold',
                                             part_set.nvb.threshold))
        # Blast Properties
        ascii_lines.append(form_prop('blastradius', part_set.nvb.blastradius))
        ascii_lines.append(form_prop('blastlength', part_set.nvb.blastlength))
        # Lightning Properties
        if part_set.nvb.update == 'lightning':
            ascii_lines.append(form_prop('lightningdelay',
                                         part_set.nvb.lightningdelay))
            ascii_lines.append(form_prop('lightningradius',
                                         part_set.nvb.lightningradius))
            ascii_lines.append(form_prop('lightningscale',
                                         part_set.nvb.lightningscale))
        # Inheritance Properties
        ascii_lines.append(form_prop('inherit', part_set.nvb.inherit))
        ascii_lines.append(form_prop('inheritvel', part_set.nvb.inheritvel))
        ascii_lines.append(form_prop('inherit_local',
                                     part_set.nvb.inherit_local))
        ascii_lines.append(form_prop('inherit_part',
                                     part_set.nvb.inherit_part))

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options, iswalkmesh=False):
        """TODO: Doc."""
        Node.generateAsciiData(obj, asciiLines, options, iswalkmesh)
        if not iswalkmesh:
            Emitter.generate_ascii_emitter(obj, asciiLines, options)


class Light(Node):
    """TODO: Doc."""

    nodetype = nvb_def.Nodetype.LIGHT

    def __init__(self, name='UNNAMED'):
        """TODO: Doc."""
        Node.__init__(self, name)

        self.shadow = True
        self.radius = 5.0
        self.multiplier = 1
        self.lightpriority = 5
        self.color = (0.0, 0.0, 0.0)
        self.ambientonly = 1
        self.ndynamictype = 1
        self.isdynamic = 1
        self.affectdynamic = 1
        self.negativelight = 0
        self.fadinglight = 1
        self.lensflares = 0
        self.flareradius = 1.0
        self.flareNumValues = [0, 0, 0, 0]
        self.flareTextures = []
        self.flareSizes = []
        self.flarePositions = []
        self.flareCShifts = []  # Flare color shifts

    def loadAsciiLine(self, itlines):
        """TODO: Doc."""
        line = Node.loadAsciiLine(self, itlines)
        if not line:
            return line
        try:
            label = line[0].lower()
        except (IndexError, AttributeError):
            return line  # Probably empty line, skip it
        if (label == 'radius'):
            self.radius = nvb_parse.ascii_float(line[1])
        elif (label == 'shadow'):
            self.shadow = nvb_parse.ascii_bool(line[1])
        elif (label == 'multiplier'):
            self.multiplier = nvb_parse.ascii_float(line[1])
        elif (label == 'color'):
            self.color = tuple([float(v) for v in line[1:4]])
        elif (label == 'ambientonly'):
            self.ambientonly = nvb_parse.ascii_int(line[1])
        elif (label == 'isdynamic'):
            self.isdynamic = nvb_parse.ascii_int(line[1])
        elif (label == 'affectdynamic'):
            self.affectdynamic = nvb_parse.ascii_int(line[1])
        elif (label == 'negativelight'):
            self.negativelight = nvb_parse.ascii_int(line[1])
        elif (label == 'lightpriority'):
            self.lightpriority = nvb_parse.ascii_int(line[1])
        elif (label == 'fadinglight'):
            self.fadinglight = nvb_parse.ascii_int(line[1])
        elif (label == 'lensflares'):
            self.lensflares = nvb_parse.ascii_int(line[1])
        elif (label == 'flareradius'):
            self.flareradius = nvb_parse.ascii_float(line[1])
        elif (label == 'texturenames'):
            if not self.flareTextures:
                vcnt = self.flareNumValues[0]
                tmp = [next(itlines) for _ in range(vcnt)]
                self.flareTextures = [v[0] for v in tmp]
        elif (label == 'flaresizes'):
            if not self.flareSizes:
                vcnt = self.flareNumValues[1]
                tmp = [next(itlines) for _ in range(vcnt)]
                self.flareSizes = [float(v[0]) for v in tmp]
        elif (label == 'flarepositions'):
            if not self.flarePositions:
                vcnt = self.flareNumValues[2]
                tmp = [next(itlines) for _ in range(vcnt)]
                self.flarePositions = [float(v[0]) for v in tmp]
        elif (label == 'flarecolorshifts'):
            if not self.flareCShifts:
                vcnt = self.flareNumValues[3]
                tmp = [next(itlines) for _ in range(vcnt)]
                self.flareCShifts = [tuple(map(float, v)) for v in tmp]
        return line

    def loadNumFlareValues(self, asciiLines):
        """Get the number of values for flares."""
        l_isNumber = nvb_utils.isNumber
        for idx, aline in enumerate(asciiLines):
            try:
                label = aline[0].lower()
            except (IndexError, AttributeError):
                return aline  # Probably empty line or comment
            if not nvb_utils.isNumber(label):
                if (label == 'texturenames'):
                    # Can't do anything here
                    pass
                elif (label == 'flaresizes'):
                    vcnt = next((i for i, v in enumerate(asciiLines[idx+1:])
                                if not l_isNumber(v[0])), -1)
                    self.flareNumValues[1] = vcnt
                elif (label == 'flarepositions'):
                    vcnt = next((i for i, v in enumerate(asciiLines[idx+1:])
                                if not l_isNumber(v[0])), -1)
                    self.flareNumValues[2] = vcnt
                elif (label == 'flarecolorshifts'):
                    vcnt = next((i for i, v in enumerate(asciiLines[idx+1:])
                                if not l_isNumber(v[0])), -1)
                    self.flareNumValues[3] = vcnt
        self.flareNumValues[0] = min(self.flareNumValues[1:])

    def loadAscii(self, asciiLines, nodeidx=-1):
        """TODO: DOC."""
        self.nodeidx = nodeidx
        #  Need to do two passes. First one is to find the number of flares
        aline = self.loadNumFlareValues(asciiLines)
        # Second pass to get the values
        iterable = iter(asciiLines)
        aline = True
        while aline is not None:
            aline = self.loadAsciiLine(iterable)

    def createLamp(self, name):
        """TODO: Doc."""
        lamp = bpy.data.lights.new(name, 'POINT')

        lamp.color = self.color
        lamp.energy = self.multiplier
        lamp.distance = self.radius

        return lamp

    def createObjectData(self, obj, options):
        """TODO: Doc."""
        Node.createObjectData(self, obj, options)
        obj.nvb.lighttype = nvb_def.Lighttype.getType(self.name)

        data = obj.data
        if data:  # might be None in batch mode
            data.nvb.ambientonly = (self.ambientonly >= 1)
            data.nvb.shadow = self.shadow
            data.nvb.lightpriority = self.lightpriority
            data.nvb.fadinglight = (self.fadinglight >= 1)
            data.nvb.isdynamic = (self.isdynamic >= 1)
            data.nvb.affectdynamic = (self.affectdynamic >= 1)
            # Disable rendering in blender if tile light (color may be black)
            obj.hide_render = options.hide_lights or \
                              obj.name.endswith('ml1') or  \
                              obj.name.endswith('ml2')
            # Create lensflares
            numflares = min(self.flareNumValues)
            if (self.flareradius > 0) or (numflares > 0):
                data.nvb.uselensflares = True
                for i in range(numflares):
                    newItem = data.nvb.flareList.add()
                    newItem.texture = self.flareTextures[i]
                    newItem.colorshift = self.flareCShifts[i]
                    newItem.size = self.flareSizes[i]
                    newItem.position = self.flarePositions[i]
            data.nvb.flareradius = self.flareradius

    def createObject(self, options):
        """TODO: Doc."""
        lamp = self.createLamp(self.name)
        obj = bpy.data.objects.new(self.name, lamp)
        obj.nvb.imporder = self.nodeidx
        self.createObjectData(obj, options)
        return obj

    @staticmethod
    def generateAsciiFlares(obj, asciiLines):
        """TODO: Doc."""
        lamp = obj.data
        if lamp.nvb.uselensflares:
            asciiLines.append('  flareradius ' +
                              str(round(lamp.nvb.flareradius, 1)))
            if len(lamp.nvb.flareList) > 0:
                # TODO: Clean this up
                asciiLines.append('  texturenames zd')
                for flare in lamp.nvb.flareList:
                    asciiLines.append('    ' + flare.texture)
                asciiLines.append('  flarepositions zd')
                for flare in lamp.nvb.flareList:
                    asciiLines.append('    ' + str(round(flare.position, 5)))
                asciiLines.append('  flaresizes zd')
                for flare in lamp.nvb.flareList:
                    asciiLines.append('    ' + str(flare.size))
                asciiLines.append('  flarecolorshifts zd')
                fstr = '    {:3.2f} {:3.2f} {:3.2f}'
                for flare in lamp.nvb.flareList:
                    asciiLines.append(fstr.format(*(flare.colorshift)))

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options, iswalkmesh=False):
        """TODO: Doc."""
        Node.generateAsciiData(obj, asciiLines, options, iswalkmesh)

        lamp = obj.data
        asciiLines.append('  ambientonly ' + str(int(lamp.nvb.ambientonly)))
        asciiLines.append('  isdynamic ' + str(int(lamp.nvb.isdynamic)))
        asciiLines.append('  affectdynamic ' +
                          str(int(lamp.nvb.affectdynamic)))
        asciiLines.append('  shadow ' + str(int(lamp.nvb.shadow)))
        asciiLines.append('  lightpriority ' + str(lamp.nvb.lightpriority))
        asciiLines.append('  fadingLight ' + str(int(lamp.nvb.fadinglight)))
        asciiLines.append('  radius ' + str(round(lamp.distance, 1)))
        asciiLines.append('  multiplier ' + str(round(lamp.energy, 1)))
        fstr = '  color {:3.2f} {:3.2f} {:3.2f}'
        asciiLines.append(fstr.format(*lamp.color))
        Light.generateAsciiFlares(obj, asciiLines)


class Aabb(Trimesh):
    """TODO: Doc."""

    nodetype = nvb_def.Nodetype.AABB

    def __init__(self, name='UNNAMED'):
        """TODO: Doc."""
        Trimesh.__init__(self, name)
        self.meshtype = nvb_def.Meshtype.AABB

    @staticmethod
    def generateAsciiAABB(obj, asciiLines, options):
        """TODO: Doc."""
        walkmesh = obj.to_mesh(options.depsgraph,
                               options.apply_modifiers,
                               calc_undeformed=False)

        faceList = []
        faceIdx = 0
        for tessface in walkmesh.tessfaces:
            if (len(tessface.vertices) == 3):
                # Tri
                v0 = tessface.vertices[0]
                v1 = tessface.vertices[1]
                v2 = tessface.vertices[2]

                centroid = mathutils.Vector((walkmesh.vertices[v0].co +
                                             walkmesh.vertices[v1].co +
                                             walkmesh.vertices[v2].co)/3)
                faceList.append((faceIdx,
                                 [walkmesh.vertices[v0].co,
                                  walkmesh.vertices[v1].co,
                                  walkmesh.vertices[v2].co],
                                 centroid))
                faceIdx += 1

            elif (len(tessface.vertices) == 4):
                # Quad
                v0 = tessface.vertices[0]
                v1 = tessface.vertices[1]
                v2 = tessface.vertices[2]
                v3 = tessface.vertices[3]

                centroid = mathutils.Vector((walkmesh.vertices[v0].co +
                                             walkmesh.vertices[v1].co +
                                             walkmesh.vertices[v2].co)/3)
                faceList.append((faceIdx,
                                 [walkmesh.vertices[v0].co,
                                  walkmesh.vertices[v1].co,
                                  walkmesh.vertices[v2].co],
                                 centroid))
                faceIdx += 1

                centroid = mathutils.Vector((walkmesh.vertices[v2].co +
                                             walkmesh.vertices[v3].co +
                                             walkmesh.vertices[v0].co)/3)
                faceList.append((faceIdx,
                                 [walkmesh.vertices[v2].co,
                                  walkmesh.vertices[v3].co,
                                  walkmesh.vertices[v0].co],
                                 centroid))
                faceIdx += 1
            else:  # Ngon or not a polygon (shouldn't happen with tessfaces)
                print('Neverblender: WARNING - Ngon in walkmesh. \
                       Unable to generate aabb.')
                return

        aabbTree = []
        nvb_aabb.generate_tree(aabbTree, faceList)

        if aabbTree:
            fstr = '  aabb ' + \
                   '{: 5.2f} {: 5.2f} {: 5.2f}  ' + \
                   '{: 5.2f} {: 5.2f} {: 5.2f} {: 3d}'
            asciiLines.append(fstr.format(*aabbTree.pop(0)))
            fstr = '    ' + \
                   '{: 5.2f} {: 5.2f} {: 5.2f}  ' + \
                   '{: 5.2f} {: 5.2f} {: 5.2f} {: 3d}'
            asciiLines.extend([fstr.format(*bb) for bb in aabbTree])

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options, iswalkmesh=True):
        """TODO: Doc."""
        Node.generateAsciiData(obj, asciiLines, options, True)

        asciiLines.append('  ambient 1.0 1.0 1.0')
        asciiLines.append('  diffuse 1.0 1.0 1.0')
        asciiLines.append('  specular 0.0 0.0 0.0')
        asciiLines.append('  bitmap ' + nvb_def.null)
        Trimesh.generateAsciiMesh(obj, asciiLines, options)
        Aabb.generateAsciiAABB(obj, asciiLines, options)

    def create_blender_mesh(self, name, options):
        """TODO: Doc."""
        # Create the mesh itself
        me = bpy.data.meshes.new(name)
        # Create vertices
        me.vertices.add(len(self.vertex_coords))
        me.vertices.foreach_set('co', unpack_list(self.vertex_coords))
        # Create faces
        face_vids = [v[0:3] for v in self.facedef]  # face vertex indices
        face_cnt = len(face_vids)
        me.polygons.add(face_cnt)
        me.loops.add(face_cnt * 3)
        me.polygons.foreach_set('loop_start', range(0, face_cnt * 3, 3))
        me.polygons.foreach_set('loop_total', (3,) * face_cnt)
        me.loops.foreach_set('vertex_index', unpack_list(face_vids))
        nvb_utils.create_wok_materials(me)
        me.update()
        # Apply the walkmesh materials to each face
        me.polygons.foreach_set('material_index',
                                [f[7] for f in self.facedef])
        return me

    def createObject(self, options):
        """TODO: Doc."""
        mesh = self.create_blender_mesh(self.name, options)
        obj = bpy.data.objects.new(self.name, mesh)
        obj.hide_render = True
        self.createObjectData(obj, options)
        obj.nvb.imporder = self.nodeidx
        return obj
