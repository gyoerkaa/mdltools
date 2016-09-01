import mathutils
import bpy
import bpy_extras.image_utils
import bmesh
from bpy_extras.io_utils import unpack_list, unpack_face_list

from . import nvb_glob
from . import nvb_def
from . import nvb_utils
from . import nvb_aabb
from . import nvb_parse

class Node(object):
    """
    Basic node from which every other is derived
    """
    nodetype = 'undefined'

    def __init__(self, name = 'unnamed'):
        self.objidx = -1 # Order in mdlfile (needs to be restored for export)

        self.name        = name
        self.parent      = ''
        self.position    = (0.0, 0.0, 0.0)
        self.orientation = (0.0, 0.0, 0.0, 0.0)
        self.scale       = 1.0
        self.wirecolor   = (0.0, 0.0, 0.0)


    def __eq__(self, other):
        if isinstance(other, Node):
            return (self.name == other.name) and (self.parent == other.parent)


    def __ne__(self, other):
        return not self.__eq__(self, other)


    def __str__(self):
        return 'node ' + self.nodetype + ' ' + self.name


    def loadAscii(self, asciiBlock):
        for line in asciiBlock:
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue

            if not l_isNumber(label):
                if (label  == 'endnode'):
                    return
                elif (label == 'parent'):
                    self.parentName = nvb_utils.getAuroraString(line[1])
                elif (label == 'position'):
                    self.position = (l_float(line[1]),
                                     l_float(line[2]),
                                     l_float(line[3]) )
                elif (label == 'orientation'):
                    self.orientation = (l_float(line[1]),
                                        l_float(line[2]),
                                        l_float(line[3]),
                                        l_float(line[4]) )
                elif (label == 'scale'):
                    self.scale = l_float(line[1])
                elif (label == 'wirecolor'):
                    self.wirecolor = (l_float(line[1]),
                                      l_float(line[2]),
                                      l_float(line[3]) )


    def createObjectData(self, obj):
        nvb_utils.setObjectRotationAurora(obj, self.orientation)
        obj.scale         = (self.scale, self.scale, self.scale)
        obj.location      = self.position
        obj.nvb.wirecolor = self.wirecolor


    def createObject(self):
        """
        Returns an object for use in blender.
        """
        obj = bpy.data.objects.new(self.name, None)
        obj.nvb.order = self.objIdx

        self.createObjectData(obj)
        return obj


    @staticmethod
    def generateAsciiData(cls, obj, asciiLines):
        if obj.parent:
            asciiLines.append('  parent ' + obj.parent.name)
        else:
            asciiLines.append('  parent ' + nvb_def.null)
        # Scaling fix
        transmat = self.getAdjustedMatrix(obj)
        loc = transmat.to_translation()
        s = '  position {: 8.5f} {: 8.5f} {: 8.5f}'.format(round(loc[0], 5),
                                                           round(loc[1], 5),
                                                           round(loc[2], 5))
        asciiLines.append(s)

        rot = nvb_utils.euler2nwangle(transmat.to_euler('XYZ'))
        s = '  orientation {: 8.5f} {: 8.5f} {: 8.5f} {: 8.5f}'.format(round(rot[0], 5),
                                                                       round(rot[1], 5),
                                                                       round(rot[2], 5),
                                                                       round(rot[3], 5))
        asciiLines.append(s)
        '''
        loc = obj.location
        s = '  position {: 8.5f} {: 8.5f} {: 8.5f}'.format(round(loc[0], 5), round(loc[1], 5), round(loc[2], 5))
        asciiLines.append(s)

        rot = nvb_utils.getAuroraRotFromObject(obj)
        s = '  orientation {: 8.5f} {: 8.5f} {: 8.5f} {: 8.5f}'.format(round(rot[0], 5), round(rot[1], 5), round(rot[2], 5), round(rot[3], 5))
        asciiLines.append(s)
        '''
        col = obj.nvb.wirecolor
        s = '  wirecolor {: 3.2f} {: 3.2f} {: 3.2f}'.format(round(col[0], 2),
                                                            round(col[1], 2),
                                                            round(col[2], 2))
        asciiLines.append(s)

        scale = round(nvb_utils.getAuroraScale(obj), 3)
        if (scale != 1.0):
            asciiLines.append('  scale ' + str(scale))


    @classmethod
    def generateAscii(cls, obj, asciiLines):
        asciiLines.append('node ' + cls.nodetype + ' ' + obj.name)
        cls.generateAsciiData(cls, obj, asciiLines)
        asciiLines.append('endnode')



