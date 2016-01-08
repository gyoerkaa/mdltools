import bpy
import bpy_extras.image_utils
from bpy_extras.io_utils import unpack_list, unpack_face_list

from . import nvb_glob
from . import nvb_def
from . import nvb_utils


class FaceList():
    def __init__(self):
        self.faces = [] # int 3-tuple, vertex indices
        self.shdgr = [] # int, shading group for this face
        self.uvIdx = [] # int 3-tuple, texture/uv vertex indices
        self.matId = [] # int, material index


class FlareList():
    def __init__(self):
        self.textures    = []
        self.sizes       = []
        self.positions   = []
        self.colorshifts = []


class GeometryNode():
    """
    Basic node from which every other is derived
    """
    def __init__(self, name = 'UNNAMED'):
        self.nodetype = 'undefined'

        self.name        = name
        self.parentName  = nvb_def.null
        self.position    = (0.0, 0.0, 0.0)
        self.orientation = (0.0, 0.0, 0.0, 0.0)
        self.scale       = 1.0
        self.wirecolor   = (0.0, 0.0, 0.0) #Unused ?

        # Name of the corresponding object in blender
        # (used to resolve naming conflicts)
        self.objref   = ''


    def __eq__(self, other):
        if isinstance(other, Base):
            return self.name == other.name


    def __ne__(self, other):
        return not self.__eq__(self, other)


    def __str__(self):
        return 'node ' + self.nodetype + ' ' + self.name


    def parse1f(self, asciiBlock, floatList):
        l_float = float
        for line in asciiBlock:
            floatList.append(l_float(line[0]))


    def parse2f(self, asciiBlock, floatList):
        l_float = float
        for line in asciiBlock:
            floatList.append( (l_float(line[0]), l_float(line[1])) )


    def parse3f(self, asciiBlock, floatList):
        l_float = float
        for line in asciiBlock:
            floatList.append( (l_float(line[0]), l_float(line[1]), l_float(line[2])) )


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
                    self.name = line[2].lower()
                elif (label  == 'endnode'):
                    return
                elif (label == 'parent'):
                    self.parentName = line[1].lower()
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


    def setObjectData(self, obj):
        self.objref = obj.name # used to resolve naming conflicts
        nvb_utils.setRotationAurora(obj, self.orientation)
        obj.scale         = (self.scale, self.scale, self.scale)
        obj.location      = self.position
        obj.nvb.wirecolor = self.wirecolor


    def addToScene(self, scene):
        obj = bpy.data.objects.new(self.name, None)
        self.setObjectData(obj)
        scene.objects.link(obj)
        return obj


    def addDataToAscii(self, obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN):
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
                                           str(round(color[2], 2)) )
        scale = round(nvb_utils.getAuroraScale(obj), 3)
        if (scale != 1.0):
            asciiLines.append('  scale ' + str(scale))



    def generateAscii(self, obj, asciiLines, exportObjects = []):
        asciiLines.append('node ' + self.nodetype + ' ' + obj.name)
        self.addDataToAscii(obj, asciiLines, exportObjects)
        asciiLines.append('endnode')


class Dummy(GeometryNode):
    '''

    '''
    def __init__(self, name = 'UNNAMED'):
        GeometryNode.__init__(self, name)
        self.nodetype  = 'dummy'

        self.dummytype = nvb_def.Dummytype.NONE


    def loadAscii(self, asciiNode):
        GeometryNode.loadAscii(self, asciiNode)


    def setObjectData(self, obj):
        GeometryNode.setObjectData(self, obj)

        obj.nvb.dummytype = self.dummytype

        obj.nvb.dummysubtype = nvb_def.DummySubtype.NONE
        subtypes = nvb_def.DummySubtype.SUFFIX_LIST
        for element in subtypes:
            if self.name.endswith(element[0]):
                obj.nvb.dummysubtype = element[1]
                break


    def addDataToAscii(self, obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN):
        if obj.parent:
            asciiLines.append('  parent ' + obj.parent.name)
        else:
            asciiLines.append('  parent ' + nvb_def.null)
        scale = round(nvb_utils.getAuroraScale(obj), 3)
        if (scale != 1.0):
            asciiLines.append('  scale ' + str(scale))

        dummytype = obj.nvb.dummytype
        if dummytype == nvb_def.Dummytype.MDLROOT:
            # Only parent and scale for rootdummys
            return

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
                                           str(round(color[2], 2)) )

        # TODO: Handle types and subtypes, i.e. Check and modify name
        subtype = obj.nvb.dummysubtype
        if subtype == nvb_def.Dummytype.NONE:
            pass



