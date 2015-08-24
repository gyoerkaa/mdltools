import neverblender.nvb.presets

def isNumber(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


class FaceList():
    def __init__(self):
        self.face = [] # int 3-tuple, vertex indices
        self.shgr = [] # int, shading group for this face
        self.texv = [] # int 3-tuple, texture vertex indices
        self.mat  = [] # int, material index


class Dummy():
    """
    Basic node from which every other is derived
    """
    def __init__(self, name = 'UNNAMED'):
        self.name   = name
        self.parent = nvb.presets.null
        self.position    = (0.0, 0.0, 0.0)
        self.orientation = (0.0, 0.0, 0.0, 0.0)
        self.scale       = 1.0
        self.wirecolor   = (0.0, 0.0, 0.0) #Unused ?

    def __eq__(self, other):
        if isinstance(other, Dummy):
            return self.name == other.name

    def fromAscii(self, asciiNode):
        lfloat = float
        for line in asciiNode:
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue

            if not isNumber(label):
                if   (label  == 'node'):
                    self.name = line[2].lower()
                elif (label  == 'parent'):
                    self.parent = line[1].lower()
                elif (label  == 'position'):
                    self.position = (lfloat(line[1]),
                                     lfloat(line[2]),
                                     lfloat(line[3]) )
                elif (label  == 'orientation'):
                    self.orientation = (lfloat(line[1]),
                                        lfloat(line[2]),
                                        lfloat(line[3]),
                                        lfloat(line[4]) )
                elif (label  == 'scale'):
                    self.scale = lfloat(line[1])
                elif (label  == 'wirecolor'):
                    self.wirecolor = (lfloat(line[1]),
                                      lfloat(line[2]),
                                      lfloat(line[3]) )

    def toBlender(self):
        pass


class Trimesh(Dummy):
    """
    Basic node from which every other is derived
    """
    def __init__(self, name = 'UNNAMED'):
        Dummy.__init__(self, name)

        self.center   = (0.0, 0.0, 0.0) # Unused ?
        self.tilefade = True
        self.render   = True
        self.shadow   = True
        self.beaming  = True
        self.inheritcolor     = 0  # Unused ?
        self.alpha            = 1.0
        self.transparencyhint = 0
        self.selfillumcolor = (0.0, 0.0, 0.0)
        self.ambient        = (0.0, 0.0, 0.0)
        self.diffuse        = (0.0, 0.0, 0.0)
        self.specular       = (0.0, 0.0, 0.0)
        self.shininess      = 0
        self.bitmap         = nvb.presets.null
        self.rotatetexture  = 0
        self.verts          = []
        self.faces          = FaceList()
        self.tverts         = []

    def fromAscii(self, asciiNode):
        Dummy.fromAscii(self, asciiNode)
        lint   = int
        lfloat = float
        for idx, line in enumerate(asciiNode):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue

            if not isNumber(label):
                if   (label == 'tilefade'):
                    self.tilefade = lint(line[1])
                elif (label == 'render'):
                    pass # TODO
                elif (label == 'shadow'):
                    self.shadow = lint(line[1])
                elif (label == 'beaming'):
                    self.beaming = lint(line[1])
                elif (label == 'inheritcolor '):
                    self.inheritcolor = lint(line[1])
                elif (label == 'rotatetexture'):
                     self.rotatetexture = lint(line[1])
                elif (label == 'alpha'):
                    self.alpha = lfloat(line[1])
                elif (label == 'transparencyhint'):
                     self.transparencyhint = lint(line[1])
                elif (label == 'selfillumcolor'): # Self illumination color
                    self.selfillumcolor = (lfloat(line[1]),
                                           lfloat(line[2]),
                                           lfloat(line[3]) )
                elif (label == 'ambient'):
                    self.ambient = (lfloat(line[1]),
                                    lfloat(line[2]),
                                    lfloat(line[3]) )
                elif (label == 'diffuse'):
                    self.diffuse = (lfloat(line[1]),
                                    lfloat(line[2]),
                                    lfloat(line[3]) )
                elif (label == 'specular'):
                    self.specular = (lfloat(line[1]),
                                     lfloat(line[2]),
                                     lfloat(line[3]) )
                elif (label == 'shininess'):
                    self.shininess = lint(lfloat(line[1]))
                elif (label == 'center'):
                    pass # TODO # Unused ?
                elif (label == 'bitmap'):
                    self.bitmap = line[1]
                elif (label == 'verts'):
                    numVals = lint(line[1])
                    self.getAsciiVerts(asciiNode[idx+1:idx+numVals])
                elif (label == 'faces'):
                    numVals = lint(line[1])
                    self.getAsciiFaces(asciiNode[idx+1:idx+numVals])
                elif (label == 'tverts'):
                    numVals = lint(line[1])
                    self.getAsciiTexVerts(asciiNode[idx+1:idx+numVals])

    def getAsciiVerts(self, asciiVerts):
        lfloat = float
        for line in asciiVerts:
            self.verts.append( (lfloat(line[0]), lfloat(line[1]), lfloat(line[2])) )

    def getAsciiFaces(self, asciiFaces):
        lint = int
        for line in asciiFaces:
            self.faces.face.append( (lint(line[0]), lint(line[1]), lint(line[2])) )
            self.faces.shgr.append(lint(line[3]))
            self.faces.texv.append( (lint(line[4]), lint(line[5]), lint(line[6])) )
            self.faces.mat.append(lint(line[7]))

    def getAsciiTexVerts(self, asciiTexVerts):
        lfloat = float
        for line in asciiTexVerts:
            self.tverts.append( (lfloat(line[0]), lfloat(line[1])) )


class Danglymesh(Trimesh):
    """
    Danglymeshes are Trimeshes with some additional
    parameters.
    """
    def __init__(self, name = 'UNNAMED'):
        Trimesh.__init__(self, name)

        self.period       = 1.0
        self.tightness    = 1.0
        self.displacement = 1.0

        self.constraints  = []

    def fromAscii(self, asciiNode):
        Trimesh.fromAscii(self, asciiNode)
        lint   = int
        lfloat = float
        for idx, line in enumerate(asciiNode):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue

            if not isNumber(label):
                if   (label == 'period'):
                    self.tilefade = lfloat(line[1])
                elif (label == 'tightness'):
                    self.tilefade = lfloat(line[1])
                elif (label == 'displacement'):
                    self.tilefade = lfloat(line[1])
                elif (label == 'constraints'):
                    numVals = lint(line[1])
                    self.getAsciiConstraints(asciiNode[idx+1:idx+numVals])

    def getAsciiConstraints(self, asciiConstraints):
        lfloat = float
        for line in asciiConstraints:
            self.constraints.append(lfloat(line[0]))


class Skinmesh(Trimesh):
    """
    Skinmeshes are Trimeshes where every vertex
    has a weight.
    """
    def __init__(self, name = 'UNNAMED'):
        Trimesh.__init__(self, name)

        self.weights = []

    def fromAscii(self, asciiNode):
        Trimesh.fromAscii(self, asciiNode)
        lint   = int
        for idx, line in enumerate(asciiNode):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue

            if not isNumber(label):
                if (label == 'weights'):
                    numVals = lint(line[1])
                    self.getAsciiWeights(asciiNode[idx+1:idx+numVals])
                    break #Only one value here, abort loop when read

    def getAsciiWeights(self, asciiWeights):
        lfloat = float
        lchunker = chunker
        for line in asciiWeights:
            # A line looks like this
            # [group_name, vertex_weight, group_name, vertex_weight]
            # We create a list looking like this:
            # [[group_name, vertex_weight], [group_name, vertex_weight]]
            memberships = []
            for chunk in lchunker(line, 2):
                memberships.append( [chunk[0], lfloat(chunk[1])] )

            self.weights.append(memberships)


class Emitter(Dummy):
    def __init__(self, name = 'UNNAMED'):
        Dummy.__init__(self, name)

        self.affectedbywind  = 0.0
        self.m_isitinted     = False
        self.bounce          = 0
        self.random          = 0
        self.inherit         = True
        self.inheritvel      = 0
        self.inherit_local   = 0
        self.inherit_part    = 0
        self.splat           = 0
        self.renderorder     = 0
        self.spawntype       = 0
        self.update          = 1
        self.render          = 0
        self.blend           = 1
        self.texture         = nvb.presets.null
        self.chunkname       = ''
        self.xgrid           = 5
        self.ygrid           = 5
        self.loop            = 0
        self.deadspace       = 0.0
        self.twosidedtex     = 0
        self.blastradius     = 0
        self.blastlength     = 0
        self.colorstart      = (1.0, 1.0, 1.0)
        self.colorend        = (1.0, 1.0, 1.0)
        self.alphastart      = 1.0
        self.alphaend        = 1.0
        self.sizestart       = 1.0
        self.sizeend         = 1.0
        self.sizestart_y     = 0.0
        self.sizeend_y       = 0.0
        self.framestart      = 0
        self.frameend        = 30
        self.birthrate       = 10
        self.lifeexp         = 3.0
        self.mass            = 0.0
        self.spread          = 1.0
        self.particlerot     = 0.0
        self.velocity        = 1.0
        self.randvel         = 0.0
        self.fps             = 10
        self.xsize           = 100
        self.ysize           = 100
        self.bounce_co       = 0.0
        self.blurlength      = 10.0
        self.lightningdelay  = 0.0
        self.lightningradius = 0.0
        self.lightningsubdiv = 0
        self.lightningscale  = 0.0
        self.combinetime     = 0.0
        self.drag            = 0.0
        self.grav            = 0.0
        self.threshold       = 0.0
        self.p2p             = 0
        self.p2p_sel         = 1
        self.p2p_bezier2     = 0.0
        self.p2p_bezier3     = 0.0

    def fromAscii(self, asciiNode):
        Dummy.fromAscii(self, asciiNode)
        #TODO


class Light(Dummy):
    def __init__(self, name = 'UNNAMED'):
        Dummy.__init__(self, name)

        self.radius           = 5.0
        self.multiplier       = 1
        self.color            = (0.0, 0.0, 0.0)
        self.ambientonly      = 1
        self.ndynamictype     = 1
        self.isdynamic        = 1
        self.affectdynamic    = 1
        self.lightpriority    = 5
        self.fadinglight      = 1
        self.flareradius      = 1

    def fromAscii(self, asciiNode):
        Dummy.fromAscii(self, asciiNode)
        lint   = int
        lfloat = float

        for idx, line in enumerate(asciiNode):
            try:
                label = line[0].lower()
            except IndexError:
                # Probably empty line or whatever, skip it
                continue

            if not isNumber(label):
                if (label == 'radius'):
                    self.radius = lfloat(line[1])

                elif (label == 'multiplier'):
                    self.multiplier = lfloat(line[1])

                elif (label == 'color'):
                    self.color = ( lfloat(line[1]),
                                   lfloat(line[2]),
                                   lfloat(line[3]) )

                elif (label== 'ambientonly'):
                     self.ambientonly = lint(line[1])

                elif (label == 'ndynamictype'):
                    self.ndynamictype = lint(line[1])

                elif (label == 'isdynamic'):
                    self.isdynamic = lint(line[1])

                elif (label == 'flareradius'):
                    self.flareradius = lint(line[1])

                elif (label == 'affectdynamic'):
                    pself.affectdynamic = lint(line[1])

                elif (label == 'lightpriority'):
                    self.lightpriority = lint(line[1])

                elif (label == 'fadinglight'):
                    self.fadinglight = lint(line[1])


class Aabb(Trimesh):
    '''
    No need to import Aaabb's. Aabb nodes in mdl files will be
    treated as trimeshes
    '''
    def __init__(self, name = 'UNNAMED'):
        Trimesh.__init__(self, name)

     def fromAscii(self, asciiNode):
        Trimesh.fromAscii(self, asciiNode)
