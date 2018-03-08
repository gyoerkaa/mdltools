"""TODO: DOC."""

import math
import array
import copy
import os
import itertools
# blender import
import mathutils
import bpy
import bpy_extras.image_utils
import bmesh
from bpy_extras.io_utils import unpack_list, unpack_face_list
# custom imports
from . import nvb_def
from . import nvb_utils
from . import nvb_aabb


class Mtr(object):
    """A material read from an mtr file."""
    def __init__(self, name='unnamed'):
        """TODO: DOC."""
        self.valid = False

        self.name = name
        self.ambient = (1.0, 1.0, 1.0)
        self.diffuse = (1.0, 1.0, 1.0)
        self.specular = (0.0, 0.0, 0.0)
        self.alpha = 1.0
        self.textures = ['']
        self.customshaders = dict()
        self.renderhints = set()
        self.parameters = dict()

    def isvalid(self):
        return self.valid

    def loadAsciiTexName(s):
        """Convert to lower case. Convert null to nvb_def.null."""
        if (not s or s.lower() == nvb_def.null):
            return nvb_def.null
        return s.lower()

    def loadFile(self, filepath):
        """Load contents of a mtr file."""
        self.valid = False
        try:
            mtrFile = open(filepath, 'r')
        except IOError:
            return
        else:
            asciiData = mtrFile.read()
            self.loadAscii(asciiData)
            mtrFile.close()

    def loadTextBlock(self, textBlock):
        """Load content of a blender text block."""
        self.valid = False
        if not textBlock:
            return
        # txtLines = [l.split() for l in textBlock.as_string().split('\n')]
        asciiData = textBlock.as_string()
        self.loadAscii(asciiData)

    def loadAscii(self, asciiData):
        """TODO: DOC."""
        asciiLines = [l.strip().split() for l in asciiData.splitlines()]
        # list(map(self.loadAsciiLine, asciiLines))
        iterable = iter(asciiLines)
        lline = True
        while lline is not None:
            lline = self.loadAsciiLine(iterable)

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
        if label == 'ambient':
            self.ambient = tuple([float(v) for v in aline[1:4]])
        elif label == 'diffuse':
            self.diffuse = tuple([float(v) for v in aline[1:4]])
        elif label == 'specular':
            self.specular = tuple([float(v) for v in aline[1:4]])
        elif label == 'alpha':
            self.alpha = float(aline[1])
        elif label == 'renderhint':
            self.renderhints.add(nvb_utils.getAuroraString(aline[1]))
        elif label == 'parameter':
            # 'parameter' 'float' 'myParam' '1.0'
            self.valid = True
            try:
                self.parameters[aline[2]] = (aline[1], aline[3:])
            except IndexError:
                # Bad parameter, skip it
                pass
        elif label.startswith('customshader'):
            self.valid = True
            self.customshaders[label] = aline[1]
        elif label.startswith('texture'):
            self.valid = True
            tid = 0
            # 'texture' has to be followed by a number
            if label[7:]:
                tid = int(label[7:])
                tcnt = len(self.textures)
                if tid+1 > tcnt:
                    self.textures.extend(['' for _ in range(tid-tcnt+1)])
                if not self.textures[tid]:
                    self.textures[tid] = self.loadAsciiTexName(aline[1])
        return aline

    def generateAscii(self, material, options):
        """Generate a mtr file as asciilines."""
        asciiLines = []
        if material.nvb.mtrtext and material.nvb.mtrtext in bpy.data.texts:
            txtBlock = bpy.data.texts[material.nvb.mtrtext]
            self.loadTextBlock(txtBlock)
        # Add custom shaders
        asciiLines.append('// Shaders')
        if material.nvb.shadervs:
            asciiLines.append('customshaderVS ' + material.nvb.shadervs)
        if material.nvb.shaderfs:
            asciiLines.append('customshaderFS ' + material.nvb.shaderfs)
        asciiLines.append('')
        asciiLines.append('// Textures')
        # Add list of textures
        texList = NodeMaterial.getAsciiTextures(material, options)
        if len(texList) > 0:
            asciiLines.extend(['texture' + str(i) + ' ' + n
                               for i, n, _ in texList])
            asciiLines.append('')
            asciiLines.append('// Parameters')
            for pname, pvalues in self.parameters.items():
                asciiLines.append('parameter ' +
                                  pvalues[0] +
                                  ' ' + pname + ' ' +
                                  ' '.join(pvalues[1]))
        return asciiLines