class Dummy(Node):
    """

    """
    nodetype  = 'dummy'

    def __init__(self, name = 'unnamed'):
        Node.__init__(self, name)

        self.dummytype = nvb_def.Dummytype.NONE


    def loadAscii(self, asciiBlock):
        Node.loadAscii(self, asciiBlock)


    def createObjectData(self, obj):
         Node.createObjectData(self, obj)

    @staticmethod
    def generateAsciiData(cls, obj):
        if obj.parent:
            asciiLines.append('  parent ' + obj.parent.name)
        else:
            asciiLines.append('  parent ' + nvb_def.null)


class Patch(Node):
    '''
    Same as a plain Dummy.
    '''
    nodetype = 'patch'

    def __init__(self, name = 'UNNAMED'):
        Node.__init__(self, name)

        self.dummytype = nvb_def.Dummytype.PATCH


    def createObjectData(self, obj):
        Node.createObjectData(self, obj)

        obj.nvb.dummytype = self.dummytype


class Reference(Node):
    '''
    Contains a reference to another mdl
    '''
    nodetype = 'reference'

    def __init__(self, name = 'UNNAMED'):
        Node.__init__(self, name)

        self.dummytype    = nvb_def.Dummytype.REFERENCE
        self.refmodel     = nvb_def.null
        self.reattachable = 0


    def loadAscii(self, asciiNode):
        Node.loadAscii(self, asciiNode)
        l_isNumber = nvb_utils.isNumber

        for line in asciiNode:
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue
            if not l_isNumber(label):
                if   (label == 'refmodel'):
                    self.refmodel = nvb_utils.getAuroraString(line[1])
                elif (label == 'reattachable'):
                    try:
                        self.reattachable = int(line[1])
                    except:
                        pass #TODO: Print a warning or smth


    def createObjectData(self, obj):
        Node.createObjectData(self, obj)
        obj.nvb.dummytype    = self.dummytype
        obj.nvb.refmodel     = self.refmodel
        obj.nvb.reattachable = (self.reattachable >= 1)


    @staticmethod
    def generateAsciiData(obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN, simple = False):
        Node.generateAsciiData(obj, asciiLines, exportObjects, classification)
        asciiLines.append('  refmodel ' + obj.nvb.refmodel)
        asciiLines.append('  reattachable ' + str(int(obj.nvb.reattachable)))