class Patch(GeometryNode):
    '''
    Same as a plain Dummy.
    '''
    def __init__(self, name = 'UNNAMED'):
        GeometryNode.__init__(self, name)
        self.nodetype = 'patch'

        self.dummytype = nvb_def.Dummytype.PATCH


    def setObjectData(self, obj):
        GeometryNode.setObjectData(self, obj)

        obj.nvb.dummytype = self.dummyType


class Reference(GeometryNode):
    '''
    Contains a reference to another mdl
    '''
    def __init__(self, name = 'UNNAMED'):
        GeometryNode.__init__(self, name)
        self.nodetype = 'reference'

        self.dummytype = nvb_def.Dummytype.REFERENCE
        self.refmodel     = nvb_def.null
        self.reattachable = 0


    def loadAscii(self, asciiNode):
        GeometryNode.loadAscii(self, asciiNode)
        l_isNumber = nvb_utils.isNumber

        for line in asciiNode:
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue
            if not l_isNumber(label):
                if   (label == 'refmodel'):
                    self.refmodel = line[1].lower()
                elif (label == 'reattachable'):
                    self.reattachable = int(line[1])


    def setObjectData(self, obj):
        GeometryNode.setObjectData(self, obj)
        obj.nvb.dummytype    = self.dummyType
        obj.nvb.refmodel     = self.refmodel
        obj.nvb.reattachable = (self.reattachable == 1)


    def addDataToAscii(self, obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN):
        GeometryNode.addDataToAscii(self, obj, asciiLines, exportObjects, classification)
        ascii_node.append('  refmodel ' + obj.nvb.refmodel)
        ascii_node.append('  reattachable ' + str(obj.nvb.reattachable))


