"""TODO: DOC."""

import mathutils
import bpy
import bpy_extras.image_utils
import bmesh
import re
from bpy_extras.io_utils import unpack_list, unpack_face_list

from . import nvb_def
from . import nvb_utils
from . import nvb_aabb
from . import nvb_parse


class FaceList():
    """TODO: DOC."""

    def __init__(self):
        """TODO: DOC."""
        self.faces = []  # int 3-tuple, vertex indices
        self.shdgr = []  # int, shading group for this face
        self.uvIdx = []  # int 3-tuple, texture/uv vertex indices
        self.matId = []  # int, material index

    def __len__(self):
        """TODO: DOC."""
        return min(len(self.faces),
                   len(self.shdgr),
                   len(self.uvIdx),
                   len(self.matId))


class FlareList():
    """TODO: DOC."""

    def __init__(self):
        """TODO: DOC."""
        self.textures = []
        self.sizes = []
        self.positions = []
        self.colorshifts = []


class Node(object):
    """TODO: DOC."""

    nodetype = 'undefined'

    def __init__(self, name='unnamed'):
        """TODO: DOC."""
        self.createdObj = ''  # Name of the corresponding object in blender
        self.nodeidx = -1  # Order in mdlfile (needs to be restored for export)

        self.name = name
        self.parent = ''
        self.position = (0.0, 0.0, 0.0)
        self.orientation = (0.0, 0.0, 0.0, 0.0)
        self.scale = 1.0
        self.wirecolor = (0.0, 0.0, 0.0)

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

    def loadAscii(self, asciiLines, nodeidx=-1):
        """TODO: DOC."""
        l_float = float
        l_isNumber = nvb_utils.isNumber

        self.nodeidx = nodeidx
        for line in asciiLines:
            try:
                label = line[0].lower()
            except (IndexError, AttributeError):
                # Probably empty line or whatever, skip it
                continue

            if not l_isNumber(label):
                if (label == 'node'):
                    self.name = nvb_utils.getAuroraString(line[2])
                elif (label == 'endnode'):
                    return
                elif (label == 'parent'):
                    self.parent = nvb_utils.getAuroraString(line[1])
                elif (label == 'position'):
                    self.position = (l_float(line[1]),
                                     l_float(line[2]),
                                     l_float(line[3]))
                elif (label == 'orientation'):
                    self.orientation = (l_float(line[1]),
                                        l_float(line[2]),
                                        l_float(line[3]),
                                        l_float(line[4]))
                elif (label == 'scale'):
                    self.scale = l_float(line[1])
                elif (label == 'wirecolor'):
                    self.wirecolor = (l_float(line[1]),
                                      l_float(line[2]),
                                      l_float(line[3]))

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
        self.createdObj = obj.name
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
        s = '  position {: 8.5f} {: 8.5f} {: 8.5f}'.format(round(loc[0], 5),
                                                           round(loc[1], 5),
                                                           round(loc[2], 5))
        asciiLines.append(s)

        rot = nvb_utils.euler2nwangle(transmat.to_euler('XYZ'))
        formatString = '  orientation {: 8.5f} {: 8.5f} {: 8.5f} {: 8.5f}'
        s = formatString.format(round(rot[0], 5),
                                round(rot[1], 5),
                                round(rot[2], 5),
                                round(rot[3], 5))
        asciiLines.append(s)

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

    def loadAscii(self, asciiLines, nodeidx=-1):
        """TODO: Doc."""
        Node.loadAscii(self, asciiLines, nodeidx)
        l_isNumber = nvb_utils.isNumber

        for line in asciiLines:
            try:
                label = line[0].lower()
            except (IndexError, AttributeError):
                # Probably empty line or whatever, skip it
                continue
            if not l_isNumber(label):
                if (label == 'refmodel'):
                    self.refmodel = nvb_utils.getAuroraString(line[1])
                elif (label == 'reattachable'):
                    try:
                        self.reattachable = int(line[1])
                    except (ValueError, IndexError):
                        pass  # TODO: Print a warning or smth

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
        self.textures = ['', '', '', '']
        self.rotatetexture = 0
        self.verts = []
        self.facelist = FaceList()
        self.tverts = []
        self.tangents = []
        self.normals = []

    def loadAscii(self, asciiLines, nodeidx=-1):
        """TODO: Doc."""
        Node.loadAscii(self, asciiLines, nodeidx)

        l_int = int
        l_float = float
        l_isNumber = nvb_utils.isNumber

        # Re-Initialize values in case this method is called multiple times
        self.verts = []
        self.tverts = []
        self.facelist = FaceList()

        for i, line in enumerate(asciiLines):
            try:
                label = line[0].lower()
            except (IndexError, AttributeError):
                # Probably empty line or whatever, skip it
                continue

            if not l_isNumber(label):
                if (label == 'tilefade'):
                    self.tilefade = l_int(line[1])
                elif (label == 'render'):
                    try:
                        self.render = l_int(line[1])
                    except (ValueError, IndexError):
                        pass
                elif (label == 'shadow'):
                    try:
                        self.shadow = l_int(line[1])
                    except (ValueError, IndexError):
                        pass
                elif (label == 'beaming'):
                    self.beaming = l_int(line[1])
                elif (label == 'inheritcolor '):
                    self.inheritcolor = l_int(line[1])
                elif (label == 'rotatetexture'):
                    self.rotatetexture = l_int(line[1])
                elif (label == 'alpha'):
                    self.alpha = l_float(line[1])
                elif (label == 'transparencyhint'):
                    self.transparencyhint = l_int(line[1])
                elif ((label == 'selfillumcolor') or
                      (label == 'setfillumcolor')):
                    self.selfillumcolor = (l_float(line[1]),
                                           l_float(line[2]),
                                           l_float(line[3]))
                elif (label == 'ambient'):
                    self.ambient = (l_float(line[1]),
                                    l_float(line[2]),
                                    l_float(line[3]))
                elif (label == 'diffuse'):
                    self.diffuse = (l_float(line[1]),
                                    l_float(line[2]),
                                    l_float(line[3]))
                elif (label == 'specular'):
                    self.specular = (l_float(line[1]),
                                     l_float(line[2]),
                                     l_float(line[3]))
                elif (label == 'shininess'):
                    self.shininess = l_int(l_float(line[1]))
                elif (label == 'center'):
                    # Unused ? Because we don't do anything with this
                    try:
                        self.center = (l_float(line[1]),
                                       l_float(line[2]),
                                       l_float(line[3]))
                    except (ValueError, IndexError):
                        # Probably a 'undefined' string, cannot be converted
                        # We just let it slide and ignore it
                        pass
                elif (label == 'bitmap'):
                    self.bitmap = nvb_utils.getAuroraString(line[1])
                elif (label == 'renderhint'):
                    self.renderhints.append(nvb_utils.getAuroraString(line[1]))
                elif (label == 'texture0'):
                    self.textures[0] = nvb_utils.getAuroraString(line[1])
                elif (label == 'texture1'):
                    self.textures[1] = nvb_utils.getAuroraString(line[1])
                elif (label == 'texture2'):
                    self.textures[2] = nvb_utils.getAuroraString(line[1])
                elif (label == 'verts'):
                    if not self.verts:
                        numVals = l_int(line[1])
                        nvb_parse.f3(asciiLines[i+1:i+numVals+1],
                                     self.verts)
                elif (label == 'faces'):
                    if len(self.facelist) <= 0:
                        numVals = l_int(line[1])
                        nvb_parse.faces(asciiLines[i+1:i+numVals+1],
                                        self.facelist)
                elif (label == 'tverts'):
                    if not self.tverts:
                        numVals = l_int(line[1])
                        nvb_parse.f2(asciiLines[i+1:i+numVals+1],
                                     self.tverts)
                elif (label == 'normals'):
                    if not self.normals:
                        numVals = l_int(line[1])
                        nvb_parse.f3(asciiLines[i+1:i+numVals+1],
                                     self.normals)
                elif (label == 'tangents'):
                    if not self.tangents:
                        numVals = l_int(line[1])
                        nvb_parse.f4(asciiLines[i+1:i+numVals+1],
                                     self.tangents)

    def createMaterial(self, options, keepunique=False):
        """TODO: Doc."""

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
                    image = bpy_extras.image_utils.load_image(
                        imgname + '.tga',
                        options.texturePath,
                        recursive=options.textureSearch,
                        place_holder=False,
                        ncase_cmp=True)
                    if image is None:
                        image = bpy.data.images.new(imgname, 512, 512)
                    image.name = imgname
                    tex.image = image
            return tex

        matname = self.bitmap
        if not matname:
            matname = self.name
        # Get textures
        # tnames = ['', '', '']
        tdiff_name = self.bitmap
        # tnames[0] = self.textures[0]
        tnorm_name = ''
        tspec_name = ''
        if 'normalandspecmapped' in self.renderhints:
            # texture0 value takes precedence
            if self.textures[0]:
                # tnames[0] = self.textures[0]
                tdiff_name = self.textures[0]
            tnorm_name = self.textures[1]
            tspec_name = self.textures[2]
        # Look for similar materials to avoid duplicates
        material = None
        if options.materialMode == 'SIN' and not keepunique:
            material = nvb_utils.find_material(
                tdiff_name, tnorm_name, tspec_name,
                self.diffuse, self.specular,
                self.alpha)
        # If no similar material was found, create a new one
        if not material:
            material = bpy.data.materials.new(matname)
            material.use_transparency = True
            material.diffuse_color = self.diffuse
            material.diffuse_intensity = 1.0
            material.specular_color = self.specular
            material.specular_intensity = 1.0
            if tdiff_name:
                tslot = material.texture_slots.add()
                tslot.texture = createTexture(tdiff_name, tdiff_name, options)
                tslot.texture_coords = 'UV'
                tslot.use_map_color_diffuse = True
                tslot.use_map_alpha = True
                tslot.alpha_factor = self.alpha
                material.alpha = 0.0
            else:
                material.alpha = self.alpha
            if tnorm_name:
                tslot = material.texture_slots.add()
                tslot.texture = createTexture(tnorm_name, tnorm_name, options)
                tslot.texture_coords = 'UV'
                tslot.use_map_color_diffuse = False
                tslot.use_map_normal = True
            if tspec_name:
                tslot = material.texture_slots.add()
                tslot.texture = createTexture(tspec_name, tspec_name, options)
                tslot.texture_coords = 'UV'
                tslot.use_map_color_diffuse = False
                tslot.use_map_color_spec = True
                # tslot.use_map_hardness = True
        return material

    def createMesh(self, name, options):
        """TODO: Doc."""
        # Create the mesh itself
        mesh = bpy.data.meshes.new(name)
        mesh.vertices.add(len(self.verts))
        mesh.vertices.foreach_set('co', unpack_list(self.verts))
        mesh.tessfaces.add(len(self.facelist.faces))
        mesh.tessfaces.foreach_set('vertices_raw',
                                   unpack_face_list(self.facelist.faces))

        # Create material
        if options.materialMode != 'NON':
            material = self.createMaterial(options)
            mesh.materials.append(material)
            # Create UV map
            if (len(self.tverts) > 0) and mesh.tessfaces and self.bitmap:
                uv = mesh.tessface_uv_textures.new(name + '.uv')
                mesh.tessface_uv_textures.active = uv
                # we need to save the order the tverts were created in blender
                # for animmeshes/uv animations
                tvert_neworder = []
                # Create uv's
                for i in range(len(self.facelist.uvIdx)):
                    # Get a tessface
                    tessface = mesh.tessfaces[i]
                    # Apply material (there is only ever one)
                    tessface.material_index = 0
                    # Grab a uv for the face
                    tessfaceUV = mesh.tessface_uv_textures[0].data[i]
                    # Get the indices of the 3 uv's for this face
                    uvIdx = self.facelist.uvIdx[i]

                    # BEGIN EEEKADOODLE FIX
                    # BUG: Evil eekadoodle problem where faces that have
                    # vert index 0 at location 3 are shuffled.
                    vertIdx = self.facelist.faces[i]
                    if vertIdx[2] == 0:
                        uvIdx = uvIdx[1], uvIdx[2], uvIdx[0]
                    # END EEEKADOODLE FIX

                    # Add uv coordinates to face
                    tessfaceUV.uv1 = self.tverts[uvIdx[0]]
                    tessfaceUV.uv2 = self.tverts[uvIdx[1]]
                    tessfaceUV.uv3 = self.tverts[uvIdx[2]]

                    tvert_neworder.extend([uvIdx[0], uvIdx[1], uvIdx[2]])

                    # Apply texture to uv face
                    tessfaceUV.image = material.texture_slots[0].texture.image
                if uv.name not in nvb_def.tvert_order:
                    nvb_def.tvert_order[uv.name] = tvert_neworder
                # Add the new uv map to texture slot (doesn't work properly)
                # if material.active_texture:
                #    ts = material.texture_slots[material.active_texture_index]
                #    ts.uv_layer = uv.name
        # Import smooth groups as sharp edges
        if options.importSmoothGroups:
            bm = bmesh.new()
            mesh.update()
            bm.from_mesh(mesh)
            if hasattr(bm.edges, "ensure_lookup_table"):
                bm.edges.ensure_lookup_table()
            # Mark edge as sharp if its faces belong to different smooth groups
            for e in bm.edges:
                f = e.link_faces
                if (len(f) > 1) and \
                   (self.facelist.shdgr[f[0].index] !=
                        self.facelist.shdgr[f[1].index]):
                    edgeIdx = e.index
                    mesh.edges[edgeIdx].use_edge_sharp = True
            bm.free()
            del bm
            mesh.show_edge_sharp = True

        mesh.update()
        return mesh

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
    def generateAsciiMaterial(obj, asciiLines):
        """TODO: Doc."""
        def getImgName(tslot):
            imgName = ''
            tex = tslot.texture
            if (tex.type == 'IMAGE') and (tex.image):
                imgName = nvb_utils.getImageFilename(tex.image)
            return imgName

        def getAlpha(mat, tslot):
            if mat and mat.use_transparency:
                if tslot:
                    return tslot.alpha_factor
                else:
                    return mat.alpha
            else:
                return 1.0

        hasImgTexture = False
        if not obj.nvb.render and obj.nvb.shadow:
            # Shadow mesh: Everything should be black, no texture, no uv
            asciiLines.append('  diffuse 0.00 0.00 0.00')
            asciiLines.append('  specular 0.00 0.00 0.00')
            asciiLines.append('  bitmap black')
        else:
            # Check if this object has a material assigned to it
            material = obj.active_material
            if material:
                formatString = '  diffuse {: 3.2f} {: 3.2f} {: 3.2f}'
                s = formatString.format(round(material.diffuse_color[0], 2),
                                        round(material.diffuse_color[1], 2),
                                        round(material.diffuse_color[2], 2))
                asciiLines.append(s)

                formatString = '  specular {: 3.2f} {: 3.2f} {: 3.2f}'
                s = formatString.format(round(material.specular_color[0], 2),
                                        round(material.specular_color[1], 2),
                                        round(material.specular_color[2], 2))
                asciiLines.append(s)

                # Check if this material has a texture assigned
                tslots = nvb_utils.get_texture_slots(material)
                # Diffuse texture will always result in an bitmap entry
                if tslots[0]:
                    imgName = getImgName(tslots[0])
                    if imgName:
                        asciiLines.append('  bitmap ' + imgName)
                        hasImgTexture = True
                alpha = getAlpha(material, tslots[0])
                if (alpha < 0.995):  # omit default value
                    asciiLines.append('  alpha ' + str(round(alpha, 2)))
                # Add renderhint if normal or specular maps were detected
                if tslots[1] or tslots[2]:
                    asciiLines.append('  renderhint NormalAndSpecMapped')
                    for idx, ts in enumerate(tslots):
                        if ts:
                            imgName = getImgName(ts)
                            if imgName:
                                asciiLines.append('  texture' +
                                                  str(idx) + ' ' + imgName)
                                hasImgTexture = True
        return hasImgTexture

    @staticmethod
    def addUVToList(uv, uvList, compress=True):
        """Helper function to avoid exporting mutiples of uv coordinates."""
        if compress and (uv in uvList):
            return uvList.index(uv)
        else:
            uvList.append(uv)
            return (len(uvList)-1)

    @staticmethod
    def generateAsciiMesh(obj, asciiLines, options, hasImgTexture):
        """TODO: Doc."""
        mesh = obj.to_mesh(bpy.context.scene,
                           options.applyModifiers,
                           options.meshConvert)
        for p in mesh.polygons:
            p.use_smooth = True

        # Scaling fix
        # TODO: Find out how exactly blender handles scaling,
        # which matrices to use etc
        scale = obj.matrix_world.to_scale()
        scale_matrix = mathutils.Matrix([[scale[0], 0, 0, 0],
                                         [0, scale[1], 0, 0],
                                         [0, 0, scale[2], 0],
                                         [0, 0, 0, 1]])
        mesh.transform(scale_matrix)

        # Triangulation (doing it with bmesh to retain edges marked as sharp)
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        del bm

        # Recalculate tessfaces for export
        mesh.calc_tessface()

        smoothGroups = []
        numSmoothGroups = 0
        if (obj.nvb.smoothgroup == 'SEPR') or \
           (obj.nvb.meshtype == nvb_def.Meshtype.WALKMESH) or \
           (not options.exportSmoothGroups):
            # 0 = Do not use smoothgroups
            smoothGroups = [0] * len(mesh.polygons)
            numSmoothGroups = 1
        elif (obj.nvb.smoothgroup == 'SING'):
            # All faces belong to smooth group 1
            smoothGroups = [1] * len(mesh.polygons)
            numSmoothGroups = 1
        else:
            (smoothGroups, numSmoothGroups) = mesh.calc_smooth_groups()

        faceList = []  # List of triangle faces
        uvList = []  # List of uv indices

        # Add vertices
        asciiLines.append('  verts ' + str(len(mesh.vertices)))
        l_round = round
        formatString = '    {: 8.5f} {: 8.5f} {: 8.5f}'
        for v in mesh.vertices:
            s = formatString.format(l_round(v.co[0], 5),
                                    l_round(v.co[1], 5),
                                    l_round(v.co[2], 5))
            asciiLines.append(s)

        # Add faces and corresponding tverts and shading groups
        tessfaces = mesh.tessfaces
        tessfaces_uvs = mesh.tessface_uv_textures.active
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
                uv1 = Trimesh.addUVToList(uvFace.uv1, uvList, compress_uvs)
                uv2 = Trimesh.addUVToList(uvFace.uv2, uvList, compress_uvs)
                uv3 = Trimesh.addUVToList(uvFace.uv3, uvList, compress_uvs)

            faceList.append([tface.vertices[0],
                             tface.vertices[1],
                             tface.vertices[2],
                             smGroup,
                             uv1, uv2, uv3,
                             matIdx])

        if hasImgTexture:
            # Export UVs too
            asciiLines.append('  faces ' + str(len(faceList)))

            vd = str(len(str(len(mesh.vertices))))  # Digits for vertices
            sd = str(len(str(numSmoothGroups)))  # Digits for smoothgroups
            ud = str(len(str(len(uvList))))  # Digits for uv's
            formatString = '    ' + \
                           '{:' + vd + 'd} {:' + vd + 'd} {:' + vd + 'd}  ' + \
                           '{:' + sd + 'd}  ' + \
                           '{:' + ud + 'd} {:' + ud + 'd} {:' + ud + 'd}  ' + \
                           '{:2d}'
            for f in faceList:
                s = formatString.format(f[0], f[1], f[2],
                                        f[3],
                                        f[4], f[5], f[6],
                                        f[7])
                asciiLines.append(s)

            if (len(uvList) > 0):
                asciiLines.append('  tverts ' + str(len(uvList)))
                formatString = '    {: 6.3f} {: 6.3f}  0'
                for uv in uvList:
                    s = formatString.format(round(uv[0], 3), round(uv[1], 3))
                    asciiLines.append(s)
        else:
            # No image texture, don't export UVs/tverts
            asciiLines.append('  faces ' + str(len(faceList)))

            vd = str(len(str(len(mesh.vertices))))
            sd = str(len(str(numSmoothGroups)))
            formatString = '    ' + \
                           '{:' + vd + 'd} {:' + vd + 'd} {:' + vd + 'd}  ' + \
                           '{:' + sd + 'd}  ' + \
                           '0 0 0  ' + \
                           '{:2d}'
            for f in faceList:
                s = formatString.format(f[0], f[1], f[2],
                                        f[3],
                                        f[7])
                asciiLines.append(s)

        bpy.data.meshes.remove(mesh)

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options):
        """TODO: Doc."""
        Node.generateAsciiData(obj, asciiLines, options)

        col = obj.nvb.wirecolor
        s = '  wirecolor {: 3.2f} {: 3.2f} {: 3.2f}'.format(round(col[0], 2),
                                                            round(col[1], 2),
                                                            round(col[2], 2))
        asciiLines.append(s)

        col = obj.nvb.ambientcolor
        s = '  ambient {: 3.2f} {: 3.2f} {: 3.2f}'.format(round(col[0], 2),
                                                          round(col[1], 2),
                                                          round(col[2], 2))
        asciiLines.append(s)

        hasImgTexture = Trimesh.generateAsciiMaterial(obj, asciiLines)
        asciiLines.append('  shininess ' + str(obj.nvb.shininess))
        if obj.nvb.meshtype is not nvb_def.Meshtype.WALKMESH:
            col = obj.nvb.selfillumcolor
            if round(sum(col), 2) > 0.0:  # Skip if default value
                s = '  selfillumcolor {: 3.2f} {: 3.2f} {: 3.2f}'. \
                    format(round(col[0], 2),
                           round(col[1], 2),
                           round(col[2], 2))
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

    def createMaterial(self, options, keepunique=False):
        """TODO: Doc."""
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

    def loadAscii(self, asciiLines, nodeidx=-1):
        """TODO: Doc."""
        Trimesh.loadAscii(self, asciiLines, nodeidx)

        # Re-initialize values, in case this member is called multiple times
        self.constraints = []

        l_int = int
        l_float = float
        l_isNumber = nvb_utils.isNumber
        for idx, line in enumerate(asciiLines):
            try:
                label = line[0].lower()
            except (IndexError, AttributeError):
                # Probably empty line or whatever, skip it
                continue
            if not l_isNumber(label):
                if (label == 'period'):
                    self.period = l_float(line[1])
                elif (label == 'tightness'):
                    self.tightness = l_float(line[1])
                elif (label == 'displacement'):
                    self.displacement = l_float(line[1])
                elif (label == 'constraints'):
                    if not self.constraints:
                        numVals = l_int(line[1])
                        nvb_parse.f1(asciiLines[idx+1:idx+numVals+1],
                                     self.constraints)

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
        pattern = '(?:\s|^)(\D+)\s+([-+]?\d*\.?\d+)(?=\s|$)'
        for al in asciiLines:
            # A line looks like this
            # [group_name, vertex_weight, group_name, vertex_weight]
            # We create a list looking like this:
            # [[group_name, vertex_weight], [group_name, vertex_weight]]
            line = ' '.join(al)
            gw_pairs = []
            matches = re.findall(pattern, line)
            for m in matches:
                gw_pairs.append([m[0], lfloat(m[1])])
            self.weights.append(gw_pairs)

    def loadAsciiWeights2(self, asciiLines):
        """TODO: Doc."""
        lfloat = float
        lchunker = nvb_utils.chunker
        for line in asciiLines:
            # A line looks like this
            # [group_name, vertex_weight, group_name, vertex_weight]
            # We create a list looking like this:
            # [[group_name, vertex_weight], [group_name, vertex_weight]]
            memberships = []
            for chunk in lchunker(line, 2):
                try:
                    sgm = [chunk[0], lfloat(chunk[1])]
                    memberships.append(sgm)
                except ValueError:
                    continue
            self.weights.append(memberships)

    def loadAscii(self, asciiLines, nodeidx=-1):
        """TODO: Doc."""
        Trimesh.loadAscii(self, asciiLines, nodeidx)
        l_int = int
        l_isNumber = nvb_utils.isNumber
        for idx, line in enumerate(asciiLines):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue

            if not l_isNumber(label):
                if (label == 'weights'):
                    numVals = l_int(line[1])
                    self.loadAsciiWeights(asciiLines[idx+1:idx+numVals+1])
                    break  # Only one relevant value, abort loop when found

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
            asciiLines.append('  ' + ' '.join(['{} {:3.3f}'.format(w[0], w[1])
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

    def loadAscii(self, asciiLines, nodeidx=-1):
        """TODO: Doc."""
        l_float = float
        l_isNumber = nvb_utils.isNumber

        self.nodeidx = nodeidx
        for line in asciiLines:
            try:
                label = line[0].lower()
            except IndexError:
                continue  # Probably empty line, skip it

            if not l_isNumber(label):
                if (label == 'node'):
                    self.name = nvb_utils.getAuroraString(line[2])
                    self.rawascii = self.rawascii + '\n' + ' '.join(line)
                elif (label == 'endnode'):
                    self.rawascii = self.rawascii + '\n' + ' '.join(line)
                    return
                elif (label == 'parent'):
                    self.parent = nvb_utils.getAuroraString(line[1])
                    self.rawascii = self.rawascii + '\n  #' + ' '.join(line)
                elif (label == 'position'):
                    self.position = (l_float(line[1]),
                                     l_float(line[2]),
                                     l_float(line[3]))
                    self.rawascii = self.rawascii + '\n  #' + ' '.join(line)
                elif (label == 'orientation'):
                    self.orientation = (l_float(line[1]),
                                        l_float(line[2]),
                                        l_float(line[3]),
                                        l_float(line[4]))
                    self.rawascii = self.rawascii + '\n  #' + ' '.join(line)
                elif (label == 'scale'):
                    self.scale = l_float(line[1])
                    self.rawascii = self.rawascii + '\n  #' + ' '.join(line)
                elif (label == 'wirecolor'):
                    self.wirecolor = (l_float(line[1]),
                                      l_float(line[2]),
                                      l_float(line[3]))
                    self.rawascii = self.rawascii + '\n  #' + ' '.join(line)
                else:
                    self.rawascii = self.rawascii + '\n  ' + ' '.join(line)

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
        self.flareList = FlareList()

    def loadAscii(self, asciiLines, nodeidx=-1):
        """TODO: Doc."""
        Node.loadAscii(self, asciiLines, nodeidx)

        flareTextureNamesStart = 0
        numFlares = 0
        numVals = 0

        l_int = int
        l_float = float
        l_isNumber = nvb_utils.isNumber
        for idx, line in enumerate(asciiLines):
            try:
                label = line[0].lower()
            except IndexError:
                continue  # Probably empty line, skip it

            if not l_isNumber(label):
                if (label == 'radius'):
                    self.radius = l_float(line[1])
                elif (label == 'shadow'):
                    self.shadow = l_int(line[1])
                elif (label == 'multiplier'):
                    self.multiplier = l_float(line[1])
                elif (label == 'color'):
                    self.color = (l_float(line[1]),
                                  l_float(line[2]),
                                  l_float(line[3]))
                elif (label == 'ambientonly'):
                    self.ambientonly = l_int(line[1])
                elif (label == 'ndynamictype'):
                    self.ndynamictype = l_int(line[1])
                elif (label == 'isdynamic'):
                    self.isdynamic = l_int(line[1])
                elif (label == 'affectdynamic'):
                    self.affectdynamic = l_int(line[1])
                elif (label == 'negativelight'):
                    self.negativelight = l_int(line[1])
                elif (label == 'lightpriority'):
                    self.lightpriority = l_int(line[1])
                elif (label == 'fadinglight'):
                    self.fadinglight = l_int(line[1])
                elif (label == 'lensflares'):
                    self.lensflares = l_int(line[1])
                elif (label == 'flareradius'):
                    self.flareradius = l_float(line[1])
                elif (label == 'texturenames'):
                    # List of names follows, but we don't necessarily know how
                    # many flares there are
                    # We 'll need to read them later. For now save the index
                    flareTextureNamesStart = idx+1
                elif (label == 'flaresizes'):
                    # List of floats
                    numVals = next((i for i, v in enumerate(asciiLines[idx+1:])
                                    if not l_isNumber(v[0])), -1)
                    nvb_parse.f1(asciiLines[idx+1:idx+numVals+1],
                                 self.flareList.sizes)
                elif (label == 'flarepositions'):
                    # List of floats
                    numVals = next((i for i, v in enumerate(asciiLines[idx+1:])
                                    if not l_isNumber(v[0])), -1)
                    nvb_parse.f1(asciiLines[idx+1:idx+numVals+1],
                                 self.flareList.positions)
                elif (label == 'flarecolorshifts'):
                    # List of float 3-tuples
                    numVals = next((i for i, v in enumerate(asciiLines[idx+1:])
                                    if not l_isNumber(v[0])), -1)
                    nvb_parse.f3(asciiLines[idx+1:idx+numVals+1],
                                 self.flareList.colorshifts)

        # Load flare texture names:
        numFlares = min(len(self.flareList.sizes),
                        min(len(self.flareList.colorshifts),
                            len(self.flareList.positions)))
        for i in range(numFlares):
            texName = asciiLines[flareTextureNamesStart+i][0]
            self.flareList.textures.append(texName)

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

        if (self.flareradius > 0) or (self.lensflares >= 1):
            obj.nvb.lensflares = True
            numFlares = len(self.flareList.textures)
            for i in range(numFlares):
                newItem = obj.nvb.flareList.add()
                newItem.texture = self.flareList.textures[i]
                newItem.colorshift = self.flareList.colorshifts[i]
                newItem.size = self.flareList.sizes[i]
                newItem.position = self.flareList.positions[i]

        obj.nvb.flareradius = self.flareradius

    def createObject(self, options):
        """TODO: Doc."""
        if options.minimapMode:
            # We don't need lights in minimap mode
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
                for flare in obj.nvb.flareList:
                    formatString = '    {: 3.2f} {: 3.2f} {: 3.2f}'
                    s = formatString.format(round(flare.colorshift[0], 2),
                                            round(flare.colorshift[1], 2),
                                            round(flare.colorshift[2], 2))
                    asciiLines.append(s)
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

        l_round = round
        if aabbTree:
            node = aabbTree.pop(0)
            asciiLines.append('  aabb  ' +
                              ' ' +
                              str(l_round(node[0], 5)) +
                              ' ' +
                              str(l_round(node[1], 5)) +
                              ' ' +
                              str(l_round(node[2], 5)) +
                              ' ' +
                              str(l_round(node[3], 5)) +
                              ' ' +
                              str(l_round(node[4], 5)) +
                              ' ' +
                              str(l_round(node[5], 5)) +
                              ' ' +
                              str(node[6]))
            for node in aabbTree:
                asciiLines.append('    ' +
                                  str(l_round(node[0], 5)) +
                                  ' ' +
                                  str(l_round(node[1], 5)) +
                                  ' ' +
                                  str(l_round(node[2], 5)) +
                                  ' ' +
                                  str(l_round(node[3], 5)) +
                                  ' ' +
                                  str(l_round(node[4], 5)) +
                                  ' ' +
                                  str(l_round(node[5], 5)) +
                                  ' ' +
                                  str(node[6]))

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options):
        """TODO: Doc."""
        loc = obj.location
        asciiLines.append('  position ' +
                          str(round(loc[0], 5)) + ' ' +
                          str(round(loc[1], 5)) + ' ' +
                          str(round(loc[2], 5)))
        rot = nvb_utils.getAuroraRotFromObject(obj)
        asciiLines.append('  orientation ' +
                          str(round(rot[0], 5)) + ' ' +
                          str(round(rot[1], 5)) + ' ' +
                          str(round(rot[2], 5)) + ' ' +
                          str(round(rot[3], 5)))
        color = obj.nvb.wirecolor
        asciiLines.append('  wirecolor ' +
                          str(round(color[0], 2)) + ' ' +
                          str(round(color[1], 2)) + ' ' +
                          str(round(color[2], 2)))
        asciiLines.append('  ambient 1.0 1.0 1.0')
        asciiLines.append('  diffuse 1.0 1.0 1.0')
        asciiLines.append('  specular 0.0 0.0 0.0')
        asciiLines.append('  shininess 0')
        asciiLines.append('  bitmap NULL')
        Trimesh.generateAsciiMesh(obj, asciiLines, options, False)
        Aabb.generateAsciiAABB(obj, asciiLines, options)

    def createMesh(self, name, options):
        """TODO: Doc."""
        # Create the mesh itself
        mesh = bpy.data.meshes.new(name)
        mesh.vertices.add(len(self.verts))
        mesh.vertices.foreach_set('co', unpack_list(self.verts))
        mesh.tessfaces.add(len(self.facelist.faces))
        mesh.tessfaces.foreach_set('vertices_raw',
                                   unpack_face_list(self.facelist.faces))

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
            mesh.materials.append(material)

        # Apply the walkmesh materials to each face
        for idx, face in enumerate(mesh.tessfaces):
            face.material_index = self.facelist.matId[idx]

        mesh.update()
        return mesh

    def createObject(self, options):
        """TODO: Doc."""
        if options.minimapMode:
            # No walkmeshes in minimap mode and we don't need an empty as
            # replacement either as AABB nodes never have children
            return
        mesh = self.createMesh(self.name, options)
        obj = bpy.data.objects.new(self.name, mesh)
        obj.nvb.imporder = self.nodeidx
        obj.hide_render = True
        self.createObjectData(obj, options)
        return obj