class Trimesh(Node):
    self.nodetype = 'trimesh'

    def __init__(self, name = 'UNNAMED'):
        Node.__init__(self, name)

        self.meshtype         = nvb_def.Meshtype.TRIMESH
        self.center           = (0.0, 0.0, 0.0) # Unused ?
        self.tilefade         = 0
        self.render           = 1
        self.shadow           = 1
        self.beaming          = 0
        self.inheritcolor     = 0  # Unused ?
        self.alpha            = 1.0
        self.transparencyhint = 0
        self.selfillumcolor   = (0.0, 0.0, 0.0)
        self.ambient          = (0.0, 0.0, 0.0)
        self.diffuse          = (0.0, 0.0, 0.0)
        self.specular         = (0.0, 0.0, 0.0)
        self.shininess        = 0
        self.bitmap           = nvb_def.null
        self.rotatetexture    = 0
        self.verts            = [] # list of vertices
        self.facelist         = FaceList()
        self.tverts           = [] # list of texture vertices


    def createImage(self, imgName, imgPath):
        image = bpy_extras.image_utils.load_image(imgName + '.tga',
                                                  imgPath,
                                                  recursive=nvb_glob.textureSearch,
                                                  place_holder=False,
                                                  ncase_cmp=True)
        if (image is None):
            print('Neverblender - WARNING: Could not load image ' + imgName)
            image = bpy.data.images.new(imgName, 512, 512)
        else:
            image.name = imgName

        return image


    def loadAscii(self, asciiNode):
        Node.loadAscii(self, asciiNode)

        l_int   = int
        l_float = float
        l_isNumber = nvb_utils.isNumber
        for idx, line in enumerate(asciiNode):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue

            if not l_isNumber(label):
                if   (label == 'tilefade'):
                    self.tilefade = l_int(line[1])
                elif (label == 'render'):
                    try:
                        self.render = l_int(line[1])
                    except:
                        pass
                elif (label == 'shadow'):
                    try:
                        self.shadow = l_int(line[1])
                    except:
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
                elif (label == 'selfillumcolor'):
                    self.selfillumcolor = (l_float(line[1]),
                                           l_float(line[2]),
                                           l_float(line[3]) )
                elif (label == 'ambient'):
                    self.ambient = (l_float(line[1]),
                                    l_float(line[2]),
                                    l_float(line[3]) )
                elif (label == 'diffuse'):
                    self.diffuse = (l_float(line[1]),
                                    l_float(line[2]),
                                    l_float(line[3]) )
                elif (label == 'specular'):
                    self.specular = (l_float(line[1]),
                                     l_float(line[2]),
                                     l_float(line[3]) )
                elif (label == 'shininess'):
                    self.shininess = l_int(l_float(line[1]))
                elif (label == 'center'):
                    # Unused ? Because we don't do anything with this
                    try:
                        self.center = ( l_float(line[1]),
                                        l_float(line[2]),
                                        l_float(line[3]) )
                    except:
                        # Probably a 'undefined' string, cannot be converted
                        # We just let it slide and ignore it
                        pass
                elif (label == 'bitmap'):
                    self.bitmap = nvb_utils.getAuroraString(line[1])
                elif (label == 'verts'):
                    numVals = l_int(line[1])
                    nvb_parse.f3(asciiNode[idx+1:idx+numVals+1], self.verts)
                    #self.verts = [(float(l[0]), float(l[1]), float(l[2])) for l in asciiNode[idx+1:idx+numVals+1]]
                elif (label == 'faces'):
                    numVals = l_int(line[1])
                    nvb_parse.faces(asciiNode[idx+1:idx+numVals+1])
                elif (label == 'tverts'):
                    numVals = l_int(line[1])
                    nvb_parse.f2(asciiNode[idx+1:idx+numVals+1], self.tverts)
                    #self.tverts = [(float(l[0]), float(l[1])) for l in asciiNode[idx+1:idx+numVals+1]]


    def createMaterial(self, name):
        material = None
        texName  = self.bitmap.lower()
        if nvb_glob.materialMode == 'SIN':
            # Avoid duplicate materials, search for similar ones.
            material = nvb_utils.matchMaterial(self.diffuse,
                                               self.specular,
                                               texName,
                                               self.alpha)

        if not material:
            material = bpy.data.materials.new(name)
            material.diffuse_color     = self.diffuse
            material.diffuse_intensity = 1.0
            material.specular_color    = self.specular

            textureSlot = material.texture_slots.add()
            # If a texture with the same name was already created treat
            # them as if they were the same, i.e. just use the old one
            if (texName in bpy.data.textures):
                textureSlot.texture = bpy.data.textures[texName]
            else:
                textureSlot.texture = bpy.data.textures.new(texName, type='IMAGE')
            textureSlot.texture_coords        = 'UV'
            textureSlot.use_map_color_diffuse = True

            # Load the image for the texture, but check if it was
            # already loaded before. If so, use that one.
            imgName = self.bitmap
            if (imgName in bpy.data.images):
                image = bpy.data.images[imgName]
                textureSlot.texture.image = image
            else:
                image = self.createImage(imgName, nvb_glob.texturePath)
                if image is not None:
                    textureSlot.texture.image = image

        nvb_utils.setMaterialAuroraAlpha(material, self.alpha)

        return material


    def createMesh(self, name):
        # Create the mesh itself
        mesh = bpy.data.meshes.new(name)
        mesh.vertices.add(len(self.verts))
        mesh.vertices.foreach_set('co', unpack_list(self.verts))
        mesh.tessfaces.add(len(self.facelist.faces))
        mesh.tessfaces.foreach_set('vertices_raw', unpack_face_list(self.facelist.faces))

        # Create material
        if nvb_glob.materialMode != 'NON':
            material = self.createMaterial(name)
            mesh.materials.append(material)

            # Create UV map
            if (len(self.tverts) > 0) and (mesh.tessfaces) and (not nvb_utils.isNull(self.bitmap)):
                uv = mesh.tessface_uv_textures.new(name + '.uv')
                mesh.tessface_uv_textures.active = uv

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
                    # Apply texture to uv face
                    tessfaceUV.image = material.texture_slots[0].texture.image

        # Import smooth groups as sharp edges
        if nvb_glob.importSmoothGroups:
            bm = bmesh.new()
            mesh.update()
            bm.from_mesh(mesh)
            if hasattr(bm.edges, "ensure_lookup_table"):
                bm.edges.ensure_lookup_table()
            # Mark edge as sharp if its faces belong to different smooth groups
            for e in bm.edges:
                f = e.link_faces
                if (len(f) > 1) and (self.facelist.shdgr[f[0].index] != self.facelist.shdgr[f[1].index]):
                    edgeIdx = e.index
                    mesh.edges[edgeIdx].use_edge_sharp = True
            bm.free()
            del bm
            mesh.show_edge_sharp = True

        mesh.update()
        return mesh


    def createObjectData(self, obj):
        Node.createObjectData(self, obj)

        obj.nvb.meshtype         = self.meshtype
        if self.tilefade == 1:
            obj.nvb.tilefade = nvb_def.Tilefade.FADE
        elif self.tilefade == 2:
            obj.nvb.tilefade = nvb_def.Tilefade.BASE
        elif self.tilefade == 4:
            obj.nvb.tilefade = nvb_def.Tilefade.NEIGHBOUR
        else:
            obj.nvb.tilefade = nvb_def.Tilefade.NONE
        obj.nvb.render           = (self.render >= 1)
        obj.nvb.shadow           = (self.shadow >= 1)
        obj.nvb.beaming          = (self.beaming >= 1)
        obj.nvb.inheritcolor     = (self.inheritcolor >= 1)
        obj.nvb.rotatetexture    = (self.rotatetexture >= 1)
        obj.nvb.transparencyhint = self.transparencyhint
        obj.nvb.selfillumcolor   = self.selfillumcolor
        obj.nvb.ambientcolor     = self.ambient
        obj.nvb.shininess        = self.shininess


    def createObject(self, scene):
        if nvb_glob.minimapMode:
            if ((self.tilefade >= 1) and nvb_glob.minimapSkipFade) or not self.render:
                # Fading objects or shadow meshes won't be imported in minimap mode
                # We may need them for the tree stucture, so import it as an empty
                return Dummy.load(self, scene)

        mesh = self.createMesh(self.name)
        obj  = bpy.data.objects.new(self.name, mesh)
        self.createObjectData(obj)
        scene.objects.link(obj)
        return obj

    @staticmethod
    def generateAsciiMaterial(obj, asciiLines):
        # Check if this object has a material assigned to it
        material = obj.active_material
        if material:
            color = material.diffuse_color
            asciiLines.append('  diffuse ' +    str(round(color[0], 2)) + ' ' +
                                                str(round(color[1], 2)) + ' ' +
                                                str(round(color[2], 2))  )
            color = material.specular_color
            asciiLines.append('  specular ' +   str(round(color[0], 2)) + ' ' +
                                                str(round(color[1], 2)) + ' ' +
                                                str(round(color[2], 2))  )

            # Check if this material has a texture assigned
            texture   = material.active_texture
            imgName = nvb_def.null
            if texture:
                # Only image textures will be exported
                if (texture.type == 'IMAGE') and (texture.image):
                    imgName = nvb_utils.getImageFilename(texture.image)
                else:
                    imgName = nvb_def.null
            asciiLines.append('  bitmap ' + imgName)
            asciiLines.append('  alpha ' + str(round(nvb_utils.getAuroraAlpha(obj), 2)))

        else:
            # No material, set some default values
            asciiLines.append('  diffuse 1.0 1.0 1.0')
            asciiLines.append('  specular 0.0 0.0 0.0')
            asciiLines.append('  alpha 1.0')
            asciiLines.append('  bitmap ' + nvb_def.null)


    @staticmethod
    def generateAsciiMesh(obj, asciiLines, simple = False):
        mesh = obj.to_mesh(nvb_glob.scene, nvb_glob.applyModifiers, nvb_glob.meshConvert)
        for p in mesh.polygons:
            p.use_smooth = True

        # Scaling fix
        # TODO: Find out how exactly blender handles scaling, which matrices to use etc
        scale = obj.matrix_world.to_scale()
        scale_matrix = mathutils.Matrix([[scale[0],0,0,0],
                                         [0,scale[1],0,0],
                                         [0,0,scale[2],0],
                                         [0,0,0       ,1]])
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

        # Calculate smooth groups
        smoothGroups    = []
        numSmoothGroups = 0
        if (obj.nvb.smoothgroup == 'SEPR') or (not nvb_glob.exportSmoothGroups):
            # 0 = Do not use smoothgroups
            smoothGroups    = [0] * len(mesh.polygons)
            numSmoothGroups = 1
        elif (obj.nvb.smoothgroup == 'SING'):
            # All faces belong to smooth group 1
            smoothGroups    = [1] * len(mesh.polygons)
            numSmoothGroups = 1
        else:
            (smoothGroups, numSmoothGroups) = mesh.calc_smooth_groups()

        faceList = [] # List of triangle faces
        uvList   = [] # List of uv indices

        # Add vertices
        asciiLines.append('  verts ' + str(len(mesh.vertices)))
        l_round = round
        formatString = '    {: 8.5f} {: 8.5f} {: 8.5f}'
        for v in mesh.vertices:
            s = formatString.format(l_round(v.co[0], 5), l_round(v.co[1], 5), l_round(v.co[2], 5))
            asciiLines.append(s)

        # Add faces and corresponding tverts and shading groups
        tessfaces     = mesh.tessfaces
        tessfaces_uvs = mesh.tessface_uv_textures.active
        for idx in range(len(tessfaces)):
            tface   = tessfaces[idx]
            smGroup = smoothGroups[idx]
            matIdx  = tface.material_index

            # We triangulated, so faces are always triangles
            uv1 = 0
            uv2 = 0
            uv3 = 0
            if tessfaces_uvs:
                uvData = tessfaces_uvs.data[idx]
                uv1 = nvb_utils.addUVToList(uvData.uv1, uvList)
                uv2 = nvb_utils.addUVToList(uvData.uv2, uvList)
                uv3 = nvb_utils.addUVToList(uvData.uv3, uvList)

            faceList.append([tface.vertices[0], tface.vertices[1], tface.vertices[2], smGroup, uv1, uv2, uv3, matIdx])

        if simple:
            asciiLines.append('  faces ' + str(len(faceList)))

            vertDigits        = str(len(str(len(mesh.vertices))))
            smoothGroupDigits = str(len(str(numSmoothGroups)))
            formatString = '    {:' + vertDigits + 'd} {:' + vertDigits + 'd} {:' + vertDigits + 'd}  ' + \
                               '{:' + smoothGroupDigits + 'd}  ' + \
                               '0 0 0  ' + \
                               '{:2d}'
            for f in faceList:
                s = formatString.format(f[0], f[1], f[2], f[3], f[7])
                asciiLines.append(s)
        else:
            asciiLines.append('  faces ' + str(len(faceList)))

            vertDigits        = str(len(str(len(mesh.vertices))))
            smoothGroupDigits = str(len(str(numSmoothGroups)))
            uvDigits          = str(len(str(len(uvList))))
            formatString = '    {:' + vertDigits + 'd} {:' + vertDigits + 'd} {:' + vertDigits + 'd}  ' + \
                               '{:' + smoothGroupDigits + 'd}  ' + \
                               '{:' + uvDigits + 'd} {:' + uvDigits + 'd} {:' + uvDigits + 'd}  ' + \
                               '{:2d}'
            for f in faceList:
                s = formatString.format(f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7])
                asciiLines.append(s)

            if (len(uvList) > 0):
                asciiLines.append('  tverts ' + str(len(uvList)))
                formatString = '    {: 6.3f} {: 6.3f}'
                for uv in uvList:
                    s = formatString.format(round(uv[0], 3), round(uv[1], 3))
                    asciiLines.append(s)

        bpy.data.meshes.remove(mesh)


    @staticmethod
    def generateAsciiData(obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN, simple = False):
        Node.generateAsciiData(obj, asciiLines, exportObjects, classification, simple)

        color = obj.nvb.ambientcolor
        asciiLines.append('  ambient ' +    str(round(color[0], 2)) + ' ' +
                                            str(round(color[1], 2)) + ' ' +
                                            str(round(color[2], 2))  )
        self.generateAsciiMaterial(obj, asciiLines)
        asciiLines.append('  shininess ' + str(obj.nvb.shininess))
        if not simple:
            color = obj.nvb.selfillumcolor
            asciiLines.append('  selfillumcolor ' + str(round(color[0], 2)) + ' ' +
                                                    str(round(color[1], 2)) + ' ' +
                                                    str(round(color[2], 2))  )

            asciiLines.append('  render ' + str(int(obj.nvb.render)))
            asciiLines.append('  shadow ' + str(int(obj.nvb.shadow)))
            asciiLines.append('  beaming ' + str(int(obj.nvb.beaming)))
            asciiLines.append('  inheritcolor ' + str(int(obj.nvb.inheritcolor)))
            asciiLines.append('  transparencyhint ' + str(obj.nvb.transparencyhint))
            # These two are for tiles only
            if classification == nvb_def.classification.TILE:
                asciiLines.append('  rotatetexture ' + str(int(obj.nvb.rotatetexture)))
                asciiLines.append('  tilefade ' + obj.nvb.tilefade)

        self.generateAsciiMesh(obj, asciiLines, simple)


