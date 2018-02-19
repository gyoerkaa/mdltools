"""TODO: DOC."""

import mathutils
import bpy
import bpy_extras.image_utils
import bmesh
import array
import copy
import itertools
import os
from bpy_extras.io_utils import unpack_list, unpack_face_list

from . import nvb_def
from . import nvb_utils
from . import nvb_aabb


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
        self.orientation = (0.0, 0.0, 0.0, 0.0)
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
        aline = None
        try:
            aline = next(itlines)
        except StopIteration:
            return None
        label = ''
        try:
            label = aline[0].lower()
        except (IndexError, AttributeError):
            return aline  # Probably empty line or comment
        if nvb_utils.isNumber(label):
            return aline
        if (label == 'node'):
            self.name = nvb_utils.getAuroraString(aline[2])
        elif (label == 'endnode'):
            return aline
        elif (label == 'parent'):
            self.parent = nvb_utils.getAuroraString(aline[1])
        elif (label == 'position'):
            self.position = tuple([float(v) for v in aline[1:4]])
        elif (label == 'orientation'):
            self.orientation = tuple([float(v) for v in aline[1:5]])
        elif (label == 'scale'):
            self.scale = float(aline[1])
        elif (label == 'wirecolor'):
            self.wirecolor = tuple([float(v) for v in aline[1:4]])
        return aline

    def loadAscii(self, asciiLines, nodeidx=-1):
        """TODO: DOC."""
        self.nodeidx = nodeidx
        # list(map(self.loadAsciiLine, asciiLines))
        iterable = iter(asciiLines)
        lline = True
        while lline is not None:
            lline = self.loadAsciiLine(iterable)

    def createObjectData(self, obj, options):
        """TODO: DOC."""
        nvb_utils.setObjectRotationAurora(obj, self.orientation)
        obj.nvb.restrot = obj.rotation_euler
        obj.scale = (self.scale, self.scale, self.scale)
        obj.location = self.position
        obj.nvb.restloc = obj.location
        obj.nvb.wirecolor = self.wirecolor
        obj.nvb.imporder = self.nodeidx

    def createObject(self, options):
        """Return an object for use in blender."""
        obj = bpy.data.objects.new(self.name, None)
        self.createdobj = obj.name
        self.createObjectData(obj, options)
        return obj

    @staticmethod
    def getAdjustedMatrix(obj):
        """TODO: DOC."""
        if obj.parent:
            parent_mw = obj.parent.matrix_world
        else:
            parent_mw = mathutils.Matrix()

        p_mw_scale = parent_mw.to_scale()

        # scale_m = mathutils.Matrix([[p_mw_scale[0],0,0,0],
        #                             [0,p_mw_scale[1],0,0],
        #                             [0,0,p_mw_scale[2],0],
        #                             [0,0,0            ,1]])

        scaled = obj.matrix_local.copy()
        scaled[0][3] = scaled[0][3] * p_mw_scale[0]
        scaled[1][3] = scaled[1][3] * p_mw_scale[1]
        scaled[2][3] = scaled[2][3] * p_mw_scale[2]
        return scaled

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options):
        """TODO: DOC."""
        # Rootdummy's get no data at all
        if obj.parent is None:
            return
        # Scaling fix
        transmat = Node.getAdjustedMatrix(obj)
        loc = transmat.to_translation()
        asciiLines.append('  position {: 8.5f} {: 8.5f} {: 8.5f}'.format(*loc))

        rot = nvb_utils.euler2nwangle(transmat.to_euler('XYZ'))
        fstr = '  orientation {: 8.5f} {: 8.5f} {: 8.5f} {: 8.5f}'
        asciiLines.append(fstr.format(*rot))

        scale = round(nvb_utils.getAuroraScale(obj), 3)
        if not (0.998 < scale < 1.002):
            asciiLines.append('  scale ' + str(scale))

    @classmethod
    def generateAscii(cls, obj, asciiLines, options):
        """TODO: Doc."""
        asciiLines.append('node ' + cls.nodetype + ' ' + obj.name)
        if obj.parent:
            asciiLines.append('  parent ' + obj.parent.name)
        else:
            asciiLines.append('  parent ' + nvb_def.null)
        cls.generateAsciiData(obj, asciiLines, options)
        asciiLines.append('endnode')

    @classmethod
    def generateAsciiWalkmesh(cls, obj, asciiLines, options):
        """TODO: Doc."""
        rootDummy = nvb_utils.findRootDummy(obj)
        nodeName = obj.name
        parentName = nvb_def.null
        if rootDummy:
            nodeName = nvb_utils.generateWalkmeshName(obj, rootDummy)
            parentName = nvb_utils.generateWalkmeshParent(rootDummy)
        asciiLines.append('node ' + cls.nodetype + ' ' + nodeName)
        asciiLines.append('  parent ' + parentName)
        cls.generateAsciiData(obj, asciiLines, options)
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
        obj.nvb.dummytype = nvb_def.Dummytype.getType(self.name)


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
        aline = Node.loadAsciiLine(self, itlines)
        if not aline:
            return aline
        try:
            label = aline[0].lower()
        except (IndexError, AttributeError):
            return aline  # Probably empty line or comment
        if (label == 'refmodel'):
            self.refmodel = nvb_utils.getAuroraString(aline[1])
        elif (label == 'reattachable'):
            try:
                self.reattachable = int(aline[1])
            except (ValueError, IndexError):
                pass
        return aline

    def createObjectData(self, obj, options):
        """TODO: Doc."""
        Node.createObjectData(self, obj, options)
        obj.nvb.emptytype = self.emptytype
        obj.nvb.refmodel = self.refmodel
        obj.nvb.reattachable = (self.reattachable >= 1)

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options):
        """TODO: Doc."""
        Node.generateAsciiData(obj, asciiLines, options)
        asciiLines.append('  refmodel ' + obj.nvb.refmodel)
        asciiLines.append('  reattachable ' + str(int(obj.nvb.reattachable)))


