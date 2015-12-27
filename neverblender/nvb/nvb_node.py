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


class GeometryNode():
    """
    Basic node from which every other is derived
    """
    def __init__(self, name = 'UNNAMED'):
        self.nodetype = 'UNDEFINED'

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
        return 'node ' + self.nodetype + ' ' +self.name


    def getFromAscii(self, asciiNode):
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


    def addToAscii(self, bObject, asciiLines, exportObjects = [], numPad = 0):
        pad = ''
        asciiLines.append(pad + 'node ' + self.nodetype + ' ' + self.name)
        asciiLines.append(pad + 'endnode')


class Dummy(GeometryNode):
    '''

    '''
    def __init__(self, name = 'UNNAMED'):
        GeometryNode.__init__(self, name)
        self.nodetype  = 'DUMMY'

        self.dummytype = 'NONE'


    def getFromAscii(self, asciiNode):
        GeometryNode.getFromAscii(self, asciiNode)


    def setObjectData(self, obj):
        GeometryNode.setObjectData(self, obj)

        obj.nvb.dummytype = self.dummytype
        subtypes = [ ('use01',     'USE1'), \
                     ('use02',     'USE2'), \
                     ('hand',      'HAND'), \
                     ('head',      'HEAD'), \
                     ('head_hit',  'HHIT'), \
                     ('hhit',      'HHIT'), \
                     ('impact',    'IMPC'), \
                     ('impc',      'IMPC'), \
                     ('ground',    'GRND'), \
                     ('grnd',      'GRND'), \
                     ('open1_01',  'O101'), \
                     ('open1_02',  'O102'), \
                     ('open2_01',  'O201'), \
                     ('open2_02',  'O202'), \
                     ('closed_01', 'CL01'), \
                     ('closed_02', 'CL02') ]
        obj.nvb.dummysubtype = 'NONE'
        for element in subtypes:
            if self.name.endswith(element[0]):
                obj.nvb.dummytype = 'SPECIAL'
                obj.nvb.dummysubtype = element[1]
                break


class Patch(GeometryNode):
    '''
    Same as a plain Dummy.
    '''
    def __init__(self, name = 'UNNAMED'):
        GeometryNode.__init__(self, name)
        self.nodetype = 'PATCH'

        self.dummytype = 'PATCH'


    def setObjectData(self, obj):
        GeometryNode.setObjectData(self, obj)

        obj.nvb.dummytype = self.dummyType


class Reference(GeometryNode):
    '''
    Contains a reference to another mdl
    '''
    def __init__(self, name = 'UNNAMED'):
        GeometryNode.__init__(self, name)
        self.nodetype = 'REFERENCE'

        self.refmodel     = nvb_def.null
        self.reattachable = 0


    def getFromAscii(self, asciiNode):
        GeometryNode.getFromAscii(self, asciiNode)
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
        obj.nvb.dummytype = 'REFERENCE'
        obj.nvb.refmodel     = self.refmodel
        obj.nvb.reattachable = (self.reattachable == 1)


class Trimesh(GeometryNode):
    """
    Basic node from which every other is derived
    """
    def __init__(self, name = 'UNNAMED'):
        GeometryNode.__init__(self, name)
        self.nodetype = 'TRIMESH'

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

        self.meshtype = 'TRIMESH'


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


    def getFromAscii(self, asciiNode):
        GeometryNode.getFromAscii(self, asciiNode)

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
                    pass # TODO
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
                    pass # TODO # Unused ?
                elif (label == 'bitmap'):
                    self.bitmap = line[1]
                elif (label == 'verts'):
                    numVals = l_int(line[1])
                    self.getAsciiVerts(asciiNode[idx+1:idx+numVals+1])
                elif (label == 'faces'):
                    numVals = l_int(line[1])
                    self.getAsciiFaces(asciiNode[idx+1:idx+numVals+1])
                elif (label == 'tverts'):
                    numVals = l_int(line[1])
                    self.getAsciiTexVerts(asciiNode[idx+1:idx+numVals+1])

    def getAsciiVerts(self, asciiVerts):
        l_float = float
        for line in asciiVerts:
            self.verts.append( (l_float(line[0]), l_float(line[1]), l_float(line[2])) )

    def getAsciiFaces(self, asciiFaces):
        l_int = int
        for line in asciiFaces:
            self.facelist.faces.append( (l_int(line[0]), l_int(line[1]), l_int(line[2])) )
            self.facelist.shdgr.append(l_int(line[3]))
            self.facelist.uvIdx.append( (l_int(line[4]), l_int(line[5]), l_int(line[6])) )
            self.facelist.matId.append(l_int(line[7]))

    def getAsciiTexVerts(self, asciiTexVerts):
        l_float = float
        for line in asciiTexVerts:
            self.tverts.append( (l_float(line[0]), l_float(line[1])) )

    def setShadingGroups(self, obj):
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

        # Create vertex groups ans add vertices
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