class Animmesh(Trimesh):

    nodetype = 'animmesh'

    def __init__(self, name = 'UNNAMED'):
        Trimesh.__init__(self, name)

        self.meshtype = nvb_def.Meshtype.ANIMMESH


class Danglymesh(Trimesh):
    """

    """
    nodetype = 'danglymesh'

    def __init__(self, name = 'UNNAMED'):
        Trimesh.__init__(self, name)

        self.meshtype     = nvb_def.Meshtype.DANGLYMESH
        self.period       = 1.0
        self.tightness    = 1.0
        self.displacement = 1.0
        self.constraints  = []


    def loadAscii(self, asciiNode):
        Trimesh.loadAscii(self, asciiNode)

        l_int   = int
        l_float = float
        l_isNumber = nvb_utils.isNumber
        for idx, line in enumerate(asciiNode):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue
            if not l_isNumber(label):
                if   (label == 'period'):
                    self.period = l_float(line[1])
                elif (label == 'tightness'):
                    self.tightness = l_float(line[1])
                elif (label == 'displacement'):
                    self.displacement = l_float(line[1])
                elif (label == 'constraints'):
                    numVals = l_int(line[1])
                    nvb_parse.f1(asciiNode[idx+1:idx+numVals+1], self.constraints)
                    #self.constraints = [float(l[0]) for l in asciiNode[idx+1:idx+numVals+1]]


    def createConstraints(self, obj):
        '''
        Creates a vertex group for the object to contain the vertex
        weights for the danglymesh. The weights are called "constraints"
        in NWN. Range is [0.0, 255.0] as opposed to [0.0, 1.0] in Blender
        '''
        vgroup = obj.vertex_groups.new('constraints')
        for vertexIdx, constraint in enumerate(self.constraints):
            weight = constraint/255
            vgroup.add([vertexIdx], weight, 'REPLACE')
        obj.nvb.constraints = vgroup.name


    def createObjectData(self, obj):
        Trimesh.createObjectData(self, obj)

        obj.nvb.period       = self.period
        obj.nvb.tightness    = self.tightness
        obj.nvb.displacement = self.displacement
        self.createConstraints(obj)


    @staticmethod
    def generateAsciiConstraints(obj, asciiLines):
        vgroupName = obj.nvb.constraints
        vgroup     = obj.vertex_groups[vgroupName]

        numVerts = len(obj.data.vertices)
        asciiLines.append('  constraints ' + str(numVerts))
        for i, v in enumerate(obj.data.vertices):
            try:
                asciiLines.append('    ' + str(round(vgroup.weight(i)*255, 3)))
            except:
                # Vertex is not part of this group
                asciiLines.append('    0.0')


    @staticmethod
    def generateAsciiData(obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN, simple = False):
        Trimesh.generateAsciiData(obj, asciiLines, exportObjects, classification)

        asciiLines.append('  period '       + str(round(obj.nvb.period, 3)))
        asciiLines.append('  tightness '    + str(round(obj.nvb.tightness, 3)))
        asciiLines.append('  displacement ' + str(round(obj.nvb.displacement, 3)))
        self.generateAsciiConstraints(obj, asciiLines)