class Trimesh(Node):
    """TODO: Doc."""

    nodetype = nvb_def.Nodetype.TRIMESH

    def __init__(self, name='UNNAMED'):
        """TODO: Doc."""
        Node.__init__(self, name)

        self.meshtype = nvb_def.Meshtype.TRIMESH
        self.walkmeshtype = nvb_def.Walkmeshtype.PWK  # Default values
        self.center = (0.0, 0.0, 0.0)  # Unused ?
        self.tilefade = 0
        self.render = 1
        self.shadow = 1
        self.beaming = 0
        self.inheritcolor = 0  # Unused ?
        self.alpha = 1.0
        self.transparencyhint = 0
        self.selfillumcolor = (0.0, 0.0, 0.0)
        self.ambient = (1.0, 1.0, 1.0)
        self.diffuse = (1.0, 1.0, 1.0)
        self.specular = (0.0, 0.0, 0.0)
        self.shininess = 0
        self.bitmap = ''
        self.renderhints = []
        self.textures = ['']
        self.rotatetexture = 0
        self.materialname = ''  # name for external mtr file
        self.verts = []
        self.facedef = []
        self.tverts = [[]]
        self.tangents = []
        self.normals = []
        self.colors = []

    def loadAsciiLine(self, itlines):
        """TODO: Doc."""
        aline = Node.loadAsciiLine(self, itlines)
        if not aline:
            return aline
        try:
            label = aline[0].lower()
        except (IndexError, AttributeError):
            return aline  # Probably empty line, skip it
        if (label == 'tilefade'):
            self.tilefade = int(aline[1])
        elif (label == 'render'):
            try:
                self.render = int(aline[1])
            except (ValueError, IndexError):
                pass
        elif (label == 'shadow'):
            try:
                self.shadow = int(aline[1])
            except (ValueError, IndexError):
                pass
        elif (label == 'beaming'):
            self.beaming = int(aline[1])
        elif (label == 'inheritcolor '):
            self.inheritcolor = int(aline[1])
        elif (label == 'rotatetexture'):
            self.rotatetexture = int(aline[1])
        elif (label == 'materialname'):
            self.materialname = aline[1]
        elif (label == 'alpha'):
            self.alpha = float(aline[1])
        elif (label == 'transparencyhint'):
            self.transparencyhint = int(aline[1])
        elif ((label == 'selfillumcolor') or
              (label == 'setfillumcolor')):
            self.selfillumcolor = tuple([float(v) for v in aline[1:4]])
        elif (label == 'ambient'):
            self.ambient = tuple([float(v) for v in aline[1:4]])
        elif (label == 'diffuse'):
            self.diffuse = tuple([float(v) for v in aline[1:4]])
        elif (label == 'specular'):
            self.specular = tuple([float(v) for v in aline[1:4]])
        elif (label == 'shininess'):
            self.shininess = int(float(aline[1]))
        elif (label == 'bitmap'):
            self.bitmap = nvb_utils.getAuroraString(aline[1])
        elif (label == 'renderhint'):
            self.renderhints.append(nvb_utils.getAuroraString(aline[1]))
        elif (label == 'bitmap'):
            self.bitmap = nvb_utils.getAuroraString(aline[1])
        elif (label == 'renderhint'):
            self.renderhints.append(nvb_utils.getAuroraString(aline[1]))
        elif (label == 'verts'):
            if not self.verts:
                nvals = int(aline[1])
                tmp = [next(itlines) for _ in range(nvals)]
                self.verts = [tuple(map(float, v)) for v in tmp]
        elif (label == 'faces'):
            if not self.facedef:
                nvals = int(aline[1])
                tmp = [next(itlines) for _ in range(nvals)]
                self.facedef = [list(map(int, v)) for v in tmp]
        elif (label == 'normals'):
            if not self.normals:
                nvals = int(aline[1])
                tmp = [next(itlines) for _ in range(nvals)]
                self.normals = [tuple(map(float, v)) for v in tmp]
        elif (label == 'tangents'):
            if not self.tangents:
                nvals = int(aline[1])
                tmp = [next(itlines) for _ in range(nvals)]
                self.tangents = [tuple(map(float, v)) for v in tmp]
        elif (label == 'colors'):
            if not self.colors:
                nvals = int(aline[1])
                tmp = [next(itlines) for _ in range(nvals)]
                self.colors = [tuple(map(float, v)) for v in tmp]
        elif (label.startswith('texture')):
            tid = 0
            # 'texture' has to be followed by a number
            if label[7:]:
                tid = int(label[7:])
                tcnt = len(self.textures)
                if tid+1 > tcnt:
                    self.textures.extend(['' for _ in range(tid-tcnt+1)])
                if not self.textures[tid]:
                    self.textures[tid] = \
                        nvb_utils.getAuroraString(aline[1])
        elif (label.startswith('tverts')):
            tvid = 0
            if label[6:]:  # might be '', which we interpret as = 0
                tvid = int(label[6:])
                tvcnt = len(self.tverts)
                if tvid+1 > tvcnt:
                    self.tverts.extend([[] for _ in range(tvid-tvcnt+1)])
            if not self.tverts[tvid]:
                nvals = int(aline[1])
                tmp = [next(itlines) for _ in range(nvals)]
                self.tverts[tvid] = [(float(v[0]), float(v[1])) for v in tmp]
        return aline

    def createMaterialFromMTL(self, options, makeunique=False):
        """TODO: Doc."""
        return None

    def createMaterialFromMDL(self, options, makeunique=False):
        """TODO: Doc."""
        def findMaterial(textures,
                         cdiff=(1.0, 1.0, 1.0), cspec=(0.0, 0.0, 0.0),
                         alpha=1.0):
            """TODO: Doc."""
            def cmp_col(a, b, rel_tol=0.1):
                """Compares two colors."""
                def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
                    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)),
                                           abs_tol)
                return (isclose(a[0], b[0], rel_tol) and
                        isclose(a[1], b[1], rel_tol) and
                        isclose(a[2], b[2], rel_tol))

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
                eq = eq and cmp_col(mat.diffuse_color, cdiff)
                eq = eq and cmp_col(mat.specular_color, cspec)
                # Check texture names:
                tstextures = list(map(get_tslot_img, mat.texture_slots))
                matches = []
                matches = itertools.zip_longest(tstextures, textures,
                                                fillvalue='')
                for m in matches:
                    eq = eq and (m[0] == m[1])
                # Texture slot 0 is used we need to compare alpha values too
                # (texture = diffuse)
                if mat.texture_slots[0]:
                    eq = eq and (alpha == mat.texture_slots[0].alpha_factor)
                else:
                    eq = eq and (alpha == mat.alpha)
                if eq:
                    return mat
            return None

        def createTexture(tname, imgname, options):
            """TODO: Doc."""
            if tname in bpy.data.textures:
                # Load the image for the texture
                tex = bpy.data.textures[tname]
            else:
                tex = bpy.data.textures.new(tname, type='IMAGE')
                if (imgname in bpy.data.images):
                    image = bpy.data.images[imgname]
                    tex.image = image
                else:
                    texpath = os.path.dirname(options.filepath)
                    image = bpy_extras.image_utils.load_image(
                        imgname + '.tga',
                        texpath,
                        recursive=options.textureSearch,
                        place_holder=False,
                        ncase_cmp=True)
                    if image is None:
                        image = bpy.data.images.new(imgname, 512, 512)
                    image.name = imgname
                    tex.image = image
            return tex

        # texture0 = bitmap, texture0 takes precedence
        texlist = self.textures
        if len(texlist) > 0:
            if not texlist[0] and self.bitmap:
                texlist[0] = self.bitmap
        else:
            if self.bitmap:
                texlist.append(self.bitmap)
        # Look for similar materials to avoid duplicates
        material = None
        if options.materialAutoMerge and not makeunique:
            material = findMaterial(texlist,
                                    self.diffuse, self.specular, self.alpha)
        if not material:
            matname = texlist[0].lower() if texlist[0] else self.name
            material = bpy.data.materials.new(matname)
            material.use_transparency = True
            material.diffuse_color = self.diffuse
            material.diffuse_intensity = 1.0
            material.specular_color = self.specular
            material.specular_intensity = 1.0
            # Load all textures first
            for idx, mdltex in enumerate(texlist):
                if mdltex:  # might be ''
                    tslot = material.texture_slots.create(idx)
                    tslot.texture = createTexture(mdltex, mdltex, options)
            # Set the default roles for texture slot:
            # texture0 = diffuse
            # texture1 = normal
            # texture2 = specular
            # texture3 = TBD
            # others are generic
            matalpha = self.alpha
            if options.textureDefaultRoles:
                # Diffuse in tslot 0
                tslot = material.texture_slots[0]
                if tslot is not None:
                    tslot.texture_coords = 'UV'
                    tslot.use_map_color_diffuse = True
                    tslot.use_map_normal = False
                    tslot.use_map_color_spec = False
                    tslot.use_map_alpha = True
                    tslot.alpha_factor = self.alpha
                    matalpha = 0.0  # alpha doesn't need to be in mat
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
            material.alpha = matalpha
            material.specular_alpha = matalpha
        return material

    def createMesh(self, name, options):
        """TODO: Doc."""
        def createUVmap(mesh, tverts, uvname, material=None):
            """TODO: Doc."""
            uvmap = None
            timg = None
            if material:
                # Set material for each face
                me.tessfaces.foreach_set('material_index',
                                         [0] * len(me.tessfaces))
                if material.texture_slots[0]:
                    timg = material.texture_slots[0].texture.image
            if tverts and mesh.tessfaces:
                uvmap = me.tessface_uv_textures.new(uvname)
                # we need to save the order the tverts were created in blender
                # for animmeshes/uv animations
                me.tessface_uv_textures.active = uvmap
                # EEEKADOODLE fix
                cuvs = [(f[5], f[6], f[4]) if f[2] == 0 else (f[4], f[5], f[6])
                        for f in self.facedef]
                # Set uv's
                for i in range(len(cuvs)):
                    tessfaceUV = uvmap.data[i]
                    tessfaceUV.uv1 = tverts[cuvs[i][0]]
                    tessfaceUV.uv2 = tverts[cuvs[i][1]]
                    tessfaceUV.uv3 = tverts[cuvs[i][2]]
                    tessfaceUV.image = timg
                # Save new order for uvs (for animesh animations)
                if uvmap.name not in nvb_def.tvert_order:
                    nvb_def.tvert_order[uvmap.name] = copy.deepcopy(cuvs)
            return uvmap

        def createVColors(mesh, vcolors, vcname):
            """TODO: Doc."""
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
                for vidx in vert_loop_map:
                    for lidx in vert_loop_map[vidx]:
                        cmap.data[lidx].color = vcolors[vidx]
            return cmap

        # Create the mesh itself
        me = bpy.data.meshes.new(name)
        # Create vertices
        me.vertices.add(len(self.verts))
        me.vertices.foreach_set('co', unpack_list(self.verts))
        # Create per-Vertex normals
        if self.normals and options.importNormals:
            me.vertices.foreach_set('normal', unpack_list(self.normals))
        # Create faces
        face_vids = [v[0:3] for v in self.facedef]
        me.tessfaces.add(len(face_vids))
        me.tessfaces.foreach_set('vertices_raw', unpack_face_list(face_vids))
        # Create material
        material = None
        if options.importMaterials:
            material = self.createMaterialFromMDL(options)
            if material:
                me.materials.append(material)
        # Create uvmaps
        # Iterate in reverse so the first uvmap can be set to active
        uvmap = None
        for idx, tvs in reversed(list(enumerate(self.tverts))):
            if tvs:  # may be []
                uvname = self.name + '.tvert.' + str(idx)
                uvmap = createUVmap(me, tvs, uvname, material)
        if uvmap:
            me.uv_textures[uvmap.name].active = True
        """
            # Create UV maps
            uv_tex = None
            uvname = name + '.tverts'
            if (len(self.tverts) > 0) and me.tessfaces and self.bitmap:
                uv_tex = me.tessface_uv_textures.new(uvname)
                me.tessface_uv_textures.active = uv_tex

                # BEGIN EEEKADOODLE FIX
                # BUG: Evil eekadoodle problem where faces that have
                # vert index 0 at location 3 are shuffled.
                # vertIdx = self.facelist.faces[i]
                # if vertIdx[2] == 0:
                #     uvIdx = uvIdx[1], uvIdx[2], uvIdx[0]
                # END EEEKADOODLE FIX

                # EEEKADOODLE fix
                # facelist element: [v1, v2, v3, sg, uv1, uv2, uv3, mi]
                cuvs = [(f[5], f[6], f[4]) if f[2] == 0 else (f[4], f[5], f[6])
                        for f in self.facedef]
                # Set uv's
                timg = material.texture_slots[0].texture.image
                for i in range(len(cuvs)):
                    tessfaceUV = uv_tex.data[i]
                    tessfaceUV.uv1 = self.tverts[cuvs[i][0]]
                    tessfaceUV.uv2 = self.tverts[cuvs[i][1]]
                    tessfaceUV.uv3 = self.tverts[cuvs[i][2]]
                    tessfaceUV.image = timg
                # Save new order for uvs (for animesh animations)
                if uv_tex.name not in nvb_def.tvert_order:
                    nvb_def.tvert_order[uv_tex.name] = copy.deepcopy(cuvs)
                # Set material for each face
                me.tessfaces.foreach_set('material_index',
                                         [0] * len(me.tessfaces))
        if options.materialMode == 'MUL':
            # Add the new uv map to all texture slots
            if material and uv_tex:
                for ts in material.texture_slots:
                    if ts:
                        ts.uv_layer = uv_tex.name
        """
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
        createVColors(me, self.colors, 'colors')
        # Import custom normals
        me.update()
        if self.normals and me.loops and options.importNormals:
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
        else:
            me.validate()
        # me.update()
        return me

    def createObjectData(self, obj, options):
        """TODO: Doc."""
        Node.createObjectData(self, obj, options)

        obj.nvb.meshtype = self.meshtype
        obj.nvb.walkmeshtype = self.walkmeshtype
        if self.tilefade == 1:
            obj.nvb.tilefade = nvb_def.Tilefade.FADE
        elif self.tilefade == 2:
            obj.nvb.tilefade = nvb_def.Tilefade.BASE
        elif self.tilefade == 4:
            obj.nvb.tilefade = nvb_def.Tilefade.NEIGHBOUR
        else:
            obj.nvb.tilefade = nvb_def.Tilefade.NONE
        obj.nvb.render = (self.render >= 1)
        obj.nvb.shadow = (self.shadow >= 1)
        obj.nvb.beaming = (self.beaming >= 1)
        obj.nvb.inheritcolor = (self.inheritcolor >= 1)
        obj.nvb.rotatetexture = (self.rotatetexture >= 1)
        obj.nvb.transparencyhint = self.transparencyhint
        obj.nvb.selfillumcolor = self.selfillumcolor
        obj.nvb.ambientcolor = self.ambient
        obj.nvb.shininess = self.shininess

    def createObject(self, options):
        """TODO: Doc."""
        if options.minimapMode:
            if ((self.tilefade >= 1) and options.minimapSkipFade) or \
               (not self.render):
                # Fading objects or shadow meshes won't be imported in
                # minimap mode
                # might need them for the tree stucture, so import it
                # as an empty
                return Node.createObject(self, options)

        mesh = self.createMesh(self.name, options)
        obj = bpy.data.objects.new(self.name, mesh)
        self.createObjectData(obj, options)
        return obj

    @staticmethod
    def getAsciiTextures(material, options):
        """Write names and indices of textures to ascii."""
        def get_img_name(tslot):
            """Get the texture name for this texture slot."""
            imgname = ''
            tex = tslot.texture
            if tex.type == 'IMAGE':
                img = tex.image
                if tex.image:
                    # 1st try: Image filepath
                    if img.filepath:
                        imgname = \
                            os.path.splitext(os.path.basename(img.filepath))[0]
                    # 2nd try: Image name
                    if not imgname:
                        imgname = \
                            os.path.splitext(os.path.basename(img.name))[0]
            # Last resort: Texture name
            if not imgname:
                imgname = os.path.splitext(os.path.basename(tex.name))[0]
            return imgname

        # Generate a list of (texture_index, texture_name) tuples
        # texture index = texture slot index
        # texture name = either image filename, image name, texture
        texList1 = [(idx, get_img_name(tslot), tslot.alpha_factor)
                    for idx, tslot in enumerate(material.texture_slots)
                    if tslot and material.use_textures[idx]]
        if options.textureOrder == 'CON':
            # Alter texture indices to be consecutive
            texList2 = [(i, *v[1:]) for i, v in enumerate(texList1)]
            return texList2
        return texList1

    @staticmethod
    def generateAsciiMTRMaterial(obj, asciiLines, options):
        """Generates Ascii lines from an objects material for a MTR file."""
        pass

    @staticmethod
    def generateAsciiMDLMaterial(obj, asciiLines, options):
        """Generates Ascii lines from an objects material for a MDL file."""
        def get_img_name(tslot):
            imgName = ''
            tex = tslot.texture
            if (tex.type == 'IMAGE') and (tex.image):
                imgName = nvb_utils.getImageFilename(tex.image)
            return imgName

        def get_img_fname(img):
            """Return the image name without the file extension."""
            # Try getting the image name from the image source path
            fname = os.path.splitext(os.path.basename(img.filepath))[0]
            if (fname == ''):
                # If that doesn't work, get it from the image name
                fname = os.path.splitext(os.path.basename(img.name))[0]
            return fname

        def get_tslot_img(tslot):
            """Get the image texture from a texture slot."""
            if tslot:
                tex = tslot.texture
                if tex and tex.type == 'IMAGE':
                    return tex.image
            return None

        def get_alpha(mat, tslot):
            if mat and mat.use_transparency:
                if tslot:
                    return tslot.alpha_factor
                else:
                    return mat.alpha
            else:
                return 1.0

        hasTexture = False
        if not obj.nvb.render:
            if obj.nvb.shadow:
                # Shadow mesh: Everything should be black, no texture, no uv
                asciiLines.append('  diffuse 0.00 0.00 0.00')
                asciiLines.append('  specular 0.00 0.00 0.00')
                asciiLines.append('  bitmap black')
            else:
                asciiLines.append('  diffuse 1.00 1.00 1.00')
                asciiLines.append('  specular 0.00 0.00 0.00')
                asciiLines.append('  bitmap NULL')
        else:
            # Check if this object has a material assigned to it
            material = obj.active_material
            if material:
                # Write Color Values
                fstr = '  diffuse {: 3.2f} {: 3.2f} {: 3.2f}'
                asciiLines.append(fstr.format(*material.diffuse_color))
                fstr = '  specular {: 3.2f} {: 3.2f} {: 3.2f}'
                asciiLines.append(fstr.format(*material.specular_color))
                # Get textures for this material
                texList = Trimesh.getAsciiTextures(material, options)
                # Write bitmap params (first texture = bitmap)
                if len(texList) > 0:
                    hasTexture = True
                    asciiLines.append('  bitmap ' + texList[0][1])
                # Write texture params (but a single texture = only bitmap)
                if len(texList) > 1:
                    asciiLines.append('  renderhint NormalAndSpecMapped')
                    asciiLines.extend(['  texture' + str(i) + ' ' + n
                                      for i, n, _ in texList])
                # Alpha value:
                # 1. Texture slots present: get alpha from 1st slot
                # 2. No texture slot get alpha from material
                alpha = 1.0
                if material.use_transparency:
                    if len(texList) > 0:
                        _, _, alpha = texList[0]
                    else:
                        alpha = material.alpha
                asciiLines.append('  alpha {: 3.2f}'.format(alpha))
                """
                # Check if this material has a texture assigned
                tslots = nvb_utils.get_texture_slots(material)
                # Diffuse texture will always result in an bitmap entry
                if tslots[0]:
                    imgName = get_img_name(tslots[0])
                    if imgName:
                        asciiLines.append('  bitmap ' + imgName)
                        hasTexture = True
                alpha = get_alpha(material, tslots[0])
                if (alpha < 0.995):  # omit default value
                    asciiLines.append('  alpha ' + str(round(alpha, 2)))
                # Add renderhint if normal or specular maps were detected
                if tslots[1] or tslots[2]:
                    asciiLines.append('  renderhint NormalAndSpecMapped')
                    for idx, ts in enumerate(tslots):
                        if ts:
                            imgName = get_img_name(ts)
                            if imgName:
                                asciiLines.append('  texture' +
                                                  str(idx) + ' ' + imgName)
                                hasTexture = True
                """
        return hasTexture

    @staticmethod
    def generateAsciiMesh(obj, asciiLines, options, hasImgTexture):
        """TODO: Doc."""
        def addUVToList(uv, uvList, compress=True):
            """Helper function to keep uv coordinates unique."""
            if compress and (uv in uvList):
                return uvList.index(uv)
            else:
                uvList.append(uv)
                return (len(uvList)-1)

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
                        vcolors[vidx] = cmap.data[lidx].color
                asciiLines.append('  colors ' + str(len(mesh.vertices)))
                fstr = '    {: 8.5f} {: 8.5f} {: 8.5f}'
                asciiLines.extend([fstr.format(*vc) for vc in vcolors])

        me = obj.to_mesh(bpy.context.scene,
                         options.applyModifiers,
                         options.meshConvert)
        for p in me.polygons:
            p.use_smooth = True

        # Scaling fix
        # TODO: Find out how exactly blender handles scaling,
        # which matrices to use etc
        scale = obj.matrix_world.to_scale()
        scale_matrix = mathutils.Matrix([[scale[0], 0, 0, 0],
                                         [0, scale[1], 0, 0],
                                         [0, 0, scale[2], 0],
                                         [0, 0, 0, 1]])
        me.transform(scale_matrix)

        # Triangulation (doing it with bmesh to retain edges marked as sharp)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        del bm

        # Recalculate tessfaces for export
        me.calc_tessface()

        smoothGroups = []
        numSmoothGroups = 0
        if (obj.nvb.smoothgroup == 'SEPR') or \
           (obj.nvb.meshtype == nvb_def.Meshtype.WALKMESH) or \
           (not options.exportSmoothGroups):
            # 0 = Do not use smoothgroups
            smoothGroups = [0] * len(me.polygons)
            numSmoothGroups = 1
        elif (obj.nvb.smoothgroup == 'SING'):
            # All faces belong to smooth group 1
            smoothGroups = [1] * len(me.polygons)
            numSmoothGroups = 1
        else:
            (smoothGroups, numSmoothGroups) = me.calc_smooth_groups()

        # Add vertices
        asciiLines.append('  verts ' + str(len(me.vertices)))
        fstr = '    {: 8.5f} {: 8.5f} {: 8.5f}'
        asciiLines.extend([fstr.format(*v.co) for v in me.vertices])
        # Add normals and tangents
        uv_tex = me.uv_textures.active
        if uv_tex:
            me.calc_tangents(uv_tex.name)
            oknormals = []
            if options.exportNormals:
                # Try vertex-per-face normals
                for i in range(len(me.vertices)):
                    # All normals for this vertex
                    normals = \
                        [l.normal for l in me.loops if l.vertex_index == i]
                    s = set([str(n) for n in normals])
                    if len(s) != 1:
                        # Something is not right, cannot export this
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
                for v in me.vertices:
                    s = formatStr.format(l_rnd(v.normal[0], 5),
                                         l_rnd(v.normal[1], 5),
                                         l_rnd(v.normal[2], 5))
                    asciiLines.append(s)
                """
                # Add tangents
                oktangents = []
                #  Vertex-per-face tangents
                for i in range(len(me.vertices)):
                    # All tangents for this vertex
                    tangents = \
                        [[l.tangent, l.bitangent_sign]
                         for l in me.loops if l.vertex_index == i]
                    s = set([str(t[0]) for t in tangents])
                    if len(s) != 1:
                        # Something is not right, cannot export this
                        oktangents = []
                        print('Neverblender: WARNING - Invalid tangents ' +
                              obj.name)
                        break
                    oktangents.append(tangents[0])
                if oktangents:
                    asciiLines.append('  tangents ' + str(len(oktangents)))
                    fstr = '    {: 8.5f} {: 8.5f} {: 8.5f} {: 3.2f}'
                    asciiLines.extend([fstr.format(*t[0], t[1])
                                      for t in oktangents])
                """
                for face in me.polygons:
                    # face loops and face vertices are in the same order
                    for v_id, l_id in zip(face.vertices, face.loop_indices):
                        # this is the loop:
                        me.loops[l_id]
                        # this is the vertex in the corner of the loop:
                        me.vertices[v_id]
                """
                del oktangents
            del oknormals
            # me.free_normals_split()  #  Not necessary, mesh will be deleted
        # Add faces, corresponding tverts and shading groups
        faceList = []  # List of triangle faces
        uvList = []  # List of uv indices
        tessfaces = me.tessfaces
        tessfaces_uvs = me.tessface_uv_textures.active
        compress_uvs = (obj.nvb.meshtype != nvb_def.Meshtype.ANIMMESH)
        for i in range(len(tessfaces)):
            tface = tessfaces[i]
            smGroup = smoothGroups[i]
            matIdx = tface.material_index

            # We triangulated, so faces are always triangles
            uv1 = 0
            uv2 = 0
            uv3 = 0
            if tessfaces_uvs:
                uvFace = tessfaces_uvs.data[i]
                uv1 = addUVToList(uvFace.uv1, uvList, compress_uvs)
                uv2 = addUVToList(uvFace.uv2, uvList, compress_uvs)
                uv3 = addUVToList(uvFace.uv3, uvList, compress_uvs)

            faceList.append([tface.vertices[0],
                             tface.vertices[1],
                             tface.vertices[2],
                             smGroup,
                             uv1, uv2, uv3,
                             matIdx])
        # UV export
        if hasImgTexture:
            # Export UVs too
            vcnt = str(len(str(len(me.vertices))))  # Digits for vertices
            scnt = str(len(str(numSmoothGroups)))  # Digits for smoothgroups
            ucnt = str(len(str(len(uvList))))  # Digits for uv's
            asciiLines.append('  faces ' + str(len(faceList)))
            fstr = '    ' + \
                   '{:' + vcnt + 'd} {:' + vcnt + 'd} {:' + vcnt + 'd}  ' + \
                   '{:' + scnt + 'd}  ' + \
                   '{:' + ucnt + 'd} {:' + ucnt + 'd} {:' + ucnt + 'd}  ' + \
                   '{:2d}'
            asciiLines.extend([fstr.format(*f) for f in faceList])

            if (len(uvList) > 0):
                asciiLines.append('  tverts ' + str(len(uvList)))
                fstr = '    {: 6.3f} {: 6.3f}  0'
                asciiLines.extend([fstr.format(uv[0], uv[1]) for uv in uvList])
        else:
            # No image texture, don't export UVs/tverts
            vcnt = str(len(str(len(me.vertices))))
            scnt = str(len(str(numSmoothGroups)))
            asciiLines.append('  faces ' + str(len(faceList)))
            fstr = '    ' + \
                   '{:' + vcnt + 'd} {:' + vcnt + 'd} {:' + vcnt + 'd}  ' + \
                   '{:' + scnt + 'd}  ' + \
                   '0 0 0  ' + \
                   '{:2d}'
            asciiLines.extend([fstr.format(*f[0:4], f[7]) for f in faceList])
        # Vertex color
        generateVColors(me, asciiLines)
        bpy.data.meshes.remove(me)

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options):
        """TODO: Doc."""
        Node.generateAsciiData(obj, asciiLines, options)

        col = obj.nvb.wirecolor
        s = '  wirecolor {: 3.2f} {: 3.2f} {: 3.2f}'.format(*col)
        asciiLines.append(s)

        col = obj.nvb.ambientcolor
        s = '  ambient {: 3.2f} {: 3.2f} {: 3.2f}'.format(*col)
        asciiLines.append(s)

        hasImgTexture = Trimesh.generateAsciiMDLMaterial(obj, asciiLines,
                                                         options)
        asciiLines.append('  shininess ' + str(obj.nvb.shininess))
        if obj.nvb.meshtype is not nvb_def.Meshtype.WALKMESH:
            col = obj.nvb.selfillumcolor
            if round(sum(col), 2) > 0.0:  # Skip if default value
                s = '  selfillumcolor {: 3.2f} {: 3.2f} {: 3.2f}'.format(*col)
                asciiLines.append(s)
            # Skip if default value
            if not (obj.nvb.shadow and obj.nvb.render):
                asciiLines.append('  render ' + str(int(obj.nvb.render)))
                asciiLines.append('  shadow ' + str(int(obj.nvb.shadow)))
            val = int(obj.nvb.beaming)
            if val != 0:  # Skip if default value
                asciiLines.append('  beaming ' + str(val))
            val = int(obj.nvb.inheritcolor)
            if val != 0:  # Skip if default value
                asciiLines.append('  inheritcolor ' + str(val))
            val = obj.nvb.transparencyhint
            if val != 0:  # Skip if default value
                asciiLines.append('  transparencyhint ' + str(val))
            # These two are for tiles only
            if options.classification == nvb_def.Classification.TILE:
                asciiLines.append('  rotatetexture ' +
                                  str(int(obj.nvb.rotatetexture)))
                asciiLines.append('  tilefade ' + obj.nvb.tilefade)

        Trimesh.generateAsciiMesh(obj, asciiLines, options, hasImgTexture)


class Animmesh(Trimesh):
    """TODO: Doc."""

    nodetype = nvb_def.Nodetype.ANIMMESH

    def __init__(self, name='UNNAMED'):
        """TODO: Doc."""
        Trimesh.__init__(self, name)

        self.meshtype = nvb_def.Meshtype.ANIMMESH

    def createMaterial(self, options, makeunique=False):
        """TODO: Doc."""
        # Material is always unique
        return Trimesh.createMaterial(self, options, True)


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
        aline = Trimesh.loadAsciiLine(self, itlines)
        if not aline:
            return aline
        try:
            label = aline[0].lower()
        except (IndexError, AttributeError):
            return aline  # Probably empty line or comment
        if (label == 'period'):
            self.period = float(aline[1])
        elif (label == 'tightness'):
            self.tightness = float(aline[1])
        elif (label == 'displacement'):
            self.displacement = float(aline[1])
        elif (label == 'constraints'):
            if not self.constraints:
                vcnt = int(aline[1])
                tmp = [next(itlines) for _ in range(vcnt)]
                self.constraints = [float(v[0]) for v in tmp]
        return aline

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
    def generateAsciiData(cls, obj, asciiLines, options):
        """TODO: Doc."""
        Trimesh.generateAsciiData(obj, asciiLines, options)

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
        lfloat = float
        lchunker = nvb_utils.chunker
        for line in asciiLines:
            # A line looks like this
            # [group_name, vertex_weight, group_name, vertex_weight]
            # We create a list looking like this:
            # [[group_name, vertex_weight], [group_name, vertex_weight]]
            name_weight_pairs = []
            for chunk in lchunker(line, 2):
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
        aline = Trimesh.loadAsciiLine(self, itlines)
        if not aline:
            return aline
        try:
            label = aline[0].lower()
        except (IndexError, AttributeError):
            return aline  # Probably empty line or comment
        if (label == 'weights'):
            vcnt = int(aline[1])
            tmp = [next(itlines) for _ in range(vcnt)]
            self.loadAsciiWeights(tmp)
        return aline

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
    def generateAsciiWeights(obj, asciiLines, options):
        """TODO: Doc."""
        vg = obj.vertex_groups
        skingroups = [vg[n].index for n in bpy.data.objects.keys() if n in vg]
        asciiLines.append('  weights ' + str(len(obj.data.vertices)))
        lrnd = round
        for v in obj.data.vertices:
            weights = [[vg[g.group].name, lrnd(vg[g.group].weight(v.index), 3)]
                       for g in v.groups if g.group in skingroups]
            asciiLines.append('    ' +
                              ' '.join(['{} {:3.3f}'.format(w[0], w[1])
                                        for w in weights]))

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options):
        """TODO: Doc."""
        Trimesh.generateAsciiData(obj, asciiLines, options)

        Skinmesh.generateAsciiWeights(obj, asciiLines, options)


class Emitter(Node):
    """TODO: Doc."""

    nodetype = nvb_def.Nodetype.EMITTER

    def __init__(self, name='UNNAMED'):
        """TODO: Doc."""
        Node.__init__(self, name)

        self.meshtype = nvb_def.Meshtype.EMITTER
        self.xsize = 2
        self.ysize = 2
        self.rawascii = ''

    def loadAsciiLine(self, itlines):
        """TODO: Doc."""
        aline = None
        try:
            aline = next(itlines)
        except StopIteration:
            return None
        label = ''
        try:
            label = aline[0].lower()
        except (IndexError, AttributeError):
            return aline  # Probably empty line or comment
        if nvb_utils.isNumber(label):
            return aline
        if (label == 'node'):
            self.name = nvb_utils.getAuroraString(aline[2])
            self.rawascii = self.rawascii + '\n' + ' '.join(aline)
        elif (label == 'endnode'):
            self.rawascii = self.rawascii + '\n' + ' '.join(aline)
            return aline
        elif (label == 'parent'):
            self.parent = nvb_utils.getAuroraString(aline[1])
            self.rawascii = self.rawascii + '\n  #' + ' '.join(aline)
        elif (label == 'position'):
            self.position = tuple([float(v) for v in aline[1:4]])
            self.rawascii = self.rawascii + '\n  #' + ' '.join(aline)
        elif (label == 'orientation'):
            self.orientation = tuple([float(v) for v in aline[1:5]])
            self.rawascii = self.rawascii + '\n  #' + ' '.join(aline)
        elif (label == 'scale'):
            self.scale = float(aline[1])
            self.rawascii = self.rawascii + '\n  #' + ' '.join(aline)
        elif (label == 'wirecolor'):
            self.wirecolor = tuple([float(v) for v in aline[1:4]])
            self.rawascii = self.rawascii + '\n  #' + ' '.join(aline)
        else:
            self.rawascii = self.rawascii + '\n  ' + ' '.join(aline)
        return aline

    def createTextEmitter(self, obj, options):
        """TODO: Doc."""
        txt = bpy.data.texts.new(options.mdlname + '.' + obj.name)
        txt.write(self.rawascii)
        obj.nvb.rawascii = txt.name

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

        # After calling update() tessfaces become inaccessible
        mesh.validate()
        mesh.update()

        return mesh

    def createObjectData(self, obj, options):
        """TODO: Doc."""
        Node.createObjectData(self, obj, options)

        obj.nvb.meshtype = self.meshtype
        self.createTextEmitter(obj, options)

    def createObject(self, options):
        """TODO: Doc."""
        if options.minimapMode:
            return Node.createObject(self, options)

        mesh = self.createMesh(self.name, options)
        obj = bpy.data.objects.new(self.name, mesh)
        obj.nvb.imporder = self.nodeidx
        self.createObjectData(obj, options)
        return obj

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options):
        """TODO: Doc."""
        Node.generateAsciiData(obj, asciiLines, options)

        if obj.nvb.rawascii not in bpy.data.texts:
            print('Neverblender: WARNING - No emitter data for ' + obj.name)
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
               (label == 'parent') or (label == 'position') or \
               (label == 'orientation') or (label == 'scale') or \
               (label == 'wirecolor'):
                # We don't need any of this as we'll take it directly from
                # the object
                pass
            else:
                # We'll take everything that doesn't start with a #
                if label[0] != '#':
                    asciiLines.append('  ' + ' '.join(line))


class Light(Node):
    """TODO: Doc."""

    nodetype = nvb_def.Nodetype.LIGHT

    def __init__(self, name='UNNAMED'):
        """TODO: Doc."""
        Node.__init__(self, name)

        self.shadow = 1
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
            self.shadow = int(aline[1])
        elif (label == 'multiplier'):
            self.multiplier = float(aline[1])
        elif (label == 'color'):
            self.color = tuple([float(v) for v in aline[1:4]])
        elif (label == 'ambientonly'):
            self.ambientonly = int(aline[1])
        elif (label == 'ndynamictype'):
            self.ndynamictype = int(aline[1])
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
        #  Need to do two runs. First one is to find the number of flares
        lline = self.loadNumFlareValues(asciiLines)
        # Second run to get the values
        iterable = iter(asciiLines)
        lline = True
        while lline is not None:
            lline = self.loadAsciiLine(iterable)

    def createLamp(self, name):
        """TODO: Doc."""
        lamp = bpy.data.lamps.new(name, 'POINT')

        # TODO: Check for negative color values and do something
        # (works fine in blender though)
        lamp.color = self.color
        lamp.energy = self.multiplier
        lamp.distance = self.radius
        lamp.use_sphere = True

        return lamp

    def createObjectData(self, obj, options):
        """TODO: Doc."""
        Node.createObjectData(self, obj, options)

        obj.nvb.ambientonly = (self.ambientonly >= 1)
        obj.nvb.lighttype = nvb_def.Lighttype.getType(self.name)
        obj.nvb.shadow = (self.shadow >= 1)
        obj.nvb.lightpriority = self.lightpriority
        obj.nvb.fadinglight = (self.fadinglight >= 1)
        obj.nvb.isdynamic = (self.isdynamic >= 1)  # or(self.ndynamictype >= 1)
        obj.nvb.affectdynamic = (self.affectdynamic >= 1)

        # Create lensflares
        numflares = min(self.flareNumValues)
        if (self.flareradius > 0) or (numflares > 0):
            obj.nvb.lensflares = True
            for i in range(numflares):
                newItem = obj.nvb.flareList.add()
                newItem.texture = self.flareTextures[i]
                newItem.colorshift = self.flareCShifts[i]
                newItem.size = self.flareSizes[i]
                newItem.position = self.flarePositions[i]

        obj.nvb.flareradius = self.flareradius

    def createObject(self, options):
        """TODO: Doc."""
        if options.minimapMode:
            # We don't want lights in minimap mode
            # We may need it for the tree stucture, so import it as an empty
            return Node.createObject(self, options)
        lamp = self.createLamp(self.name)
        obj = bpy.data.objects.new(self.name, lamp)
        obj.nvb.imporder = self.nodeidx
        self.createObjectData(obj, options)
        return obj

    @staticmethod
    def generateAsciiFlares(obj, asciiLines):
        """TODO: Doc."""
        if obj.nvb.lensflares:
            asciiLines.append('  lensflares ' + str(int(obj.nvb.lensflares)))
            if len(obj.nvb.flareList) > 0:

                # TODO: Clean this up
                asciiLines.append('  texturenames zd')
                for flare in obj.nvb.flareList:
                    asciiLines.append('    ' + flare.texture)
                asciiLines.append('  flarepositions zd')
                for flare in obj.nvb.flareList:
                    asciiLines.append('    ' + str(round(flare.position, 5)))
                asciiLines.append('  flaresizes zd')
                for flare in obj.nvb.flareList:
                    asciiLines.append('    ' + str(flare.size))
                asciiLines.append('  flarecolorshifts zd')
                fstr = '    {: 3.2f} {: 3.2f} {: 3.2f}'
                for flare in obj.nvb.flareList:
                    asciiLines.append(fstr.format(*(flare.colorshift)))
        asciiLines.append('  flareradius ' +
                          str(round(obj.nvb.flareradius, 1)))

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options):
        """TODO: Doc."""
        Node.generateAsciiData(obj, asciiLines, options)

        lamp = obj.data
        asciiLines.append('  radius ' + str(round(lamp.distance, 1)))
        asciiLines.append('  multiplier ' + str(round(lamp.energy, 1)))
        asciiLines.append('  color ' +
                          str(round(lamp.color[0], 2)) + ' ' +
                          str(round(lamp.color[1], 2)) + ' ' +
                          str(round(lamp.color[2], 2)))
        asciiLines.append('  ambientonly ' + str(int(obj.nvb.ambientonly)))
        asciiLines.append('  nDynamicType ' + str(int(obj.nvb.isdynamic)))
        asciiLines.append('  affectDynamic ' + str(int(obj.nvb.affectdynamic)))
        asciiLines.append('  shadow ' + str(int(obj.nvb.shadow)))
        asciiLines.append('  lightpriority ' + str(obj.nvb.lightpriority))
        asciiLines.append('  fadingLight ' + str(int(obj.nvb.fadinglight)))
        Light.generateAsciiFlares(obj, asciiLines)


class Aabb(Trimesh):
    """TODO: Doc."""

    nodetype = nvb_def.Nodetype.AABB

    def __init__(self, name='UNNAMED'):
        """TODO: Doc."""
        Trimesh.__init__(self, name)

        self.meshtype = nvb_def.Meshtype.WALKMESH
        self.walkmeshtype = nvb_def.Walkmeshtype.AABB

    @staticmethod
    def generateAsciiAABB(obj, asciiLines, options):
        """TODO: Doc."""
        walkmesh = obj.to_mesh(bpy.context.scene,
                               options.applyModifiers,
                               options.meshConvert)

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
            else:
                # Ngon or no polygon at all
                # (This should never be the case with tessfaces)
                print('Neverblender: WARNING - Ngon in walkmesh. \
                       Unable to generate aabb.')
                return

        aabbTree = []
        nvb_aabb.generateTree(aabbTree, faceList)

        l_rnd = round
        if aabbTree:
            node = aabbTree.pop(0)
            asciiLines.append('  aabb  ' +
                              ' ' +
                              str(l_rnd(node[0], 5)) +
                              ' ' +
                              str(l_rnd(node[1], 5)) +
                              ' ' +
                              str(l_rnd(node[2], 5)) +
                              ' ' +
                              str(l_rnd(node[3], 5)) +
                              ' ' +
                              str(l_rnd(node[4], 5)) +
                              ' ' +
                              str(l_rnd(node[5], 5)) +
                              ' ' +
                              str(node[6]))
            for node in aabbTree:
                asciiLines.append('    ' +
                                  str(l_rnd(node[0], 5)) +
                                  ' ' +
                                  str(l_rnd(node[1], 5)) +
                                  ' ' +
                                  str(l_rnd(node[2], 5)) +
                                  ' ' +
                                  str(l_rnd(node[3], 5)) +
                                  ' ' +
                                  str(l_rnd(node[4], 5)) +
                                  ' ' +
                                  str(l_rnd(node[5], 5)) +
                                  ' ' +
                                  str(node[6]))

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options):
        """TODO: Doc."""

        loc = obj.location
        asciiLines.append('  position {: 8.5f} {: 8.5f} {: 8.5f}'.format(*loc))

        rot = nvb_utils.getAuroraRotFromObject(obj)
        fstr = '  orientation {: 8.5f} {: 8.5f} {: 8.5f} {: 8.5f}'
        asciiLines.append(fstr.format(*rot))

        col = obj.nvb.wirecolor
        s = '  wirecolor {: 3.2f} {: 3.2f} {: 3.2f}'.format(*col)
        asciiLines.append(s)

        asciiLines.append('  ambient 1.0 1.0 1.0')
        asciiLines.append('  diffuse 1.0 1.0 1.0')
        asciiLines.append('  specular 0.0 0.0 0.0')
        # asciiLines.append('  shininess 0')  # No shininess on wok
        asciiLines.append('  bitmap NULL')
        Trimesh.generateAsciiMesh(obj, asciiLines, options, False)
        Aabb.generateAsciiAABB(obj, asciiLines, options)

    def createMesh(self, name, options):
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

        # Apply the walkmesh materials to each face
        me.tessfaces.foreach_set('material_index',
                                 [f[7] for f in self.facedef])
        me.update()
        return me

    def createObject(self, options):
        """TODO: Doc."""
        if options.minimapMode:
            # We don't want walkmeshes in minimap mode
            obj = bpy.data.objects.new(self.name, None)
        else:
            mesh = self.createMesh(self.name, options)
            obj = bpy.data.objects.new(self.name, mesh)
            obj.hide_render = True
            self.createObjectData(obj, options)
        obj.nvb.imporder = self.nodeidx
        return obj