class Danglymesh(Trimesh):
    """

    """
    def __init__(self, name = 'UNNAMED'):
        Trimesh.__init__(self, name)
        self.nodetype = 'DANGLYMESH'

        self.meshtype     = 'DANGLYMESH'
        self.period       = 1.0
        self.tightness    = 1.0
        self.displacement = 1.0
        self.constraints  = []


    def getFromAscii(self, asciiNode):
        Trimesh.getFromAscii(self, asciiNode)

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
                    self.tilefade = l_float(line[1])
                elif (label == 'tightness'):
                    self.tilefade = l_float(line[1])
                elif (label == 'displacement'):
                    self.tilefade = l_float(line[1])
                elif (label == 'constraints'):
                    numVals = l_int(line[1])
                    self.getAsciiConstraints(asciiNode[idx+1:idx+numVals+1])


    def getAsciiConstraints(self, asciiConstraints):
        l_float = float
        for line in asciiConstraints:
            self.constraints.append(l_float(line[0]))


    def setConstraintGroup(self, obj):
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
        self.setConstraintGroup(obj)


class Skinmesh(Trimesh):
    """
    Skinmeshes are Trimeshes where every vertex
    has a weight.
    """
    def __init__(self, name = 'UNNAMED'):
        Trimesh.__init__(self, name)
        self.nodetype = 'SKIN'

        self.meshtype = 'SKIN'
        self.weights = []


    def getFromAscii(self, asciiNode):
        Trimesh.getFromAscii(self, asciiNode)
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
                    self.getAsciiWeights(asciiNode[idx+1:idx+numVals+1])
                    break # Only one value here, abort loop when read


    def getAsciiWeights(self, asciiWeights):
        lfloat = float
        lchunker = nvb_utils.chunker
        for line in asciiWeights:
            # A line looks like this
            # [group_name, vertex_weight, group_name, vertex_weight]
            # We create a list looking like this:
            # [[group_name, vertex_weight], [group_name, vertex_weight]]
            memberships = []
            for chunk in lchunker(line, 2):
                memberships.append( [chunk[0], lfloat(chunk[1])] )

            self.weights.append(memberships)


    def setSkinGroups(self, obj):
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

        self.setSkinGroups(obj)


class Emitter(GeometryNode):
    def __init__(self, name = 'UNNAMED'):
        GeometryNode.__init__(self, name)
        self.nodetype = 'EMITTER'

        self.meshtype = 'EMITTER'
        self.xsize    = 2
        self.ysize    = 2
        self.rawascii = ''


    def getFromAscii(self, asciiNode):
        GeometryNode.getFromAscii(self, asciiNode)

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


class Light(GeometryNode):
    def __init__(self, name = 'UNNAMED'):
        GeometryNode.__init__(self, name)
        self.nodetype = 'LIGHT'

        self.shadow           = 1
        self.radius           = 5.0
        self.multiplier       = 1
        self.color            = (0.0, 0.0, 0.0)
        self.ambientonly      = 1
        self.ndynamictype     = 1
        self.isdynamic        = 1
        self.affectdynamic    = 1
        self.lightpriority    = 5
        self.fadinglight      = 1
        self.lensflares       = 0
        self.flareradius      = 1.0


    def getFromAscii(self, asciiNode):
        GeometryNode.getFromAscii(self, asciiNode)

        l_int = int
        l_float = float
        l_isNumber = nvb_utils.isNumber
        for line in asciiNode:
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
                elif (label == 'lensflares'):
                    self.lensflares = l_int(line[1])
                elif (label == 'flareradius'):
                    self.flareradius = l_float(line[1])
                elif (label == 'affectdynamic'):
                    self.affectdynamic = l_int(line[1])
                elif (label == 'lightpriority'):
                    self.lightpriority = l_int(line[1])
                elif (label == 'fadinglight'):
                    self.fadinglight = l_int(line[1])

    def createLamp(self, name):
        lamp = bpy.data.lamps.new(name, 'POINT')

        lamp.use_diffuse = self.ambientonly
        lamp.color       = self.color
        lamp.energy      = self.multiplier
        lamp.distance    = self.radius
        #obj.use_negative = self.negative # No effect ?
        #obj.use_sphere   = True # No effect ?

        return lamp


    def setObjectData(self, obj):
        GeometryNode.setObjectData(self, obj)

        switch = {'ml1': 'MAINLIGHT1', \
                  'ml2': 'MAINLIGHT2', \
                  'sl1': 'SOURCELIGHT1', \
                  'sl2': 'SOURCELIGHT2'}
        obj.nvb.lighttype     = switch.get(self.name[-3:], 'NONE')
        obj.nvb.shadow        = (self.shadow == 1)
        obj.nvb.lightpriority = self.lightpriority
        obj.nvb.fadinglight   = (self.fadinglight == 1)
        obj.nvb.isdynamic     = (self.ndynamictype == 1) or (self.isdynamic == 1)
        obj.nvb.affectdynamic = (self.affectdynamic == 1)
        obj.nvb.flareradius   = (self.affectdynamic == 1)


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


class Aabb(Trimesh):
    '''
    No need to import Aaabb's. Aabb nodes in mdl files will be
    treated as trimeshes
    '''
    def __init__(self, name = 'UNNAMED'):
        Trimesh.__init__(self, name)
        nodetype = 'AABB'

        meshtype = 'AABB'


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
        obj  = bpy.data.objects.new(self.name, mesh)
        self.setObjectData(obj)
        scene.objects.link(obj)
        return obj