class Skinmesh(Trimesh):
    """
    Skinmeshes are Trimeshes where every vertex
    has a weight.
    """
    nodetype = 'skin'

    def __init__(self, name = 'UNNAMED'):
        Trimesh.__init__(self, name)

        self.meshtype = nvb_def.Meshtype.SKIN
        self.weights = []


    def loadAscii(self, asciiNode):
        Trimesh.loadAscii(self, asciiNode)
        l_int      = int
        l_isNumber = nvb_utils.isNumber
        for idx, line in enumerate(asciiNode):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue

            if not l_isNumber(label):
                if (label == 'weights'):
                    numVals = l_int(line[1])
                    nvb_parse.weights(asciiNode[idx+1:idx+numVals+1], self.weights)
                    break # Only one relevant value here, abort loop when found


    def createSkinGroups(self, obj):
        skinGroupDict = {}
        for vertIdx, vertMemberships in enumerate(self.weights):
            for membership in vertMemberships:
                if membership[0] in skinGroupDict:
                    skinGroupDict[membership[0]].add([vertIdx], membership[1], 'REPLACE')
                else:
                    vgroup = obj.vertex_groups.new(membership[0])
                    skinGroupDict[membership[0]] = vgroup
                    vgroup.add([vertIdx], membership[1], 'REPLACE')


    def createObjectData(self, obj):
        Trimesh.loadData(self, obj)

        self.createSkinGroups(obj)

    @staticmethod
    def generateAsciiWeights(obj, asciiLines, exportObjects):
        # Get a list of skingroups for this object:
        # A vertex group is a skingroup if there is an object in the mdl
        # with the same name as the group
        skingroups = []
        for objName in exportObjects:
            if objName in obj.vertex_groups:
                skingroups.append(obj.vertex_groups[objName])

        vertexWeights = []
        for i, v in enumerate(obj.data.vertices):
            weights = []
            for group in skingroups:
                try:
                    weights.append([group.name, group.weight(i)])
                except:
                    # Vertex not part of this group
                    pass
            vertexWeights.append(weights)

        numVerts = len(obj.data.vertices)
        asciiLines.append('  weights ' + str( numVerts))
        for weights in vertexWeights:
            line = '  '
            if weights:
                for w in weights:
                    line += '  ' + w[0] + ' ' + str(round(w[1], 3))
            else:
                # No weights for this vertex ... this is a problem
                print('Neverblender - WARNING: Missing vertex weight')
                line = 'ERROR: no weight'
            asciiLines.append(line)

    @staticmethod
    def generateAsciiData(obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN, simple = False):
        Trimesh.generateAsciiData(obj, asciiLines, exportObjects, classification)

        self.generateAsciiWeights(obj, asciiLines, exportObjects)