class Trimesh(GeometryNode):
    """
    Basic node from which every other is derived
    """
    def __init__(self, name = 'UNNAMED'):
        GeometryNode.__init__(self, name)
        self.nodetype = 'trimesh'

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
                                                  ncase_cmp=False)
        if (image is None):
            image = bpy.data.images.new(imgName, 512, 512)
        else:
            image.name = imgName

        return image


    def loadAscii(self, asciiNode):
        GeometryNode.loadAscii(self, asciiNode)

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
                    self.render = l_int(line[1])
                elif (label == 'shadow'):
                    self.shadow = l_int(line[1])
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
                elif (label == 'selfillumcolor'): # Self illumination color
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
                    # Unused ? Becuase we don't do anything with this
                    self.center = ( l_float(line[1]),
                                    l_float(line[2]),
                                    l_float(line[3]) )
                elif (label == 'bitmap'):
                    self.bitmap = line[1]
                elif (label == 'verts'):
                    numVals = l_int(line[1])
                    self.parse3f(asciiNode[idx+1:idx+numVals+1], self.verts)
                elif (label == 'faces'):
                    numVals = l_int(line[1])
                    self.getAsciiFaceList(asciiNode[idx+1:idx+numVals+1])
                elif (label == 'tverts'):
                    numVals = l_int(line[1])
                    self.parse2f(asciiNode[idx+1:idx+numVals+1], self.tverts)


    def getAsciiFaceList(self, asciiFaces):
        l_int = int
        for line in asciiFaces:
            self.facelist.faces.append( (l_int(line[0]), l_int(line[1]), l_int(line[2])) )
            self.facelist.shdgr.append(l_int(line[3]))
            self.facelist.uvIdx.append( (l_int(line[4]), l_int(line[5]), l_int(line[6])) )
            self.facelist.matId.append(l_int(line[7]))


    def setShadingGroups(self, obj):
        '''
        Converts the shading groups of an object to vertex groups
        '''
        if not nvb_glob.useShadingGroups:
            return

        # Create a dictionary of shading groups with group id's as keys
        # and a vertex lists as values
        shadingGroupDict= {}
        for faceId, groupId in enumerate(self.facelist.shdgr):
            if groupId not in shadingGroupDict:
                shadingGroupDict[groupId] = []
            shadingGroupDict[groupId].append(self.facelist.faces[faceId][0])
            shadingGroupDict[groupId].append(self.facelist.faces[faceId][1])
            shadingGroupDict[groupId].append(self.facelist.faces[faceId][2])

        # Check the number of shading groups on this object. If there is only
        # one we do nothing.
        if len(shadingGroupDict) <= 1:
            return

        # Create vertex groups and add vertices
        for groupId, groupMembers in shadingGroupDict.items():
            vgroup = obj.vertex_groups.new(nvb_def.shadingGroupName + str(groupId))
            vgroup.add(groupMembers, 1.0, 'REPLACE')


    def createMaterial(self, name):
        material = bpy.data.materials.new(name)
        material.diffuse_color     = self.diffuse
        material.diffuse_intensity = 1.0
        material.specular_color    = self.specular

        # Set alpha values. Note: This is always'0.0' and 'True'
        # MDL's alpha value = Texture alpha_factor in Blender
        material.alpha            = 0.0
        material.use_transparency = True

        texName = self.bitmap.lower()
        if (texName != nvb_def.null):
            textureSlot = material.texture_slots.add()
            # If a texture with the same name was already created treat
            # them as if they were the same, i.e. just use the old one
            if (texName in bpy.data.textures):
                textureSlot.texture = bpy.data.textures[texName]
            else:
                textureSlot.texture = bpy.data.textures.new(texName, type='IMAGE')
            textureSlot.texture_coords        = 'UV'
            textureSlot.use_map_color_diffuse = True
            textureSlot.alpha_factor  = self.alpha
            textureSlot.use_map_alpha = True

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

        return material


    def createMesh(self, name):
        # Create the mesh itself
        mesh = bpy.data.meshes.new(name)
        mesh.vertices.add(len(self.verts))
        mesh.vertices.foreach_set('co', unpack_list(self.verts))
        mesh.tessfaces.add(len(self.facelist.faces))
        mesh.tessfaces.foreach_set('vertices_raw', unpack_face_list(self.facelist.faces))

        # Create material
        material = self.createMaterial(name)
        mesh.materials.append(material)

        # Create UV map
        if (len(self.tverts) > 0) and (mesh.tessfaces) and (self.bitmap.lower() != nvb_def.null):
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

        mesh.update()
        return mesh


    def setObjectData(self, obj):
        GeometryNode.setObjectData(self, obj)

        obj.nvb.meshtype         = self.meshtype
        obj.nvb.tilefade         = self.tilefade
        obj.nvb.render           = (self.render == 1)
        obj.nvb.shadow           = (self.shadow == 1)
        obj.nvb.beaming          = (self.beaming == 1)
        obj.nvb.inheritcolor     = (self.inheritcolor == 1)
        obj.nvb.rotatetexture    = (self.rotatetexture == 1)
        obj.nvb.transparencyhint = self.transparencyhint
        obj.nvb.selfillumcolor   = self.selfillumcolor
        obj.nvb.ambientcolor     = self.ambient
        obj.nvb.shininess        = self.shininess
        self.setShadingGroups(obj)


    def addToScene(self, scene):
        if nvb_glob.minimapMode and self.tilefade:
            # Fading objects won't be imported in minimap mode
            # We may need it for the tree stucture, so import it as an empty
            return Dummy.convert(self, scene)
        mesh = self.createMesh(self.name)
        obj  = bpy.data.objects.new(self.name, mesh)
        self.setObjectData(obj)
        scene.objects.link(obj)
        return obj


    def getFaceShadingGroup(self, tface, obj):
        '''
        Takes an object and one of its tessfaces as its parameters

        A face belongs to a shading/vertex group, if all of
        its vertices belong to a shading/vertex group
        If it belongs to more than one group, the first group will be used.
        '''

        groupId = 1
        if not nvb_glob.useShadingGroups:
            return groupId

        #TODO: Fix this mess
        return groupId

        # Vertex groups of the face. We start with all vertex groups of the
        # object and intersect with the
        # There should eb only one group left at the end.
        faceVGroups = set(obj.vertex_groups.keys())

        # Iterate over vertex indices of the face
        if faceVGroups:
            for vIdx in tface.vertices:
                # Get the actual vertex from the mesh object
                vertex = obj.data.vertices[vIdx]
                # Vertex groups of the vertex
                vertexVGroups = set([])
                for vgroup_element in vertex.groups:
                    vgroup = obj.vertex_groups[vgroup_element.group]
                    if nvb_utils.getIsShadingGroup(vgroup):
                        vertexVGroups.add(vgroup.name)
                faceVGroups = faceVGroups & vertexVGroups

            if faceVGroups:
                # Get an element from the set and get its shading group id
                try:
                    groupId = int(objectVGroups.pop().replace(nvb_def.shadingGroupName,''))
                except:
                    print('WARNING: Unable to get shading group.')

        return groupId


    def addMaterialDataToAscii(self, obj, asciiLines):
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
            imageName = nvb_def.null
            if texture:
                # Only image textures will be exported
                if (texture.type == 'IMAGE') and (texture.image):
                    imageName = nvb_utils.getImageFilename(texture.image)
                # Get alpha value from texture alpha
                if (material.use_transparency):
                    textureSlot = material.texture_slots[material.active_texture_index]
                    asciiLines.append('  alpha ' + str(round(textureSlot.alpha_factor, 1)))
                else:
                    asciiLines.append('  alpha 1.0')
            asciiLines.append('  bitmap ' + imageName)
        else:
            # No material, set some default values
            asciiLines.append('  diffuse 1.0 1.0 1.0')
            asciiLines.append('  specular 0.0 0.0 0.0')
            asciiLines.append('  alpha 1.0')
            asciiLines.append('  bitmap ' + nvb_def.null)


    def addUVToList(self, uv, uvList):
        '''
        Helper function to keep UVs unique
        '''
        if uv in uvList:
            return uvList.index(uv)
        else:
            uvList.append(uv)
            return (len(uvList)-1)


    def addMeshDataToAscii(self, obj, asciiLines, textured = True):
        mesh = obj.to_mesh(nvb_glob.scene, True, 'RENDER')

        faceList = [] # List of triangle faces
        uvList   = [] # List of uv indices

        # Add vertices
        asciiLines.append('  verts ' + str(len(mesh.vertices)))
        l_round = round
        for v in mesh.vertices:
            asciiLines.append('    ' +  str(l_round(v.co[0], 5)) + ' ' +
                                        str(l_round(v.co[1], 5)) + ' ' +
                                        str(l_round(v.co[2], 5)) ) #.rjust(10)

        # Add faces and corresponding tverts and shading groups
        tessfaces     = mesh.tessfaces
        tessfaces_uvs = mesh.tessface_uv_textures.active
        for idx in range(len(tessfaces)):
            tface        = tessfaces[idx]
            shadingGroup = self.getFaceShadingGroup(tface, obj)
            matIdx       = tface.material_index

            if (len(tface.vertices) == 3):
                #Triangle
                uv1 = 0
                uv2 = 0
                uv3 = 0
                if tessfaces_uvs:
                    uvData = tessfaces_uvs.data[idx]
                    uv1 = self.addUVToList(uvData.uv1, uvList)
                    uv2 = self.addUVToList(uvData.uv2, uvList)
                    uv3 = self.addUVToList(uvData.uv3, uvList)

                faceList.append([tface.vertices[0], tface.vertices[1], tface.vertices[2], shadingGroup, uv1, uv2, uv3, matIdx])

            elif (len(face.vertices) == 4):
                #Quad
                uv1 = 0
                uv2 = 0
                uv3 = 0
                uv4 = 0
                if tessfaces_uvs:
                    uvData = tessfaces_uvs.data[idx]
                    uv1 = self.addUVToList(uvData.uv1, uvList)
                    uv2 = self.addUVToList(uvData.uv2, uvList)
                    uv3 = self.addUVToList(uvData.uv3, uvList)
                    uv4 = self.addUVToList(uvData.uv4, uvList)

                faceList.append([face.vertices[0], face.vertices[1], face.vertices[2], shadingGroup, uv1, uv2, uv3, matIdx])
                faceList.append([face.vertices[2], face.vertices[3], face.vertices[0], shadingGroup, uv3, uv4, uv1, matIdx])
            else:
                # Ngon or no polygon at all (This should never be the case with tessfaces)
                print('WARNING: Ngon in ' + mesh_object.name + '. Unable to export.')
                return

        if (textured):
            asciiLines.append('  faces ' + str(len(faceList)))
            for f in faceList:
                asciiLines.append('    ' +  str(f[0]) + ' '  + # Vertex index
                                            str(f[1]) + ' '  + # Vertex index
                                            str(f[2]) + '  ' + # Vertex index
                                            str(f[3]) + '  ' + # Shading group
                                            str(f[4]) + ' '  + # Texture vertex index
                                            str(f[5]) + ' '  + # Texture vertex index
                                            str(f[6]) + '  ' + # Texture vertex index
                                            str(f[7]) )        # Misc

            asciiLines.append('  tverts ' + str(len(uvList)))
            for uv in uvList:
                asciiLines.append('    ' +  str(round(uv[0], 3)) + ' ' +
                                            str(round(uv[1], 3)) + ' ' +
                                            '0' )

        else:
            asciiLines.append('  faces ' + str(len(faceList)))
            for f in faceList:
                asciiLines.append('    ' +  str(f[0]) + ' '  + # Vertex index
                                            str(f[1]) + ' '  + # Vertex index
                                            str(f[2]) + '  ' + # Vertex index
                                            str(f[3]) + '  ' + # Shading group
                                            str(0)    + ' '  + # Texture vertex index
                                            str(0)    + ' '  + # Texture vertex index
                                            str(0)    + '  ' + # Texture vertex index
                                            str(f[7]) )        # Misc

        bpy.data.meshes.remove(mesh)


    def addDataToAscii(self, obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN):
        GeometryNode.addDataToAscii(self, obj, asciiLines, exportObjects, classification)

        color = obj.nvb.ambientcolor
        asciiLines.append('  ambient ' +    str(round(color[0], 2)) + ' ' +
                                            str(round(color[1], 2)) + ' ' +
                                            str(round(color[2], 2))  )
        self.addMaterialDataToAscii(obj, asciiLines)
        asciiLines.append('  shininess ' + str(obj.nvb.shininess))

        color = obj.nvb.selfillumcolor
        asciiLines.append('  selfillumcolor ' + str(round(color[0], 2)) + ' ' +
                                                str(round(color[1], 2)) + ' ' +
                                                str(round(color[2], 2))  )

        asciiLines.append('  render ' + str(obj.nvb.render))
        asciiLines.append('  shadow ' + str(obj.nvb.shadow))
        asciiLines.append('  beaming ' + str(obj.nvb.beaming))
        asciiLines.append('  inheritcolor ' + str(obj.nvb.inheritcolor))
        asciiLines.append('  transparencyhint ' + str(obj.nvb.transparencyhint))
        # These two are for tiles only
        if classification == 'TILE':
            asciiLines.append('  rotatetexture ' + str(obj.nvb.rotatetexture))
            asciiLines.append('  tilefade ' + str(obj.nvb.tilefade))

        self.addMeshDataToAscii(obj, asciiLines, True)


