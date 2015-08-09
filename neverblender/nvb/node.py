import neverblender.nvb.presets

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
            
    def from_object(self, object):
        pass
        
    def to_object(self):
        pass
        
    def from_ascii(self, asciiNode):
        for line in asciiNode:
            property = line[0]
            if   (property == 'node'):
                self.name = line[2].lower()
            elif (property == 'parent'):
                self.parent = line[1].lower()
            elif (property == 'position'):
                self.position = ( float(line[1]),
                                  float(line[2]),
                                  float(line[3]) )
            elif (property == 'orientation'):
                self.orientation = ( float(line[1]),
                                     float(line[2]),
                                     float(line[3]),
                                     float(line[4]) )
            elif (first_word == 'scale'):
                self.scale = float(line[1])
            elif (property == 'wirecolor'):
                self.wirecolor = ( float(line[1]),
                                   float(line[2]),
                                   float(line[3]) )


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
        self.verts           = []
        self.faces           = []
        self.tverts          = []
        
    def from_ascii(self, asciiNode):
        Dummy.from_ascii(self, asciiNode)
        for line in asciiNode:
            property = line[0]        
            if   (property == 'tilefade'): 
                self.tilefade = int(line[1])
            elif (property == 'render'):
                pass # TODO
            elif (property == 'shadow'):
                self.shadow = int(line[1])
            elif (property == 'beaming'):
                self.beaming = int(line[1])       
            elif (property == 'inheritcolor '):
                self.inheritcolor = int(line[1])        
            elif (property == 'rotatetexture'):
                 self.rotatetexture = int(line[1])         
            elif (property == 'alpha'): 
                self.alpha = float(line[1])       
            elif (property == 'transparencyhint'):
                 self.transparencyhint = int(line[1])
            elif (property == 'selfillumcolor'): # Self illumination color
                self.selfillumcolor = ( float(line[1]), 
                                        float(line[2]), 
                                        float(line[3]) )
            elif (property == 'ambient'): 
                self.ambient = ( float(line[1]), 
                                 float(line[2]), 
                                 float(line[3]) )
            elif (property == 'diffuse'): 
                self.diffuse = ( float(line[1]), 
                                 float(line[2]), 
                                 float(line[3]) )  
            elif (property == 'specular'):   
                self.specular = ( float(line[1]), 
                                  float(line[2]), 
                                  float(line[3]) )
            elif (property == 'shininess'): 
                self.shininess = int(float(line[1]))        
            elif (property == 'center'):
                pass # TODO # Unused ?
            elif (property == 'bitmap'): 
                self.bitmap = line[1] 
            elif (property == 'verts'): 
                pass # TODO 
            elif (property == 'faces'): 
                pass # TODO 
            elif (property == 'tverts'):
                pass # TODO             


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

    def from_ascii(self, asciiNode):
        Trimesh.from_ascii(self, asciiNode)


class Skinmesh(Trimesh):
    """
    Skinmeshes are Trimeshes where every vertex
    has a weight.
    """
    def __init__(self, name = 'UNNAMED'):
        Trimesh.__init__(self, name)
        
        self.weights = []

    def from_ascii(self, asciiNode):
        Trimesh.from_ascii(self, asciiNode)


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
        
    def from_ascii(self, asciiNode):
        Dummy.from_ascii(self, asciiNode)


class Light(Dummy):
    def __init__(self, name = 'UNNAMED'):
        Dummy.__init__(self, name)
        
        self.radius           = 5.0
        self.multiplier       = 1
        self.color            = (0.0, 0.0, 0.0)
        self.ambientonly      = 1
        self.ndynamictype     = 0 #unused ?
        self.isdynamic        = 0
        self.affectdynamic    = 0
        self.lightpriority    = 5
        self.fadinglight      = 1
        self.flareradius      = 1

    def from_ascii(self, asciiNode):
        Dummy.from_ascii(self, asciiNode)

        
class Aabb(Dummy):
    def __init__(self, name = 'UNNAMED'):
        Dummy.__init__(self, name)
        
        self.ambient        = (0.0, 0.0, 0.0)
        self.diffuse        = (0.0, 0.0, 0.0)
        self.specular       = (0.0, 0.0, 0.0)
        self.shininess      = 0       
        self.bitmap         = nvb.presets.null
        
     def from_ascii(self, asciiNode):
        Dummy.from_ascii(self, asciiNode)       