class Emitter(Node):
    nodetype = 'emitter'

    def __init__(self, name = 'UNNAMED'):
        GeometryNode.__init__(self, name)

        self.meshtype = nvb_def.Meshtype.EMITTER
        self.xsize    = 2
        self.ysize    = 2
        self.rawascii = ''


    def loadAscii(self, asciiNode):
        l_float = float
        l_isNumber = nvb_utils.isNumber

        for line in asciiNode:
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue

            if not l_isNumber(label):
                if   (label == 'node'):
                    self.name = nvb_utils.getName(line[2])
                    self.rawascii = self.rawascii + '\n' + ' '.join(line)
                elif (label  == 'endnode'):
                    self.rawascii = self.rawascii + '\n' + ' '.join(line)
                    return
                elif (label == 'parent'):
                    self.parentName = nvb_utils.getName(line[1])
                    self.rawascii = self.rawascii + '\n  #' + ' '.join(line)
                elif (label == 'position'):
                    self.position = (l_float(line[1]),
                                     l_float(line[2]),
                                     l_float(line[3]) )
                    self.rawascii = self.rawascii + '\n  #' + ' '.join(line)
                elif (label == 'orientation'):
                    self.orientation = (l_float(line[1]),
                                        l_float(line[2]),
                                        l_float(line[3]),
                                        l_float(line[4]) )
                    self.rawascii = self.rawascii + '\n  #' + ' '.join(line)
                elif (label == 'scale'):
                    self.scale = l_float(line[1])
                    self.rawascii = self.rawascii + '\n  #' + ' '.join(line)
                elif (label == 'wirecolor'):
                    self.wirecolor = (l_float(line[1]),
                                      l_float(line[2]),
                                      l_float(line[3]) )
                    self.rawascii = self.rawascii + '\n  #' + ' '.join(line)
                else:
                    self.rawascii = self.rawascii + '\n  ' + ' '.join(line)


    def createTextEmitter(self, obj):
        txt = bpy.data.texts.new(obj.name)
        txt.write(self.rawascii)
        obj.nvb.rawascii = txt.name


    def createMesh(self, objName):
        # Create the mesh itself
        mesh = bpy.data.meshes.new(objName)
        mesh.vertices.add(4)
        mesh.vertices[0].co = ( self.xsize/2,  self.ysize/2, 0.0)
        mesh.vertices[1].co = ( self.xsize/2, -self.ysize/2, 0.0)
        mesh.vertices[2].co = (-self.xsize/2, -self.ysize/2, 0.0)
        mesh.vertices[3].co = (-self.xsize/2,  self.ysize/2, 0.0)
        mesh.tessfaces.add(1)
        mesh.tessfaces.foreach_set('vertices_raw', [0, 1, 2, 3])

        # After calling update() tessfaces become inaccessible
        mesh.validate()
        mesh.update()

        return mesh


    def createObjectData(self, obj):
        Node.createObjectData(self, obj)

        obj.nvb.meshtype = self.meshtype
        self.createTextEmitter(obj)


    @staticmethod
    def generateAsciiData(obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN, simple = False):
        Node.addDataToAscii(obj, asciiLines, exportObjects, classification, simple)

        if obj.nvb.rawascii not in bpy.data.texts:
            print('Neverblender - Warning: No emitter data for ' + obj.name)
            return
        txt      = bpy.data.texts[obj.nvb.rawascii]
        txtLines = [l.split() for l in txt.as_string().split('\n')]
        for line in txtLines:
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue
            if  (label == 'node') or (label  == 'endnode') or \
                (label == 'parent') or (label == 'position') or \
                (label == 'orientation') or (label == 'scale') or (label == 'wirecolor'):
                # We don't need any of this as we'll take it directly from
                # the object
                pass
            else:
                # We'll take everything that doesn't start with a #
                if label[0] != '#':
                    asciiLines.append('  ' + ' '.join(line))


