

class Dummy():
    """
    Basic node from which every other is derived
    """
    def __init__(self, name):
        self.name   = name
        self.parent = 'null'
        self.position    = (0.0, 0.0, 0.0)
        self.orientation = (0.0, 0.0, 0.0, 0.0)
        self.scale       = 1.0
        self.wirecolor   = (0.0, 0.0, 0.0) #Unused ?
        
    def from_object(self, object):
        pass
        
    def to_ascii(self):
        lines = []
        return lines


class Trimesh(Dummy):
    """
    Basic node from which every other is derived
    """
    def __init__(self, name):
        Dummy.__init__(self, name)
        
        self.center   = (0.0, 0.0, 0.0)
        self.tilefade = True
        self.render   = True
        self.shadow   = True
        self.beaming  = True
        self.inheritcolor     = 0  #Unused ?     
        self.alpha            = 1.0
        self.transparencyhint = 0
        self.selfillumcolor = (0.0, 0.0, 0.0)
        self.ambient        = (0.0, 0.0, 0.0)
        self.diffuse        = (0.0, 0.0, 0.0)
        self.specular       = (0.0, 0.0, 0.0)
        self.shininess      = 0       
        self.bitmap         = 'null'
        self.rotatetexture  = 0
        self.verts           = []
        self.faces           = []
        self.tverts          = []
        
    def to_ascii(self):
        lines = Dummy.to_ascii(self)
        return lines;


class Danglymesh(Trimesh):
    """
    Danglymeshes are Trimeshes with some additional
    parameters.
    """
    def __init__(self, name):
        Trimesh.__init__(self, name)
        
        self.period       = 1.0
        self.tightness    = 1.0
        self.displacement = 1.0


class Skinmesh(Trimesh):
    """
    Skinmeshes are Trimeshes where every vertex
    has a weight.
    """
    def __init__(self, name):
        Trimesh.__init__(self, name)
        
        self.weights = []


class Emitter(Dummy):
    def __init__(self, name):
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
        self.texture         = 'NULL'
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


class Light(Dummy):
    def __init__(self, name):
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

