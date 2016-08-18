import bpy

from . import nvb_def

class Node():
    """
    Basic node from which every other is derived
    """
    def __init__(self, name = 'unnamed'):
        self.nodetype = 'undefined'

        self.name        = name
        self.parent      = nvb_def.null
        self.position    = (0.0, 0.0, 0.0)
        self.orientation = (0.0, 0.0, 0.0, 0.0)
        self.scale       = 1.0
        self.wirecolor   = (0.0, 0.0, 0.0)

        # Name of the corresponding object in blender
        # (used to resolve naming conflicts)
        self.objref = ''
        self.objidx = -1


    def __eq__(self, other):
        if isinstance(other, Base):
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
                if   (label == 'node'):
                    self.name = nvb_utils.getName(line[2])
                elif (label  == 'endnode'):
                    return
                elif (label == 'parent'):
                    self.parentName = nvb_utils.getName(line[1])
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

        self.objref = obj.name
        self.createObjectData(obj)
        return obj


    @staticmethod
    def createAsciiData(obj, asciiLines):
        if obj.parent:
            asciiLines.append('  parent ' + obj.parent.name)
        else:
            asciiLines.append('  parent ' + nvb_def.null)
        # Scaling fix
        transmat = self.getAdjustedMatrix(obj)
        loc = transmat.to_translation()
        s = '  position {: 8.5f} {: 8.5f} {: 8.5f}'.format(round(loc[0], 5), round(loc[1], 5), round(loc[2], 5))
        asciiLines.append(s)

        rot = nvb_utils.euler2nwangle(transmat.to_euler('XYZ'))
        s = '  orientation {: 8.5f} {: 8.5f} {: 8.5f} {: 8.5f}'.format(round(rot[0], 5), round(rot[1], 5), round(rot[2], 5), round(rot[3], 5))
        asciiLines.append(s)
        '''
        loc = obj.location
        s = '  position {: 8.5f} {: 8.5f} {: 8.5f}'.format(round(loc[0], 5), round(loc[1], 5), round(loc[2], 5))
        asciiLines.append(s)

        rot = nvb_utils.getAuroraRotFromObject(obj)
        s = '  orientation {: 8.5f} {: 8.5f} {: 8.5f} {: 8.5f}'.format(round(rot[0], 5), round(rot[1], 5), round(rot[2], 5), round(rot[3], 5))
        asciiLines.append(s)
        '''
        color = obj.nvb.wirecolor
        asciiLines.append('  wirecolor ' + str(round(color[0], 2)) + ' ' +
                                           str(round(color[1], 2)) + ' ' +
                                           str(round(color[2], 2)) )
        scale = round(nvb_utils.getAuroraScale(obj), 3)
        if (scale != 1.0):
            asciiLines.append('  scale ' + str(scale))


    @staticmethod
    def createAscii(obj, asciiLines):
        asciiLines.append('node ' + self.nodetype + ' ' + obj.name)
        self.createAsciiData(obj, asciiLines)
        asciiLines.append('endnode')



class Dummy(Node):
    """

    """
    def __init__(self, name = 'unnamed'):
        Node.__init__(self, name)
        self.nodetype  = 'dummy'

        self.dummytype = nvb_def.Dummytype.NONE


    def __eq__(self, other):
        if isinstance(other, Base):
            return (self.name == other.name) and (self.parent == other.parent)


    def __ne__(self, other):
        return not self.__eq__(self, other)


    def __str__(self):
        return 'node ' + self.nodetype + ' ' + self.name


    def loadAscii(self, asciiBlock):
        Node.loadAscii(self, asciiBlock)


    def createObjectData(self, obj):
         Node.createObjectData(self, obj)


    def createObject(self):
        """
        Returns an object for use in blender.
        """
        obj = bpy.data.objects.new(self.name, None)
        obj.nvb.order = self.objIdx

        self.objref = obj.name
        self.createObjectData(obj)
        return obj


class Patch(Node):
    '''
    Same as a plain Dummy.
    '''
    def __init__(self, name = 'UNNAMED'):
        GeometryNode.__init__(self, name)
        self.nodetype = 'patch'

        self.dummytype = nvb_def.Dummytype.PATCH


    def createObjectData(self, obj):
        Node.createObjectData(self, obj)

        obj.nvb.dummytype = self.dummytype


class Reference(Node):
    '''
    Contains a reference to another mdl
    '''
    def __init__(self, name = 'UNNAMED'):
        Node.__init__(self, name)
        self.nodetype = 'reference'

        self.dummytype    = nvb_def.Dummytype.REFERENCE
        self.refmodel     = nvb_def.null
        self.reattachable = 0


    def loadAscii(self, asciiNode):
        GeometryNode.parse(self, asciiNode)
        l_isNumber = nvb_utils.isNumber

        for line in asciiNode:
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue
            if not l_isNumber(label):
                if   (label == 'refmodel'):
                    #self.refmodel = line[1].lower()
                    self.refmodel = line[1]
                elif (label == 'reattachable'):
                    self.reattachable = int(line[1])


    def createObjectData(self, obj):
        Node.createObjectData(self, obj)
        obj.nvb.dummytype    = self.dummytype
        obj.nvb.refmodel     = self.refmodel
        obj.nvb.reattachable = (self.reattachable == 1)


    def createAsciiData(self, obj, asciiLines, exportObjects = [], classification = nvb_def.Classification.UNKNOWN, simple = False):
        Node.createAsciiData(self, obj, asciiLines, exportObjects, classification)
        asciiLines.append('  refmodel ' + obj.nvb.refmodel)
        asciiLines.append('  reattachable ' + str(int(obj.nvb.reattachable)))


class Trimesh(Node):
    def __init__(self, name = 'UNNAMED'):
        Node.__init__(self, name)
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