class Aabb(Trimesh):
    '''
    No need to import Aaabb's. Aabb nodes in mdl files will be
    treated as trimeshes
    '''
    nodetype = 'aabb'

    def __init__(self, name = 'UNNAMED'):
        Trimesh.__init__(self, name)

        self.meshtype = nvb_def.Meshtype.AABB


    @staticmethod
    def generateAsciiAABB(obj, asciiLines):
        walkmesh = obj.to_mesh(nvb_glob.scene, nvb_glob.applyModifiers, nvb_glob.meshConvert)

        faceList = []
        faceIdx  = 0
        for tessface in walkmesh.tessfaces:
            if (len(tessface.vertices) == 3):
                # Tri
                v0 = tessface.vertices[0]
                v1 = tessface.vertices[1]
                v2 = tessface.vertices[2]

                centroid = mathutils.Vector((walkmesh.vertices[v0].co + walkmesh.vertices[v1].co + walkmesh.vertices[v2].co)/3)
                faceList.append((faceIdx, [walkmesh.vertices[v0].co, walkmesh.vertices[v1].co, walkmesh.vertices[v2].co], centroid))
                faceIdx += 1

            elif (len(tessface.vertices) == 4):
                # Quad
                v0 = tessface.vertices[0]
                v1 = tessface.vertices[1]
                v2 = tessface.vertices[2]
                v3 = tessface.vertices[3]

                centroid = mathutils.Vector((walkmesh.vertices[v0].co + walkmesh.vertices[v1].co + walkmesh.vertices[v2].co)/3)
                faceList.append((faceIdx, [walkmesh.vertices[v0].co, walkmesh.vertices[v1].co, walkmesh.vertices[v2].co], centroid))
                faceIdx += 1

                centroid = mathutils.Vector((walkmesh.vertices[v2].co + walkmesh.vertices[v3].co + walkmesh.vertices[v0].co)/3)
                faceList.append((faceIdx, [walkmesh.vertices[v2].co, walkmesh.vertices[v3].co, walkmesh.vertices[v0].co], centroid))
                faceIdx += 1
            else:
                # Ngon or no polygon at all (This should never be the case with tessfaces)
                print('Neverblender - WARNING: Ngon in walkmesh. Unable to generate aabb.')
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
                              str(node[6]) )
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
                                  str(node[6]) )

    @staticmethod
    def generateAsciiData(obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN, simple = False):
        if obj.parent:
            asciiLines.append('  parent ' + obj.parent.name)
        else:
            asciiLines.append('  parent ' + nvb_def.null)
        loc = obj.location
        asciiLines.append('  position ' + str(round(loc[0], 5)) + ' ' +
                                          str(round(loc[1], 5)) + ' ' +
                                          str(round(loc[2], 5)) )
        rot = nvb_utils.getAuroraRotFromObject(obj)
        asciiLines.append('  orientation ' + str(round(rot[0], 5)) + ' ' +
                                             str(round(rot[1], 5)) + ' ' +
                                             str(round(rot[2], 5)) + ' ' +
                                             str(round(rot[3], 5)) )
        color = obj.nvb.wirecolor
        asciiLines.append('  wirecolor ' + str(round(color[0], 2)) + ' ' +
                                           str(round(color[1], 2)) + ' ' +
                                           str(round(color[2], 2))  )
        asciiLines.append('  ambient 1.0 1.0 1.0')
        asciiLines.append('  diffuse 1.0 1.0 1.0')
        asciiLines.append('  specular 0.0 0.0 0.0')
        asciiLines.append('  shininess 0')
        asciiLines.append('  bitmap NULL')
        Trimesh.generateAsciiData(obj, asciiLines, simple)
        Aabb.generateAsciiAABB(obj, asciiLines)


    def createMesh(self, name):
        # Create the mesh itself
        mesh = bpy.data.meshes.new(name)
        mesh.vertices.add(len(self.verts))
        mesh.vertices.foreach_set('co', unpack_list(self.verts))
        mesh.tessfaces.add(len(self.facelist.faces))
        mesh.tessfaces.foreach_set('vertices_raw', unpack_face_list(self.facelist.faces))

        # Create materials
        for wokMat in nvb_def.wok_materials:
            matName = wokMat[0]
            # Walkmesh materials will be shared across multiple walkmesh
            # objects
            if matName in bpy.data.materials:
                material = bpy.data.materials[matName]
            else:
                material = bpy.data.materials.new(matName)
                material.diffuse_color      = wokMat[1]
                material.diffuse_intensity  = 1.0
                material.specular_color     = (0.0,0.0,0.0)
                material.specular_intensity = wokMat[2]
            mesh.materials.append(material)

        # Apply the walkmesh materials to each face
        for idx, face in enumerate(mesh.tessfaces):
            face.material_index = self.facelist.matId[idx]

        mesh.update()
        return mesh


    def createObject(self, scene):
        if nvb_glob.minimapMode:
            # No walkmeshes in minimap mode and we don't need an empty as
            # replacement either as AABB nodes never have children
            return
        mesh = self.createMesh(self.name)
        obj = bpy.data.objects.new(self.name, mesh)
        self.createObjectData(obj)
        scene.objects.link(obj)
        return obj