class NodeMaterial(object):
    """A material read from an mdl node."""

    def __init__(self, name='unnamed'):
        """TODO: DOC."""
        self.name = name
        self.ambient = (1.0, 1.0, 1.0)
        self.diffuse = (1.0, 1.0, 1.0)
        self.specular = (0.0, 0.0, 0.0)
        self.alpha = 1.0
        self.bitmap = ''  # 'null' will be convertd to ''
        self.textures = ['']  # texture[0] overwrites bitmap
        self.renderhints = set()
        self.materialname = ''  # Name of external mtr file
        self.customshaderVS = ''
        self.customshaderFS = ''

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
            eq = eq and NodeMaterial.colorisclose(mat.diffuse_color, cdiff)
            eq = eq and NodeMaterial.colorisclose(mat.specular_color, cspec)
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
        d = d and NodeMaterial.colorisclose(self.ambient, (1.0, 1.0, 1.0))
        d = d and NodeMaterial.colorisclose(self.diffuse, (1.0, 1.0, 1.0))
        d = d and NodeMaterial.colorisclose(self.specular, (0.0, 0.0, 0.0))
        d = d and math.isclose(self.alpha, 1.0, abs_tol=0.03)
        d = d and self.bitmap == ''
        d = d and self.textures.count('') == len(self.textures)
        d = d and self.materialname == ''
        return d

    def loadAsciiLine(self, aline):
        """TODO: Doc."""
        try:
            label = aline[0].lower()
        except (IndexError, AttributeError):
            return aline  # Probably empty line or comment
        if (label == 'ambient'):
            self.ambient = tuple([float(v) for v in aline[1:4]])
        elif (label == 'diffuse'):
            self.diffuse = tuple([float(v) for v in aline[1:4]])
        elif (label == 'specular'):
            self.specular = tuple([float(v) for v in aline[1:4]])
        elif (label == 'alpha'):
            self.alpha = float(aline[1])
        elif (label == 'materialname'):
            self.materialname = nvb_utils.getAuroraString(aline[1])
        elif (label == 'renderhint'):
            self.renderhints.add(nvb_utils.getAuroraString(aline[1]))
        elif (label == 'bitmap'):
            self.bitmap = nvb_utils.getAuroraString(aline[1])
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

    def loadMTR(self, options):
        """Loads contents of a mtr file into the this material."""
        if not self.materialname:
            return
        mtrMat = None
        if self.materialname in options.mtrdb:
            # MTR was already loaded before
            mtrMat = options.mtrdb[self.materialname]
        else:
            # Load MTR from file
            mdlPath, _ = os.path.split(options.filepath)
            mtrFilename = self.name + '.mtr'
            mtrPath = os.fsencode(os.path.join(mdlPath, mtrFilename))
            mtrMat = Mtr()
            mtrMat.loadFile(mtrPath)
            options.mtrdb[self.materialname] = mtrMat
        # Load values into self
        if mtrMat and mtrMat.isvalid():  # Abort if no file was read
            # If there are any textures in the mtr load them into self
            if mtrMat.textures:
                # TODO: Decide between two options
                # A. Selecetive loading, override only present texture
                l1 = len(self.textures)
                l2 = len(mtrMat.textures)
                if l1 < l2:
                    self.textures.extend(['' for _ in range(l2-l1+1)])
                for tidx, texname in enumerate(mtrMat.textures):
                    self.textures
                # B. Override all if only a single texture is present
                # self.textures = mtrMat.textures
            if 'customshadervs' in mtrMat.customshaders:
                self.customshaderVS = mtrMat.customshaders['customshadervs']
            if 'customshaderfs' in mtrMat.customshaders:
                self.customshaderFS = mtrMat.customshaders['customshaderfs']

    @staticmethod
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

    @staticmethod
    def applyTextureRoles(material, alpha, options):
        """Apply settings to material and texture slots for default shader."""
        matalpha = alpha
        if options.textureDefaultRoles:
            # Diffuse in tslot 0
            tslot = material.texture_slots[0]
            if tslot is not None:
                tslot.texture_coords = 'UV'
                tslot.use_map_color_diffuse = True
                tslot.use_map_normal = False
                tslot.use_map_color_spec = False
                tslot.use_map_alpha = True
                tslot.alpha_factor = alpha
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
            # Other slots are generic
        material.use_transparency = True
        material.alpha = matalpha
        material.specular_alpha = matalpha

    def create(self, options, makeunique=False):
        """Creates a blender material with the stored values."""
        # Load mtr values intro this material
        if options.materialLoadMTR and self.materialname != '':
            self.loadMTR(options)
        # If this material has no texture, no alpha and default values
        if self.isdefault():
            return None
        # texture0 == bitmap, texture0 takes precedence
        texlist = self.textures
        if len(texlist) > 0:
            if texlist[0] == '':
                texlist[0] = self.bitmap
        else:
            if self.bitmap:
                texlist.append(self.bitmap)
        # Look for similar materials to avoid duplicates
        material = None
        if options.materialAutoMerge and not makeunique:
            material = NodeMaterial.findMaterial(
                texlist, self.materialname,
                self.diffuse, self.specular, self.alpha)
        if not material:
            matname = texlist[0].lower() if texlist[0] else self.name
            material = bpy.data.materials.new(matname)
            material.use_transparency = True
            material.diffuse_color = self.diffuse
            material.diffuse_intensity = 1.0
            material.specular_color = self.specular
            material.specular_intensity = 1.0
            material.nvb.ambient_color = self.ambient
            material.nvb.shadervs = self.customshaderVS
            material.nvb.shaderfs = self.customshaderFS
            # Load all textures
            for idx, mdltex in enumerate(texlist):
                if mdltex:  # might be ''
                    tslot = material.texture_slots.create(idx)
                    tslot.texture = NodeMaterial.createTexture(mdltex, mdltex,
                                                               options)
            # Set the default roles for texture slots:
            NodeMaterial.applyTextureRoles(material, self.alpha, options)
        return material

    @staticmethod
    def generateDefaultValues(asciiLines):
        """Write default material values to ascii."""
        asciiLines.append('  ambient 1.00 1.00 1.00')
        asciiLines.append('  diffuse 1.00 1.00 1.00')
        asciiLines.append('  specular 0.00 0.00 0.00')
        asciiLines.append('  bitmap ' + nvb_def.null)

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
                imgname = tex.name
            return imgname

        # Generate a list of (texture_index, texture_name) tuples
        # texture index = texture slot index
        # texture name = either image filename, image name, texture
        texList1 = [(idx, get_img_name(tslot), tslot.alpha_factor)
                    for idx, tslot in enumerate(material.texture_slots)
                    if tslot and material.use_textures[idx]]
        # Alter texture indices to be consecutive
        # texList2 = [(i, *v[1:]) for i, v in enumerate(texList1)]
        # return texList2
        return texList1

    @staticmethod
    def generateAscii(obj, asciiLines, options):
        """Write Ascii lines from the objects material for a MDL file."""
        istextured = False  # Return value
        if not obj.nvb.render:
            NodeMaterial.generateDefaultValues(asciiLines)
        else:
            # Check if this object has a material assigned to it
            material = obj.active_material
            if material:
                # Write Color Values
                fstr = '  ambient {: 3.2f} {: 3.2f} {: 3.2f}'
                asciiLines.append(fstr.format(*material.nvb.ambient_color))
                fstr = '  diffuse {: 3.2f} {: 3.2f} {: 3.2f}'
                asciiLines.append(fstr.format(*material.diffuse_color))
                fstr = '  specular {: 3.2f} {: 3.2f} {: 3.2f}'
                asciiLines.append(fstr.format(*material.specular_color))
                # Get textures for this material
                texList = NodeMaterial.getAsciiTextures(material, options)
                # Write first texture as bitmap
                if len(texList) > 0:
                    istextured = True
                    asciiLines.append('  bitmap ' + texList[0][1])
                    # Add renderhint
                    if len(texList) > 1:
                        asciiLines.append('  renderhint NormalAndSpecMapped')
                else:
                    asciiLines.append('  bitmap ' + nvb_def.null)
                # Either add material reference or textures
                if options.materialUseMTR and material.nvb.usemtr:
                    asciiLines.append('  materialname ' +
                                      material.nvb.mtrname)
                else:
                    # Write the rest of the textures as textureX
                    if len(texList) > 1:
                        asciiLines.extend(['  texture' + str(i) + ' ' + n
                                          for i, n, _ in texList[1:]])
                # Alpha value:
                # 1. Texture slots present: get alpha from 1st slot
                # 2. No texture slot get alpha from material
                if material.use_transparency:
                    alpha = 1.0
                    if len(texList) > 0:
                        _, _, alpha = texList[0]
                    else:
                        alpha = material.alpha
                    # Skip if 1.0
                    if not math.isclose(alpha, 1.0, rel_tol=0.01):
                        asciiLines.append('  alpha {: 3.2f}'.format(alpha))
            else:
                NodeMaterial.generateDefaultValues(asciiLines)
        return istextured


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
    def generateAsciiData(cls, obj, asciiLines, options, iswalkmesh=False):
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
    def generateAscii(cls, obj, asciiLines, options, iswalkmesh=False):
        """TODO: Doc."""
        asciiLines.append('node ' + cls.nodetype + ' ' + obj.name)
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
        # obj.nvb.dummytype = nvb_def.Dummytype.getType(self.name)


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
        self.render = 1
        self.shadow = 1
        self.beaming = 0
        self.inheritcolor = 0  # Unused ?
        self.transparencyhint = 0
        self.selfillumcolor = (0.0, 0.0, 0.0)
        self.shininess = 0
        self.rotatetexture = 0
        self.material = NodeMaterial()
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
        elif (label == 'inheritcolor'):
            self.inheritcolor = int(aline[1])
        elif (label == 'rotatetexture'):
            self.rotatetexture = int(aline[1])
        elif (label == 'transparencyhint'):
            self.transparencyhint = int(aline[1])
        elif ((label == 'selfillumcolor') or
              (label == 'setfillumcolor')):
            self.selfillumcolor = tuple([float(v) for v in aline[1:4]])
        elif (label == 'shininess'):
            self.shininess = int(float(aline[1]))
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
        else:
            self.material.loadAsciiLine(aline)
        return aline

    @staticmethod
    def createUVlayer2(mesh, uvcoords, faceuvs, uvname, uvimg=None):
        """TODO: Doc."""
        uvlay = None
        if uvcoords and mesh.polygons:
            uvtex = mesh.uv_textures.new(uvname)
            uvlay = mesh.uv_layers[uvtex.name].data
            for fidx, poly in enumerate(mesh.polygons):
                v1, v2, v3 = faceuvs[fidx]
                uvlay[poly.loop_start].uv = uvcoords[v1]
                uvlay[poly.loop_start + 1].uv = uvcoords[v2]
                uvlay[poly.loop_start + 2].uv = uvcoords[v3]
                uvtex.data[fidx].image = uvimg
        # For blender 2.8:
        # for uvf in mesh.data.uv_textures.active.data:
        #     uvf.image = timg
        return uvlay

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
        if self.normals and options.importNormals:
            me.vertices.foreach_set('normal', unpack_list(self.normals))
            me.create_normals_split()
        # Create material
        material = None
        matimg = None
        if options.importMaterials:
            material = self.material.create(options)
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
        if self.normals and me.loops and options.importNormals:
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
        matimg = None
        if options.importMaterials:
            material = self.material.create(options)
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
        # Create Vertex colors
        Trimesh.createVColors(me, self.colors, 'colors')
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
    def generateAsciiMesh(obj, asciiLines, options, hasImgTexture):
        """TODO: Doc."""

        def getSmoothGroups(obj, mesh, options):
            smoothGroups = []
            numSmoothGroups = 0
            if (obj.nvb.smoothgroup == 'SEPR') or \
               (obj.nvb.meshtype == nvb_def.Meshtype.AABB) or \
               (not options.exportSmoothGroups):
                # 0 = Do not use smoothgroups
                smoothGroups = [0] * len(mesh.polygons)
                numSmoothGroups = 1
            elif (obj.nvb.smoothgroup == 'SING') or \
                 (options.exportNormals):
                # All faces belong to smooth group 1
                smoothGroups = [1] * len(mesh.polygons)
                numSmoothGroups = 1
            else:
                (smoothGroups, numSmoothGroups) = mesh.calc_smooth_groups()
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
                        vcolors[vidx] = cmap.data[lidx].color
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
        me.calc_tessface()  # Recalculate tessfaces after triangulation

        # Generate Smoothgroups
        fcSGrps = getSmoothGroups(obj, me, options)
        # Add vertices
        asciiLines.append('  verts ' + str(len(me.vertices)))
        fstr = '    {: 8.5f} {: 8.5f} {: 8.5f}'
        asciiLines.extend([fstr.format(*v.co) for v in me.vertices])
        # Add normals and tangents
        uvmap = me.uv_textures.active
        if uvmap and options.exportNormals:
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
        # Write tverts to file (if any)
        fstr = '    {: 6.3f} {: 6.3f}  0'
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
        bpy.data.meshes.remove(me)

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options, iswalkmesh=False):
        """TODO: Doc."""
        Node.generateAsciiData(obj, asciiLines, options, iswalkmesh)

        col = obj.nvb.wirecolor
        s = '  wirecolor {: 3.2f} {: 3.2f} {: 3.2f}'.format(*col)
        asciiLines.append(s)

        hastexture = False
        if iswalkmesh:
            asciiLines.append('  ambient 1.00 1.00 1.00')
            asciiLines.append('  diffuse 1.00 1.00 1.00')
            asciiLines.append('  specular 0.00 0.00 0.00')
            asciiLines.append('  bitmap ' + nvb_def.null)
        else:
            hastexture = NodeMaterial.generateAscii(obj, asciiLines, options)
            # Shininess
            asciiLines.append('  shininess ' + str(obj.nvb.shininess))
            # Self illumination color
            col = obj.nvb.selfillumcolor
            if round(sum(col), 2) > 0.0:  # Skip default value
                s = '  selfillumcolor {: 3.2f} {: 3.2f} {: 3.2f}'.format(*col)
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
    def generateAsciiData(cls, obj, asciiLines, options, iswalkmesh=False):
        """TODO: Doc."""
        Trimesh.generateAsciiData(obj, asciiLines, options, iswalkmesh)
        if iswalkmesh:
            return
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
        mesh.vertices[0].co = (0.5,  0.5, 0.0)
        mesh.vertices[1].co = (0.5, -0.5, 0.0)
        mesh.vertices[2].co = (-0.5, -0.5, 0.0)
        mesh.vertices[3].co = (-0.5,  0.5, 0.0)
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
    def generateAsciiData(cls, obj, asciiLines, options, iswalkmesh=False):
        """TODO: Doc."""
        Node.generateAsciiData(obj, asciiLines, options, iswalkmesh)

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
        obj.nvb.lighttype = nvb_def.Lighttype.getType(self.name)

        data = obj.data
        if data:  # might be None in batch mode
            data.nvb.ambientonly = (self.ambientonly >= 1)
            data.nvb.shadow = (self.shadow >= 1)
            data.nvb.lightpriority = self.lightpriority
            data.nvb.fadinglight = (self.fadinglight >= 1)
            data.nvb.isdynamic = (self.isdynamic >= 1)
            data.nvb.affectdynamic = (self.affectdynamic >= 1)

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
                fstr = '    {: 3.2f} {: 3.2f} {: 3.2f}'
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
        fstr = '  color {: 3.2f} {: 3.2f} {: 3.2f}'
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

        # l_rnd = round
        if aabbTree:
            fstr = '  aabb ' + \
                   '{: 5.2f} {: 5.2f} {: 5.2f}  ' + \
                   '{: 5.2f} {: 5.2f} {: 5.2f} {: 3d}'
            asciiLines.append(fstr.format(*aabbTree.pop(0)))
            fstr = '       ' + \
                   '{: 5.2f} {: 5.2f} {: 5.2f}  ' + \
                   '{: 5.2f} {: 5.2f} {: 5.2f} {: 3d}'
            asciiLines.extend([fstr.format(*bb) for bb in aabbTree])

    @classmethod
    def generateAsciiData(cls, obj, asciiLines, options, iswalkmesh=False):
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
        """
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
                material.specular_intensity = 0.0
            me.materials.append(material)
        """
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
