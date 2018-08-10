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
from . import nvb_aabb


class Material(object):
    """A material read from an mdl node."""

    def __init__(self, name='unnamed'):
        """TODO: DOC."""
        self.name = name
        self.ambient = (1.0, 1.0, 1.0)
        self.diffuse = (1.0, 1.0, 1.0)
        self.diffuse_alpha = -1.0  # EE stores an alpha as 4th diffuse value
        self.specular = (0.0, 0.0, 0.0)
        self.alpha = 1.0
        self.textures = [nvb_def.null]
        self.renderhints = set()
        self.materialname = ''
        self.mtr = None

    @staticmethod
    def colorisclose(a, b, tol=0.05):
        return (math.isclose(a[0], b[0], abs_tol=tol) and
                math.isclose(a[1], b[1], abs_tol=tol) and
                math.isclose(a[2], b[2], abs_tol=tol))

    @staticmethod
    def findMaterial(textures, mtrname, cdiff, cspec, alpha):
        """TODO: Doc."""
        def get_tslot_img(tslot):
            """Get the image texture from a texture slot."""
            if tslot:
                tex = tslot.texture
                if tex and tex.type == 'IMAGE' and tex.image:
                    return tex.image.name
            return ''

        for mat in bpy.data.materials:
            eq = True
            # Check diffuse and specular color
            eq = eq and Material.colorisclose(mat.diffuse_color, cdiff)
            eq = eq and Material.colorisclose(mat.specular_color, cspec)
            # Check texture names:
            tstextures = list(map(get_tslot_img, mat.texture_slots))
            matches = []
            matches = itertools.zip_longest(tstextures, textures,
                                            fillvalue='')
            for m in matches:
                eq = eq and (m[0] == m[1])
            # If tslot 0 is used we need to compare alpha values too
            # (texture 0 = diffuse)
            if mat.texture_slots[0]:
                eq = eq and (alpha == mat.texture_slots[0].alpha_factor)
            else:
                eq = eq and (alpha == mat.alpha)
            # Check materialname (= name of MTR file)
            if mtrname:
                eq = eq and mat.nvb.usemtr and mat.nvb.mtrname == mtrname
            if eq:
                return mat
        return None

    def isdefault(self):
        """Return True if the material contains only default values"""
        d = True
        d = d and Material.colorisclose(self.ambient, (1.0, 1.0, 1.0))
        d = d and Material.colorisclose(self.diffuse, (1.0, 1.0, 1.0))
        d = d and Material.colorisclose(self.specular, (0.0, 0.0, 0.0))
        d = d and math.isclose(self.alpha, 1.0, abs_tol=0.03)
        d = d and self.textures.count(nvb_def.null) == len(self.textures)
        d = d and self.materialname == ''
        return d

    def loadAsciiLine(self, line):
        """TODO: Doc."""
        label = line[0].lower()
        if label == 'ambient':
            self.ambient = tuple([float(v) for v in line[1:4]])
        elif label == 'diffuse':
            self.diffuse = tuple([float(v) for v in line[1:4]])
            if len(line) > 4:  # EE may store an alpha as 4th diffuse value
                self.diffuse_alpha = float(line[4])
        elif label == 'specular':
            self.specular = tuple([float(v) for v in line[1:4]])
        elif label == 'alpha':
            self.alpha = float(line[1])
        elif label == 'materialname':
            self.materialname = nvb_utils.str2identifier(line[1])
        elif label == 'renderhint':
            self.renderhints.add(nvb_utils.str2identifier(line[1]))
        elif label == 'bitmap':
            if self.textures[0] == nvb_def.null:  # Do not overwrite existing
                self.textures[0] = nvb_utils.str2texture(line[1])
        elif label.startswith('texture'):
            if label[7:]:  # 'texture' is followed by a number
                idx = int(label[7:])
                cnt = len(self.textures)
                if idx+1 > cnt:
                    self.textures.extend([nvb_def.null
                                         for _ in range(idx+1-cnt)])
                self.textures[idx] = nvb_utils.str2texture(line[1])

    @staticmethod
    def applyNASMSettings(material, options):
        """Apply settings to material and texture slots for default shader."""
        # Diffuse in tslot 0
        tslot = material.texture_slots[0]
        if tslot is not None:
            tslot.texture_coords = 'UV'
            tslot.use_map_color_diffuse = True
            tslot.use_map_normal = False
            tslot.use_map_color_spec = False
            tslot.use_map_alpha = True
        # Normal in tslot 1
        tslot = material.texture_slots[1]
        if tslot is not None:
            tslot.texture_coords = 'UV'
            tslot.use_map_color_diffuse = False
            tslot.use_map_normal = True
            tslot.use_map_color_spec = False
            tslot.normal_map_space = 'TANGENT'
            tslot.texture.use_normal_map = True
        # Specular in tslot 2
        tslot = material.texture_slots[2]
        if tslot is not None:
            tslot.texture_coords = 'UV'
            tslot.use_map_color_diffuse = False
            tslot.use_map_normal = False
            tslot.use_map_color_spec = True
        # ??? in tslot 3
        tslot = material.texture_slots[3]
        if tslot is not None:
            tslot.texture_coords = 'UV'

    @staticmethod
    def applyAlphaSettings(material, alpha, options):
        """Applies settings to correctly display alpha values

           1. If there is a texture, alpha goes into texture slot, material
              alpha is 0.0
           2. Alpha goes in material if there is no texture.
        """
        material.use_transparency = True
        material.specular_alpha = 0.0
        tslot = material.texture_slots[0]
        if tslot:
            material.alpha = 0.0
            tslot.use_map_alpha = True
            tslot.alpha_factor = alpha
        else:
            material.alpha = alpha

    def createMtr(self, options):
        """Loads contents of the mtr file into the this material."""
        self.mtr = None
        namelist = [(self.materialname, True), (self.textures[0], False)]
        for mtrname, alwayscreate in namelist:
            if mtrname not in [nvb_def.null, '']:
                if mtrname in options.mtrdb:
                    self.mtr = options.mtrdb[mtrname]
                else:  # Always load, use empty mtr if no file was found
                    mtr_filename = mtrname + '.mtr'
                    mdl_dir, _ = os.path.split(options.filepath)
                    mtr_path = os.path.join(mdl_dir, mtr_filename)
                    tmp = nvb_mtr.Mtr(mtrname)
                    if tmp.loadFile(mtr_path) or alwayscreate:
                        options.mtrdb[mtrname] = tmp
                        self.mtr = tmp
        # Merge values from mtr, overwrite existing
        if self.mtr:
            self.renderhints = self.renderhints.union(self.mtr.renderhints)
            if self.mtr.textures:  # Transfer texture names
                l1 = len(self.textures)
                l2 = len(self.mtr.textures)
                if l2 > l1:
                    self.textures.extend(['' for _ in range(l2-l1+1)])
                for idx, txname in enumerate(self.mtr.textures):
                    if txname:  # null value in mtr overwrites existing in mdl
                        self.textures[idx] = txname

    def create(self, options, makeunique=False):
        """Creates a blender material with the stored values."""
        # Load mtr values intro this material
        if options.mtr_import:
            self.createMtr(options)
        # Do not create if this material has default values
        if self.isdefault():
            return None
        # Look for similar materials to avoid duplicates
        material = None
        if options.mat_automerge and not makeunique:
            material = Material.findMaterial(
                self.textures, self.materialname,
                self.diffuse, self.specular, self.alpha)
        # Create new material as necessary
        if not material:
            if self.materialname:
                matname = self.materialname
            elif self.textures[0] and self.textures[0] is not nvb_def.null:
                matname = self.textures[0].lower()
            else:
                matname = self.name
            material = bpy.data.materials.new(matname)
            material.use_transparency = True
            material.diffuse_color = self.diffuse
            material.diffuse_intensity = 1.0
            material.specular_color = self.specular
            material.specular_intensity = 1.0
            material.nvb.ambient_color = self.ambient
            material.nvb.ambient_intensity = 1.0
            # Load all textures
            for idx, txname in enumerate(self.textures):
                if txname and txname is not nvb_def.null:
                    tslot = material.texture_slots.create(idx)
                    tslot.texture = nvb_utils.create_texture(
                        txname, txname, options.filepath, options.tex_search)
            # Set Renderhint and set up textures accordingly
            if nvb_def.Renderhint.NORMALANDSPECMAPPED in self.renderhints:
                material.nvb.renderhint = 'NASM'
                Material.applyNASMSettings(material, options)
            Material.applyAlphaSettings(material, self.alpha, options)
            # Set MTR values
            if self.mtr:
                material.nvb.mtrsrc = 'FILE'
                self.mtr.create(material, options)
        return material

    @staticmethod
    def generateDefaultValues(asciiLines):
        """Write default material values to ascii."""
        asciiLines.append('  ambient 1.00 1.00 1.00')
        asciiLines.append('  diffuse 1.00 1.00 1.00')
        asciiLines.append('  specular 0.00 0.00 0.00')
        asciiLines.append('  bitmap ' + nvb_def.null)

    @staticmethod
    def generateAscii(obj, asciiLines, options):
        """Write Ascii lines from the objects material for a MDL file."""
        material = obj.active_material
        txlist = []
        if obj.nvb.render and material:
            # Write Color Values
            fstr = '  ambient {:3.2f} {:3.2f} {:3.2f}'
            asciiLines.append(fstr.format(*material.nvb.ambient_color))
            fstr = '  diffuse {:3.2f} {:3.2f} {:3.2f}'
            asciiLines.append(fstr.format(*material.diffuse_color))
            fstr = '  specular {:3.2f} {:3.2f} {:3.2f}'
            asciiLines.append(fstr.format(*material.specular_color))
            # Get textures for this material
            txlist = nvb_utils.get_textures(material)
            if material.nvb.usemtr:
                mtrname = material.nvb.mtrname
                asciiLines.append('  ' + options.mtr_ref + ' ' + mtrname)
                options.mtrdb.add(material.name)  # export later on demand
            else:
                # Add Renderhint
                if (material.nvb.renderhint == 'NASM') or \
                   (material.nvb.renderhint == 'AUTO' and len(txlist) > 1):
                    asciiLines.append('  renderhint NormalAndSpecMapped')
                # Export texture[0] as "bitmap", not "texture0"
                if len(txlist) > 0:
                    asciiLines.append('  bitmap ' + txlist[0][1])
                else:
                    asciiLines.append('  bitmap ' + nvb_def.null)
                # Export texture1 and texture2
                fs = '  texture{:d} {:s}'
                asciiLines.extend([fs.format(i, n) for i, n, _ in txlist[1:3]])
            # Alpha value:
            # 1. Texture slots present: get alpha from 1st slot
            # 2. No texture slots: get alpha from material
            if material.use_transparency:
                if len(txlist) > 0:
                    _, _, alpha = txlist[0]
                else:
                    alpha = material.alpha
                if not math.isclose(alpha, 1.0, rel_tol=0.01):  # Omit 1.0
                    asciiLines.append('  alpha {: 3.2f}'.format(alpha))
        else:
            Material.generateDefaultValues(asciiLines)
        return len(txlist) > 0  # Needed later to decide whether to add UVs


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
        return not self.__eq__(self, other)

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
            self.name = nvb_utils.str2identifier(line[2])
        elif label == 'endnode':
            return line
        elif label == 'parent':
            self.parent = nvb_utils.str2identifier(line[1])
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
        mat = obj.matrix_parent_inverse * obj.matrix_basis

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
        if obj.parent:
            asciiLines.append('  parent ' + obj.parent.name)
        else:
            asciiLines.append('  parent ' + nvb_def.null)
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
                self.refmodel = nvb_utils.str2identifier(line[1])
            elif label == 'reattachable':
                self.reattachable = nvb_utils.str2bool(line[1])
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
        self.selfillumcolor = (0.0, 0.0, 0.0)
        self.shininess = 0
        self.rotatetexture = 0
        self.material = Material()
        self.verts = []
        self.facedef = []
        self.tverts = [[]]
        self.tangents = []
        self.normals = []
        self.colors = []

    def loadAsciiLine(self, itlines):
        """TODO: Doc."""
        line = Node.loadAsciiLine(self, itlines)
        if line:
            label = line[0].lower()
            if label == 'tilefade':
                self.tilefade = int(line[1])
            elif label == 'render':
                self.render = nvb_utils.str2bool(line[1])
            elif label == 'shadow':
                self.shadow = nvb_utils.str2bool(line[1])
            elif label == 'beaming':
                self.beaming = int(line[1])
            elif label == 'inheritcolor':
                self.inheritcolor = int(line[1])
            elif label == 'rotatetexture':
                self.rotatetexture = int(line[1])
            elif label == 'transparencyhint':
                self.transparencyhint = int(line[1])
            elif ((label == 'selfillumcolor') or
                  (label == 'setfillumcolor')):
                self.selfillumcolor = tuple([float(v) for v in line[1:4]])
            elif label == 'shininess':
                self.shininess = int(float(line[1]))
            elif label == 'verts':
                if not self.verts:
                    nvals = int(line[1])
                    tmp = [next(itlines) for _ in range(nvals)]
                    self.verts = [tuple(map(nvb_utils.str2float, v))
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
                    tvcnt = len(self.tverts)
                    if tvid+1 > tvcnt:
                        self.tverts.extend([[] for _ in range(tvid-tvcnt+1)])
                if not self.tverts[tvid]:
                    nvals = int(line[1])
                    tmp = [next(itlines) for _ in range(nvals)]
                    self.tverts[tvid] = [(float(v[0]), float(v[1]))
                                         for v in tmp]
            else:
                self.material.loadAsciiLine(line)
        return line

    def fix_degenerated_uvs(self):
        """Fixes degenerated UVs by adding dummy coordinates."""
        def distance(p0, p1):
            """Euclidean Distance."""
            return math.sqrt(sum([(a - b)**2 for a, b in list(zip(p0, p1))]))

        tvert_cnt = len(self.tverts[0])
        if tvert_cnt > 0:
            add_dummy_uvs = False
            for f in self.facedef:
                uvs = self.tverts[0][f[4]], \
                      self.tverts[0][f[5]], \
                      self.tverts[0][f[6]]
                min_distance = distance(uvs[0], uvs[1])
                for p0, p1 in itertools.combinations(uvs, 2):
                    min_distance = min(min_distance, distance(p0, p1))
                # tverts are too close == degenerated
                if min_distance <= 0.001:
                    add_dummy_uvs = True
                    f[4], f[5], f[6] = tvert_cnt, tvert_cnt + 1, tvert_cnt + 2
            if add_dummy_uvs:
                self.tverts[0].extend([(0, 0), (0, 1), (1, 1)])

    @staticmethod
    def createUVlayer2(mesh, tverts, faceuvs, uvname, uvimg=None):
        """TODO: Doc."""
        uvlay = None
        if tverts and mesh.polygons:
            uvtex = mesh.uv_textures.new(uvname)
            uvlay = mesh.uv_layers[uvtex.name].data
            for fidx, poly in enumerate(mesh.polygons):
                v1, v2, v3 = faceuvs[fidx]
                uvlay[poly.loop_start].uv = tverts[v1]
                uvlay[poly.loop_start + 1].uv = tverts[v2]
                uvlay[poly.loop_start + 2].uv = tverts[v3]
                uvtex.data[fidx].image = uvimg
        # For blender 2.8:
        # for uvf in mesh.data.uv_textures.active.data:
        #     uvf.image = timg
        return uvlay

    @staticmethod
    def createUVlayer(mesh, tverts, faceuvs, uvname, uvimg=None):
        """TODO: Doc."""
        uvmap = None
        if tverts and mesh.tessfaces:
            uvmap = mesh.tessface_uv_textures.new(uvname)
            mesh.tessface_uv_textures.active = uvmap
            # Set uv's
            for i in range(len(faceuvs)):
                tessfaceUV = uvmap.data[i]
                tessfaceUV.uv1 = tverts[faceuvs[i][0]]
                tessfaceUV.uv2 = tverts[faceuvs[i][1]]
                tessfaceUV.uv3 = tverts[faceuvs[i][2]]
                tessfaceUV.image = uvimg
        return uvmap

    @staticmethod
    def createVColors(mesh, vcolors, vcname):
        """Create a color map from a per-vertex color list for the mesh."""
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

    def createMesh2(self, name, options):
        """TODO: Doc."""

        # Create the mesh itself
        me = bpy.data.meshes.new(name)
        # Create vertices
        me.vertices.add(len(self.verts))
        me.vertices.foreach_set('co', unpack_list(self.verts))
        # Create faces
        face_vids = [v[0:3] for v in self.facedef]  # face vertex indices
        face_cnt = len(face_vids)
        me.polygons.add(face_cnt)
        me.loops.add(face_cnt * 3)
        me.polygons.foreach_set('loop_start', range(0, face_cnt * 3, 3))
        me.polygons.foreach_set('loop_total', (3,) * face_cnt)
        me.loops.foreach_set('vertex_index', unpack_list(face_vids))
        # Create per-Vertex normals
        if self.normals and options.import_normals:
            me.vertices.foreach_set('normal', unpack_list(self.normals))
            me.create_normals_split()
        # Create material
        material = None
        matimg = None
        if options.importMaterials:
            uniqueMat = (self.nodetype == nvb_def.Nodetype.ANIMMESH)
            material = self.material.create(options, uniqueMat)
            if material:
                me.materials.append(material)
                # Set material idx (always 0, only a single material)
                me.polygons.foreach_set('material_index',
                                        [0] * len(me.polygons))
                tslot0 = material.texture_slots[0]
                if tslot0 and tslot0.texture:
                    matimg = tslot0.texture.image
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
        # Create Vertex colors
        Trimesh.createVColors(me, self.colors, 'colors')
        # Import custom normals
        me.update()
        if self.normals and me.loops and options.import_normals:
            for l in me.loops:
                l.normal[:] = self.normals[l.vertex_index]
            me.validate(clean_customdata=False)
            clnors = array.array('f', [0.0] * (len(me.loops) * 3))
            me.loops.foreach_get('normal', clnors)
            me.normals_split_custom_set(tuple(zip(*(iter(clnors),) * 3)))
            me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
            me.use_auto_smooth = True
            me.show_edge_sharp = True
        else:
            me.validate()
        return me

    def createMesh(self, name, options):
        """TODO: Doc."""
        if options.fix_uvs:
            self.fix_degenerated_uvs()
        # Create the mesh itself
        me = bpy.data.meshes.new(name)
        # Create vertices
        me.vertices.add(len(self.verts))
        me.vertices.foreach_set('co', unpack_list(self.verts))
        # Create per-Vertex normals
        if self.normals and options.import_normals:
            me.vertices.foreach_set('normal', unpack_list(self.normals))
        # Create faces
        face_vids = [v[0:3] for v in self.facedef]
        me.tessfaces.add(len(face_vids))
        me.tessfaces.foreach_set('vertices_raw', unpack_face_list(face_vids))
        # Create material
        material = None
        matimg = None
        if options.importMaterials:
            uniqueMat = (self.nodetype == nvb_def.Nodetype.ANIMMESH)
            material = self.material.create(options, uniqueMat)
            if material:
                me.materials.append(material)
                # Set material idx (always 0, only a single material)
                me.tessfaces.foreach_set('material_index',
                                         [0] * len(me.tessfaces))
                tslot0 = material.texture_slots[0]
                if tslot0 and tslot0.texture:
                    matimg = tslot0.texture.image
        # Create uvmaps
        # EEEKADOODLE fix
        eeka_faceuvs = [(f[5], f[6], f[4]) if f[2] == 0 else (f[4], f[5], f[6])
                        for f in self.facedef]
        # Save fixed uvs for animeshes
        if self.nodetype == nvb_def.Nodetype.ANIMMESH:
            if me.name not in nvb_def.tvert_order:
                nvb_def.tvert_order[me.name] = copy.deepcopy(eeka_faceuvs)
        # Iterate in reverse so the first uvmap can be set to active
        uvmap = None
        for idx, tvs in reversed(list(enumerate(self.tverts))):
            if tvs:  # may be []
                uvname = me.name + '.tvert' + str(idx)
                uvmap = Trimesh.createUVlayer(me, tvs, eeka_faceuvs,
                                              uvname, matimg)
        if uvmap:
            me.uv_textures[uvmap.name].active = True  # blender 2.8 error!
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
        me.update()
        if self.normals and me.loops and options.import_normals:
            # Use normals for shading
            # TODO: Test this... faster?
            # me.normals_split_custom_set_from_vertices(self.normals)
            for l in me.loops:
                l.normal[:] = self.normals[l.vertex_index]
            me.validate(clean_customdata=False)
            clnors = array.array('f', [0.0] * (len(me.loops) * 3))
            me.loops.foreach_get('normal', clnors)
            me.create_normals_split()
            me.normals_split_custom_set(tuple(zip(*(iter(clnors),) * 3)))
            me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
            me.use_auto_smooth = True
            me.show_edge_sharp = True
        elif options.importSmoothGroups:
            # Use shading groups for shading
            sgr_list = set([fd[3] for fd in self.facedef])
            if len(sgr_list) == 1 and sgr_list.pop() == 0:
                # single smoothgroup 0 means non-smooth
                me.polygons.foreach_set('use_smooth',
                                        [False] * len(me.polygons))
                me.use_auto_smooth = False
                me.auto_smooth_angle = 0.523599
            else:
                me.polygons.foreach_set('use_smooth',
                                        [True] * len(me.polygons))
                me.use_auto_smooth = True
                me.auto_smooth_angle = 1.570796
        # Create Vertex colors
        Trimesh.createVColors(me, self.colors, 'colors')
        me.validate()
        # me.update()
        return me

    def createObjectData(self, obj, options):
        """TODO: Doc."""
        Node.createObjectData(self, obj, options)

        obj.nvb.meshtype = self.meshtype
        if self.tilefade == 1:
            obj.nvb.tilefade = nvb_def.Tilefade.FADE
        elif self.tilefade == 2:
            obj.nvb.tilefade = nvb_def.Tilefade.BASE
        elif self.tilefade == 4:
            obj.nvb.tilefade = nvb_def.Tilefade.NEIGHBOUR
        else:
            obj.nvb.tilefade = nvb_def.Tilefade.NONE
        if (self.tilefade >= 1) and not options.render_fading:
            obj.hide_render = True
        if not self.render:
            obj.nvb.render = False
            obj.hide_render = True
        obj.nvb.shadow = self.shadow
        obj.nvb.beaming = (self.beaming >= 1)
        obj.nvb.inheritcolor = (self.inheritcolor >= 1)
        obj.nvb.rotatetexture = (self.rotatetexture >= 1)
        obj.nvb.transparencyhint = self.transparencyhint
        obj.nvb.selfillumcolor = self.selfillumcolor
        obj.nvb.shininess = self.shininess
        obj.color = (*self.wirecolor, 1.0)

    def createObject(self, options):
        """TODO: Doc."""
        mesh = self.createMesh(self.name, options)
        obj = bpy.data.objects.new(self.name, mesh)
        self.createObjectData(obj, options)
        return obj

    @staticmethod
    def generateAsciiMesh(obj, asciiLines, options, hasImgTexture):
        """TODO: Doc."""

        def getSmoothGroups(obj, mesh, options):
            smoothGroups = []
            if (obj.nvb.smoothgroup == 'SEPR') or \
               (obj.nvb.meshtype == nvb_def.Meshtype.AABB) or \
               (not options.export_smoothgroups):
                # 0 = Do not use smoothgroups
                smoothGroups = [0] * len(mesh.polygons)
            elif (obj.nvb.smoothgroup == 'SING') or \
                 (options.export_normals):
                # All faces belong to smooth group 1
                smoothGroups = [1] * len(mesh.polygons)
            else:
                smoothGroups, _ = mesh.calc_smooth_groups()
            return smoothGroups

        def getFaceUVs(faceData, uvMapData, join=True):
            """Get a list of uvmap indices and uvmap coodinates."""

            def joinUV(uvco, fvidx, uvlist):
                """Add the uv coordinale to the list and return the index."""
                listItem = [fvidx, uvco]
                if listItem in uvlist:
                    return uvlist.index(listItem)
                else:
                    uvlist.append(listItem)
                    return (len(uvlist)-1)

            faceUVIdList = []  # Per face uv indices
            faceUVCoList = []  # uv coordinates
            # Pairs of tuples of vertex indices vX_idx and
            # uv coordinates uvX_co
            # [(v1_idx, v2_idx, v3,idx), (uv1_co, uv2_co, uv3_co)]
            pairs = zip(faceData, [[d.uv1, d.uv2, d.uv3] for d in uvMapData])
            if join:
                tmpList = []
                for p in pairs:
                    uvidx = [-1, -1, -1]
                    for i in range(3):
                        listItem = [p[0][i], p[1][i]]
                        if listItem in tmpList:
                            uvidx[i] = tmpList.index(listItem)
                        else:
                            tmpList.append(listItem)
                            uvidx[i] = len(tmpList)-1
                    faceUVIdList.append(uvidx)
                faceUVCoList = [e[1] for e in tmpList]
            else:
                for p in pairs:
                    uvidx = [-1, -1, -1]
                    for i in range(3):
                        faceUVCoList.append(p[1][i])
                        uvidx[i] = len(faceUVCoList)-1
                    faceUVIdList.append(uvidx)
            return faceUVIdList, faceUVCoList

        def generateVColors(mesh, asciiLines):
            """Generate per-vert. vertex-colors from per-loop vertex-colors."""
            cmap = me.vertex_colors.active
            if cmap:
                # Per vertex vertex-color list
                vcolors = [(1.0, 1.0, 1.0)] * len(mesh.vertices)
                # Get all loops for each vertex
                vert_loop_map = {}
                for l in mesh.loops:
                    if l.vertex_index in vert_loop_map:
                        vert_loop_map[l.vertex_index].append(l.index)
                    else:
                        vert_loop_map[l.vertex_index] = [l.index]
                # Get color for each vertex (in every loop)
                for vidx in vert_loop_map:
                    for lidx in vert_loop_map[vidx]:
                        vcolors[vidx] = cmap.data[lidx].color[:3]
                asciiLines.append('  colors ' + str(len(mesh.vertices)))
                fstr = '    {: 8.5f} {: 8.5f} {: 8.5f}'
                asciiLines.extend([fstr.format(*vc) for vc in vcolors])

        def generateNormals(mesh, asciiLines, uvmap):
            """Generates normals and tangents."""
            # Generate readable normals and tangents
            mesh.calc_tangents(uvmap.name)
            # Add normals
            oknormals = []
            # Try vertex-per-face normals
            for i in range(len(mesh.vertices)):
                # All normals for this vertex
                normals = \
                    [l.normal for l in mesh.loops if l.vertex_index == i]
                s = set([str(n) for n in normals])
                if len(s) != 1:  # Something is not right, cannot export this
                    oknormals = []
                    print('Neverblender: WARNING - Invalid normals ' +
                          obj.name)
                    break
                oknormals.append(normals[0])
            if oknormals:
                asciiLines.append('  normals ' + str(len(oknormals)))
                fstr = '    {: 8.5f} {: 8.5f} {: 8.5f}'
                asciiLines.extend([fstr.format(*n) for n in oknormals])
            """
            # Try vertex normals
            for v in mesh.vertices:
                s = formatStr.format(l_rnd(v.normal[0], 5),
                                     l_rnd(v.normal[1], 5),
                                     l_rnd(v.normal[2], 5))
                asciiLines.append(s)
            """
            # Add tangents
            oktangents = []
            #  Vertex-per-face tangents
            for i in range(len(mesh.vertices)):
                # All tangents for this vertex
                tangents = [[l.tangent, l.bitangent_sign]
                            for l in mesh.loops if l.vertex_index == i]
                oktangents.append(tangents[0])
            if oktangents:
                asciiLines.append('  tangents ' + str(len(oktangents)))
                fstr = '    {: 8.5f} {: 8.5f} {: 8.5f} {: 3.1f}'
                asciiLines.extend([fstr.format(*t[0], t[1])
                                  for t in oktangents])
            """
            for face in mesh.polygons:
                # face loops and face vertices are in the same order
                for v_id, l_id in zip(face.vertices, face.loop_indices):
                    # this is the loop:
                    mesh.loops[l_id]
                    # this is the vertex in the corner of the loop:
                    mesh.vertices[v_id]
            """
            # mesh.free_normals_split()

        me = obj.to_mesh(options.scene,
                         options.apply_modifiers,
                         options.mesh_convert)
        for p in me.polygons:
            p.use_smooth = True
        # Triangulation (doing it with bmesh to retain edges marked as sharp)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        del bm
        me.calc_tessface()  # Recalculate tessfaces after triangulation

        # Generate Smoothgroups
        fcSGrps = getSmoothGroups(obj, me, options)
        # Add vertices
        asciiLines.append('  verts ' + str(len(me.vertices)))
        fstr = '    {: 8.5f} {: 8.5f} {: 8.5f}'
        asciiLines.extend([fstr.format(*v.co) for v in me.vertices])
        # Add normals and tangents
        uvmap = me.uv_textures.active
        if uvmap and options.export_normals and obj.nvb.render:
            generateNormals(me, asciiLines, uvmap)
        # Face vertex indices and face materials
        fcVertIds = [tuple(tf.vertices) for tf in me.tessfaces]
        fcMatIds = [tf.material_index for tf in me.tessfaces]
        # Per face uv indices and a list of their coordinates
        fcUVData = []
        exportUVs = ((options.uvmapMode == 'ALL') or
                     (options.uvmapMode == 'REN' and obj.nvb.render) or
                     (options.uvmapMode == 'TEX' and hasImgTexture))
        if exportUVs:
            joinUVs = ((obj.nvb.meshtype != nvb_def.Meshtype.ANIMMESH) and
                       options.uvmapAutoJoin)
            # Find out which UV maps to export and their order:
            uvmapNames = []
            if options.uvmapOrder == 'AL0':
                # Export all, sort alphabetically
                uvmapNames = [uvt.name for uvt in me.tessface_uv_textures]
                uvmapNames.sort()
            elif options.uvmapOrder == 'AL1':
                # Export all, sort alphabetically, put active first
                uvmapActiveName = me.tessface_uv_textures.active.name
                uvmapNames = [uvt.name for uvt in me.tessface_uv_textures
                              if not uvt.name == uvmapActiveName]
                uvmapNames.sort()
                uvmapNames.insert(0, me.tessface_uv_textures.active.name)
            else:
                # Export active uvmap only
                uvmapNames.append(me.tessface_uv_textures.active.name)
            # Generate the tverts for the faces
            for uvn in uvmapNames:
                fcUVData.append(getFaceUVs(fcVertIds,
                                           me.tessface_uv_textures[uvn].data,
                                           joinUVs))
            if not fcUVData:
                fcUVIdList = [[0, 0, 0] for _ in range(len(me.tessfaces))]
                fcUVCoList = []
                fcUVData.append([fcUVIdList, fcUVCoList])
        else:
            fcUVIdList = [[0, 0, 0] for _ in range(len(me.tessfaces))]
            fcUVCoList = []
            fcUVData.append([fcUVIdList, fcUVCoList])
        # Write tverts to file (if any)
        fstr = '    {: 5.3f} {: 5.3f}  0'
        for idx, fuvd in enumerate(fcUVData):
            if len(fuvd[1]) > 0:
                if idx == 0:
                    asciiLines.append('  tverts ' +
                                      str(len(fuvd[1])))
                else:
                    asciiLines.append('  tverts' + str(idx) + ' ' +
                                      str(len(fuvd[1])))
                asciiLines.extend([fstr.format(v[0], v[1]) for v in fuvd[1]])
        # Vertex color
        generateVColors(me, asciiLines)
        # Write faces to file
        vdigs = str(max(1, len(str(len(me.vertices)))))  # Digits for vertices
        sdigs = str(max(1, len(str(max(fcSGrps)))))  # Digits for smoothgrps
        udigs = str(max(1, len(str(len(fcUVData[0][1])))))  # Digits for UVs
        mdigs = str(max(1, len(str(max(fcMatIds)))))
        # Zip face data
        faces = [[*fcVertIds[i], fcSGrps[i], *fcUVData[0][0][i], fcMatIds[i]]
                 for i in range(len(fcVertIds))]
        asciiLines.append('  faces ' + str(len(faces)))
        fstr = '    ' + \
               '{:' + vdigs + 'd} {:' + vdigs + 'd} {:' + vdigs + 'd}  ' + \
               '{:' + sdigs + 'd}  ' + \
               '{:' + udigs + 'd} {:' + udigs + 'd} {:' + udigs + 'd}  ' + \
               '{:' + mdigs + 'd}'
        asciiLines.extend([fstr.format(*f) for f in faces])
        bpy.data.meshes.remove(me)

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options, iswalkmesh=False):
        """TODO: Doc."""
        Node.generateAsciiData(obj, asciiLines, options, iswalkmesh)

        s = '  wirecolor {:3.2f} {:3.2f} {:3.2f}'.format(*obj.color[:3])
        asciiLines.append(s)

        hastexture = False
        if iswalkmesh:
            asciiLines.append('  ambient 1.00 1.00 1.00')
            asciiLines.append('  diffuse 1.00 1.00 1.00')
            asciiLines.append('  specular 0.00 0.00 0.00')
            asciiLines.append('  bitmap ' + nvb_def.null)
        else:
            hastexture = Material.generateAscii(obj, asciiLines, options)
            # Shininess
            asciiLines.append('  shininess ' + str(obj.nvb.shininess))
            # Self illumination color
            col = obj.nvb.selfillumcolor
            if round(sum(col), 2) > 0.0:  # Skip default value
                s = '  selfillumcolor {:3.2f} {:3.2f} {:3.2f}'.format(*col)
                asciiLines.append(s)
            # Render and Shadow
            if not (obj.nvb.shadow and obj.nvb.render):  # Skip default value
                asciiLines.append('  render ' + str(int(obj.nvb.render)))
                asciiLines.append('  shadow ' + str(int(obj.nvb.shadow)))
            # Beaming
            val = int(obj.nvb.beaming)
            if val != 0:  # Skip default value
                asciiLines.append('  beaming ' + str(val))
            # INherit color from parent
            val = int(obj.nvb.inheritcolor)
            if val != 0:  # Skip default value
                asciiLines.append('  inheritcolor ' + str(val))
            # Transparency hint (rendering order)
            val = obj.nvb.transparencyhint
            if val != 0:  # Skip default value
                asciiLines.append('  transparencyhint ' + str(val))
            # These two are for tiles only
            if options.classification == nvb_def.Classification.TILE:
                asciiLines.append('  rotatetexture ' +
                                  str(int(obj.nvb.rotatetexture)))
                asciiLines.append('  tilefade ' + obj.nvb.tilefade)

        Trimesh.generateAsciiMesh(obj, asciiLines, options, hastexture)


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
                self.period = float(line[1])
            elif label == 'tightness':
                self.tightness = float(line[1])
            elif label == 'displacement':
                self.displacement = float(line[1])
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
        vgroup = obj.vertex_groups.new('constraints')
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

        lfloat = float
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
                    n = n.lower()
                    w = lfloat(w)
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
                    vgroup = obj.vertex_groups.new(membership[0])
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

    def createMesh(self, objName, options):
        """TODO: Doc."""
        # Create the mesh itself
        mesh = bpy.data.meshes.new(objName)
        mesh.vertices.add(4)
        mesh.vertices[0].co = (1.0,  1.0, 0.0)
        mesh.vertices[1].co = (1.0, -1.0, 0.0)
        mesh.vertices[2].co = (-1.0, -1.0, 0.0)
        mesh.vertices[3].co = (-1.0,  1.0, 0.0)
        mesh.tessfaces.add(1)
        mesh.tessfaces.foreach_set('vertices_raw', [0, 1, 2, 3])

        em_size = (max(self.xsize/100, 0), max(self.ysize/100, 0))
        scale_mat = mathutils.Matrix.Scale(em_size[0], 4, [1, 0, 0]) * \
            mathutils.Matrix.Scale(em_size[1], 4, [0, 1, 0])
        mesh.transform(scale_mat)
        # After calling update() tessfaces become inaccessible
        mesh.validate()
        mesh.update()

        return mesh

    def createObjectData(self, obj, options):
        """TODO: Doc."""
        Node.createObjectData(self, obj, options)

        obj.nvb.meshtype = self.meshtype
        self.create_particle_system(obj, options)

    def createObject(self, options):
        """TODO: Doc."""
        mesh = self.createMesh(self.name, options)
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
        aline = Node.loadAsciiLine(self, itlines)
        if not aline:
            return aline
        try:
            label = aline[0].lower()
        except (IndexError, AttributeError):
            return aline  # Probably empty line, skip it
        if (label == 'radius'):
            self.radius = float(aline[1])
        elif (label == 'shadow'):
            self.shadow = nvb_utils.str2bool(aline[1])
        elif (label == 'multiplier'):
            self.multiplier = float(aline[1])
        elif (label == 'color'):
            self.color = tuple([float(v) for v in aline[1:4]])
        elif (label == 'ambientonly'):
            self.ambientonly = int(aline[1])
        elif (label == 'isdynamic'):
            self.isdynamic = int(aline[1])
        elif (label == 'affectdynamic'):
            self.affectdynamic = int(aline[1])
        elif (label == 'negativelight'):
            self.negativelight = int(aline[1])
        elif (label == 'lightpriority'):
            self.lightpriority = int(aline[1])
        elif (label == 'fadinglight'):
            self.fadinglight = int(aline[1])
        elif (label == 'lensflares'):
            self.lensflares = int(aline[1])
        elif (label == 'flareradius'):
            self.flareradius = float(aline[1])
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
        return aline

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
        lamp = bpy.data.lamps.new(name, 'POINT')

        lamp.color = self.color
        lamp.energy = self.multiplier
        lamp.distance = self.radius
        lamp.use_sphere = True

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
            if obj.name.endswith('ml1') or obj.name.endswith('ml2') or \
               not options.render_lights:
                obj.hide_render = True
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
        walkmesh = obj.to_mesh(options.scene,
                               options.apply_modifiers,
                               options.mesh_convert)

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
        Trimesh.generateAsciiMesh(obj, asciiLines, options, True)
        Aabb.generateAsciiAABB(obj, asciiLines, options)

    def createMesh(self, name, options):
        """TODO: Doc."""
        # Create the mesh itself
        me = bpy.data.meshes.new(name)
        # Create vertices
        me.vertices.add(len(self.verts))
        me.vertices.foreach_set('co', unpack_list(self.verts))
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

    def createMeshOLD(self, name, options):
        """TODO: Doc."""
        # Create the mesh itself
        me = bpy.data.meshes.new(name)
        # Create vertices
        me.vertices.add(len(self.verts))
        me.vertices.foreach_set('co', unpack_list(self.verts))
        # Create faces
        face_vids = [v[0:3] for v in self.facedef]
        me.tessfaces.add(len(face_vids))
        me.tessfaces.foreach_set('vertices_raw', unpack_face_list(face_vids))
        # Create materials
        for wokMat in nvb_def.wok_materials:
            matName = wokMat[0]
            # Walkmesh materials will be shared across multiple walkmesh
            # objects
            if matName in bpy.data.materials:
                material = bpy.data.materials[matName]
            else:
                material = bpy.data.materials.new(matName)
                material.diffuse_color = wokMat[1]
                material.diffuse_intensity = 1.0
                material.specular_color = (0.0, 0.0, 0.0)
                material.specular_intensity = wokMat[2]
            me.materials.append(material)
        me.update()
        # Apply the walkmesh materials to each face
        me.polygons.foreach_set('material_index',
                                [f[7] for f in self.facedef])
        return me

    def createObject(self, options):
        """TODO: Doc."""
        mesh = self.createMesh(self.name, options)
        obj = bpy.data.objects.new(self.name, mesh)
        obj.hide_render = True
        self.createObjectData(obj, options)
        obj.nvb.imporder = self.nodeidx
        return obj