class Danglymesh(Trimesh):
    """

    """
    def __init__(self, name = 'UNNAMED'):
        Trimesh.__init__(self, name)
        self.nodetype = 'danglymesh'

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
                    self.parse1f(asciiNode[idx+1:idx+numVals+1], self.constraints)


    def addConstraintsToObject(self, obj):
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


    def setObjectData(self, obj):
        Trimesh.setObjectData(self, obj)

        obj.nvb.period       = self.period
        obj.nvb.tightness    = self.tightness
        obj.nvb.displacement = self.displacement
        self.addConstraintsToObject(obj)


    def addConstraintsToAscii(self, obj, asciiLines):
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


    def addDataToAscii(self, obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN):
        Trimesh.addDataToAscii(self, obj, asciiLines, exportObjects, classification)

        asciiLines.append('  period '       + str(round(obj.nvb.period, 3)))
        asciiLines.append('  tightness '    + str(round(obj.nvb.tightness, 3)))
        asciiLines.append('  displacement ' + str(round(obj.nvb.displacement, 3)))
        self.addConstraintsToAscii(obj, asciiLines)


class Skinmesh(Trimesh):
    """
    Skinmeshes are Trimeshes where every vertex
    has a weight.
    """
    def __init__(self, name = 'UNNAMED'):
        Trimesh.__init__(self, name)
        self.nodetype = 'skin'

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
                    self.getWeightsFromAscii(asciiNode[idx+1:idx+numVals+1])
                    break # Only one value here, abort loop when read


    def getWeightsFromAscii(self, asciiBlock):
        lfloat = float
        lchunker = nvb_utils.chunker
        for line in asciiBlock:
            # A line looks like this
            # [group_name, vertex_weight, group_name, vertex_weight]
            # We create a list looking like this:
            # [[group_name, vertex_weight], [group_name, vertex_weight]]
            memberships = []
            for chunk in lchunker(line, 2):
                memberships.append( [chunk[0], lfloat(chunk[1])] )

            self.weights.append(memberships)


    def addSkinGroupsToObject(self, obj):
        skinGroupDict = {}
        for vertIdx, vertMemberships in enumerate(self.weights):
            for membership in vertMemberships:
                if membership[0] in skinGroupDict:
                    skinGroupDict[membership[0]].add([vertIdx], membership[1], 'REPLACE')
                else:
                    vgroup = obj.vertex_groups.new(membership[0])
                    skinGroupDict[membership[0]] = vgroup
                    vgroup.add([vertIdx], membership[1], 'REPLACE')


    def setObjectData(self, obj):
        Trimesh.setObjectData(self, obj)

        self.addSkinGroupsToObject(obj)


    def addWeightsToAscii(self, obj, asciiLines, exportObjects):
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
                print('WARNING: Missing vertex weight')
                line = 'ERROR: no weight'
            asciiLines.append(line)


    def addDataToAscii(self, obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN):
        Trimesh.addDataToAscii(self, obj, asciiLines, exportObjects, classification)

        self.addWeightsToAscii(obj, asciiLines, exportObjects)


class Emitter(GeometryNode):
    def __init__(self, name = 'UNNAMED'):
        GeometryNode.__init__(self, name)
        self.nodetype = 'emitter'

        self.meshtype = nvb_def.Meshtype.EMITTER
        self.xsize    = 2
        self.ysize    = 2
        self.rawascii = ''


    def loadAscii(self, asciiNode):
        GeometryNode.loadAscii(self, asciiNode)

        l_int   = int
        l_float = float
        for line in asciiNode:
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue
            self.rawascii = self.rawascii + '\n' + ' '.join(line)
            if (label == 'xsize'):
                self.xsize = l_float(line[1])/100
            elif (label == 'ysize'):
                self.ysize = l_float(line[1])/100


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


    def addRawAscii(self, obj):
        txt = bpy.data.texts.new(obj.name)
        txt.write(self.rawascii)
        obj.nvb.rawascii = txt.name


    def setObjectData(self, obj):
        GeometryNode.setObjectData(self, obj)

        obj.nvb.meshtype = self.meshtype
        self.addRawAscii(obj)


    def addToScene(self, scene):
        if nvb_glob.minimapMode:
            # We don't need emitters in minimap mode
            # We may need it for the tree stucture, so import it as an empty
            return GeometryNode.convert(self, scene)

        mesh = self.createMesh(self.name)
        obj  = bpy.data.objects.new(self.name, mesh)

        self.setObjectData(obj)
        scene.objects.link(obj)
        return obj


    def addDataToAscii(self, obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN):
        GeometryNode.addDataToAscii(self, obj, asciiLines, exportObjects, classification)


class Light(GeometryNode):
    def __init__(self, name = 'UNNAMED'):
        GeometryNode.__init__(self, name)
        self.nodetype = 'light'

        self.shadow        = 1
        self.radius        = 5.0
        self.multiplier    = 1
        self.lightpriority = 5
        self.color         = (0.0, 0.0, 0.0)
        self.ambientonly   = 1
        self.ndynamictype  = 1
        self.isdynamic     = 1
        self.affectdynamic = 1
        self.negativelight = 0
        self.fadinglight   = 1
        self.lensflares    = 0
        self.flareradius   = 1.0
        self.flareList     = FlareList()


    def loadAscii(self, asciiNode):
        GeometryNode.loadAscii(self, asciiNode)

        flareTextureNamesStart = 0
        numFlares              = 0

        l_int = int
        l_float = float
        l_isNumber = nvb_utils.isNumber
        for idx, line in enumerate(asciiNode):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue

            if not l_isNumber(label):
                if (label == 'radius'):
                    self.radius = l_float(line[1])
                elif (label == 'shadow'):
                    self.shadow = l_int(line[1])
                elif (label == 'multiplier'):
                    self.multiplier = l_float(line[1])
                elif (label == 'color'):
                    self.color = ( l_float(line[1]),
                                   l_float(line[2]),
                                   l_float(line[3]) )
                elif (label== 'ambientonly'):
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
                    # List of name follows, but we don't necessarily know how
                    # many flares there are
                    # We 'll need to read them later. For now save the index
                    flareTextureNamesStart = idx+1
                elif (label == 'flaresizes'):
                    # List of floats
                    numFlares = next((i for i, v in enumerate(asciiNode[idx+1:]) if not l_isNumber(v[0])), -1)
                    print(numFlares)
                    self.parse1f(asciiNode[idx+1:idx+numFlares+1], self.flareList.sizes)
                elif (label == 'flarepositions'):
                    # List of floats
                    numFlares = next((i for i, v in enumerate(asciiNode[idx+1:]) if not l_isNumber(v[0])), -1)
                    print(numFlares)
                    self.parse1f(asciiNode[idx+1:idx+numFlares+1], self.flareList.positions)
                elif (label == 'flarecolorshifts'):
                    # List of float 3-tuples
                    numFlares = next((i for i, v in enumerate(asciiNode[idx+1:]) if not l_isNumber(v[0])), -1)
                    print(numFlares)
                    self.parse3f(asciiNode[idx+1:idx+numFlares+1], self.flareList.colorshifts)

        # Load flare texture names:
        for i in range(numFlares):
            texName = asciiNode[flareTextureNamesStart+i][0]
            print(texName)
            self.flareList.textures.append(texName)


    def createLamp(self, name):
        lamp = bpy.data.lamps.new(name, 'POINT')

        # TODO: Check for negative color values and do something (works fine in blender though)
        lamp.color       = self.color
        lamp.energy      = self.multiplier
        lamp.distance    = self.radius
        #lamp.use_sphere  = True

        return lamp


    def setObjectData(self, obj):
        GeometryNode.setObjectData(self, obj)

        switch = {'ml1': 'MAINLIGHT1', \
                  'ml2': 'MAINLIGHT2', \
                  'sl1': 'SOURCELIGHT1', \
                  'sl2': 'SOURCELIGHT2'}
        obj.nvb.ambientonly   = self.ambientonly
        obj.nvb.lighttype     = switch.get(self.name[-3:], 'NONE')
        obj.nvb.shadow        = (self.shadow == 1)
        obj.nvb.lightpriority = self.lightpriority
        obj.nvb.fadinglight   = (self.fadinglight == 1)
        obj.nvb.isdynamic     = (self.ndynamictype == 1) or (self.isdynamic == 1)
        obj.nvb.affectdynamic = (self.affectdynamic == 1)

        if (self.flareradius > 0) or (self.lensflares == 1):
            obj.nvb.lensflares = True
            numFlares = len(self.flareList.textures)
            for i in range(numFlares):
                print(i)
                newItem = obj.nvb.flareList.add()
                newItem.texture    = self.flareList.textures[i]
                newItem.colorshift = self.flareList.colorshifts[i]
                newItem.size       = self.flareList.sizes[i]
                newItem.position   = self.flareList.positions[i]

        obj.nvb.flareradius = self.flareradius


    def addToScene(self, scene):
        if nvb_glob.minimapMode:
            # We don't need lights in minimap mode
            # We may need it for the tree stucture, so import it as an empty
            return GeometryNode.convert(self, scene)
        lamp = self.createLamp(self.name)
        obj  = bpy.data.objects.new(self.name, lamp)
        self.setObjectData(obj)
        scene.objects.link(obj)
        return obj


    def addDataToAscii(self, obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN):
        GeometryNode.addDataToAscii(self, obj, asciiLines, exportObjects, classification)

        lamp = obj.data
        asciiLines.append('  radius ' + str(round(lamp.distance, 1)))
        asciiLines.append('  multiplier ' + str(round(lamp.energy, 1)))
        asciiLines.append('  color ' +  str(round(lamp.color[0], 2)) + ' ' +
                                        str(round(lamp.color[1], 2)) + ' ' +
                                        str(round(lamp.color[2], 2)) )

        asciiLines.append('  ambientonly ' + str(int(obj.nvb.ambientonly)))
        asciiLines.append('  nDynamicType ' + str(int(obj.nvb.isdynamic)))
        asciiLines.append('  affectDynamic ' + str(int(obj.nvb.affectdynamic)))
        asciiLines.append('  shadow ' + str(int(obj.nvb.shadow)))
        asciiLines.append('  lightpriority ' + str(obj.nvb.lightpriority))
        asciiLines.append('  fadingLight ' + str(int(obj.nvb.fadinglight)))
        if obj.nvb.lensflares:
            asciiLines.append('  lensflares ' + str(int(obj.nvb.lensflares)))
        asciiLines.append('  flareradius ' + str(round(obj.nvb.flareradius, 1)))


class Aabb(Trimesh):
    '''
    No need to import Aaabb's. Aabb nodes in mdl files will be
    treated as trimeshes
    '''
    def __init__(self, name = 'UNNAMED'):
        Trimesh.__init__(self, name)
        self.nodetype = 'aabb'

        self.meshtype = nvb_def.Meshtype.AABB

    def addAABBToAscii(obj, asciiLines):

        walkmesh = obj.to_mesh(nvb_glob.scene, nvb_glob.applyModifiers, 'PREVIEW')
        pass
        '''
        # Grab all vertices
        vert_list = []
        for vertex in walkmesh.vertices:
            vert_list.append((vertex.co[0], vertex.co[1], vertex.co[2]))

        face_list     = []
        face_idx      = 0
        for tessface in walkmesh.tessfaces:
            if (len(tessface.vertices) == 3):
                v0_idx = tessface.vertices[0]
                v1_idx = tessface.vertices[1]
                v2_idx = tessface.vertices[2]

                face_centroid = mathutils.Vector((walkmesh.vertices[v0_idx].co + walkmesh.vertices[v1_idx].co + walkmesh.vertices[v2_idx].co)/3)
                face_list.append((face_idx, [walkmesh.vertices[v0_idx].co, walkmesh.vertices[v1_idx].co, walkmesh.vertices[v2_idx].co], face_centroid))
                face_idx += 1

            elif (len(tessface.vertices) == 4):
                #Quad
                if (glob_triangulate):
                    v0_idx = tessface.vertices[0]
                    v1_idx = tessface.vertices[1]
                    v2_idx = tessface.vertices[2]
                    v3_idx = tessface.vertices[3]

                    face_centroid = mathutils.Vector((walkmesh.vertices[v0_idx].co + walkmesh.vertices[v1_idx].co + walkmesh.vertices[v2_idx].co)/3)
                    face_list.append((face_idx, [walkmesh.vertices[v0_idx].co, walkmesh.vertices[v1_idx].co, walkmesh.vertices[v2_idx].co], face_centroid))
                    face_idx += 1

                    face_centroid = mathutils.Vector((walkmesh.vertices[v2_idx].co + walkmesh.vertices[v3_idx].co + walkmesh.vertices[v0_idx].co)/3)
                    face_list.append((face_idx, [walkmesh.vertices[v2_idx].co, walkmesh.vertices[v3_idx].co, walkmesh.vertices[v0_idx].co], face_centroid))
                    face_idx += 1
                else:
                    # This is a Quad and we are not allowed to triangulate: We are unable export this
                    print('WARNING: Quad in walkmesh. Unable to generate aabb, triangulation required (manual or activate export option)')
                    return []
            else:
                # Ngon or no polygon at all (This should never be the case with tessfaces)
                print('WARNING: Ngon in walkmesh. Unable to generate aabb.')
                return []

        aabb_tree = []
        generate_aabbtree(aabb_tree, face_list)

        ascii_tree = []
        if aabb_tree:
            tree_node = aabb_tree.pop(0)
            ascii_tree.append('  aabb  ' +
                              ' ' +
                              str(round(tree_node[0], glob_aabb_digits)) +
                              ' ' +
                              str(round(tree_node[1], glob_aabb_digits)) +
                              ' ' +
                              str(round(tree_node[2], glob_aabb_digits)) +
                              ' ' +
                              str(round(tree_node[3], glob_aabb_digits)) +
                              ' ' +
                              str(round(tree_node[4], glob_aabb_digits)) +
                              ' ' +
                              str(round(tree_node[5], glob_aabb_digits)) +
                              ' ' +
                              str(tree_node[6]) )
            for tree_node in aabb_tree:
                ascii_tree.append('    ' +
                                  str(round(tree_node[0], glob_aabb_digits)) +
                                  ' ' +
                                  str(round(tree_node[1], glob_aabb_digits)) +
                                  ' ' +
                                  str(round(tree_node[2], glob_aabb_digits)) +
                                  ' ' +
                                  str(round(tree_node[3], glob_aabb_digits)) +
                                  ' ' +
                                  str(round(tree_node[4], glob_aabb_digits)) +
                                  ' ' +
                                  str(round(tree_node[5], glob_aabb_digits)) +
                                  ' ' +
                                  str(tree_node[6]) )

        return ascii_tree
        '''

    def addDataToAscii(self, obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN):
        if obj.parent:
            asciiLines.append('  parent ' + obj.parent.name)
        else:
            asciiLines.append('  parent ' + nvb_def.null)
        loc = obj.location
        asciiLines.append('  position ' + str(round(loc[0], 5)) + ' ' +
                                          str(round(loc[1], 5)) + ' ' +
                                          str(round(loc[2], 5)) )
        rot = nvb_utils.getRotationAurora(obj)
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
        Trimesh.addMeshDataToAscii(self, obj, asciiLines, False)
        self.addAABBToAscii(obj, asciiLines)


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


    def addToScene(self, scene):
        if nvb_glob.minimapMode:
            # No walkmeshes in minimap mode and we don't need an empty as
            # replacement either as AABB nodes never have children
            return
        mesh = self.createMesh(self.name)
        obj = bpy.data.objects.new(self.name, mesh)
        self.setObjectData(obj)
        scene.objects.link(obj)
        return obj
